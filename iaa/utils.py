import os
import sys
from importlib import resources

from kotonebot import logging

logger = logging.getLogger(__name__)

def sprite_path(path: str) -> str:
    """返回 sprite 图片的绝对路径。

    优先按以下顺序查找：
    1. 源码目录：与本文件同级的 `res/sprites` 目录（开发模式）
    2. 打包目录：可执行文件所在目录下的 `assets/res_compiled/sprites`
    3. 包资源：`importlib.resources`（作为兜底）
    """
    # 打包运行：基于可执行文件所在目录（资源被移动到 assets/res_compiled 下）
    pyinstaller = hasattr(sys, '_MEIPASS')
    try:
        __compiled__ # type: ignore
        nukita = True
    except NameError:
        nukita = False
    if pyinstaller or nukita:
        exe_dir = os.path.dirname(sys.executable)
        packaged_path = os.path.join(exe_dir, 'assets', 'res_compiled', path)
        if not os.path.exists(packaged_path):
            raise RuntimeError(f"Missing resource folder: {packaged_path}")
        return packaged_path
    
    # 源码运行：基于模块文件的绝对路径
    dev_path = os.path.join(os.path.dirname(__file__), 'res', path)
    if os.path.exists(dev_path):
        return dev_path

    # 兜底：包内资源（适用于以包形式安装时）
    return str(resources.files('iaa.res') / path)