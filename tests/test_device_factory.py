import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from kotonebot.errors import UserFriendlyError

from iaa.application.service.device_factory import DeviceFactory, LifecyclePolicy
from iaa.config.base import IaaConfig


class DeviceFactoryTests(unittest.TestCase):
    def _factory_for(self, device_payload: dict, *, server: str = 'jp') -> DeviceFactory:
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

    def test_require_running_rejects_stopped_mumu(self) -> None:
        factory = self._factory_for(
            {
                'lifecycle': {'type': 'mumu_v5', 'instance_id': '0'},
                'connection': {'type': 'auto'},
                'control_impl': 'scrcpy',
            }
        )
        mock_host = MagicMock()
        mock_host.running.return_value = False

        with (
            patch('kotonebot.client.host.Mumu12V5Host.query', return_value=mock_host),
            patch('kotonebot.client.host.Mumu12V5Host.check_app_keptlive', return_value=False),
        ):
            with self.assertRaises(UserFriendlyError) as ctx:
                factory.resolve_host(
                    factory._config.conf.device,
                    policy=LifecyclePolicy.REQUIRE_RUNNING,
                    impl_hint='scrcpy',
                )
        self.assertIn('请先运行任务', str(ctx.exception))

    def test_check_and_start_starts_custom_emulator(self) -> None:
        factory = self._factory_for(
            {
                'lifecycle': {
                    'type': 'custom',
                    'start_command': 'echo start',
                    'check_and_start': True,
                },
                'connection': {
                    'type': 'tcp',
                    'ip': '127.0.0.1',
                    'port': 5555,
                },
                'control_impl': 'scrcpy',
            }
        )
        mock_host = MagicMock()
        mock_host.running.return_value = False
        mock_host.stop = MagicMock()

        with patch(
            'iaa.application.service.device_factory.CustomEmulatorInstance',
            return_value=mock_host,
        ):
            resolved = factory.resolve_host(
                factory._config.conf.device,
                policy=LifecyclePolicy.CHECK_AND_START,
                impl_hint='scrcpy',
            )

        mock_host.start.assert_called_once()
        mock_host.wait_available.assert_called_once()
        self.assertTrue(resolved.started_by_us)
        self.assertIs(resolved.stop_callback, mock_host.stop)

    def test_preview_rejects_playcover(self) -> None:
        factory = self._factory_for(
            {
                'lifecycle': {'type': 'playcover'},
                'connection': {'type': 'auto'},
                'control_impl': 'scrcpy',
            }
        )
        with self.assertRaises(UserFriendlyError) as ctx:
            factory.create_scrcpy_preview_device(
                factory._config.conf.device, factory._config.conf.game.server
            )
        self.assertIn('PlayCover', str(ctx.exception))

    def test_create_device_for_current_config_returns_device(self) -> None:
        factory = self._factory_for(
            {
                'lifecycle': {
                    'type': 'custom',
                    'start_command': 'echo start',
                },
                'connection': {
                    'type': 'tcp',
                    'ip': '127.0.0.1',
                    'port': 5555,
                },
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

        self.assertIs(device, fake_device)
        self.assertFalse(resolved.started_by_us)
        mock_host.create_device.assert_called_once()


if __name__ == '__main__':
    unittest.main()