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
                'device': {
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
                },
                'game': {
                    'server': 'jp',
                    'link_account': 'no',
                },
            }
        )
        self.assertEqual(conf.device.control_impl, 'scrcpy')
        self.assertTrue(conf.device.scrcpy_virtual_display)

    def test_scheduler_builds_scrcpy_device_for_custom_emulator(self):
        conf = IaaConfig.model_validate(
            {
                'version': 1,
                'name': 'test',
                'description': 'test',
                'device': {
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
                },
                'game': {
                    'server': 'jp',
                    'link_account': 'no',
                },
            }
        )

        iaa_service = SimpleNamespace(config=SimpleNamespace(conf=conf))
        scheduler = SchedulerService(iaa_service)

        fake_device = MagicMock()
        fake_kotone_conf = SimpleNamespace(
            loop=SimpleNamespace(loop_callbacks=[]),
            device=SimpleNamespace(default_logic_resolution=None, default_scaler_factory=None),
        )
        mock_host = MagicMock()
        mock_host.running.return_value = True
        mock_host.create_device.return_value = fake_device

        with (
            patch.dict(sys.modules, {'av': MagicMock()}),
            patch('iaa.application.service.device_factory.asset_path', return_value=r'E:\repo\assets\scrcpy.jar'),
            patch('iaa.application.service.device_factory.os.path.isfile', return_value=True),
            patch('iaa.application.service.device_factory.package_by_server', return_value='com.sega.pjsekai'),
            patch('iaa.application.service.device_factory.CustomEmulatorInstance', return_value=mock_host),
            patch('iaa.application.service.scheduler.init_config_context'),
            patch('kotonebot.config.conf', return_value=fake_kotone_conf),
        ):
            scheduler._SchedulerService__prepare_context()

        self.assertIs(scheduler.device, fake_device)
        mock_host.create_device.assert_called_once()
        scrcpy_config = mock_host.create_device.call_args.args[1]
        self.assertEqual(scrcpy_config.server_jar_path, r'E:\repo\assets\scrcpy.jar')
        self.assertEqual(scrcpy_config.server_version, '3.3.1')
        self.assertIsNotNone(scrcpy_config.virtual_display)
        assert scrcpy_config.virtual_display is not None
        self.assertTrue(scrcpy_config.virtual_display.enabled)
        self.assertTrue(scrcpy_config.virtual_display.reuse_existing)
        self.assertEqual(scrcpy_config.virtual_display.launch_package, 'com.sega.pjsekai')

    def test_scheduler_calls_ensure_device_started_before_prepare_context(self):
        conf = IaaConfig.model_validate(
            {
                'version': 1,
                'name': 'test',
                'description': 'test',
                'device': {
                    'lifecycle': {'type': 'mumu_v5'},
                    'connection': {'type': 'auto'},
                    'control_impl': 'scrcpy',
                    'scrcpy_virtual_display': True,
                    'resolution_method': 'keep',
                    'stop_on_finish': False,
                },
                'game': {'server': 'jp', 'link_account': 'no'},
                'developer': {'dump_sekai_home_enabled': False, 'sekai_dump_post_process': False, 'screen_recording_enabled': False},
                'scheduler': {'continue_on_error': False},
                'tasks': {},
            }
        )
        iaa_service = SimpleNamespace(config=SimpleNamespace(conf=conf))
        scheduler = SchedulerService(iaa_service)
        calls: list[str] = []

        def ensure_started() -> None:
            calls.append('ensure_started')

        scheduler._ensure_device_started = ensure_started

        fake_device = MagicMock()

        with patch.object(
            scheduler._device_factory,
            'create_device_for_current_config',
            return_value=(SimpleNamespace(stop_callback=None), fake_device),
        ):
            scheduler._SchedulerService__prepare_context()

        self.assertEqual(calls, ['ensure_started'])
        self.assertIs(scheduler.device, fake_device)

    def test_scheduler_stops_device_after_completion(self):
        conf = IaaConfig.model_validate(
            {
                'version': 1,
                'name': 'test',
                'description': 'test',
                'device': {
                    'lifecycle': {'type': 'mumu_v5'},
                    'connection': {'type': 'auto'},
                    'control_impl': 'scrcpy',
                    'scrcpy_virtual_display': True,
                    'resolution_method': 'keep',
                    'stop_on_finish': False,
                },
                'game': {'server': 'jp', 'link_account': 'no'},
                'developer': {'dump_sekai_home_enabled': False, 'sekai_dump_post_process': False, 'screen_recording_enabled': False},
                'scheduler': {'continue_on_error': False},
                'tasks': {},
            }
        )
        iaa_service = SimpleNamespace(config=SimpleNamespace(conf=conf))
        scheduler = SchedulerService(iaa_service)
        fake_device = MagicMock()

        def fake_prepare_context() -> None:
            scheduler.device = fake_device
            scheduler._device_started = True

        with (
            patch.object(scheduler, '_SchedulerService__prepare_context', fake_prepare_context),
            patch.object(scheduler, '_get_enabled_tasks', return_value=[]),
        ):
            scheduler.start_regular(run_in_thread=False)

        fake_device.stop.assert_called_once()
        self.assertIsNone(scheduler.device)


if __name__ == '__main__':
    unittest.main()