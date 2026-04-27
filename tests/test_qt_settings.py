import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from iaa.application.qt.controllers.settings_controller import SettingsController
from iaa.config.base import IaaConfig
from iaa.config.schemas import MuMuEmulatorData


def make_conf() -> IaaConfig:
    return IaaConfig.model_validate(
        {
            'version': 1,
            'name': 'test',
            'description': 'test',
            'game': {
                'server': 'jp',
                'link_account': 'google',
                'emulator': 'mumu_v5',
                'control_impl': 'scrcpy',
                'check_emulator': False,
                'scrcpy_virtual_display': True,
                'emulator_data': {'instance_id': '42'},
            },
            'live': {},
        }
    )


def make_config_service(conf: IaaConfig, *, save: Mock | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        conf=conf,
        save=save or Mock(),
        save_shared=Mock(),
        current_config_name='test',
        shared=SimpleNamespace(telemetry=SimpleNamespace(sentry=None)),
    )


class SettingsControllerTests(unittest.TestCase):
    def test_save_json_forces_tw_link_account_to_no(self) -> None:
        conf = make_conf()
        config_service = make_config_service(conf, save=Mock())
        controller = SettingsController(
            SimpleNamespace(
                config=config_service,
                scheduler=SimpleNamespace(device=None, connect_device=Mock()),
            )
        )
        state = json.loads(controller.stateJson())
        state['game']['server'] = 'tw'
        state['game']['linkAccount'] = 'google_play'
        controller.saveJson(json.dumps(state, ensure_ascii=False))
        self.assertEqual(conf.game.server, 'tw')
        self.assertEqual(conf.game.link_account, 'no')
        config_service.save.assert_not_called()
        config_service.save_shared.assert_called_once()

    @patch('kotonebot.client.host.Mumu12V5Host.list')
    def test_refresh_mumu_instances_preserves_existing_selection(self, list_mock: Mock) -> None:
        list_mock.return_value = [SimpleNamespace(id='42', name='Main'), SimpleNamespace(id='43', name='Alt')]
        conf = make_conf()
        controller = SettingsController(
            SimpleNamespace(
                config=make_config_service(conf, save=Mock()),
                scheduler=SimpleNamespace(device=None, connect_device=Mock()),
            )
        )
        payload = json.loads(controller.refreshMumuInstancesJson())
        self.assertEqual(payload['selectedId'], '42')
        self.assertEqual(len(payload['items']), 3)

    @patch('kotonebot.client.host.Mumu12V5Host.list')
    def test_refresh_mumu_instances_prefers_ui_selected_id(self, list_mock: Mock) -> None:
        list_mock.return_value = [SimpleNamespace(id='42', name='Main'), SimpleNamespace(id='43', name='Alt')]
        conf = make_conf()
        controller = SettingsController(
            SimpleNamespace(
                config=make_config_service(conf, save=Mock()),
                scheduler=SimpleNamespace(device=None, connect_device=Mock()),
            )
        )
        payload = json.loads(controller.refreshMumuInstancesJsonFor('mumu_v5', '43'))
        self.assertEqual(payload['selectedId'], '43')
        self.assertIn('当前选择 ID: 43', payload['statusText'])

    def test_state_json_exposes_saved_mumu_instance(self) -> None:
        conf = make_conf()
        conf.game.emulator_data = MuMuEmulatorData(instance_id='42')
        controller = SettingsController(
            SimpleNamespace(
                config=make_config_service(conf, save=Mock()),
                scheduler=SimpleNamespace(device=None, connect_device=Mock()),
            )
        )
        state = json.loads(controller.stateJson())
        self.assertEqual(state['game']['mumuInstanceId'], '42')


if __name__ == '__main__':
    unittest.main()
