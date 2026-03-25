import unittest

from iaa.application.desktop.schema.dsl import SectionBuilder, SettingsRegistry
from iaa.application.desktop.schema.reactive import Signal, of, signal, watch
from iaa.config.base import IaaConfig
from iaa.config.schemas import EventStoreConfig, ShopItem


class SignalTests(unittest.TestCase):
    def test_signal_subscribe_and_set(self) -> None:
        signal = Signal(1)
        called = []

        unsubscribe = signal.subscribe(lambda value: called.append(value))
        signal.set(2)
        signal.set(2)
        unsubscribe()
        signal.set(3)

        self.assertEqual(called, [2])


class PathSignalTests(unittest.TestCase):
    def _make_config(self) -> IaaConfig:
        return IaaConfig(
            name='default',
            description='test',
            game={
                'server': 'jp',
                'link_account': 'google',
                'emulator': 'mumu_v5',
                'control_impl': 'nemu_ipc',
                'check_emulator': True,
                'emulator_data': {'instance_id': '0'},
            },
            live={
                'song_name': 'メルト',
                'auto_set_unit': False,
                'ap_multiplier': 10,
                'append_fc': False,
                'prepend_random': False,
            },
            challenge_live={},
            cm={'watch_ad_wait_sec': 70},
            event_shop=EventStoreConfig(purchase_items=[ShopItem.ITEM_CRYSTAL]),
            scheduler={},
        )

    def test_signal_of_path_read_write(self) -> None:
        conf = self._make_config()
        song_name = signal(of(conf).live.song_name)
        wait_sec = signal(of(conf).cm.watch_ad_wait_sec)

        song_name.set('独りんぼエンヴィー')
        wait_sec.set(88)

        self.assertEqual(conf.live.song_name, '独りんぼエンヴィー')
        self.assertEqual(conf.cm.watch_ad_wait_sec, 88)
        self.assertEqual(song_name.get(), '独りんぼエンヴィー')

    def test_watch_notifies_subscriber(self) -> None:
        conf = self._make_config()
        server = signal(of(conf).game.server)
        called: list[str] = []
        unwatch = watch(server, lambda value: called.append(value))
        server.set('tw')
        unwatch()
        server.set('jp')

        self.assertEqual(called, ['tw'])


class DslRegistryTests(unittest.TestCase):
    def test_build_screen_spec(self) -> None:
        registry = SettingsRegistry()
        fake_signal = Signal('x')

        @registry.section('live', '演出设置')
        def make_live(ui: SectionBuilder) -> None:
            ui.select('song_name', '歌曲名称', bind=fake_signal, options=['保持不变', 'メルト'])

        spec = registry.build(screen_key='settings', screen_title='配置')

        self.assertEqual(spec.key, 'settings')
        self.assertEqual(len(spec.sections), 1)
        self.assertEqual(spec.sections[0].key, 'live')
        self.assertEqual(spec.sections[0].items[0].key, 'song_name')

    def test_build_fragment_spec(self) -> None:
        registry = SettingsRegistry()
        fake_signal = Signal('x')
        switch_signal = Signal('custom')

        @registry.section('game', '游戏设置')
        def make_game(ui: SectionBuilder) -> None:
            fragment = ui.fragment('custom_emulator', visible_if=lambda: switch_signal.get() == 'custom', depends_on=[switch_signal])
            fragment.text_input('adb_ip', 'ADB IP', bind=fake_signal)
            fragment.commit()

        spec = registry.build(screen_key='settings', screen_title='配置')
        self.assertEqual(len(spec.sections[0].items), 1)
        fragment = spec.sections[0].items[0]
        self.assertEqual(fragment.key, 'custom_emulator')
        self.assertEqual(len(fragment.fields), 1)
        self.assertEqual(fragment.fields[0].key, 'adb_ip')

    def test_build_fragment_spec_with_context_manager(self) -> None:
        registry = SettingsRegistry()
        fake_signal = Signal('x')
        switch_signal = Signal('custom')

        @registry.section('game', '游戏设置')
        def make_game(ui: SectionBuilder) -> None:
            with ui.fragment('custom_emulator', visible_if=lambda: switch_signal.get() == 'custom', depends_on=[switch_signal]) as frag:
                frag.text_input('adb_ip', 'ADB IP', bind=fake_signal)

        spec = registry.build(screen_key='settings', screen_title='配置')
        self.assertEqual(len(spec.sections[0].items), 1)
        fragment = spec.sections[0].items[0]
        self.assertEqual(fragment.key, 'custom_emulator')
        self.assertEqual(fragment.fields[0].key, 'adb_ip')


if __name__ == '__main__':
    unittest.main()
