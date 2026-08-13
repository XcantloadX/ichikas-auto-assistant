"""Qt 层在无 pynput（Android 模拟）时的 import 冒烟测试。

Android(p4a) 没有 pynput recipe,``global_hotkey_controller`` 曾模块级
``from pynput import keyboard`` 导致整个 controllers 包 import 即失败。
本测试把 pynput 模拟为未安装后,验证相关模块仍可正常导入,且热键实现
退化为 noop 空壳、不会启动任何监听线程。
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


if __name__ == '__main__':
    unittest.main()