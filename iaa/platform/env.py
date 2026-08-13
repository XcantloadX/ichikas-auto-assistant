"""平台环境层：统一 app_root 与资源/配置/数据目录的路径解析。

桌面（Windows 源码运行 + PyInstaller / Nuitka 打包）与 Android（p4a）两种
环境下,各业务模块通过本模块获取正确的运行目录,避免各自基于 ``sys.executable``
与 cwd 推导导致的误判（Android 上 ``sys.executable`` 指向 p4a 私有目录里的解释器）。

.. NOTE::
    - 本模块只依赖标准库,严禁 import 任何 ``iaa`` 内部模块（env 是最底层,
      避免循环依赖）。
    - Android(p4a) 的标准做法:可写数据（conf / logs 等）放在
      ``ANDROID_PRIVATE``（app 私有 files 目录）之下;只读资源走
      ``importlib.resources`` 打包资源（如 ``iaa.res``）。
"""

import os
import sys
from importlib import resources

# p4a 启动时注入 ANDROID_PRIVATE（app 私有文件目录）与 ANDROID_APP_PATH。
# 模块导入时即确定:这些常量的判定会在导入瞬间被倒引,运行期再改环境变量不可靠。
# 不能用 sys.platform == 'linux' 判断:p4a 下 sys.platform 仍是 linux,会与桌面 Linux 混淆。
IS_ANDROID: bool = 'ANDROID_PRIVATE' in os.environ or 'ANDROID_APP_PATH' in os.environ
"""当前是否运行在 Android(p4a) 环境:存在 ``ANDROID_PRIVATE`` 或
``ANDROID_APP_PATH`` 环境变量即视为 Android。模块导入时计算。"""


def _android_root_dir() -> str:
    """返回 Android 上的 app 可写私有根目录。

    优先使用 ``ANDROID_APP_PATH``,其次 ``ANDROID_PRIVATE``。
    仅当 :data:`IS_ANDROID` 为真时调用;若运行期环境变量被清除则抛出异常。

    :return: Android 私有根目录绝对路径。
    :raises RuntimeError: ``ANDROID_APP_PATH``/``ANDROID_PRIVATE`` 均不存在时。
    """
    root = os.environ.get('ANDROID_APP_PATH') or os.environ.get('ANDROID_PRIVATE')
    if not root:
        raise RuntimeError('Android 环境缺少 ANDROID_APP_PATH / ANDROID_PRIVATE 环境变量')
    return root


def _is_packaged() -> bool:
    """判断当前是否处于打包/冻结运行（PyInstaller / Nuitka）。

    桌面源码运行下列条件全为假（回归保真）;打包运行时至少命中其一:
    ``sys.frozen``（PyInstaller）、``__compiled__``（Nuitka 注入的魔法变量）、
    或 ``sys.executable`` 的可执行文件名不以 ``python`` 开头。
    该方法只在非 Android 分支被引用,避免与 ``IS_ANDROID`` 判定叠加。
    """
    # PyInstaller 冻结产物会设置 sys.frozen
    if getattr(sys, 'frozen', False):
        return True
    # Nuitka 编译产物会注入 __compiled__,沿用原 utils.sprite_path 的探测手法
    try:
        __compiled__  # type: ignore[name-defined]
        return True
    except NameError:
        pass
    # 通用兜底:可执行文件名不以 python 开头即视为打包产物
    return not os.path.basename(sys.executable).startswith('python')


def app_root() -> str:
    """返回软件根目录。

    桌面源码运行返回仓库根（含 ``conf/``、``assets/``、``logs/`` 的那一级）,
    桌面打包运行返回可执行文件所在目录;Android 返回 p4a 私有可写目录。

    :return: 软件根目录绝对路径。
    :raises RuntimeError: Android 环境但 ``ANDROID_APP_PATH``/``ANDROID_PRIVATE`` 缺失时。
    """
    if IS_ANDROID:
        return _android_root_dir()
    if _is_packaged():
        return os.path.dirname(sys.executable)
    # 源码运行:从本文件所在上级（iaa/）再上溯一级即仓库根
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


def asset_dir() -> str:
    """返回 assets 资源的根目录。

    桌面源码返回 ``app_root()/assets``;桌面打包返回 ``exe目录/assets``
    （PyInstaller 打包资源通常放这里）,若不存在则回退到
    ``importlib.resources`` 的 ``iaa/assets`` 路径（该兜底路径仅在打包时
    assets 被收进包内才有效）;Android 端 assets 不按独立目录存放,
    调用方应改用 :func:`importlib.resources` 读取打包资源,或依赖
    :func:`asset_path` 的异常语义。

    :return: assets 根目录绝对路径。
    :raises NotImplementedError: Android 环境（调用方应回退 importlib.resources）。
    """
    if IS_ANDROID:
        raise NotImplementedError(
            'Android 端 assets 不按独立目录存放,请改用 importlib.resources 打包资源'
        )
    if _is_packaged():
        candidate = os.path.join(os.path.dirname(sys.executable), 'assets')
        if os.path.isdir(candidate):
            return candidate
        # 兜底:打包时 assets 若被收进 iaa 包内（PyInstaller add-data 形式）
        return str(resources.files('iaa') / 'assets')
    return os.path.join(app_root(), 'assets')


def asset_path(path: str) -> str:
    """返回 assets 下某资源的绝对路径。

    保持原 :func:`iaa.utils.asset_path` 的语义:仅校验 assets 根目录是否存在,
    不校验目标资源本身。Android 端该函数与 :func:`asset_dir` 同进退,
    会抛出 ``NotImplementedError`` 让调用方改用打包资源。

    :param path: 相对 assets 根目录的资源路径（如 ``ichika.png``）。
    :return: 资源的绝对路径。
    :raises NotImplementedError: Android 环境（调用方应回退 importlib.resources）。
    :raises FileNotFoundError: assets 根目录不存在时。
    """
    root = asset_dir()
    if not os.path.isdir(root):
        raise FileNotFoundError(f'Missing assets folder: {root}')
    return os.path.abspath(os.path.join(root, path))


def config_dir() -> str:
    """返回可写配置目录（*.json 配置文件所在）。

    桌面返回 ``app_root()/conf``;Android 返回 ``ANDROID_PRIVATE/conf``,
    并自动创建该目录（app 私有目录在 p4a 下就是 ``ANDROID_PRIVATE``）。

    :return: 配置目录绝对路径。
    :raises RuntimeError: Android 环境但缺少私有目录环境变量时。
    """
    if IS_ANDROID:
        conf_dir = os.path.join(_android_root_dir(), 'conf')
        os.makedirs(conf_dir, exist_ok=True)
        return conf_dir
    return os.path.join(app_root(), 'conf')


def data_dir() -> str:
    """返回可写数据目录（logs、dumps 等运行时产物）。

    桌面为 ``app_root()`` 本身（现状即 logs 等直接落在 app_root 下）;
    Android 为 ``ANDROID_PRIVATE`` 根下与 conf 平级（即私有根目录本身）。
    保证返回值目录已存在。

    :return: 数据目录绝对路径。
    :raises RuntimeError: Android 环境但缺少私有目录环境变量时。
    """
    if IS_ANDROID:
        data_dir = _android_root_dir()
    else:
        data_dir = app_root()
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


def logs_dir() -> str:
    """返回日志目录,即 :func:`data_dir` 下的 ``logs`` 子目录,保证已创建。

    :return: 日志目录绝对路径。
    :raises RuntimeError: Android 环境但缺少私有目录环境变量时。
    """
    logs_dir = os.path.join(data_dir(), 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    return logs_dir


def sprite_root() -> str:
    """返回游戏 sprite 资源根目录。

    桌面保持原 :func:`iaa.utils.sprite_path` 的既有优先级:打包运行
    返回 ``exe目录/assets/res_compiled``（缺失时抛异常,与原逻辑一致）;
    源码运行返回 ``iaa/res``;以上都不成立时返回 ``importlib.resources``
    的 ``iaa.res`` 包路径（打 zip 或独立目录均可）。

    :return: sprite 资源根目录绝对路径。
    :raises FileNotFoundError: 打包运行但缺少 ``assets/res_compiled`` 目录时。
    """
    if IS_ANDROID:
        # Android 端 sprite 资源随包内 iaa.res 打进 APK（zip 包或独立目录）
        return str(resources.files('iaa.res'))
    if _is_packaged():
        # 打包运行:资源被移动到 exe 目录下的 assets/res_compiled
        packaged = os.path.join(os.path.dirname(sys.executable), 'assets', 'res_compiled')
        if not os.path.isdir(packaged):
            raise FileNotFoundError(f'Missing resource folder: {packaged}')
        return packaged
    # 源码运行:基于模块文件的绝对路径追到 iaa/res
    dev_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'res'))
    if os.path.isdir(dev_path):
        return dev_path
    # 兜底:包内资源（适用于以包形式安装时）
    return str(resources.files('iaa.res'))