import os
from importlib import resources

from kotonebot import logging

from iaa.platform import env

logger = logging.getLogger(__name__)

def sprite_path(path: str) -> str:
    """返回 sprite 图片的绝对路径。

    委托给 :func:`iaa.platform.env.sprite_root` 解析根目录,然后按以下顺序查找
    对应文件:
    1. Android: 包内资源 ``importlib.resources('iaa.res')``（随 APK 打包）
    2. 打包运行: 可执行文件所在目录下的 ``assets/res_compiled``
    3. 源码目录: 与本包同级的 ``iaa/res``
    4. 包资源: 兜底 ``importlib.resources('iaa.res')``（打 zip 或独立目录均可）

    :param path: 相对 sprite 根目录的资源路径（如 ``xx_template.png``）。
    :return: sprite 图片的绝对路径。
    :raises FileNotFoundError: 打包运行但缺少 ``assets/res_compiled`` 目录时。
    """
    if env.IS_ANDROID:
        return str(resources.files('iaa.res') / path)
    try:
        root = env.sprite_root()
    except FileNotFoundError:
        # 打包运行但缺少 res_compiled 目录:兜底到包内资源
        return str(resources.files('iaa.res') / path)
    candidate = os.path.join(root, path)
    if os.path.exists(candidate):
        return candidate
    # 兜底:包内资源（适用于以包形式安装时）
    return str(resources.files('iaa.res') / path)

def asset_path(path: str) -> str:
    """返回 assets 下某资源的绝对路径,委托给 :func:`iaa.platform.env.asset_path`。

    :param path: 相对 assets 根目录的资源路径。
    :return: 资源的绝对路径。
    :raises NotImplementedError: Android 环境（调用方应回退 importlib.resources）。
    :raises FileNotFoundError: assets 根目录不存在时。
    """
    return env.asset_path(path)