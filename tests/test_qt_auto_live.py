import unittest

from iaa.tasks.live.auto_live_constants import AP_KEEP_UNCHANGED, SONG_KEEP_UNCHANGED
from iaa.application.qt.models.auto_live import auto_live_payload_to_plan
from iaa.tasks.live.live import ListLoopPlan, SingleLoopPlan


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


if __name__ == '__main__':
    unittest.main()
