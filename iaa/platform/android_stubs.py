"""Android 平台启动桩（shim）模块。

p4a 的 opencv recipe（``-DOPENCV_SKIP_PYTHON_LOADER=ON``）只把 ``cv2.so``
作为**单个扩展模块**装进 site-packages,不会带桌面 wheel 里的纯 Python
``cv2/typing`` 子包。而 kotonebot / iaa 的很多模块顶部有
``from cv2.typing import MatLike``（仅用于类型注解,运行期从不取值）。
若不做处理,``import kotonebot`` 即抛
``ModuleNotFoundError: No module named 'cv2.typing'; 'cv2' is not a package``。

本模块在入口 ``main.py`` 里、任何 kotonebot/iaa import 之前被调用,把
``cv2.typing`` 以 ``sys.modules`` 注册成轻量桩模块。因 ``MatLike`` 只是
``Union[cv2.mat_wrapper.Mat, numpy.ndarray]`` 的类型别名、``Rect`` 只是
``Sequence[int]``,桩只需提供同名别名即可满足注解求值;真实取值逻辑从不
使用它们。桌面平台不注册（桌面有完整 ``cv2.typing``）。
"""

from __future__ import annotations

import os
import re
import sys
import types
from typing import Any, Sequence

from iaa.platform import env


def install_cv2_typing_stub(is_android: bool | None = None) -> None:
    """注册 ``cv2.typing`` 桩模块到 ``sys.modules``。

    仅在 Android 平台执行;桌面平台（有完整 ``cv2.typing`` 包）直接跳过。
    幂等：已注册时不再重复创建。

    :param is_android: 平台判定覆盖值。默认取 :data:`iaa.platform.env.IS_ANDROID`
        （模块导入时固化）；测试等场景可显式传入覆盖。

    .. NOTE:: 必须在任何 ``import kotonebot`` / ``import iaa`` 之前调用
        （入口 ``main.py`` 顶部），否则 import 链会先触发
        ``cv2.typing`` 查找并失败。
    """
    if is_android is None:
        is_android = env.IS_ANDROID
    if not is_android:
        return
    if 'cv2.typing' in sys.modules:
        return

    stub = types.ModuleType('cv2.typing')
    # 桌面定义 MatLike = Union[Mat, NumPyArrayNumeric]、Rect = Sequence[int]，
    # 均只用于类型注解、运行期从不取值；桩用 Any/Sequence 占位即可。
    stub.MatLike = Any
    stub.Rect = Sequence[int]
    sys.modules['cv2.typing'] = stub


def _find_library(name: str) -> str | None:
    """在 Android 原生库目录中按名字查找 ``.so`` 库。

    模仿 p4a ``android`` recipe 的 ``_ctypes_library_finder.find_library``
    的**纯文件系统**部分（其真实实现还用 pyjnius 查 Activity 的 nativeLibraryDir，
    但本桩不依赖 pyjnius）：扫描 ``/system/lib64``、``/system/lib`` 与
    ``LD_LIBRARY_PATH`` 各目录，按 ``lib<name>.so`` / ``<name>.so`` 等形态匹配。
    Android 上绝大多数场合只需要 ``ctypes.util`` 能解析出系统库路径，而 iaa
    不在 Android 上做模拟点击/输入（该链路用桌面 placeholder），找不到返回
    ``None`` 也安全。

    :param name: 要查找的库名，如 ``'c'``、``'sqlite3'``。
    :return: 找到的库绝对路径；未找到返回 ``None``。
    """
    search_dirs = ['/system/lib64', '/system/lib']
    ld_path = os.environ.get('LD_LIBRARY_PATH', '')
    search_dirs += [d for d in ld_path.split(':') if d]
    pattern = re.compile(r'^(?:lib)?' + re.escape(name) + r'\.so(?:\.[0-9]+)*$')
    for lib_dir in search_dirs:
        if not os.path.isdir(lib_dir):
            continue
        for entry in os.listdir(lib_dir):
            if pattern.match(entry):
                return os.path.join(lib_dir, entry)
    return None


def install_android_package_stub() -> None:
    """注册 ``android`` 包桩到 ``sys.modules``。

    p4a 会打补丁把 stdlib ``ctypes/util.py`` 的 ``find_library`` 替换为
    ``from android._ctypes_library_finder import find_library``。而 ``android``
    包本身是 p4a 的一个 recipe（依赖 pyjnius / sdl bootstrap），**qt bootstrap
    构建默认不包含它**。因此只要任何代码 ``import ctypes.util``（例如纯 Python
    ``mouse`` 包的 ``_nixmouse``），在 Android 上就会因缺 ``android`` 包而失败，
    继而拖垮 ``kotonebot.interop.win._mouse`` 的导入链。

    本桩只注册 ``android`` 与 ``android._ctypes_library_finder`` 两个模块，
    提供文件系统层面的 ``find_library``（见 :func:`_find_library`），足以让
    ``ctypes.util`` 正常导入。iaa 自身的平台层（``env.py`` 等）只用
    ``os.environ`` / ``importlib.resources``，不依赖真实的 ``android`` 包，
    故桩是安全的。

    .. NOTE:: 必须在任何可能 ``import ctypes.util`` 的代码之前调用
        （入口 ``main.py`` 顶部，与 :func:`install_cv2_typing_stub` 一起）。
        幂等：已注册时直接返回。
    """
    if 'android' in sys.modules:
        return

    android_pkg = types.ModuleType('android')
    finder = types.ModuleType('android._ctypes_library_finder')
    finder.find_library = _find_library
    sys.modules['android'] = android_pkg
    sys.modules['android._ctypes_library_finder'] = finder


def install_dotenv_find_stub(is_android: bool | None = None) -> None:
    """把 ``dotenv.main.find_dotenv`` 替换为 Android 安全实现。

    ``kotonebot.ui.pushkit.image_host`` 在模块级调用 ``load_dotenv()``
    （无参），会走 ``python-dotenv`` 的 ``find_dotenv``：它用 ``sys._getframe()``
    沿调用栈向上找 ``co_filename`` 真实存在于磁盘的调用者帧。而 p4a 打包的
    代码是**预编译 ``.pyc``**，每个帧的 ``co_filename`` 都是构建机路径
    （``/home/runner/work/...``），在设备上不存在 → 它一路走到栈顶（``__main__``
    帧，``f_back is None``）后访问 ``frame.f_code`` → 抛
    ``AttributeError: 'NoneType' object has no attribute 'f_code'``。

    Android 上没有任何 ``.env`` 需要加载（pushkit 只用于桌面推送），把
    ``find_dotenv`` 换成返回空串的实现即可：``load_dotenv()`` 拿到空路径后
    在 ``DotEnv._get_stream`` 里直接跳过文件读取，行为与"找不到 .env"一致。

    .. NOTE:: 必须在任何 ``import kotonebot`` 之前调用（入口 ``main.py`` 顶部，
        与其它桩一起），否则 ``image_host`` 的模块级 ``load_dotenv()`` 会先崩溃。
        桌面平台不替换（桌面有真实文件系统与 ``.env``）。

    :param is_android: 平台判定覆盖值，同 :func:`install_cv2_typing_stub`。
    """
    if is_android is None:
        is_android = env.IS_ANDROID
    if not is_android:
        return
    try:
        from dotenv import main as dotenv_main
    except ImportError:
        # dotenv 不在环境里时无需打补丁（本来 import 也会失败，不影响这里）
        return

    def _android_find_dotenv(filename='.env', raise_error_if_not_found=False, usecwd=False) -> str:
        """Android 上的安全 ``find_dotenv``：不遍历调用栈，直接视为无 .env。

        :param filename: 与桌面签名一致，但 Android 上不实际查找。
        :param raise_error_if_not_found: 与桌面签名一致；Android 上固定返回空串，
            不抛错（避免 ``load_dotenv()`` 因找不到而中断）。
        :param usecwd: 与桌面签名一致；忽略。
        :return: 恒为 ``''``，表示不存在 ``.env``。
        """
        return ''

    dotenv_main.find_dotenv = _android_find_dotenv


def install_android_stubs() -> None:
    """安装 Android 平台所需的全部启动桩。

    目前包含 :func:`install_cv2_typing_stub`、
    :func:`install_android_package_stub` 与 :func:`install_dotenv_find_stub`。
    入口 ``main.py`` 在 import iaa 前调用一次；后续发现新的平台缺失包（如
    其它纯 Python 子包）继续在此追加，保持入口唯一。
    """
    install_cv2_typing_stub()
    install_android_package_stub()
    install_dotenv_find_stub()
