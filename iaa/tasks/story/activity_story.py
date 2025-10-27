from kotonebot import action, task, Loop, device, image, sleep
from kotonebot import logging

from iaa.tasks.common import has_red_dot, go_home

from .. import R
from .._fragments import handle_data_download
from ._common import enter_story, skip_stories

logger = logging.getLogger(__name__)

@action('前往活动剧情')
def go_activity_story():
    """
    前置：位于首页\n
    结束：活动剧情界面
    """
    go_home()
    for _ in Loop():
        # 新开活动，第一次进入，会弹出数据下载
        if handle_data_download():
            # 第一次进入会自动阅读第一话
            skip_stories(mode='skip')
            continue
        if image.find(R.Hud.ButtonLive):
            device.click()
            logger.debug('Clicked live button.')
            sleep(0.4)
        elif image.find(R.Live.ButtonSoloLive):
            # 说明已经打开了手机页面，点击活动页
            device.click(R.Live.PointEventButton)
            logger.debug('Entered event.')
            sleep(1)
        elif image.find(R.Activity.ButtonIconEventStory):
            device.click()
            logger.debug('Clicked event story button.')
            sleep(0.4)
        elif image.find(R.Story.TextEventStory):
            logger.info('Now at story list.')
            break

@task('刷当期活动剧情')
def activity_story():
    go_activity_story()
    badge_wl = has_red_dot(R.Activity.BoxLatestEpisodeBadgeWl)
    badge = has_red_dot(R.Activity.BoxLatestEpisodeBadge)
    if badge_wl or badge:
        logger.info('Unread activity story found. Entering story.')
        enter_story(is_wl=badge_wl)
        skip_stories(mode='skip')
    else:
        logger.info('No unread activity story found.')