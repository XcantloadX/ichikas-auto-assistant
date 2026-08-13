"""self_android（Android 自身设备）占位实现的接入测试。

覆盖三件事：
- 桌面环境（IS_ANDROID=False）下 ``create_device_for_current_config`` 行为完全不变，
  仍走 resolve_host / 既有 impl 分支；
- Android 模拟（注入 ANDROID_PRIVATE 并重载 env 模块）下短路返回
  ``impl == 'self_android'`` 的占位设备，截图抛 NotImplementedError、
  ``launch_app`` no-op 不崩；
- Android 下 ``iaa.context.keyboard()`` 返回可调用 send 的占位 IME 输入。

由于 ``env.IS_ANDROID`` 是模块导入时计算的常量，模拟 Android 依赖
``importlib.reload(iaa.platform.env)``；每个用例结束都会 reload 回桌面态，
避免污染同进程内的其它测试。
"""

import importlib
import os
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from iaa.application.service.device_factory import DeviceFactory, LifecyclePolicy
from iaa.config.base import IaaConfig

import iaa.platform.env as env_module


def _factory_for(device_payload: dict, *, server: str = 'jp') -> DeviceFactory:
    conf = IaaConfig.model_validate(
        {
            'version': 1,
            'name': 'test',
            'description': 'test',
            'device': device_payload,
            'game': {'server': server, 'link_account': 'no'},
        }
    )
    return DeviceFactory(SimpleNamespace(conf=conf))


class SelfAndroidTests(unittest.TestCase):
    """self_android 占位设备接入 DeviceFactory 的行为测试。"""

    def _restore_desktop(self) -> None:
        # 还原环境变量后重载 env，回到桌面态，避免影响同进程其它测试。
        for key in [k for k in os.environ if k.startswith('ANDROID_')]:
            os.environ.pop(key)
        importlib.reload(env_module)

    def test_desktop_keeps_original_path(self) -> None:
        """桌面下 create_device_for_current_config 仍走原 scrcpy 分支。"""
        factory = _factory_for(
            {
                'lifecycle': {'type': 'custom', 'start_command': 'echo start'},
                'connection': {'type': 'tcp', 'ip': '127.0.0.1', 'port': 5555},
                'control_impl': 'scrcpy',
                'scrcpy_virtual_display': True,
            }
        )
        fake_device = MagicMock()
        mock_host = MagicMock()
        mock_host.running.return_value = True
        mock_host.create_device.return_value = fake_device

        with (
            patch.dict(sys.modules, {'av': MagicMock()}),
            patch('iaa.application.service.device_factory.asset_path', return_value=r'E:\repo\assets\scrcpy.jar'),
            patch('iaa.application.service.device_factory.os.path.isfile', return_value=True),
            patch('iaa.application.service.device_factory.package_by_server', return_value='com.sega.pjsekai'),
            patch(
                'iaa.application.service.device_factory.CustomEmulatorInstance',
                return_value=mock_host,
            ),
        ):
            resolved, device = factory.create_device_for_current_config(
                policy=LifecyclePolicy.CHECK_AND_START
            )

        # 桌面分支返回的是原 scrcpy 流程产出的 fake_device，而非 self_android 占位。
        self.assertIs(device, fake_device)
        self.assertEqual(resolved.impl, 'scrcpy')
        mock_host.create_device.assert_called_once()

    def test_desktop_short_circuit_not_triggered_without_android_env(self) -> None:
        """未注入 ANDROID_* 变量时，create_device_for_current_config 不短路。"""
        factory = _factory_for(
            {
                'lifecycle': {'type': 'custom', 'start_command': 'echo start'},
                'connection': {'type': 'tcp', 'ip': '127.0.0.1', 'port': 5555},
                'control_impl': 'scrcpy',
            }
        )
        fake_device = MagicMock()
        mock_host = MagicMock()
        mock_host.running.return_value = True
        mock_host.create_device.return_value = fake_device

        with (
            patch.dict(sys.modules, {'av': MagicMock()}),
            patch('iaa.application.service.device_factory.asset_path', return_value=r'E:\repo\assets\scrcpy.jar'),
            patch('iaa.application.service.device_factory.os.path.isfile', return_value=True),
            patch('iaa.application.service.device_factory.package_by_server', return_value='com.sega.pjsekai'),
            patch(
                'iaa.application.service.device_factory.CustomEmulatorInstance',
                return_value=mock_host,
            ),
        ):
            resolved, device = factory.create_device_for_current_config(
                policy=LifecyclePolicy.CHECK_AND_START
            )

        self.assertIs(device, fake_device)
        self.assertEqual(resolved.impl, 'scrcpy')

    def test_android_returns_self_android_placeholder(self) -> None:
        """Android 模拟下短路返回 self_android 占位设备。"""
        factory = _factory_for(
            {
                'lifecycle': {'type': 'mumu_v5', 'instance_id': '0'},
                'connection': {'type': 'auto'},
                'control_impl': 'scrcpy',
            }
        )

        with tempfile.TemporaryDirectory() as tmp:
            private = os.path.join(tmp, 'files')
            os.makedirs(private)
            with patch.dict(os.environ, {'ANDROID_PRIVATE': private}):
                importlib.reload(env_module)
                self.assertTrue(env_module.IS_ANDROID)

                resolved, device = factory.create_device_for_current_config(
                    policy=LifecyclePolicy.CHECK_AND_START
                )

                self.assertEqual(resolved.impl, 'self_android')
                self.assertFalse(resolved.started_by_us)
                self.assertIsNone(resolved.stop_callback)
                self.assertIsInstance(device, type(resolved.host))

                # launch_app no-op 不崩
                device.launch_app('com.sega.pjsekai')
                self.assertEqual(device.commands.adb_shell('wm size'), '')
                self.assertIsNone(device.current_package())

                # 截图抛 NotImplementedError
                with self.assertRaises(NotImplementedError) as ctx:
                    device.screenshot()
                self.assertIn('placeholder', str(ctx.exception))

                # start/stop 直接通过
                device.start()
                device.stop()

        self._restore_desktop()

    def test_create_device_explicit_self_android(self) -> None:
        """create_device 显式指定 self_android 分支返回占位 host 本身。"""
        from iaa.application.service.device_factory import ResolvedHost
        from iaa.platform.device_android import SelfAndroidDevice

        host = SelfAndroidDevice()
        resolved = ResolvedHost(
            host=host,
            started_by_us=False,
            stop_callback=None,
            impl='self_android',
        )
        factory = _factory_for(
            {
                'lifecycle': {'type': 'mumu_v5', 'instance_id': '0'},
                'connection': {'type': 'auto'},
                'control_impl': 'scrcpy',
            }
        )
        device = factory.create_device(
            resolved,
            impl='self_android',
            use_virtual_display=False,
            game_server='jp',
        )
        self.assertIs(device, host)

    def test_keyboard_placeholder_on_android(self) -> None:
        """Android 模拟下 iaa.context.keyboard() 返回可调用 send 的占位输入。"""
        with tempfile.TemporaryDirectory() as tmp:
            private = os.path.join(tmp, 'files')
            os.makedirs(private)
            with patch.dict(os.environ, {'ANDROID_PRIVATE': private}):
                importlib.reload(env_module)
                from iaa.context import keyboard
                kbd = keyboard()
                # 占位：send 可调用且 no-op，不触发 device.of_android()。
                self.assertTrue(callable(kbd.send))
                kbd.send('test')
                kbd.enter()
                kbd.clear()
                self.assertIsNone(kbd.can_input())

        self._restore_desktop()


if __name__ == '__main__':
    unittest.main()