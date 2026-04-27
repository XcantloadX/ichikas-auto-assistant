import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import sys

from iaa.application.qt.models.mappings import CONTROL_IMPL_DISPLAY_MAP, CONTROL_IMPL_VALUE_MAP
from iaa.application.service.scheduler import SchedulerService
from iaa.config.base import IaaConfig

class ScrcpyIntegrationTests(unittest.TestCase):
    def test_control_impl_maps_include_scrcpy(self):
        self.assertEqual(CONTROL_IMPL_DISPLAY_MAP['scrcpy'], 'Scrcpy')
        self.assertEqual(CONTROL_IMPL_VALUE_MAP['Scrcpy'], 'scrcpy')

    def test_config_accepts_scrcpy_control_impl(self):
        conf = IaaConfig.model_validate(
            {
                'version': 1,
                'name': 'test',
                'description': 'test',
                'game': {
                    'server': 'jp',
                    'link_account': 'no',
                    'emulator': 'custom',
                    'control_impl': 'scrcpy',
                    'check_emulator': False,
                    'scrcpy_virtual_display': True,
                    'emulator_data': {
                        'adb_ip': '127.0.0.1',
                        'adb_port': 5555,
                        'emulator_path': '',
                        'emulator_args': '',
                    },
                },
                'live': {},
            }
        )
        self.assertEqual(conf.game.control_impl, 'scrcpy')

    def test_scheduler_builds_scrcpy_device_for_custom_emulator(self):
        conf = IaaConfig.model_validate(
            {
                'version': 1,
                'name': 'test',
                'description': 'test',
                'game': {
                    'server': 'jp',
                    'link_account': 'no',
                    'emulator': 'custom',
                    'control_impl': 'scrcpy',
                    'check_emulator': False,
                    'scrcpy_virtual_display': True,
                    'emulator_data': {
                        'adb_ip': '127.0.0.1',
                        'adb_port': 5555,
                        'emulator_path': '',
                        'emulator_args': '',
                    },
                },
                'live': {},
            }
        )

        iaa_service = SimpleNamespace(config=SimpleNamespace(conf=conf))
        scheduler = SchedulerService(iaa_service)

        fake_instance = MagicMock()
        fake_device = MagicMock()
        fake_kotone_conf = SimpleNamespace(
            loop=SimpleNamespace(loop_callbacks=[]),
            device=SimpleNamespace(default_logic_resolution=None, default_scaler_factory=None),
        )

        with (
            patch.dict(sys.modules, {'av': MagicMock()}),
            patch('iaa.application.service.scheduler.asset_path', return_value=r'E:\repo\assets\scrcpy.jar'),
            patch('iaa.application.service.scheduler.os.path.isfile', return_value=True),
            patch('iaa.application.service.scheduler.package_by_server', return_value='com.sega.pjsekai'),
            patch('kotonebot.client.host.create_custom', return_value=fake_instance),
            patch('iaa.application.service.scheduler.init_config_context'),
            patch('kotonebot.config.conf', return_value=fake_kotone_conf),
        ):
            fake_instance.create_device.return_value = fake_device
            scheduler._SchedulerService__prepare_context()

        self.assertIs(scheduler.device, fake_device)
        fake_instance.create_device.assert_called_once()
        recipe, scrcpy_config = fake_instance.create_device.call_args[0]
        self.assertEqual(recipe, 'scrcpy')
        self.assertEqual(scrcpy_config.server_jar_path, r'E:\repo\assets\scrcpy.jar')
        self.assertEqual(scrcpy_config.server_version, '3.3.1')
        self.assertIsNotNone(scrcpy_config.virtual_display)
        assert scrcpy_config.virtual_display is not None
        self.assertTrue(scrcpy_config.virtual_display.enabled)
        self.assertTrue(scrcpy_config.virtual_display.reuse_existing)
        self.assertEqual(scrcpy_config.virtual_display.launch_package, 'com.sega.pjsekai')


if __name__ == '__main__':
    unittest.main()
