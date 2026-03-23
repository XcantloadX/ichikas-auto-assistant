from typing import Literal, Callable
from typing_extensions import assert_never

from kotonebot import action, Loop, device, sleep
from kotonebot import logging

from .. import R

logger = logging.getLogger(__name__)

SkipMode = Literal['skip', 'read']

@action('进入剧情阅读')
def enter_story(*, is_wl: bool = False):
    """
    前置：位于剧情列表界面\n
    结束：剧情阅读界面

    :param is_wl: 是否是为 WorldLink 当期活动剧情
    """
    for _ in Loop():
        if R.Story.ButtonStoryMenu.find():
            # 位于剧情画面
            logger.info('Now at story.')
            break
        elif R.Story.CheckboxContinuousReading.q(threshold=0.98).find():
            # threshold 0.98 是因为更低会命中未选中状态
            # TODO: 需要一个更好的区别方式
            # 勾选连续阅读
            device.click()
            logger.debug('Clicked continuous reading checkbox.')
            sleep(0.4)
        elif R.Story.ButtonWithoutVoice.try_click():
            # 选择无语音模式
            logger.debug('Clicked without voice button.')
            sleep(0.4)
        else:
            # 尝试点进最上面一话
            if is_wl:
                device.click(R.Story.PointFirstEpisodeWl)
            else:
                device.click(R.Story.PointFirstEpisode)

@action('跳过剧情')
def skip_stories(mode: SkipMode = 'skip', *, end_condition: Callable[[], bool]):
    """
    跳过剧情。同时支持单集阅读模式与连续阅读模式。
    
    前置：位于剧情阅读界面\n
    结束：剧情列表界面

    :param mode: 跳过模式，可选值为 'skip'（跳过）, 'read'（连点跳过）。
    """
    for _ in Loop(interval=0.5):
        if R.Story.ButtonStoryMenu.try_click():
            logger.debug('Clicked story menu button.')
        elif R.CommonDialog.TextAwardClaimedOk.find():
            # 奖励领取
            logger.debug('Found award claimed dialog.')
            if R.CommonDialog.ButtonAwardClaimedOk.try_click():
                logger.debug('Clicked award claimed ok button.')
        elif end_condition():
            logger.info('Skip stories (skip mode) finished.')
            break
        else:
            # 跳过处理
            match mode:
                case 'skip':
                    # 跳过模式
                    if R.Story.ButtonReadNext.try_click():
                        logger.debug('Clicked read next button.')
                    elif R.Story.ButtonSkipStory.try_click():
                        logger.debug('Clicked skip button (last episode).')
                    elif R.Story.ButtonIconSkip.try_click():
                        logger.debug('Clicked skip button.')
                case 'read':
                    # 连点器模式
                    for _ in Loop():
                        for __ in range(10):
                            device.click_center()
                            sleep(0.1)
                        if end_condition():
                            logger.info('Skip stories (read mode) finished.')
                            return
                case _:
                    assert_never(mode)
