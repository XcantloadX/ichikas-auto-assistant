from typing import Literal

from kotonebot import logging
from kotonebot import device, image, task, Loop, action, sleep, color

from .. import R

logger = logging.getLogger(__name__)

def ensure_list_view():
    """
    确保位于列表视图。

    前置：位于选歌界面
    结束：位于选歌界面的列表视图
    """
    if R.Live.ButtonToListView.try_click():
        logger.info('Switched to list view.')

@action('选曲.下一首', screenshot_mode='manual')
def next_song(ensure_unlocked: bool = True):
    """
    选中下一首歌曲。

    前置：位于选歌界面\n
    结束：仍在选歌界面

    :param ensure_unlocked: 是否确保选中歌曲已解锁。\n
    """
    device.screenshot()
    # 首先确保是列表视图
    ensure_list_view()
    device.click(R.Live.PointNextSong)
    logger.debug('Clicked next song button.')
    sleep(0.3)
    if ensure_unlocked:
        logger.warning('Ensure unlocked is not implemented yet.')
    # if ensure_unlocked:
    #     for _ in Loop():
    #         if image.find(R.Live.ButtonDecide, colored=True):
    #             break
    #         logger.debug('Current song is locked. Go next.')
    #         device.click(R.Live.PointNextSong)
            
    logger.info('Next song selected.')


