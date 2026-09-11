import json
import tempfile
import unittest
from pathlib import Path

from iaa.application.qt.models.auto_live import (
    AutoLivePayloadError,
    auto_live_payload_to_plan,
    auto_live_preset_label_key,
    builtin_auto_presets,
)
from iaa.config.live_presets import LivePresetManager
from iaa.i18n import translate
from iaa.tasks.live.auto_live_constants import AP_KEEP_UNCHANGED, LAST_PRESET_NAME, SONG_KEEP_UNCHANGED
from iaa.tasks.live.live import ListLoopPlan, SingleLoopPlan
from iaa.tasks.live.auto_live_core import latency_ms_to_px


class AutoLivePayloadTests(unittest.TestCase):
    def test_single_loop_payload_becomes_single_loop_plan(self) -> None:
        plan = auto_live_payload_to_plan(
            {
                'countMode': 'specify',
                'count': '3',
                'loopMode': 'single',
                'playMode': 'game_auto',
                'debugEnabled': False,
                'autoSetUnit': True,
                'apMultiplier': '2',
                'songName': 'メルト',
            }
        )
        self.assertIsInstance(plan, SingleLoopPlan)
        assert isinstance(plan, SingleLoopPlan)
        self.assertEqual(plan.loop_count, 3)
        self.assertEqual(plan.song_select_mode, 'specified')
        self.assertEqual(plan.song_name, 'メルト')
        self.assertEqual(plan.ap_multiplier, 2)
        self.assertTrue(plan.auto_set_unit)

    def test_list_random_payload_becomes_list_loop_plan(self) -> None:
        plan = auto_live_payload_to_plan(
            {
                'countMode': 'all',
                'count': '',
                'loopMode': 'random',
                'playMode': 'script_auto',
                'debugEnabled': True,
                'autoSetUnit': False,
                'apMultiplier': '0',
                'songName': SONG_KEEP_UNCHANGED,
            }
        )
        self.assertIsInstance(plan, ListLoopPlan)
        assert isinstance(plan, ListLoopPlan)
        self.assertIsNone(plan.loop_count)
        self.assertEqual(plan.loop_song_mode, 'random')
        self.assertEqual(plan.play_mode, 'script_auto')
        self.assertTrue(plan.debug_enabled)
        self.assertEqual(plan.ap_multiplier, 0)

    def test_maximum_ap_multiplier_payload(self) -> None:
        plan = auto_live_payload_to_plan(
            {
                'countMode': 'all',
                'count': '',
                'loopMode': 'list',
                'playMode': 'game_auto',
                'apMultiplier': 'maximum',
            }
        )
        self.assertIsInstance(plan, ListLoopPlan)
        self.assertEqual(plan.ap_multiplier, 'maximum')

    def test_ap_keep_payloads_become_none(self) -> None:
        for raw in (AP_KEEP_UNCHANGED, '保持现状', '', None):
            with self.subTest(raw=raw):
                plan = auto_live_payload_to_plan(
                    {
                        'countMode': 'all',
                        'count': '',
                        'loopMode': 'list',
                        'playMode': 'game_auto',
                        'apMultiplier': raw,
                    }
                )
                self.assertIsNone(plan.ap_multiplier)

    def test_numeric_ap_multiplier_payload_becomes_int(self) -> None:
        for raw, expected in (('0', 0), ('10', 10)):
            with self.subTest(raw=raw):
                plan = auto_live_payload_to_plan(
                    {
                        'countMode': 'all',
                        'count': '',
                        'loopMode': 'list',
                        'playMode': 'game_auto',
                        'apMultiplier': raw,
                    }
                )
                self.assertEqual(plan.ap_multiplier, expected)

    def test_out_of_range_ap_multiplier_raises(self) -> None:
        with self.assertRaises(ValueError):
            auto_live_payload_to_plan(
                {
                    'countMode': 'all',
                    'count': '',
                    'loopMode': 'list',
                    'playMode': 'game_auto',
                    'apMultiplier': '11',
                }
            )

    def test_song_name_sentinel_and_legacy_keep_become_none(self) -> None:
        for raw in (SONG_KEEP_UNCHANGED, '保持不变', ''):
            with self.subTest(raw=raw):
                plan = auto_live_payload_to_plan(
                    {
                        'countMode': 'all',
                        'count': '',
                        'loopMode': 'single',
                        'playMode': 'game_auto',
                        'songName': raw,
                    }
                )
                self.assertIsInstance(plan, SingleLoopPlan)
                assert isinstance(plan, SingleLoopPlan)
                self.assertIsNone(plan.song_name)
                self.assertEqual(plan.song_select_mode, 'current')

    def test_invalid_count_raises(self) -> None:
        with self.assertRaises(ValueError):
            auto_live_payload_to_plan(
                {
                    'countMode': 'specify',
                    'count': '0',
                    'loopMode': 'list',
                    'playMode': 'game_auto',
                    'apMultiplier': AP_KEEP_UNCHANGED,
                }
            )

    def test_latency_ms_payload(self) -> None:
        plan = auto_live_payload_to_plan(
            {
                'countMode': 'all',
                'loopMode': 'list',
                'playMode': 'script_auto',
                'latencyCompensationMs': '150',
            }
        )
        assert isinstance(plan, ListLoopPlan)
        self.assertEqual(plan.latency_compensation_ms, 150)

    def test_latency_ms_defaults_to_zero(self) -> None:
        plan = auto_live_payload_to_plan(
            {
                'countMode': 'all',
                'loopMode': 'list',
                'playMode': 'game_auto',
            }
        )
        self.assertEqual(plan.latency_compensation_ms, 0)

    def test_invalid_latency_ms_raises(self) -> None:
        for bad in ('-5', 'abc', '2001'):
            with self.assertRaises(ValueError, msg=f'latency={bad}'):
                auto_live_payload_to_plan(
                    {
                        'countMode': 'all',
                        'loopMode': 'list',
                        'playMode': 'script_auto',
                        'latencyCompensationMs': bad,
                    }
                )

    def test_legacy_px_key_raises(self) -> None:
        with self.assertRaises(ValueError):
            auto_live_payload_to_plan(
                {
                    'countMode': 'all',
                    'loopMode': 'list',
                    'playMode': 'script_auto',
                    'latencyCompensationPx': '60',
                }
            )

    def test_latency_ms_to_px(self) -> None:
        self.assertEqual(latency_ms_to_px(0), 0)
        # 流速 1：D=(0.74-0.08)*720=475.2px，T=4.0s，线速系数 2.6221
        # 100ms -> 100/1000*475.2*2.6221/4.0 = 31.15 -> 31
        self.assertEqual(latency_ms_to_px(100), 31)
        with self.assertRaises(ValueError):
            latency_ms_to_px(-1)
        with self.assertRaises(ValueError):
            latency_ms_to_px(2001)


class AutoLivePayloadErrorTests(unittest.TestCase):
    """payload 解析错误应携带 i18n 键与参数；str() 渲染 zh_CN 默认文本（CLI 输出）。"""

    def test_count_error_carries_key(self) -> None:
        with self.assertRaises(AutoLivePayloadError) as cm:
            auto_live_payload_to_plan({'countMode': 'specify', 'count': '0', 'loopMode': 'list'})
        self.assertEqual(cm.exception.key, 'auto_live.error.count_positive')
        self.assertEqual(cm.exception.params, {})
        self.assertEqual(str(cm.exception), '指定次数必须为正整数。')

    def test_unknown_count_mode_carries_mode_param(self) -> None:
        with self.assertRaises(AutoLivePayloadError) as cm:
            auto_live_payload_to_plan({'countMode': 'bogus', 'loopMode': 'list'})
        self.assertEqual(cm.exception.key, 'auto_live.error.unknown_count_mode')
        self.assertEqual(cm.exception.params, {'mode': 'bogus'})
        self.assertEqual(str(cm.exception), '未知的次数模式：bogus')

    def test_unknown_loop_mode_carries_mode_param(self) -> None:
        with self.assertRaises(AutoLivePayloadError) as cm:
            auto_live_payload_to_plan({'countMode': 'all', 'loopMode': 'bogus'})
        self.assertEqual(cm.exception.key, 'auto_live.error.unknown_loop_mode')
        self.assertEqual(cm.exception.params, {'mode': 'bogus'})

    def test_non_numeric_ap_multiplier_is_structured_error(self) -> None:
        """此前此处泄漏 Python 原生英文 ValueError，应归一为结构化错误。"""
        with self.assertRaises(AutoLivePayloadError) as cm:
            auto_live_payload_to_plan({'countMode': 'all', 'loopMode': 'list', 'apMultiplier': 'abc'})
        self.assertEqual(cm.exception.key, 'auto_live.error.ap_multiplier')
        self.assertEqual(str(cm.exception), 'AP 倍率必须在 0 到 10 之间，或为 maximum。')

    def test_error_text_resolves_for_ui_language(self) -> None:
        """控制器渲染路径：translate 取模板、params 格式化。"""
        with self.assertRaises(AutoLivePayloadError) as cm:
            auto_live_payload_to_plan({'countMode': 'bogus', 'loopMode': 'list'})
        text = translate('en_US', cm.exception.key)
        self.assertEqual(text.format(**cm.exception.params), 'Unknown count mode: bogus')


class AutoLivePresetMigrationTests(unittest.TestCase):
    """last_auto.json 语义上只代表"上次设定"：name 恒为 LAST_PRESET_NAME，
    历史版本强制写入的展示名等残留值在读取时统一归一化。"""

    LEGACY_NAMES = ('上次设定', 'CLEAR 10 首歌', 'FC 10 次', '队长次数', '脚本x999', '自定义名字')

    def _write_last_auto(self, preset_dir: Path, name: str) -> None:
        plan = ListLoopPlan(loop_count=10, play_mode='game_auto', ap_multiplier=1)
        payload = {'version': 1, 'name': name, 'plan': plan.model_dump(mode='json')}
        (preset_dir / 'last_auto.json').write_text(
            json.dumps(payload, ensure_ascii=False), encoding='utf-8'
        )

    def test_non_sentinel_name_loads_as_last_preset(self) -> None:
        for legacy in self.LEGACY_NAMES:
            with self.subTest(legacy=legacy), tempfile.TemporaryDirectory() as root:
                preset_dir = Path(root)
                self._write_last_auto(preset_dir, legacy)
                preset = LivePresetManager(preset_dir=preset_dir).load_last_auto()
                self.assertIsNotNone(preset)
                assert preset is not None
                self.assertEqual(preset.name, LAST_PRESET_NAME)

    def test_stable_id_passes_through(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            preset_dir = Path(root)
            self._write_last_auto(preset_dir, LAST_PRESET_NAME)
            preset = LivePresetManager(preset_dir=preset_dir).load_last_auto()
            assert preset is not None
            self.assertEqual(preset.name, LAST_PRESET_NAME)

    def test_builtin_preset_payloads_resolve_label_keys(self) -> None:
        for payload in builtin_auto_presets():
            with self.subTest(name=payload['name']):
                self.assertIsNotNone(auto_live_preset_label_key(str(payload['name'])))
        self.assertEqual(auto_live_preset_label_key(LAST_PRESET_NAME), 'auto_live.preset.last')

    def test_unmigrated_display_name_is_not_reverse_matched(self) -> None:
        """展示名反查已移除；未迁移的名字应由读取路径归一化，而非 label 层猜测。"""
        self.assertIsNone(auto_live_preset_label_key('上次设定'))
        self.assertIsNone(auto_live_preset_label_key('队长次数'))


if __name__ == '__main__':
    unittest.main()
