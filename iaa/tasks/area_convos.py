import logging

from kotonebot import device, task, sleep

from . import R
from ._fragments import scan_area
from .common import at_home, go_home
from iaa.context import task_reporter
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
        rep.message('扫描中')
        convos = R.Map.IconNewAreaConvo.find_all()
        for c in convos:
            rep.message('阅读剧情')
            c.click()
            sleep(0.1)
            skip_stories(mode='skip', end_condition=at_home)
    logger.info('Current area unread conversations cleared.')


@task('地图对话', screenshot_mode='manual')
def area_convos():
    go_home()
    sleep(1) # 等待聚焦动画结束
    _clear()
    return