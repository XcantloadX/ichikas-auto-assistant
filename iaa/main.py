import argparse
from typing import Sequence
from dataclasses import dataclass

from kotonebot.backend import debug

import iaa.application.service.config_service as config_service_module
from iaa.application.service.iaa_service import IaaService
from iaa.tasks.registry import MANUAL_TASKS, REGULAR_TASKS, list_task_infos

ALL_TASK_IDS = tuple([*REGULAR_TASKS.keys(), *MANUAL_TASKS.keys()])


@dataclass(frozen=True)
class CliAction:
    kind: str
    task_ids: tuple[str, ...] = ()
    config_name: str = 'default'
    debug_enabled: bool = False
    auto_live_kwargs: dict[str, object] | None = None
    help_text: str | None = None


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument('--debug', '-d', action='store_true', help='Enable debug mode')
    parser.add_argument('--config', '-c', default='default', help='Configuration name to use')


def add_auto_live_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        '--run-count',
        type=int,
        default=10,
        help='auto_live only: number of runs; omit value with --run-until-exhausted to loop until AP is exhausted',
    )
    parser.add_argument(
        '--run-until-exhausted',
        action='store_true',
        help='auto_live only: ignore --run-count and loop until AP is exhausted',
    )
    parser.add_argument(
        '--cycle-mode',
        choices=['single', 'list'],
        default='list',
        help='auto_live only: loop current song or cycle the song list',
    )
    parser.add_argument(
        '--play-mode',
        choices=['game_auto', 'script_auto'],
        default='game_auto',
        help='auto_live only: use in-game auto or script auto',
    )
    parser.add_argument(
        '--debug-enabled',
        action='store_true',
        help='auto_live only: show script auto debug overlay',
    )
    parser.add_argument(
        '--ap-multiplier',
        type=int,
        choices=range(0, 11),
        help='auto_live only: set AP multiplier to 0-10 before starting; omit to keep current',
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Run Ichika Auto Assistant tasks')
    add_common_args(parser)
    add_auto_live_args(parser)

    subparsers = parser.add_subparsers(dest='command')

    subparsers.add_parser('run', help='Run configured regular tasks')

    invoke_parser = subparsers.add_parser('invoke', help='Run one or more tasks explicitly')
    invoke_parser.add_argument('task_ids', nargs='+', help='Task id(s) to run in order')
    add_auto_live_args(invoke_parser)

    list_parser = subparsers.add_parser('list', help='List metadata')
    list_subparsers = list_parser.add_subparsers(dest='list_command', required=True)
    list_subparsers.add_parser('tasks', help='List available tasks')
    list_subparsers.add_parser('configs', help='List available configs')

    return parser


def validate_task_ids(
    parser: argparse.ArgumentParser,
    task_ids: Sequence[str],
) -> tuple[str, ...]:
    unknown = [task_id for task_id in task_ids if task_id not in ALL_TASK_IDS]
    if unknown:
        available = ', '.join(ALL_TASK_IDS)
        parser.error(f'Unknown task id(s): {", ".join(unknown)}. Available: {available}')
    return tuple(task_ids)


def build_auto_live_kwargs(args: argparse.Namespace) -> dict[str, object]:
    if not args.run_until_exhausted and (args.run_count is None or args.run_count <= 0):
        raise ValueError('--run-count must be a positive integer unless --run-until-exhausted is set')
    return {
        'run_count': None if args.run_until_exhausted else args.run_count,
        'cycle_mode': args.cycle_mode,
        'play_mode': args.play_mode,
        'debug_enabled': bool(args.debug_enabled),
        'ap_multiplier': args.ap_multiplier,
    }


def parse_cli_action(argv: Sequence[str] | None = None) -> CliAction:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == 'list':
        return CliAction(
            kind=f'list_{args.list_command}',
            config_name=args.config,
            debug_enabled=bool(args.debug),
        )

    if args.command == 'run':
        return CliAction(
            kind='run_regular',
            config_name=args.config,
            debug_enabled=bool(args.debug),
        )

    if args.command == 'invoke':
        task_ids = validate_task_ids(parser, args.task_ids)
        auto_live_kwargs = build_auto_live_kwargs(args) if task_ids == ('auto_live',) else None
        return CliAction(
            kind='invoke_tasks',
            task_ids=task_ids,
            config_name=args.config,
            debug_enabled=bool(args.debug),
            auto_live_kwargs=auto_live_kwargs,
        )

    return CliAction(
        kind='show_help',
        config_name=args.config,
        debug_enabled=bool(args.debug),
        help_text=parser.format_help(),
    )


def configure_debug(debug_enabled: bool) -> None:
    if debug_enabled:
        debug.debug.enabled = True
        debug.debug.auto_save_to_folder = 'dumps'


def print_task_list() -> None:
    for info in list_task_infos():
        supports_kwargs = 'yes' if info.supports_kwargs else 'no'
        print(
            f'{info.task_id:<16} | {info.display_name:<8} | {info.kind:<7} | '
            f'kwargs: {supports_kwargs}'
        )


def execute_cli_action(action: CliAction) -> int:
    configure_debug(action.debug_enabled)
    config_service_module.DEFAULT_CONFIG_NAME = action.config_name

    if action.kind == 'list_tasks':
        print_task_list()
        return 0

    if action.kind == 'show_help':
        if action.help_text:
            print(action.help_text, end='')
        return 0

    iaa = IaaService()

    if action.kind == 'list_configs':
        for name in iaa.config.list():
            print(name)
        return 0

    if action.kind == 'invoke_tasks':
        for task_id in action.task_ids:
            if task_id == 'main_story':
                print('Warning: main_story runs continuously until you stop it manually.')
            iaa.scheduler.run_single(
                task_id,
                run_in_thread=False,
                kwargs=(action.auto_live_kwargs if task_id == 'auto_live' else None),
            )
        return 0

    if action.kind == 'run_regular':
        iaa.scheduler.start_regular(run_in_thread=False)
        return 0

    raise RuntimeError(f'Unsupported CLI action: {action.kind}')


def main(argv: Sequence[str] | None = None) -> int:
    action = parse_cli_action(argv)
    return execute_cli_action(action)


if __name__ == "__main__":
    raise SystemExit(main())
