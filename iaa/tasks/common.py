from kotonebot import logging
from kotonebot.backend.core import HintBox
from kotonebot import device, Loop, action, color
from kotonebot.util import Throttler, Countdown

from . import R
from iaa.context import task_reporter

logger = logging.getLogger(__name__)

@action('是否位于首页')
def at_home() -> bool:
    return R.Hud.IconCrystal.find() is not None

@action('返回首页', screenshot_mode='manual')
def go_home(threshold_timeout: float = 0):
    rep = task_reporter()
    rep.message('正在返回首页')
    logger.info('Try to go home.')
    th = Throttler(1)
    cd = Countdown(threshold_timeout)
    for _ in Loop():
        if R.Hud.ButtonLive.find():
            cd.start()
            logger.debug('Crystal icon found.')
            # 因为进入游戏后，公告弹窗会延迟弹出，因此不可以立即返回
            # 必须等待一段时间，关掉公告后再返回
            if cd.expired():
                logger.info('Now at home.')
                break
        elif R.Hud.ButtonGoBack.try_click():
            logger.debug('Go back button found and clicked.')
        else:
            cd.reset()

        if th.request():
            device.click(1, 367)

def has_red_dot(box: HintBox) -> bool:
    return color.find('#ff5589', rect=box) is not None
