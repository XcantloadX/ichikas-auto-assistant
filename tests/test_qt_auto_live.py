import unittest

from iaa.tasks.live.live import auto_live_payload_to_plan
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
                'songName': '保持不变',
            }
        )
        self.assertIsInstance(plan, ListLoopPlan)
        assert isinstance(plan, ListLoopPlan)
        self.assertIsNone(plan.loop_count)
        self.assertEqual(plan.loop_song_mode, 'random')
        self.assertEqual(plan.play_mode, 'script_auto')
        self.assertTrue(plan.debug_enabled)
        self.assertEqual(plan.ap_multiplier, 0)

    def test_invalid_count_raises(self) -> None:
        with self.assertRaises(ValueError):
            auto_live_payload_to_plan(
                {
                    'countMode': 'specify',
                    'count': '0',
                    'loopMode': 'list',
                    'playMode': 'game_auto',
                    'apMultiplier': '保持现状',
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


if __name__ == '__main__':
    unittest.main()
