"""
领取礼物
"""
import logging

from kotonebot import task, device, Loop, sleep

from . import R
from .common import go_home

logger = logging.getLogger(__name__)

@task('领取礼物', screenshot_mode='manual')
def gift():
    # 进入礼物界面
    go_home()
    logger.debug('Entering gift ui')
    for _ in Loop():
        if R.Hud.ButtonClaimAll.find():
            logger.info('Now at gift ui')
            break
        elif R.Daily.ButtonGift.try_click():
            logger.debug('Clicked gift button')
            sleep(0.5)
    # 领取礼物
    if R.Hud.ButtonClaimAll.q(colored=True).find():
        device.click()
        sleep(0.5)
    else:
        logger.info('No gift to claim')
    go_home()
