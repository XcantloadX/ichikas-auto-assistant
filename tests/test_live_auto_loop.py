import unittest
from unittest import mock

from iaa.tasks.live import live
from iaa.tasks.live.live import ListLoopPlan, solo_live


class _FakePhase:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def step(self, _message: str) -> None:
        raise AssertionError('phase.step should not run when no AP is available')


class _FakeReporter:
    def message(self, _message: str) -> None:
        pass

    def phase(self, _name: str, total: int | None = None) -> _FakePhase:
        return _FakePhase()


class AutoLiveLoopTests(unittest.TestCase):
    @mock.patch('iaa.tasks.live.live.Loop', return_value=[None, None, None])
    @mock.patch('iaa.tasks.live.live.task_reporter', return_value=_FakeReporter())
    @mock.patch('iaa.tasks.live.live.go_home')
    @mock.patch('iaa.tasks.live.live.start_auto_live', return_value=False)
    @mock.patch('iaa.tasks.live.live._prepare_solo_live')
    def test_list_loop_stops_when_start_auto_live_reports_no_ap(
        self,
        prepare_solo_live: mock.Mock,
        start_auto_live: mock.Mock,
        go_home: mock.Mock,
        _task_reporter: mock.Mock,
        _loop: mock.Mock,
    ) -> None:
        solo_live(ListLoopPlan(loop_count=None, play_mode='game_auto', ap_multiplier='maximum'))

        prepare_solo_live.assert_called_once_with('list_next', None)
        start_auto_live.assert_called_once()
        go_home.assert_called_once()

    @mock.patch('iaa.tasks.live.live.task_reporter', return_value=_FakeReporter())
    @mock.patch('iaa.tasks.live.live.Loop', return_value=[None])
    def test_maximum_ap_multiplier_stops_when_value_no_longer_increases(
        self,
        _loop: mock.Mock,
        _task_reporter: mock.Mock,
    ) -> None:
        device = mock.Mock()
        ocr = mock.Mock()
        resources = mock.Mock()
        values = iter([3, 4, 5, 5])
        ocr.ocr.return_value.squash.return_value.numbers.side_effect = lambda: [next(values)]
        resources.Live.ApMultiplierDialog.TextTip.find.return_value = True

        with mock.patch.dict(
            live.__dict__,
            {'device': device, 'ocr': ocr, 'R': resources, 'sleep': mock.Mock()},
        ):
            live._configure_ap_multiplier('maximum')

        self.assertEqual(device.click.call_count, 3)
        resources.Live.ApMultiplierDialog.ButtonConfirm.wait.return_value.click.assert_called_once()


if __name__ == '__main__':
    unittest.main()
