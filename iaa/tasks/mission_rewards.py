from kotonebot import task, logging, Loop, sleep

from . import R
from .common import go_home, at_home
from ..context import task_reporter
from iaa.game_ui.side_tabbar import SideTabbar

logger = logging.getLogger(__name__)

@task('领取任务奖励', screenshot_mode='manual')
def collect_mission_rewards():
    """领取所有任务奖励"""
    rep = task_reporter()

    if not at_home():
        go_home()

    logger.info('Navigated to mission page.')
    rep.message('前往任务奖励页面')

    for _ in Loop(interval=1):
        if R.Daily.ButtonMission.try_click():
            logger.debug('Clicked "Mission" button.')
            pass
        elif R.Hud.ButtonClaimAll.find():
            logger.info('Now at mission rewards page.')
            sleep(1)
            break
    
    tabbar = SideTabbar()
    state = tabbar.update()
    logger.info(f'Tabbar count={len(state.tabs)} current={state.active_index} unread={state.badge_indices}')
    if not state.badge_indices:
        logger.info('No more rewards to claim.')
        return
    
    while state.badge_indices:
        for i in state.badge_indices:
            rep.message(f'任务奖励 {i+1}/{len(state.tabs)}')
            tabbar.switch_to(i)
            logger.info(f'Switched to tab index={i} to claim rewards.')
            sleep(2)
            while not R.Hud.ButtonClaimAll.try_click():
                sleep(1)
            sleep(1)
        logger.debug('Updating tabbar state.')
        state = tabbar.update()
    logger.info('Finished claiming all mission rewards.')


