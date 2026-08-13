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


def install_android_stubs() -> None:
    """安装 Android 平台所需的全部启动桩。

    目前只包含 :func:`install_cv2_typing_stub`。入口 ``main.py`` 在 import
    iaa 前调用一次；后续发现新的平台缺失包（如其它纯 Python 子包）继续在此
    追加，保持入口唯一。
    """
    install_cv2_typing_stub()
