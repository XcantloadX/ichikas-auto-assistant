import os
from importlib import resources

from kotonebot import logging

logger = logging.getLogger(__name__)

def sprite_path(path: str) -> str:
    """返回 sprite 图片的绝对路径。

    优先按以下顺序查找：

    1. 源码目录：与本文件同级的 ``res`` 目录（开发模式）。
    2. 包资源：随 wheel 安装的 ``iaa/res`` 目录（``importlib.resources``）。

    :param path: 相对于 ``iaa/res`` 目录的图片路径，以 ``/`` 分隔。
    :return: sprite 图片的绝对路径。
    """
    # 开发模式：基于模块文件的绝对路径
    dev_path = os.path.join(os.path.dirname(__file__), 'res', path)
    if os.path.exists(dev_path):
        return dev_path

    # 包内资源（wheel 安装时）
    return str(resources.files('iaa') / 'res' / path)

def assets_root() -> str:
    """返回随包分发的 ``iaa/assets`` 运行时资源根目录。

    :return: ``iaa/assets`` 目录的绝对路径。
    """
    return str(resources.files('iaa') / 'assets')

def asset_path(path: str) -> str:
    """返回 ``iaa/assets`` 内指定资源的绝对路径。

    :param path: 相对于 ``iaa/assets`` 目录的资源路径，以 ``/`` 或 ``\\\\`` 分隔。
    :return: 资源的绝对路径。
    """
    traversable = resources.files('iaa')
    for part in ('assets', *path.replace('\\', '/').split('/')):
        traversable = traversable / part
    return str(traversable)
