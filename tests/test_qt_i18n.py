import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from iaa.application.qt.controllers.i18n_controller import I18nController
from iaa.application.qt.controllers.preferences_controller import PreferencesController
from iaa.application.qt.controllers.settings_controller import SettingsController
from iaa.config import manager
from iaa.config.base import IaaConfig
from iaa.config.schemas import GameConfig, LiveConfig
from iaa.config.shared import SharedConfig


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
        self.assertEqual(controller.t('app.name'), '一歌小助手')
        self.assertEqual(controller.t('app.name_full'), '一歌小助手 iaa')
        self.assertEqual(controller.t('app.name_sidebar'), '一歌小助手')

        controller.setLanguage('en_US')

        self.assertEqual(controller.language, 'en_US')
        self.assertEqual(controller.t('nav.preferences'), 'Preferences')
        self.assertEqual(controller.t('app.name'), 'Ichika Auto Assistant')
        self.assertEqual(controller.t('app.name_full'), 'Ichika Auto Assistant (iaa)')
        self.assertEqual(controller.t('app.name_sidebar'), 'IAA')
        self.assertEqual(controller.t('app.window_title_macos'), 'Ichika Auto Assistant (macOS)')
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
        self.assertEqual(controller.t('auto_live.preset.clear_10'), 'CLEARx10')
        self.assertEqual(controller.t('auto_live.ap.maximum'), 'Maximum')
        self.assertEqual(controller.t('auto_live.song.keep'), 'Keep current')

    def test_preferences_language_field_applies_on_save(self) -> None:
        """语言字段保存后应触发 languageChanged 并写盘（草稿模式）。"""
        with tempfile.TemporaryDirectory() as root:
            manager.config_path = str(Path(root) / 'conf')
            manager.write_shared(SharedConfig())
            changed_languages: list[str] = []
            succeeded: list[str] = []
            controller = PreferencesController()
            controller.languageChanged.connect(changed_languages.append)
            controller.operationSucceeded.connect(succeeded.append)

            controller.setField('interface.language', 'en_US')
            self.assertTrue(controller.isDirty())
            # 保存前 shared 不应变化
            self.assertEqual(manager.read_shared().interface.language, 'auto')

            self.assertTrue(controller.save())

            self.assertEqual(changed_languages, ['en_US'])
            self.assertEqual(succeeded, ['Saved'])
            self.assertEqual(manager.read_shared().interface.language, 'en_US')
            self.assertFalse(controller.isDirty())

    def test_preferences_color_scheme_field_saves_to_shared(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            manager.config_path = str(Path(root) / 'conf')
            manager.write_shared(SharedConfig())
            controller = PreferencesController()

            controller.setField('interface.color_scheme', 'dark')

            self.assertTrue(controller.save())

            self.assertEqual(manager.read_shared().interface.color_scheme, 'dark')

    def test_settings_controller_labels_resolve_for_language(self) -> None:
        """选项标签应按当前 GUI 语言解析为字符串（而非 TStr 对象）。"""
        service = make_iaa_service()
        controller = SettingsController(service)

        servers = json.loads(controller.serverOptionsJson())
        self.assertEqual(servers[0], {'value': 'jp', 'label': '日服'})

        service.config.shared.interface.language = 'en_US'
        servers = json.loads(controller.serverOptionsJson())
        self.assertEqual(servers[0], {'value': 'jp', 'label': 'JP'})
        # feat/en-server 新增的 en 服务器选项应保留
        self.assertEqual(
            [o['value'] for o in servers],
            ['jp', 'tw', 'cn', 'en'],
        )

        lifecycles = json.loads(controller.lifecycleOptionsJson())
        by_value = {o['value']: o['label'] for o in lifecycles}
        self.assertEqual(by_value['custom'], 'Custom emulator')
        self.assertEqual(by_value['none'], 'Physical device / manual management')

        issues = controller._collect_issues({'device': {'connection': {'type': 'tcp'}, 'lifecycle': {}}}, 'en_US')
        self.assertTrue(any(i['message'] == 'Port is required' for i in issues))

    def test_settings_controller_language_getter_takes_precedence(self) -> None:
        """注入的 get_language 应优先于 config.shared（偏好保存后 shared 不热更新）。"""
        service = make_iaa_service()
        language = {'value': 'zh_CN'}
        controller = SettingsController(service, get_language=lambda: language['value'])

        self.assertEqual(json.loads(controller.serverOptionsJson())[0]['label'], '日服')

        language['value'] = 'en_US'
        self.assertEqual(json.loads(controller.serverOptionsJson())[0]['label'], 'JP')

    def test_event_shop_items_follow_ui_language(self) -> None:
        """商店道具 label 应跟随界面语言（zh 简中 / en 英文），与所选服务器无关。"""
        service = make_iaa_service()
        controller = SettingsController(service)

        by_value = {i['value']: i['label'] for i in json.loads(controller.eventShopItemsJson())}
        self.assertEqual(by_value['magic_cloth'], '魔法之布')

        # 切换服务器不影响显示名
        controller.setField('game.server', 'tw')
        by_value = {i['value']: i['label'] for i in json.loads(controller.eventShopItemsJson())}
        self.assertEqual(by_value['magic_cloth'], '魔法之布')

        en_controller = SettingsController(service, get_language=lambda: 'en_US')
        by_value = {i['value']: i['label'] for i in json.loads(en_controller.eventShopItemsJson())}
        self.assertEqual(by_value['magic_cloth'], 'Magic Cloth')
        self.assertEqual(by_value['coin_100000'], 'Coins ×100000')

    def test_settings_controller_profile_messages_use_language(self) -> None:
        service = make_iaa_service()
        controller = SettingsController(service)
        service.config.list = Mock(return_value=['alpha'])
        service.config.current_config_name = 'alpha'

        profiles = json.loads(controller.profilesJson())
        self.assertEqual(profiles['profiles'], [{'value': 'alpha', 'label': 'alpha'}])


if __name__ == '__main__':
    unittest.main()
