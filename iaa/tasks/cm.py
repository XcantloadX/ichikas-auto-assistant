import time
from typing import Callable

from kotonebot import logging
from kotonebot.core import AnyOf
from kotonebot import device, task, Loop, action, sleep

from . import R
from .common import go_home
from iaa.definitions.consts import package_name
from iaa.context import conf as get_conf, task_reporter, server
from iaa.i18n import TStr

logger = logging.getLogger(__name__)

def _sleep(sec: float, msg: 'Callable[[int], TStr] | None' = None, interval: float = 1):
    """带有任务消息更新的 sleep。

    :param sec: 睡眠总时长，单位秒
    :param msg: 接受剩余秒数并返回 TStr 的函数，defaults to None
    :param interval: 检查间隔，单位秒， defaults to 1
    """
    rp = task_reporter()
    logger.debug(f'Sleeping for {sec} seconds.')
    start_time = time.time()
    while time.time() - start_time < sec:
        if msg is not None:
            rp.message(msg(max(0, int(sec - (time.time() - start_time)))))
        sleep(interval)

@action('是否位于交叉路口')
def is_at_intersection() -> bool:
    # return AnyOf[
    #     R.Scene.Intersection.BuildingLogo,
    #     R.Scene.Intersection.IconCm
    # ].find(threshold=0.8) is not None
    return (
        R.Scene.Intersection.BuildingLogo.q(threshold=0.9).find() is not None or
        R.Scene.Intersection.IconCm.q(threshold=0.9).find() is not None
    )

@action('前往交叉路口', screenshot_mode='manual')
def go_intersection():
    """
    前置：位于首页\n
    结束：位于交叉路口
    """
    logger.info('Going to intersection.')
    device.screenshot()
    if is_at_intersection():
        logger.info('Now at intersection.')
        return
    # 打开地图
    for _ in Loop(interval=0.6):
        if R.Map.ButtonOpenMap.try_click():
            logger.debug('Clicked open map button.')
            sleep(0.5)
        elif R.Map.ButtonGoToReality.try_click():
            logger.info('Now at Sekai map. Changing to real world.')
            sleep(0.5)
        elif R.Map.ButtonGoToSekai.find():
            logger.debug('Now at real world map.')
            break
    # 进入交叉路口
    device.screenshot()
    swipe_count = 0
    MAX_SWIPE_COUNT = 5
    for _ in Loop(interval=0.6):
        if R.Map.Intersection.try_click():
            logger.debug('Clicked intersection on map.')
        elif is_at_intersection():
            logger.debug('Now at intersection.')
            break
        else:
            # 重置视图到右下角
            device.swipe_scaled(x1=0.7, x2=0.4, y1=0.5, y2=0.5)
            swipe_count += 1
            if swipe_count >= MAX_SWIPE_COUNT:
                logger.debug('Reached max swipe count but still not found. Stop.')
                return

@action('打开 CM 界面', screenshot_mode='manual')
def open_cm() -> bool:
    """
    前置：位于交叉路口\n
    结束：位于 CM 弹窗

    :returns: 是否成功打开 CM 界面。若为 False，原因是今天的广告都看完了。
    """
    logger.info('Opening CM.')
    swipe_count = 0
    MAX_SWIPE_COUNT = 5
    for _ in Loop(interval=0.6):
        if ret := R.Scene.Intersection.IconCm.q(threshold=0.6).find():
            # TODO: 改用 image.find 的 rect 参数重构
            x1, y1, x2, y2 = R.Cm.BoxCmIconDetectRect.xyxy
            x, y = ret.rect.center
            if x1 < x < x2 and y1 < y < y2:
                logger.debug('CM icon is in the detection area.')
                device.click(x, y)
                logger.debug('Clicked CM icon.')
                continue
            sleep(0.4)
        elif R.Cm.ButtonPlayCm.find():
            logger.debug('Now at CM.')
            return True
        
        # 向左滑
        device.swipe_scaled(x1=0.7, x2=0.4, y1=0.5, y2=0.5)
        logger.debug('Swiped left.')
        swipe_count += 1
        if swipe_count >= MAX_SWIPE_COUNT:
            logger.debug('Reached max swipe count but still not found. Stop.')
            return False
    return False

@action('看广告', screenshot_mode='manual')
def clear_common_cm():
    """
    前置：已经在 CM 弹窗\n
    结束：位于交叉路口
    """
    logger.info('Clearing CM.') 
    rep = task_reporter()
    d = device.of_android()
    current_server = server()
    def _en_ad_started() -> bool:
        if current_server != 'en':
            return False
        try:
            if device.commands.current_package() != package_name():
                return True
            activity = d.commands.adb_shell('dumpsys activity activities | grep ResumedActivity')
        except Exception:
            logger.exception('Failed to check foreground ad activity.')
            return False
        return package_name() in activity and 'MessagingUnityPlayerActivity' not in activity

    def _find_reward_text():
        if current_server == 'en':
            return AnyOf[
                R.Cm.TextAwardClaimed,
                R.Cm.TextApRecovered,
                R.Cm.TextAutoPlayLimitIncreased
            ].find()
        return AnyOf[
            R.Cm.TextAwardClaimed,
            R.Cm.TextApRecovered
        ].find()

    def _dismiss_reward_text(reward_text) -> None:
        if current_server == 'en':
            if getattr(reward_text, 'prefab', None) is R.Cm.TextAwardClaimed:
                # EN claimed-reward popups can put item art at screen center. Tap the text line instead.
                x, y = reward_text.rect.center
                tap_x, tap_y = int(x + 80), int(y)
            else:
                tap_x, tap_y = 1000, 600
            logger.info('Dismissing EN CM reward toast at (%s, %s).', tap_x, tap_y)
            device.click(tap_x, tap_y)
            sleep(0.5)
            for _ in range(10):
                device.screenshot()
                if _find_reward_text() is None:
                    return
                sleep(0.2)
            logger.debug('Reward toast still visible after dismiss click.')
        else:
            device.click_center() # 关闭奖励领取提示

    state: int = 1 # 1=开始看，2=载入，3=正在看，4=等结果
    wait_sec = get_conf().cm.watch_ad_wait_sec
    for _ in Loop(interval=0.6):
        if state == 1:
            if current_server == 'en':
                if _en_ad_started():
                    state = 3
                    continue
                device.screenshot()
                if reward_text := _find_reward_text():
                    logger.info('Reward toast is still visible. Dismissing before starting next ad.')
                    _dismiss_reward_text(reward_text)
                    continue
            # 开始看
            if current_server != 'en' and R.Cm.ButtonCmStart.q(threshold=0.7).try_click():
                logger.debug('Clicked 視聴開始 button.')
                sleep(1)
                state = 2
            elif R.Cm.ButtonPlayCm.try_click():
                rep.message(TStr(zh_CN='播放广告', en_US='Playing ad'))
                logger.debug('Clicked CM start button.')
                sleep(1)
                if current_server == 'en':
                    state = 1
                    for _ in range(10):
                        if _en_ad_started():
                            logger.info('Ad activity detected after CM start click.')
                            state = 3
                            break
                        device.screenshot()
                        if R.Cm.ButtonPlayCm.q(threshold=0.7).find() is None:
                            state = 2
                            break
                        sleep(0.5)
            # 没有剩余广告了
            else:
                if not R.Hud.ButtonGoBack.exists():
                    logger.info('All ads cleared.')
                    break
        elif state == 2:
            if current_server == 'en':
                if _en_ad_started():
                    logger.info('Ad activity detected while waiting for ad load.')
                    state = 3
                    continue
            if R.Cm.ButtonPlayCm.q(threshold=0.7).find():
                rep.message(TStr(zh_CN='等待广告载入', en_US='Waiting for ad to load'))
                logger.debug('Loading ad...')
                sleep(0.2)
            else:
                rep.message(TStr(zh_CN='等待广告结束', en_US='Waiting for ad to finish'))
                logger.info(f'Ad loaded. Wait {wait_sec} sec.')
                state = 3
        elif state == 3:
            _sleep(wait_sec, msg=lambda s: TStr(zh_CN=f'等待广告结束，剩余 {s} 秒', en_US=f'Waiting for ad to end, {s}s remaining'))
            logger.debug('Wait ad finished.')
            if current_server == 'en' and _en_ad_started():
                device.screenshot()
                if R.Cm.Ad1.ButtonClose.q(threshold=0.69).try_click():
                    logger.info('Closed EN ad through the provider exit button.')
                    sleep(1)
                    state = 4
                    continue
            # 返回桌面再重新打开游戏就可以关闭广告
            d.commands.adb_shell('input keyevent KEYCODE_HOME')
            sleep(0.5)
            d.launch_app(package_name())
            sleep(0.5)
            logger.debug('Ad skipped.')
            state = 4
        elif state == 4:
            if current_server == 'en':
                device.screenshot()
            # 由于广告没放完就点了跳过导致领取奖励失败
            if R.Cm.TextCmFailed.find():
                logger.info('Ad play failed due to early skip.')
                device.click(1, 1) # 关闭弹窗
                sleep(0.5)
                state = 1
            # 看完了
            elif award_text := _find_reward_text():
                logger.info('Ad award claimed.')
                _dismiss_reward_text(award_text)
                rep.message(TStr(zh_CN='奖励已领取', en_US='Reward claimed'))
                state = 1
            # Applovin 广告特判
            elif (current_server != 'en' or _en_ad_started()) and R.Cm.Ad1.ButtonClose.try_click():
                logger.info('Close button clicked. (Applovin/GP ad?)')
                sleep(1)
                state = 1
            elif (current_server != 'en' or _en_ad_started()) and R.Cm.Ad1.ButtonSkip.q(threshold=0.7).try_click():
                logger.info('Skip button clicked. (Applovin/GP ad?)')
                sleep(1)
            # GooglePlay App 广告特判：
            # 点击 skip 按钮后会自动跳转到商店页面，需要跳过回来
            elif device.commands.current_package() != package_name():
                logger.info('Returning to game from ad. (GP ad?)')
                # device.commands.launch_app(package_name())
                # 有些广告，调用 launch_app 会触发重新播放，导致无限循环
                device.commands.adb_shell('am force-stop com.android.vending')
                sleep(1)
            # 还在加载
            else:
                rep.message(TStr(zh_CN='等待结果', en_US='Waiting for result'))
                logger.debug('Waiting for result...')

@task('看广告', screenshot_mode='manual')
def cm():
    """
    看广告并领取奖励。包括演出积分/心愿结晶、活动货币、两次 AP 恢复、两次礼物、水晶、音乐商店。
    """
    if server() == 'cn':
        logger.info('CM task is not supported on CN server.')
        return
    go_home()
    rep = task_reporter()
    rep.message(TStr(zh_CN='正在前往交叉路口', en_US='Going to Scramble Crossing'))
    go_intersection()
    rep.message(TStr(zh_CN='正在打开 CM 界面', en_US='Opening CM screen'))
    if open_cm():
        clear_common_cm()
    else:
        logger.info('No ads available.')
