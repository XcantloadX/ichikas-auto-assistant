from iaa.application.cli.index import CliTaskConfig, configure
from iaa.application.qt.models.auto_live import auto_live_payload_to_plan

import click

configure({
    'main_story': CliTaskConfig(
        before_invoke=lambda: click.echo(
            'Warning: main_story runs continuously until you stop it manually.'
        ),
    ),
    'auto_live': CliTaskConfig(
        kwargs_transform=lambda raw: {'plan': auto_live_payload_to_plan(raw)},
    ),
})
