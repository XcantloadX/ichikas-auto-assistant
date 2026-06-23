import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from iaa.application.qt.controllers.i18n_controller import I18nController
from iaa.application.qt.controllers.preferences_controller import PreferencesController
from iaa.application.qt.controllers.settings_controller import SettingsController
from iaa.config.base import IaaConfig
from iaa.config.schemas import GameConfig, LiveConfig
from iaa.config.shared import SharedConfig


def make_config_service(shared: SharedConfig | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        shared=shared or SharedConfig(),
        save_shared=Mock(),
    )


def make_iaa_service(shared: SharedConfig | None = None) -> SimpleNamespace:
    config = SimpleNamespace(
        conf=IaaConfig(name='test', description='test', game=GameConfig(), live=LiveConfig()),
        shared=shared or SharedConfig(),
        current_config_name='default',
        save=Mock(),
        save_shared=Mock(),
        list=Mock(return_value=['default']),
    )
    return SimpleNamespace(
        config=config,
        scheduler=SimpleNamespace(device=None, connect_device=Mock()),
    )


class QtI18nTests(unittest.TestCase):
    def test_shared_config_normalizes_legacy_language_value(self) -> None:
        shared = SharedConfig.model_validate({'interface': {'language': 'en'}})

        self.assertEqual(shared.interface.language, 'en_US')

    def test_i18n_controller_translates_current_language(self) -> None:
        controller = I18nController('zh_CN')

        self.assertEqual(controller.t('nav.preferences'), '偏好')

        controller.setLanguage('en_US')

        self.assertEqual(controller.language, 'en_US')
        self.assertEqual(controller.t('nav.preferences'), 'Preferences')
        self.assertEqual(controller.t('modal.exit.title'), 'Confirm Exit')
        self.assertEqual(controller.t('config_manager.delete_title'), 'Confirm Delete')
        self.assertEqual(controller.t('control.export_report'), 'Export Report')
        self.assertEqual(controller.t('task.auto_live'), 'Auto Live')
        self.assertEqual(controller.t('task.activity_story'), 'Event Story')
        self.assertEqual(controller.t('status.ready'), 'Ready')
        self.assertEqual(controller.t('progress.task_started'), 'Starting')
        self.assertEqual(controller.t('progress.returning_home'), 'Returning home')
        self.assertEqual(controller.t('notice.save_success'), 'Saved')
        self.assertEqual(controller.t('dialog.save_report.title'), 'Save Report')
        self.assertEqual(controller.t('settings.group.game'), 'Game Settings')
        self.assertEqual(controller.t('auto_live.preset.clear_10'), 'Clear 10 songs')
        self.assertEqual(controller.t('auto_live.ap.maximum'), 'Maximum')
        self.assertEqual(controller.t('auto_live.song.keep'), 'Keep unchanged')

    def test_preferences_language_field_rebuilds_runtime_labels(self) -> None:
        config_service = make_config_service()
        controller = PreferencesController(SimpleNamespace(config=config_service))
        changed_languages: list[str] = []
        changed_interfaces: list[bool] = []
        succeeded: list[str] = []
        controller.languageChanged.connect(changed_languages.append)
        controller.interfaceChanged.connect(lambda: changed_interfaces.append(True))
        controller.operationSucceeded.connect(succeeded.append)

        initial_runtime = json.loads(controller.getRuntime())
        self.assertEqual(initial_runtime['fieldMap']['interface.language']['label'], '界面语言')

        controller.setValue('interface.language', 'en_US')

        updated_runtime = json.loads(controller.getRuntime())
        self.assertEqual(config_service.shared.interface.language, 'en_US')
        self.assertEqual(changed_languages, ['en_US'])
        self.assertEqual(updated_runtime['title'], 'Preferences')
        self.assertEqual(updated_runtime['groups'][0]['title'], 'Data Collection')
        self.assertEqual(updated_runtime['groups'][1]['title'], 'Interface')
        self.assertEqual(updated_runtime['groups'][2]['title'], 'Notifications')
        self.assertEqual(updated_runtime['groups'][3]['title'], 'Hotkeys')
        self.assertEqual(
            updated_runtime['fieldMap']['telemetry.sentry']['label'],
            'Send anonymous error reports automatically',
        )
        self.assertEqual(updated_runtime['fieldMap']['interface.language']['label'], 'Interface language')
        self.assertEqual(updated_runtime['fieldMap']['interface.window_style']['label'], 'Window background style')
        self.assertEqual(
            updated_runtime['fieldMap']['interface.window_style']['options'][0]['label'],
            'Auto',
        )
        self.assertEqual(updated_runtime['fieldMap']['notify.push.type']['label'], 'Push type')
        self.assertEqual(
            updated_runtime['fieldMap']['notify.push.type']['options'][0]['label'],
            'Custom command',
        )
        self.assertEqual(updated_runtime['fieldMap']['hotkeys.start']['label'], 'Start script')
        self.assertEqual(
            updated_runtime['fieldMap']['hotkeys.start']['props']['idlePlaceholder'],
            'Click to set',
        )
        self.assertEqual(
            updated_runtime['fieldMap']['hotkeys.start']['props']['recordingPlaceholder'],
            'Press shortcut... (Esc to cancel)',
        )
        self.assertEqual(updated_runtime['fieldMap']['hotkeys.start']['props']['clearText'], 'Clear')
        self.assertEqual(changed_interfaces, [True])

        self.assertTrue(controller.save())
        self.assertEqual(succeeded, ['Saved'])
        config_service.save_shared.assert_called_once()

    def test_preferences_interface_field_notifies_app_shell(self) -> None:
        config_service = make_config_service()
        controller = PreferencesController(SimpleNamespace(config=config_service))
        changed_interfaces: list[bool] = []
        controller.interfaceChanged.connect(lambda: changed_interfaces.append(True))

        controller.setValue('interface.color_scheme', 'dark')

        self.assertEqual(config_service.shared.interface.color_scheme, 'dark')
        self.assertEqual(changed_interfaces, [True])

    def test_settings_controller_rebuilds_config_labels_for_language(self) -> None:
        service = make_iaa_service()
        controller = SettingsController(service)

        initial_runtime = json.loads(controller.getRuntime())
        self.assertEqual(initial_runtime['title'], '配置')
        self.assertEqual(initial_runtime['groups'][0]['title'], '游戏设置')
        self.assertEqual(initial_runtime['fieldMap']['game.server']['label'], '服务器')

        service.config.shared.interface.language = 'en_US'
        controller.setLanguage('en_US')

        updated_runtime = json.loads(controller.getRuntime())
        self.assertFalse(updated_runtime['dirty'])
        self.assertEqual(updated_runtime['title'], 'Config')
        self.assertEqual(updated_runtime['groups'][0]['title'], 'Game Settings')
        self.assertEqual(updated_runtime['groups'][1]['title'], 'Device Settings')
        self.assertEqual(updated_runtime['fieldMap']['game.server']['label'], 'Server')
        self.assertEqual(
            updated_runtime['fieldMap']['game.server']['options'][3],
            {'value': 'en', 'label': 'Global / EN'},
        )
        self.assertEqual(
            updated_runtime['fieldMap']['device.lifecycleType']['options'][2],
            {'value': 'custom', 'label': 'Custom emulator'},
        )
        self.assertEqual(
            updated_runtime['fieldMap']['device.mumuInstanceId']['options'][0],
            {'value': '', 'label': 'Default'},
        )
        self.assertEqual(
            updated_runtime['fieldMap']['device.mumuInstanceId']['props']['refreshText'],
            'Refresh',
        )
        self.assertEqual(
            updated_runtime['fieldMap']['device.resolutionMethod']['props']['resetText'],
            'Reset Resolution',
        )
        self.assertEqual(
            updated_runtime['fieldMap']['live.apMultiplier']['options'][0],
            {'value': '保持现状', 'label': 'Keep current'},
        )
        self.assertEqual(
            updated_runtime['fieldMap']['challengeLive.characters']['options'][1]['options'][0]['label'],
            'Ichika Hoshino',
        )
        self.assertEqual(
            updated_runtime['fieldMap']['eventShop.selectedItems']['props']['addText'],
            '← Add',
        )


if __name__ == '__main__':
    unittest.main()
