import unittest
from types import SimpleNamespace
from unittest import mock

from iaa.main import execute_cli_action, parse_cli_action
from iaa.tasks.live.live import ListLoopPlan


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
        action = parse_cli_action(['--count-mode', 'all'])
        self.assertEqual(action.kind, 'show_help')


class CliExecuteTests(unittest.TestCase):
    @mock.patch('iaa.main.manager.list', return_value=[])
    @mock.patch('iaa.main.IaaService')
    def test_execute_invoke_task_calls_scheduler(
        self,
        iaa_service_cls: mock.Mock,
        _list_configs: mock.Mock,
    ) -> None:
        scheduler = mock.Mock()
        iaa_service_cls.return_value = SimpleNamespace(scheduler=scheduler, config=mock.Mock())

        action = parse_cli_action([
            'invoke', 'auto_live',
            '--count-mode', 'specify',
            '--count', '3',
            '--loop-mode', 'list',
            '--auto-mode', 'game_auto',
        ])
        code = execute_cli_action(action)

        self.assertEqual(code, 0)
        iaa_service_cls.assert_called_once_with(config_name=None)
        plan = scheduler.run_single.call_args.kwargs['kwargs']['plan']
        scheduler.run_single.assert_called_once_with(
            'auto_live',
            run_in_thread=False,
            kwargs={'plan': plan},
        )
        self.assertIsInstance(plan, ListLoopPlan)
        assert isinstance(plan, ListLoopPlan)
        self.assertEqual(plan.loop_count, 3)
        self.assertEqual(plan.loop_song_mode, 'list_next')
        self.assertEqual(plan.play_mode, 'game_auto')

    @mock.patch('iaa.main.manager.list', return_value=[])
    @mock.patch('iaa.main.IaaService')
    def test_execute_run_regular_calls_scheduler(
        self,
        iaa_service_cls: mock.Mock,
        _list_configs: mock.Mock,
    ) -> None:
        scheduler = mock.Mock()
        iaa_service_cls.return_value = SimpleNamespace(scheduler=scheduler, config=mock.Mock())

        action = parse_cli_action(['run'])
        code = execute_cli_action(action)

        self.assertEqual(code, 0)
        scheduler.start_regular.assert_called_once_with(run_in_thread=False)

    @mock.patch('iaa.main.manager.list', return_value=[])
    @mock.patch('iaa.main.IaaService')
    def test_execute_invoke_multiple_tasks_in_order(
        self,
        iaa_service_cls: mock.Mock,
        _list_configs: mock.Mock,
    ) -> None:
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

    @mock.patch('iaa.main.IaaService')
    def test_execute_requires_config_when_multiple_configs_exist(self, iaa_service_cls: mock.Mock) -> None:
        with mock.patch('iaa.main.manager.list', return_value=['alt', 'default']):
            action = parse_cli_action(['run'])
            with self.assertRaisesRegex(RuntimeError, 'Multiple configs found'):
                execute_cli_action(action)

        iaa_service_cls.assert_not_called()

    @mock.patch('iaa.main.manager.list', return_value=['alpha'])
    @mock.patch('builtins.print')
    @mock.patch('iaa.main.IaaService')
    def test_list_configs_does_not_initialize_service(
        self,
        iaa_service_cls: mock.Mock,
        print_mock: mock.Mock,
        _list_configs: mock.Mock,
    ) -> None:
        action = parse_cli_action(['list', 'configs'])
        code = execute_cli_action(action)

        self.assertEqual(code, 0)
        iaa_service_cls.assert_not_called()
        print_mock.assert_called_once_with('alpha')

    @mock.patch('iaa.main.manager.list', return_value=['alt', 'default'])
    @mock.patch('iaa.main.IaaService')
    def test_execute_passes_explicit_config_name(
        self,
        iaa_service_cls: mock.Mock,
        _list_configs: mock.Mock,
    ) -> None:
        scheduler = mock.Mock()
        iaa_service_cls.return_value = SimpleNamespace(scheduler=scheduler, config=mock.Mock())

        action = parse_cli_action(['-c', 'alt', 'run'])
        code = execute_cli_action(action)

        self.assertEqual(code, 0)
        iaa_service_cls.assert_called_once_with(config_name='alt')
        scheduler.start_regular.assert_called_once_with(run_in_thread=False)


if __name__ == '__main__':
    unittest.main()
