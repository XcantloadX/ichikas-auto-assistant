from iaa.application.cli.index import CliTaskConfig, configure

import click


def _auto_live_transform(raw):
    from iaa.tasks.live.live import auto_live_payload_to_plan
    return {'plan': auto_live_payload_to_plan(raw)}


configure({
    'main_story': CliTaskConfig(
        before_invoke=lambda: click.echo(
            'Warning: main_story runs continuously until you stop it manually.'
        ),
    ),
    'auto_live': CliTaskConfig(
        kwargs_transform=_auto_live_transform,
    ),
})
