import json
import os
import sys
from dataclasses import dataclass
from typing import Callable

import click

from iaa.application.service.iaa_service import IaaService
from iaa.config import manager
from iaa.telemetry import setup as setup_telemetry
from iaa.tasks.registry import TASK_INFOS, list_task_infos

ALL_TASK_IDS = tuple(TASK_INFOS.keys())


@dataclass
class CliTaskConfig:
    before_invoke: Callable[[], None] | None = None
    kwargs_transform: Callable[[dict], dict] | None = None


_task_configs: dict[str, CliTaskConfig] = {}


def configure(task_configs: dict[str, CliTaskConfig]) -> None:
    _task_configs.update(task_configs)


def cli_root_dir() -> str:
    if not os.path.basename(sys.executable).startswith('python'):
        return os.path.dirname(sys.executable)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))


def make_iaa(config: str | None) -> IaaService:
    if config is None:
        manager.config_path = os.path.join(cli_root_dir(), 'conf')
        configs = manager.list()
        if len(configs) > 1:
            names = ', '.join(configs)
            raise click.UsageError(
                f'Multiple configs found ({names}). Please specify one with -c/--config.'
            )
    return IaaService(config_name=config)


@click.group()
@click.option('--debug', '-d', is_flag=True, help='Enable debug mode')
@click.option('--config', '-c', default=None, help='Configuration name to use')
@click.pass_context
def cli(ctx: click.Context, debug: bool, config: str | None) -> None:
    """Run Ichika Auto Assistant tasks"""
    ctx.ensure_object(dict)
    ctx.obj['debug'] = debug
    ctx.obj['config'] = config


@cli.command()
@click.pass_context
def run(ctx: click.Context) -> None:
    """Run configured regular tasks"""
    iaa = make_iaa(ctx.obj['config'])
    iaa.scheduler.start_regular(run_in_thread=False)


@cli.command()
@click.argument('task_ids', nargs=-1, required=True)
@click.option('--kwargs', 'raw_kwargs', default=None, help='Task kwargs as JSON string')
@click.pass_context
def invoke(ctx: click.Context, task_ids: tuple[str, ...], raw_kwargs: str | None) -> None:
    """Run one or more tasks explicitly"""
    unknown = [t for t in task_ids if t not in ALL_TASK_IDS]
    if unknown:
        available = ', '.join(ALL_TASK_IDS)
        raise click.UsageError(
            f'Unknown task id(s): {", ".join(unknown)}. Available: {available}'
        )

    iaa = make_iaa(ctx.obj['config'])
    kwargs = json.loads(raw_kwargs) if raw_kwargs else None

    for task_id in task_ids:
        task_cfg = _task_configs.get(task_id)
        if task_cfg and task_cfg.before_invoke:
            task_cfg.before_invoke()
        task_kwargs = kwargs
        if task_cfg and task_cfg.kwargs_transform and task_kwargs is not None:
            task_kwargs = task_cfg.kwargs_transform(task_kwargs)
        iaa.scheduler.run_single(task_id, run_in_thread=False, kwargs=task_kwargs)


@cli.group(name='list')
def list_group() -> None:
    """List metadata"""


@list_group.command('tasks')
def list_tasks() -> None:
    """List available tasks"""
    for info in list_task_infos():
        supports_kwargs = 'yes' if info.supports_kwargs else 'no'
        click.echo(
            f'{info.task_id:<16} | {info.display_name:<8} | {info.kind:<7} | '
            f'kwargs: {supports_kwargs}'
        )


@list_group.command('configs')
def list_configs() -> None:
    """List available configs"""
    manager.config_path = os.path.join(cli_root_dir(), 'conf')
    for name in manager.list():
        click.echo(name)


def main() -> None:
    click.echo(f'Arguments: {sys.argv}')
    setup_telemetry()
    cli()


if __name__ == '__main__':
    main()
