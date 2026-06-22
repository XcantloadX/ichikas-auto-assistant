import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from iaa.application.qt.controllers.i18n_controller import I18nController
from iaa.application.qt.controllers.preferences_controller import PreferencesController
from iaa.config.shared import SharedConfig


def make_config_service(shared: SharedConfig | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        shared=shared or SharedConfig(),
        save_shared=Mock(),
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
        self.assertEqual(controller.t('notice.save_success'), 'Saved')
        self.assertEqual(controller.t('dialog.save_report.title'), 'Save Report')

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


if __name__ == '__main__':
    unittest.main()
