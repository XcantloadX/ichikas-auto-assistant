from typing import Literal
from typing_extensions import assert_never

from kotonebot import action, task, Loop, device, image, sleep
from kotonebot import logging

from .. import R

logger = logging.getLogger(__name__)

SkipMode = Literal['skip', 'read']

def at_story_list():
    return image.find(R.Story.TextEventStory) is not None

@action('进入剧情阅读')
def enter_story(*, is_wl: bool = False):
    """
    前置：位于剧情列表界面\n
    结束：剧情阅读界面

    :param is_wl: 是否是为 WorldLink 当期活动剧情
    """
    for _ in Loop():
        if image.find(R.Story.ButtonStoryMenu):
            # 位于剧情画面
            logger.info('Now at story.')
            break
        elif image.find(R.Story.CheckboxContinuousReading, threshold=0.98):
            # threshold 0.98 是因为更低会命中未选中状态
            # TODO: 需要一个更好的区别方式
            # 勾选连续阅读
            device.click()
            logger.debug('Clicked continuous reading checkbox.')
            sleep(0.4)
        elif image.find(R.Story.ButtonWithoutVoice):
            # 选择无语音模式
            device.click()
            logger.debug('Clicked without voice button.')
            sleep(0.4)
        else:
            # 尝试点进最上面一话
            if is_wl:
                device.click(R.Story.PointFirstEpisodeWl)
            else:
                device.click(R.Story.PointFirstEpisode)

@action('跳过剧情')
def skip_stories(mode: SkipMode = 'skip'):
    """
    跳过剧情。同时支持单集阅读模式与连续阅读模式。
    
    前置：位于剧情阅读界面\n
    结束：剧情列表界面

    :param mode: 跳过模式，可选值为 'skip'（跳过）, 'fast_forward'（快进）, 'read'（连点跳过）。
    """
    for _ in Loop(interval=0.5):
        if image.find(R.Story.ButtonStoryMenu):
            device.click()
            logger.debug('Clicked story menu button.')
        elif image.find(R.CommonDialog.TextAwardClaimedOk):
            # 奖励领取
            logger.debug('Found award claimed dialog.')
            if image.find(R.CommonDialog.ButtonAwardClaimedOk):
                device.click()
                logger.debug('Clicked award claimed ok button.')
        elif at_story_list():
            # 位于剧情列表
            logger.info('Now at story list.')
            break
        else:
            # 跳过处理
            match mode:
                case 'skip':
                    if image.find(R.Story.ButtonReadNext):
                        device.click()
                        logger.debug('Clicked read next button.')
                    elif image.find(R.Story.ButtonSkipStory):
                        device.click()
                        logger.debug('Clicked skip button (last episode).')
                    elif image.find(R.Story.ButtonIconSkip):
                        device.click()
                        logger.debug('Clicked skip button.')
                case 'read':
                    raise NotImplementedError('Read mode is not implemented.')
                case _:
                    assert_never(mode)
