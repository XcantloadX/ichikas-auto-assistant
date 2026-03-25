import unittest

from iaa.application.desktop.schema.dsl import SettingsRegistry
from iaa.application.desktop.schema.reactive import Signal, state_from_config, to_config
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


class ReactiveAdapterTests(unittest.TestCase):
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

    def test_state_roundtrip(self) -> None:
        conf = self._make_config()
        state = state_from_config(conf)

        state.live.song_name.set('独りんぼエンヴィー')
        state.game.check_emulator.set(False)
        state.cm.watch_ad_wait_sec.set(88)

        rebuilt = to_config(state, IaaConfig)

        self.assertEqual(rebuilt.live.song_name, '独りんぼエンヴィー')
        self.assertFalse(rebuilt.game.check_emulator)
        self.assertEqual(rebuilt.cm.watch_ad_wait_sec, 88)


class DslRegistryTests(unittest.TestCase):
    def test_build_screen_spec(self) -> None:
        registry = SettingsRegistry()
        fake_signal = Signal('x')

        @registry.section('live', '演出设置')
        def make_live(ui) -> None:
            ui.select('song_name', '歌曲名称', bind=fake_signal, options=['保持不变', 'メルト'])

        spec = registry.build(screen_key='settings', screen_title='配置')

        self.assertEqual(spec.key, 'settings')
        self.assertEqual(len(spec.sections), 1)
        self.assertEqual(spec.sections[0].key, 'live')
        self.assertEqual(spec.sections[0].fields[0].key, 'song_name')


if __name__ == '__main__':
    unittest.main()
