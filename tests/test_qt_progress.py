import time
import unittest

from iaa.application.qt.models.progress import ProgressState, progress_event_to_state
from iaa.progress import TaskProgressEvent


class ProgressBridgeStateTests(unittest.TestCase):
    def test_task_started_sets_status_and_percent(self) -> None:
        state = progress_event_to_state(
            TaskProgressEvent(
                run_id='run',
                task_id='solo_live',
                task_name='单人演出',
                timestamp=time.time(),
                type='task_started',
                payload={'message': '开始执行', 'run_total_tasks': 2, 'run_completed_tasks': 0},
            )
        )
        self.assertEqual(state.progress_percent, 0)
        self.assertEqual(state.status_text, '单人演出 > 开始执行')

    def test_phase_message_updates_total_progress(self) -> None:
        prev = ProgressState(status_text='单人演出 > 开始执行', progress_percent=0)
        state = progress_event_to_state(
            TaskProgressEvent(
                run_id='run',
                task_id='solo_live',
                task_name='单人演出',
                timestamp=time.time(),
                type='step',
                payload={
                    'message': '已完成 1 次',
                    'percent': 50,
                    'run_total_tasks': 2,
                    'run_completed_tasks': 1,
                    'phase_path': [{'name': '列表循环', 'current': 1, 'total': 2}],
                },
            ),
            prev,
        )
        self.assertEqual(state.progress_percent, 75)
        self.assertIn('列表循环 (1/2)', state.status_text)

    def test_task_failed_sets_error_text(self) -> None:
        state = progress_event_to_state(
            TaskProgressEvent(
                run_id='run',
                task_id='solo_live',
                task_name='单人演出',
                timestamp=time.time(),
                type='task_failed',
                payload={'error': 'boom'},
            )
        )
        self.assertEqual(state.last_error_text, '执行「单人演出」时出错：boom')
        self.assertEqual(state.status_text, '执行「单人演出」时出错：boom')


if __name__ == '__main__':
    unittest.main()
