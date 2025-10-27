from kotonebot import device, image, task, Loop, action, sleep, color
from kotonebot import logging
from kotonebot.util import Throttler, Countdown

from kotonebot.backend.core import HintBox

from . import R
from ._fragments import handle_data_download

logger = logging.getLogger(__name__)

@action('是否位于首页')
def at_home() -> bool:
    return image.find(R.Hud.IconCrystal) is not None

@action('返回首页', screenshot_mode='manual')
def go_home(threshold_timeout: float = 0):
    logger.info('Try to go home.')
    th = Throttler(1)
    cd = Countdown(threshold_timeout)
    for _ in Loop():
        if image.find(R.Hud.IconCrystal):
            cd.start()
            logger.debug('Crystal icon found.')
            # 因为进入游戏后，公告弹窗会延迟弹出，因此不可以立即返回
            # 必须等待一段时间，关掉公告后再返回
            if cd.expired():
                logger.info('Now at home.')
                break
        else:
            cd.reset()
        # 有新需要数据下载
        if handle_data_download():
            continue

        if th.request():
            device.click(1, 1)

def has_red_dot(box: HintBox) -> bool:
    return color.find('#ff5589', rect=box) is not None