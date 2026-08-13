import json
import sys
from dataclasses import dataclass
from typing import Callable

import click

from iaa.platform import env


@dataclass
class CliTaskConfig:
    before_invoke: Callable[[], None] | None = None
    kwargs_transform: Callable[[dict], dict] | None = None


_task_configs: dict[str, CliTaskConfig] = {}


def configure(task_configs: dict[str, CliTaskConfig]) -> None:
    _task_configs.update(task_configs)


def cli_root_dir() -> str:
    """CLI 视角的软件根目录,等价于 :func:`iaa.platform.env.app_root`。"""
    return env.app_root()


def make_iaa(config: str | None):
    from iaa.config import manager
    if config is None:
        manager.config_path = env.config_dir()
        configs = manager.list()
        if len(configs) > 1:
            names = ', '.join(configs)
            raise click.UsageError(
                f'Multiple configs found ({names}). Please specify one with -c/--config.'
            )
    from iaa.application.service.iaa_service import IaaService
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
    from iaa.tasks.registry import TASK_INFOS
    all_ids = tuple(TASK_INFOS.keys())
    unknown = [t for t in task_ids if t not in all_ids]
    if unknown:
        available = ', '.join(all_ids)
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
    from iaa.tasks.registry import list_task_infos
    for info in list_task_infos():
        supports_kwargs = 'yes' if info.supports_kwargs else 'no'
        click.echo(
            f'{info.task_id:<16} | {info.display_name:<8} | {info.kind:<7} | '
            f'kwargs: {supports_kwargs}'
        )


@list_group.command('configs')
def list_configs() -> None:
    """List available configs"""
    from iaa.config import manager
    manager.config_path = env.config_dir()
    for name in manager.list():
        click.echo(name)


def main() -> None:
    click.echo(f'Arguments: {sys.argv}')
    from iaa.telemetry import setup as setup_telemetry
    setup_telemetry()
    cli()


if __name__ == '__main__':
    main()
