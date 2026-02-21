from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from kotonebot import Loop

from ._fragments import handle_data_download

def data_download(loop: 'Loop'):
    handle_data_download()