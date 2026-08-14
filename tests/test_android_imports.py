"""Qt 层在无 pynput（Android 模拟）时的 import 冒烟测试。

Android(p4a) 没有 pynput recipe,``global_hotkey_controller`` 曾模块级
``from pynput import keyboard`` 导致整个 controllers 包 import 即失败。
本测试把 pynput 模拟为未安装后,验证相关模块仍可正常导入,且热键实现
退化为 noop 空壳、不会启动任何监听线程。

另含 ``cv2.typing`` 桩测试：p4a 的 opencv recipe 只装单个 ``cv2.so``
（无纯 Python 的 ``cv2.typing`` 子包）,而 kotonebot/iaa 多处有
``from cv2.typing import MatLike``,需验证 :mod:`iaa.platform.android_stubs`
提供的 ``sys.modules`` 桩能覆盖该场景。
"""

import sys
import unittest
from unittest.mock import Mock


def _block_pynput() -> None:
    """把 pynput 模拟为"未安装",并清空已缓存的 qt controllers 子模块。"""
    # sys.modules 置 None 等价于"模块不存在":importlib.util.find_spec 返回
    # None,任何 ``import pynput`` 都会抛 ImportError
    sys.modules['pynput'] = None
    for name in list(sys.modules):
        if name == 'iaa.application.qt.controllers' or name.startswith('iaa.application.qt.controllers.'):
            del sys.modules[name]


def _restore_controllers() -> None:
    """恢复 pynput 可见,并重新导入 controllers,避免污染同进程其它测试。"""
    sys.modules.pop('pynput', None)
    for name in list(sys.modules):
        if name == 'iaa.application.qt.controllers' or name.startswith('iaa.application.qt.controllers.'):
            del sys.modules[name]
    import iaa.application.qt.controllers  # noqa: F401


class AndroidImportSmokeTests(unittest.TestCase):
    """Android 上无 pynput 时 Qt 控制器层的可导入性回归。"""

    def tearDown(self) -> None:
        # 恢复桌面默认状态（pynput 可用）,避免影响同进程内其它测试模块
        _restore_controllers()

    def test_hotkey_controller_importable_without_pynput(self) -> None:
        _block_pynput()
        from iaa.application.qt.controllers.global_hotkey_controller import GlobalHotkeyController
        self.assertIsNotNone(GlobalHotkeyController)

    def test_app_controller_importable_without_pynput(self) -> None:
        _block_pynput()
        from iaa.application.qt.controllers import AppController
        self.assertIsNotNone(AppController)

    def test_hotkey_impl_falls_back_to_noop_without_pynput(self) -> None:
        _block_pynput()
        from iaa.application.qt.controllers import global_hotkey_controller as ghc
        self.assertEqual(ghc._HOTKEY_IMPL, 'noop')

    def test_hotkey_controller_constructs_without_starting_listener(self) -> None:
        _block_pynput()
        from iaa.application.qt.controllers.global_hotkey_controller import GlobalHotkeyController
        ctrl = GlobalHotkeyController(Mock(), Mock())
        # noop 分支不创建任何监听线程
        self.assertIsNone(ctrl._listener)
        ctrl.shutdown()


class AndroidPackageStubTests(unittest.TestCase):
    """android package stub enables import under Android (no p4a android recipe).

    p4a patches stdlib ctypes/util.py find_library to
    ``from android._ctypes_library_finder import find_library``; the qt
    bootstrap build does not include the android recipe, so this stub must
    make ``android`` and its submodule importable.
    """

    def tearDown(self) -> None:
        # clean up the stub to avoid polluting other tests in the same process
        sys.modules.pop('android', None)
        sys.modules.pop('android._ctypes_library_finder', None)

    def test_stub_enables_android_library_finder_import(self) -> None:
        from iaa.platform import android_stubs
        android_stubs.install_android_package_stub()

        # this is exactly how the patched ctypes.util imports it
        from android._ctypes_library_finder import find_library  # noqa: F401
        self.assertIsNotNone(find_library)
        # idempotent: reinstalling must not raise
        android_stubs.install_android_package_stub()

    def test_find_library_matches_so_patterns(self) -> None:
        from iaa.platform.android_stubs import _find_library
        # must return None for a library that does not exist on the host
        self.assertIsNone(_find_library('__definitely_missing_iaa_lib__'))


class Cv2TypingStubTests(unittest.TestCase):
    """``cv2.typing`` 桩在 Android（cv2 为单文件模块）场景下的可导入性。

    模拟 p4a 布局：``cv2`` 仅为一个非包模块（``cv2.so``），不存在
    ``cv2.typing`` 子包。注册桩后 ``from cv2.typing import MatLike`` 必须成功。
    """

    def tearDown(self) -> None:
        # 清理桩，避免污染同进程其它测试（桌面真实 cv2.typing 仍在）
        sys.modules.pop('cv2', None)
        sys.modules.pop('cv2.typing', None)

    def test_stub_enables_cv2_typing_import(self) -> None:
        import types

        # 模拟 p4a：cv2 是单文件扩展模块（非包），无 typing 子包
        bare_cv2 = types.ModuleType('cv2')
        sys.modules['cv2'] = bare_cv2
        sys.modules.pop('cv2.typing', None)

        from iaa.platform import android_stubs
        android_stubs.install_cv2_typing_stub(is_android=True)

        from cv2.typing import MatLike, Rect as CvRect  # noqa: F401
        self.assertIsNotNone(MatLike)
        self.assertIsNotNone(CvRect)
        # 桩幂等：重复安装不抛错
        android_stubs.install_cv2_typing_stub(is_android=True)


if __name__ == '__main__':
    unittest.main()