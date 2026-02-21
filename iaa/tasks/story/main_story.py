import time
import logging
from itertools import count

from kotonebot import device, task, Loop, sleep

from .. import R
from ..common import go_home
from ._common import enter_story, skip_stories

logger = logging.getLogger(__name__)

def _go_list():
    """
    前往主线剧情列表

    前置：-\n
    结束：主线剧情列表
    """
    go_home()
    for _ in Loop():
        if R.Story.ImageMainStory.try_click():
            pass
        elif R.Hud.ButtonStory.try_click():
            pass
        elif R.Story.StoryList.ButtonExpandUnit.find():
            break

def _filter_unread():
    """
    设置为过滤未读剧情

    前置：主线剧情列表
    结束：主线剧情列表，且已过滤未读剧情
    """
    for _ in Loop():
        # 等过滤弹窗展示
        if R.Story.StoryList.ButtonConfirmFilter.find():
            break
        # 打开过滤弹窗
        elif R.Story.StoryList.ButtonFilter.try_click():
            pass
    clicked = False
    for _ in Loop():
        # 选择只展示未读剧情
        if not clicked and R.Story.StoryList.RadioUnread.try_click():
            clicked = True
        # 确认过滤弹窗
        elif R.Story.StoryList.ButtonConfirmFilter.try_click():
            pass
        # 等弹窗关闭
        elif R.Story.StoryList.ButtonFilter.find():
            break

def _farm_single():
    """
    刷单个剧情

    前置：主线剧情列表，且已过滤未读剧情
    结束：主线剧情列表，且已过滤未读剧情
    """
    # 进入分集列表
    for _ in Loop():
        if R.Story.StoryList.ButtonEnter.try_click():
            pass
        elif R.Story.ButtonBookmark.exists():
            break
    # 刷剧情
    enter_story()
    def _end():
        # 处理 MV 播放（主线剧情）
        if R.Story.TextMvPausedDialog.exists():
            R.Story.ButtonSkipMv.try_click()
            return False
        return R.Story.ButtonBookmark.exists()
    skip_stories(
        mode='read',
        end_condition=_end
    )
    # 返回列表
    R.Story.ButtonGoBack.wait().click()

def _select_next():
    """
    选择下一个剧情

    前置：主线剧情列表
    结束：主线剧情列表
    """
    # 先等到返回列表页面
    R.Story.StoryList.ButtonExpandUnit.wait()
    # 再点下一个
    device.click(R.Story.StoryList.PointNext)
    sleep(0.2)

@task('刷剧情')
def farm_story():
    _go_list()
    _filter_unread()
    for i in count(1):
        start_time = time.time()
        logger.info(f'Farming story, starting {i}/∞.')
        _farm_single()
        logger.info(f'Farming story, finished {i}/∞. Took {time.time() - start_time:.2f}s.')