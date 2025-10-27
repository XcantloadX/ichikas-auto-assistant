from kotonebot import logging
from kotonebot import device, image, task, Loop, action, sleep

from . import R
from .common import go_home
from iaa.consts import PACKAGE_NAME_JP

logger = logging.getLogger(__name__)
WATCH_AD_WAIT_SEC = 70

@action('是否位于交叉路口')
def is_at_intersection() -> bool:
    return image.find_multi([
        R.Scene.Intersection.BuildingLogo,
        R.Scene.Intersection.IconCm
    ], threshold=0.8) is not None

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
        if image.find(R.Map.ButtonOpenMap):
            device.click()
            logger.debug('Clicked open map button.')
            sleep(0.5)
        elif image.find(R.Map.ButtonGoToReality):
            logger.info('Now at Sekai map. Changing to real world.')
            device.click()
            sleep(0.5)
        elif image.find(R.Map.ButtonGoToSekai):
            logger.debug('Now at real world map.')
            break
    # 进入交叉路口
    device.screenshot()
    swipe_count = 0
    MAX_SWIPE_COUNT = 5
    for _ in Loop(interval=0.6):
        if image.find(R.Map.Intersection):
            device.click()
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
        if ret := image.find(R.Scene.Intersection.IconCm, threshold=0.6):
            # TODO: 改用 image.find 的 rect 参数重构
            x1, y1, x2, y2 = R.Cm.BoxCmIconDetectRect.xyxy
            x, y = ret.position
            if x1 < x < x2 and y1 < y < y2:
                logger.debug('CM icon is in the detection area.')
                device.click()
                logger.debug('Clicked CM icon.')
            sleep(0.4)
        elif image.find(R.Cm.ButtonPlayCm):
            logger.debug('Now at CM.')
            return True
        else:
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
    d = device.of_android()
    state: int = 1 # 1=开始看，2=载入，3=正在看，4=等结果
    for _ in Loop(interval=0.6):
        if state == 1:
            # 开始看
            if image.find(R.Cm.ButtonCmStart, threshold=0.7):
                device.click()
                logger.debug('Clicked 視聴開始 button.')
                sleep(1)
                state = 2
            elif image.find(R.Cm.ButtonPlayCm):
                device.click()
                logger.debug('Clicked CM start button.')
                sleep(0.2)
            # 没有剩余广告了
            else:
                logger.info('All ads cleared.')
                break
        elif state == 2:
            if image.find(R.Cm.ButtonPlayCm, threshold=0.7):
                logger.debug('Loading ad...')
                sleep(0.2)
            else:
                logger.info(f'Ad loaded. Wait {WATCH_AD_WAIT_SEC} sec.')
                state = 3
        elif state == 3:
            sleep(WATCH_AD_WAIT_SEC)
            logger.debug('Wait ad finished.')
            # 返回桌面再重新打开游戏就可以关闭广告
            d.commands.adb_shell('input keyevent KEYCODE_HOME')
            sleep(0.5)
            d.launch_app(PACKAGE_NAME_JP)
            sleep(0.5)
            logger.debug('Ad skipped.')
            state = 4
        elif state == 4:
            # 由于广告没放完就点了跳过导致领取奖励失败
            if image.find(R.Cm.TextCmFailed):
                logger.info('Ad play failed due to early skip.')
                device.click(1, 1) # 关闭弹窗
                sleep(0.5)
                state = 1
            # 看完了
            elif image.find_multi([
                R.Cm.TextAwardClaimed,
                R.Cm.TextApRecovered
            ]):
                logger.info('Ad award claimed.')
                device.click_center() # 关闭奖励领取提示
                state = 1
            # 还在加载
            else:
                logger.debug('Waiting for result...')

@task('看广告', screenshot_mode='manual')
def cm():
    """
    看广告并领取奖励。包括演出积分/心愿结晶、活动货币、两次 AP 恢复、两次礼物、水晶、音乐商店。
    """
    go_home()
    go_intersection()
    if open_cm():
        clear_common_cm()
    else:
        logger.info('No ads available.')
