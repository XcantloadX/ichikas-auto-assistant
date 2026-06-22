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

    def test_preferences_language_field_rebuilds_runtime_labels(self) -> None:
        config_service = make_config_service()
        controller = PreferencesController(SimpleNamespace(config=config_service))
        changed_languages: list[str] = []
        controller.languageChanged.connect(changed_languages.append)

        initial_runtime = json.loads(controller.getRuntime())
        self.assertEqual(initial_runtime['fieldMap']['interface.language']['label'], '界面语言')

        controller.setValue('interface.language', 'en_US')

        updated_runtime = json.loads(controller.getRuntime())
        self.assertEqual(config_service.shared.interface.language, 'en_US')
        self.assertEqual(changed_languages, ['en_US'])
        self.assertEqual(updated_runtime['title'], 'Preferences')
        self.assertEqual(updated_runtime['fieldMap']['interface.language']['label'], 'Interface language')

        self.assertTrue(controller.save())
        config_service.save_shared.assert_called_once()


if __name__ == '__main__':
    unittest.main()
