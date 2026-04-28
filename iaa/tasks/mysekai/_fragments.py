from kotonebot import Loop, sleep, logging

from .. import R
from ..common import go_home

logger = logging.getLogger(__name__)

def go_to_mysekai():
    go_home()

    for _ in Loop():
        if R.Hud.ButtonMySekai.try_click():
            logger.info('Clicked MySekai button')
            sleep(5)
        elif R.MySekai.Hud.ButtonLayout.exists():
            logger.info('Arrived at MySekai')
            return
        elif R.MySekai.DialogCrowded.Text.exists():
            logger.warning('MySekai is crowded, retrying...')
            if R.MySekai.DialogCrowded.ButtonOk.try_click():
                logger.info('Clicked OK on crowded dialog')
                sleep(2)
        