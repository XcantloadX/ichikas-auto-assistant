import logging
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from kotonebot import Loop

from ._fragments import handle_data_download, handle_notification
from . import R

logger = logging.getLogger(__name__)

def handle_network_error():
    if R.NetworkError.DialogConnectionError.Text.exists():
        logger.info('Network error dialog found.')
        if R.NetworkError.DialogConnectionError.ButtonRetry.click():
            logger.info('Clicked retry button on network error dialog.')
            return True
    if R.NetworkError.DialogReturningToTitle.Text.exists():
        logger.info('Returning to title dialog found.')
        if R.NetworkError.DialogReturningToTitle.ButtonOk.click():
            logger.info('Clicked OK button on returning to title dialog.')
            return True
    return False

def data_download(loop: 'Loop'):
    if handle_network_error():
        return
    elif handle_data_download():
        return
    elif handle_notification():
        return
