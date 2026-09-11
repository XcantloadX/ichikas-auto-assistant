import logging

from kotonebot import device, task, sleep

from . import R
from ._fragments import scan_area
from .common import at_home, go_home
from iaa.context import task_reporter
from iaa.i18n import TStr
from .story._common import skip_stories

logger = logging.getLogger(__name__)

def _navigate():
    pass

def _clear():
    """
    清理区域里的对话

    前置：位于某区域\n
    结束：不变
    """
    rep = task_reporter()
    for _ in scan_area(step_scale=0.2):
        rep.message(TStr(zh_CN='扫描中', en_US='Scanning'))
        while convo := R.Map.IconNewAreaConvo.q(threshold=0.75).find():
            rep.message(TStr(zh_CN='阅读剧情', en_US='Reading story'))
            convo.click()
            logger.debug('Clicked unread area conversation at %s.', convo.rect)
            if R.Story.ButtonStoryMenu.try_wait(timeout=30, interval=0.2) is None:
                logger.warning('Story menu did not appear after area conversation click.')
                break
            logger.debug('Story menu appeared after area conversation click.')
            skip_stories(mode='skip', end_condition=at_home)
            sleep(0.5)
            device.screenshot()
    logger.info('Current area unread conversations cleared.')


@task('地图对话', screenshot_mode='manual')
def area_convos():
    go_home()
    sleep(1) # 等待聚焦动画结束
    _clear()
    return
