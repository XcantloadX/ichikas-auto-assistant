import unittest
from types import SimpleNamespace
from unittest import mock

from iaa.main import execute_cli_action, parse_cli_action


class CliParseTests(unittest.TestCase):
    def test_run_parses_configured_regular(self) -> None:
        action = parse_cli_action(['run'])
        self.assertEqual(action.kind, 'run_regular')

    def test_no_args_shows_help(self) -> None:
        action = parse_cli_action([])
        self.assertEqual(action.kind, 'show_help')

    def test_invoke_multiple_tasks_parses(self) -> None:
        action = parse_cli_action(['invoke', 'start_game', 'solo_live'])
        self.assertEqual(action.kind, 'invoke_tasks')
        self.assertEqual(action.task_ids, ('start_game', 'solo_live'))

    def test_invalid_task_exits(self) -> None:
        with self.assertRaises(SystemExit):
            parse_cli_action(['invoke', 'auto-liv'])

    def test_auto_live_flags_without_command_show_help(self) -> None:
        action = parse_cli_action(['--run-until-exhausted'])
        self.assertEqual(action.kind, 'show_help')


class CliExecuteTests(unittest.TestCase):
    @mock.patch('iaa.main.IaaService')
    def test_execute_invoke_task_calls_scheduler(self, iaa_service_cls: mock.Mock) -> None:
        scheduler = mock.Mock()
        iaa_service_cls.return_value = SimpleNamespace(scheduler=scheduler, config=mock.Mock())

        action = parse_cli_action([
            'invoke', 'auto_live',
            '--run-count', '3',
            '--cycle-mode', 'list',
            '--play-mode', 'game_auto',
        ])
        code = execute_cli_action(action)

        self.assertEqual(code, 0)
        scheduler.run_single.assert_called_once_with(
            'auto_live',
            run_in_thread=False,
            kwargs={
                'run_count': 3,
                'cycle_mode': 'list',
                'play_mode': 'game_auto',
                'debug_enabled': False,
                'ap_multiplier': None,
            },
        )

    @mock.patch('iaa.main.IaaService')
    def test_execute_run_regular_calls_scheduler(self, iaa_service_cls: mock.Mock) -> None:
        scheduler = mock.Mock()
        iaa_service_cls.return_value = SimpleNamespace(scheduler=scheduler, config=mock.Mock())

        action = parse_cli_action(['run'])
        code = execute_cli_action(action)

        self.assertEqual(code, 0)
        scheduler.start_regular.assert_called_once_with(run_in_thread=False)

    @mock.patch('iaa.main.IaaService')
    def test_execute_invoke_multiple_tasks_in_order(self, iaa_service_cls: mock.Mock) -> None:
        scheduler = mock.Mock()
        iaa_service_cls.return_value = SimpleNamespace(scheduler=scheduler, config=mock.Mock())

        action = parse_cli_action(['invoke', 'start_game', 'solo_live'])
        code = execute_cli_action(action)

        self.assertEqual(code, 0)
        self.assertEqual(
            scheduler.run_single.call_args_list,
            [
                mock.call('start_game', run_in_thread=False, kwargs=None),
                mock.call('solo_live', run_in_thread=False, kwargs=None),
            ],
        )


if __name__ == '__main__':
    unittest.main()
