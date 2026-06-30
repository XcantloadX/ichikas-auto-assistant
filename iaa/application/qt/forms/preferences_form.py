from __future__ import annotations

from iaa.application.framework.dsl import Checkbox, FormPage, FormSpec, Group, Hotkey, Select, Text, bind, custom_ref
from typing import Callable, cast
from .context import PreferencesContext
from iaa.i18n import tstr
from iaa.config.shared import CustomPushData, DiscordPushData

ctx, ref = bind(PreferencesContext)


def _push_is_custom(c: PreferencesContext) -> bool:
    return isinstance(c.shared.notify.push.data, CustomPushData)

def _push_is_discord(c: PreferencesContext) -> bool:
    return isinstance(c.shared.notify.push.data, DiscordPushData)


def _get_push_type(c: PreferencesContext) -> str:
    return c.shared.notify.push.data.type

def _set_push_type(c: PreferencesContext, value: str) -> None:
    # 切换类型时整个替换 data 实例（而不是改字段），type 与数据始终保持一致
    c.shared.notify.push.data = DiscordPushData() if value == 'discord' else CustomPushData()

def _get_push_command(c: PreferencesContext) -> str:
    data = c.shared.notify.push.data
    return data.command if isinstance(data, CustomPushData) else ''

def _set_push_command(c: PreferencesContext, value: str) -> None:
    data = c.shared.notify.push.data
    if isinstance(data, CustomPushData):
        data.command = value

def _get_push_webhook_url(c: PreferencesContext) -> str:
    data = c.shared.notify.push.data
    return data.webhook_url if isinstance(data, DiscordPushData) else ''

def _set_push_webhook_url(c: PreferencesContext, value: str) -> None:
    data = c.shared.notify.push.data
    if isinstance(data, DiscordPushData):
        data.webhook_url = value


def build_preferences_form() -> tuple[FormSpec[PreferencesContext], list[Callable[[PreferencesContext], None]]]:
    with FormPage(tstr('preferences.title')) as page:
        with Group(tstr('preferences.group.telemetry')):
            Checkbox(
                key='telemetry.sentry',
                label=tstr('preferences.field.telemetry_sentry'),
                ref=ref(ctx.shared.telemetry.sentry),
            )

        with Group(tstr('preferences.group.interface')):
            Select(
                key='interface.language',
                label=tstr('preferences.field.language'),
                ref=ref(ctx.shared.interface.language),
                options=[
                    {'value': 'auto', 'label': tstr('preferences.option.follow_system')},
                    {'value': 'zh_CN', 'label': tstr('preferences.language.zh_CN')},
                    {'value': 'en_US', 'label': tstr('preferences.language.en_US')},
                ],
            )
            Select(
                key='interface.window_style',
                label=tstr('preferences.field.window_style'),
                ref=ref(ctx.shared.interface.window_style),
                options=[
                    {'value': '', 'label': tstr('preferences.option.auto')},
                    {'value': 'mica', 'label': tstr('preferences.option.window_style.mica')},
                    {'value': 'blur', 'label': tstr('preferences.option.window_style.blur')},
                    {'value': 'acrylic', 'label': tstr('preferences.option.window_style.acrylic')},
                    {'value': 'solid', 'label': tstr('preferences.option.window_style.solid')},
                ],
            )
            Select(
                key='interface.color_scheme',
                label=tstr('preferences.field.color_scheme'),
                ref=ref(ctx.shared.interface.color_scheme),
                options=[
                    {'value': 'auto', 'label': tstr('preferences.option.follow_system')},
                    {'value': 'light', 'label': tstr('preferences.option.color_scheme.light')},
                    {'value': 'dark', 'label': tstr('preferences.option.color_scheme.dark')},
                ],
            )
            Select(
                key='interface.theme_color',
                label=tstr('preferences.field.theme_color'),
                ref=ref(ctx.shared.interface.theme_color).map(
                    to_ui=lambda v: '' if v is None else str(v),
                    from_ui=lambda v: (str(v).strip() or None),
                ),
                options=[
                    {'value': '', 'label': tstr('preferences.option.follow_system')},
                    {'value': '#0078d4', 'label': tstr('preferences.option.theme.blue')},
                    {'value': '#e81123', 'label': tstr('preferences.option.theme.red')},
                    {'value': '#107c10', 'label': tstr('preferences.option.theme.green')},
                    {'value': '#ff8c00', 'label': tstr('preferences.option.theme.orange')},
                    {'value': '#5c2d91', 'label': tstr('preferences.option.theme.purple')},
                    {'value': '#00b7c3', 'label': tstr('preferences.option.theme.cyan')},
                    {'value': '#6b69d6', 'label': tstr('preferences.option.theme.indigo')},
                    {'value': '#4a5459', 'label': tstr('preferences.option.theme.graphite')},
                ],
            )

        with Group(tstr('preferences.group.notify')):
            Checkbox(
                key='notify.system',
                label=tstr('preferences.field.notify_system'),
                ref=ref(ctx.shared.notify.system),
            )
            Checkbox(
                key='notify.push.enabled',
                label=tstr('preferences.field.notify_push'),
                ref=ref(ctx.shared.notify.push.enabled),
            )
            Select(
                key='notify.push.type',
                label=tstr('preferences.field.notify_push_type'),
                ref=custom_ref(_get_push_type, _set_push_type),
                options=[
                    {'value': 'custom', 'label': tstr('preferences.option.notify_push.custom')},
                    {'value': 'discord', 'label': tstr('preferences.option.notify_push.discord')},
                ],
                visible=lambda ctx: ctx.shared.notify.push.enabled,
            )
            Text(
                key='notify.push.data.command',
                label=tstr('preferences.field.notify_custom_command'),
                ref=custom_ref(_get_push_command, _set_push_command),
                placeholder=tstr('preferences.placeholder.notify_custom_command'),
                visible=lambda ctx: ctx.shared.notify.push.enabled and _push_is_custom(ctx),
            )
            Text(
                key='notify.push.data.webhook_url',
                label='Webhook URL',
                help_text=lambda lang: (
                    '<a href="https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks">'
                    f'{tstr("preferences.help.discord_webhook").resolve(lang)}</a>'
                ),
                ref=custom_ref(_get_push_webhook_url, _set_push_webhook_url),
                placeholder='https://discord.com/api/webhooks/...',
                visible=lambda ctx: ctx.shared.notify.push.enabled and _push_is_discord(ctx),
            )

        with Group(tstr('preferences.group.hotkeys')):
            Hotkey(
                key='hotkeys.start',
                label=tstr('preferences.field.hotkey_start'),
                ref=ref(ctx.shared.hotkeys.start).map(
                    to_ui=lambda v: '' if v is None else v,
                    from_ui=lambda v: None if not v else v,
                ),
                props={
                    'idlePlaceholder': tstr('preferences.hotkey.placeholder.idle'),
                    'recordingPlaceholder': tstr('preferences.hotkey.placeholder.recording'),
                    'clearText': tstr('preferences.hotkey.clear'),
                },
            )
            Hotkey(
                key='hotkeys.stop',
                label=tstr('preferences.field.hotkey_stop'),
                ref=ref(ctx.shared.hotkeys.stop).map(
                    to_ui=lambda v: '' if v is None else v,
                    from_ui=lambda v: None if not v else v,
                ),
            )

    return (
        cast(FormSpec[PreferencesContext], page.spec),
        cast(list[Callable[[PreferencesContext], None]], page.hooks),
    )
