from __future__ import annotations

from typing import Any, Callable, Literal, cast
import platform

from iaa.application.framework.dsl import (
    Checkbox,
    FieldSpec,
    FormPage,
    FormSpec,
    Group,
    IconItemPicker,
    NoticeBlock,
    Segmented,
    Select,
    Text,
    TransferList,
    register_field,
    bind,
    custom_ref,
)
from .context import FormContext
from iaa.application.qt.i18n import translate
from ..models import (
    SONG_KEEP_UNCHANGED,
    normalize_song_name_input,
    SONG_NAME_OPTIONS,
    challenge_character_groups_for_ui,
    challenge_awards_for_ui,
)
from iaa.config.schemas import (
    MuMuDevice,
    CustomDevice,
    NoDevice,
    PlayCoverDevice,
    AutoConnection,
    UsbConnection,
    TcpConnection,
)
from iaa.definitions.enums import (
    ChallengeLiveAward,
    GameCharacter,
    ShopItem,
)

ctx, ref = bind(FormContext)


def _tr(language: str, key: str) -> str:
    return translate(language, key)


def _ctx_tr(state: FormContext, key: str) -> str:
    return translate(state.shared.interface.language, key)


def _shop_item_label(item: ShopItem, language: str) -> str:
    if language == 'en_US':
        return _tr(language, f'settings.option.event_shop.{item.value}')
    return item.display('cn')


# ── 辅助判断 ──────────────────────────────────────────────────────────────────

def _lifecycle_is(*types) -> Callable[[FormContext], bool]:
    return lambda s: isinstance(s.conf.device.lifecycle, types)

def _connection_is(*types) -> Callable[[FormContext], bool]:
    return lambda s: isinstance(s.conf.device.connection, types)

def _is_mumu(s: FormContext) -> bool:
    return isinstance(s.conf.device.lifecycle, MuMuDevice)

def _is_custom(s: FormContext) -> bool:
    return isinstance(s.conf.device.lifecycle, CustomDevice)

def _is_no_device(s: FormContext) -> bool:
    return isinstance(s.conf.device.lifecycle, NoDevice)

def _is_playcover(s: FormContext) -> bool:
    return isinstance(s.conf.device.lifecycle, PlayCoverDevice)

def _is_tcp(s: FormContext) -> bool:
    return isinstance(s.conf.device.connection, TcpConnection)

def _show_connection_section(s: FormContext) -> bool:
    return not _is_mumu(s) and not _is_playcover(s)

def _show_tcp_fields(s: FormContext) -> bool:
    return _show_connection_section(s) and _is_tcp(s)

def _show_usb_serial(s: FormContext) -> bool:
    return _show_connection_section(s) and isinstance(s.conf.device.connection, UsbConnection)


# ── 验证器 ────────────────────────────────────────────────────────────────────

def _validate_tcp_port(value: object, state: FormContext) -> str | None:
    if not _show_tcp_fields(state):
        return None
    port = str(value or '').strip()
    if not port:
        return _ctx_tr(state, 'settings.error.tcp_port_required')
    if not port.isdigit():
        return _ctx_tr(state, 'settings.error.tcp_port_numeric')
    return None

def _validate_start_command(value: object, state: FormContext) -> str | None:
    if not _is_custom(state):
        return None
    if not str(value or '').strip():
        return _ctx_tr(state, 'settings.error.start_command_required')
    return None

def _validate_watch_ad_wait_sec(value: object, _state: FormContext) -> str | None:
    state = _state
    text = str(value or '').strip()
    if not text:
        return _ctx_tr(state, 'settings.error.watch_ad_wait_sec_required')
    if not text.isdigit():
        return _ctx_tr(state, 'settings.error.watch_ad_wait_sec_numeric')
    if int(text) <= 0:
        return _ctx_tr(state, 'settings.error.watch_ad_wait_sec_positive')
    return None


# ── lifecycle type ────────────────────────────────────────────────────────────

def _get_lifecycle_type(state: FormContext) -> str:
    lc = state.conf.device.lifecycle
    if isinstance(lc, MuMuDevice):
        return lc.type
    if isinstance(lc, CustomDevice):
        return 'custom'
    if isinstance(lc, PlayCoverDevice):
        return 'playcover'
    return 'none'

def _set_lifecycle_type(state: FormContext, value: object) -> None:
    val = str(value or '')
    current = state.conf.device.lifecycle
    if val in ('mumu', 'mumu_v5'):
        if isinstance(current, MuMuDevice) and current.type == val:
            return
        t: Literal['mumu', 'mumu_v5'] = 'mumu' if val == 'mumu' else 'mumu_v5'
        state.conf.device.lifecycle = MuMuDevice(type=t)
        state.conf.device.connection = AutoConnection(type='auto')
        # 切到 MuMu 时，若 control_impl 不支持则重置
        if state.conf.device.control_impl == 'nemu_ipc':
            pass  # nemu_ipc 是 MuMu 的推荐
    elif val == 'custom':
        if isinstance(current, CustomDevice):
            return
        state.conf.device.lifecycle = CustomDevice(type='custom')
        if isinstance(state.conf.device.connection, AutoConnection):
            state.conf.device.connection = TcpConnection(type='tcp')
        if state.conf.device.control_impl == 'nemu_ipc':
            state.conf.device.control_impl = 'adb'
    elif val == 'none':
        if isinstance(current, NoDevice):
            return
        state.conf.device.lifecycle = NoDevice(type='none')
        if isinstance(state.conf.device.connection, AutoConnection):
            state.conf.device.connection = UsbConnection(type='usb')
        if state.conf.device.control_impl == 'nemu_ipc':
            state.conf.device.control_impl = 'adb'
    elif val == 'playcover':
        if isinstance(current, PlayCoverDevice):
            return
        state.conf.device.lifecycle = PlayCoverDevice(type='playcover')
        if state.conf.device.control_impl == 'nemu_ipc':
            state.conf.device.control_impl = 'adb'


# ── MuMu instance id ──────────────────────────────────────────────────────────

def _get_mumu_instance_id(state: FormContext) -> str:
    lc = state.conf.device.lifecycle
    if isinstance(lc, MuMuDevice):
        return lc.instance_id or ''
    return ''

def _set_mumu_instance_id(state: FormContext, value: object) -> None:
    lc = state.conf.device.lifecycle
    if isinstance(lc, MuMuDevice):
        lc.instance_id = str(value or '').strip() or None


# ── MuMu check_and_start ──────────────────────────────────────────────────────

def _get_check_and_start(state: FormContext) -> bool:
    lc = state.conf.device.lifecycle
    return lc.check_and_start if isinstance(lc, (MuMuDevice, CustomDevice, PlayCoverDevice)) else False

def _set_check_and_start(state: FormContext, value: object) -> None:
    lc = state.conf.device.lifecycle
    if isinstance(lc, (MuMuDevice, CustomDevice, PlayCoverDevice)):
        lc.check_and_start = bool(value)



# ── CustomDevice lifecycle fields ─────────────────────────────────────────────

def _get_custom_start_command(state: FormContext) -> str:
    lc = state.conf.device.lifecycle
    return lc.start_command if isinstance(lc, CustomDevice) else ''

def _set_custom_start_command(state: FormContext, value: object) -> None:
    lc = state.conf.device.lifecycle
    if isinstance(lc, CustomDevice):
        lc.start_command = str(value or '').strip()

def _get_custom_wait_start_command(state: FormContext) -> bool:
    lc = state.conf.device.lifecycle
    return bool(lc.wait_start_command) if isinstance(lc, CustomDevice) else False

def _set_custom_wait_start_command(state: FormContext, value: object) -> None:
    lc = state.conf.device.lifecycle
    if isinstance(lc, CustomDevice):
        lc.wait_start_command = bool(value)

def _get_custom_stop_command(state: FormContext) -> str:
    lc = state.conf.device.lifecycle
    return lc.stop_command if isinstance(lc, CustomDevice) else ''

def _set_custom_stop_command(state: FormContext, value: object) -> None:
    lc = state.conf.device.lifecycle
    if isinstance(lc, CustomDevice):
        lc.stop_command = str(value or '').strip()

def _get_custom_running_command(state: FormContext) -> str:
    lc = state.conf.device.lifecycle
    return lc.running_command if isinstance(lc, CustomDevice) else ''

def _set_custom_running_command(state: FormContext, value: object) -> None:
    lc = state.conf.device.lifecycle
    if isinstance(lc, CustomDevice):
        lc.running_command = str(value or '').strip()


# ── connection type ───────────────────────────────────────────────────────────

def _get_connection_type(state: FormContext) -> str:
    conn = state.conf.device.connection
    if isinstance(conn, UsbConnection):
        return 'usb'
    if isinstance(conn, TcpConnection):
        return 'tcp'
    return 'usb'  # auto 不对用户展示，fallback 到 usb

def _set_connection_type(state: FormContext, value: object) -> None:
    val = str(value or '')
    if val == 'usb':
        state.conf.device.connection = UsbConnection(type='usb')
    elif val == 'tcp':
        state.conf.device.connection = TcpConnection(type='tcp')


# ── USB fields ────────────────────────────────────────────────────────────────

def _get_usb_serial(state: FormContext) -> str:
    conn = state.conf.device.connection
    return conn.device_serial if isinstance(conn, UsbConnection) else ''

def _set_usb_serial(state: FormContext, value: object) -> None:
    conn = state.conf.device.connection
    if isinstance(conn, UsbConnection):
        conn.device_serial = str(value or '').strip()


# ── TCP fields ────────────────────────────────────────────────────────────────

def _get_tcp_ip(state: FormContext) -> str:
    conn = state.conf.device.connection
    return conn.ip if isinstance(conn, TcpConnection) else '127.0.0.1'

def _set_tcp_ip(state: FormContext, value: object) -> None:
    conn = state.conf.device.connection
    if isinstance(conn, TcpConnection):
        conn.ip = str(value or '').strip() or '127.0.0.1'

def _get_tcp_port(state: FormContext) -> str:
    conn = state.conf.device.connection
    if isinstance(conn, TcpConnection):
        return '' if conn.port is None else str(conn.port)
    return ''

def _set_tcp_port(state: FormContext, value: object) -> None:
    conn = state.conf.device.connection
    if not isinstance(conn, TcpConnection):
        return
    text = str(value or '').strip()
    if not text:
        conn.port = None
        return
    if text.isdigit():
        conn.port = int(text)

def _get_tcp_run_adb_connect(state: FormContext) -> bool:
    conn = state.conf.device.connection
    return bool(conn.run_adb_connect) if isinstance(conn, TcpConnection) else True

def _set_tcp_run_adb_connect(state: FormContext, value: object) -> None:
    conn = state.conf.device.connection
    if isinstance(conn, TcpConnection):
        conn.run_adb_connect = bool(value)

def _get_tcp_device_serial(state: FormContext) -> str:
    conn = state.conf.device.connection
    return conn.device_serial if isinstance(conn, TcpConnection) else ''

def _set_tcp_device_serial(state: FormContext, value: object) -> None:
    conn = state.conf.device.connection
    if isinstance(conn, TcpConnection):
        conn.device_serial = str(value or '').strip()


# ── CM ────────────────────────────────────────────────────────────────────────

def _get_watch_ad_wait_sec(state: FormContext) -> str:
    return str(int(state.conf.cm.watch_ad_wait_sec))

def _set_watch_ad_wait_sec(state: FormContext, value: object) -> None:
    text = str(value or '').strip()
    if not text.isdigit():
        return
    num = int(text)
    if num <= 0:
        return
    state.conf.cm.watch_ad_wait_sec = num

def _on_server_change(state: FormContext, value: object) -> None:
    if value != 'jp':
        state.conf.game.link_account = 'no'


# ── Form ──────────────────────────────────────────────────────────────────────

def ResolutionSelect(
    key: str,
    label: str | None,
    *,
    ref: Any,
    options: Any = None,
    on_reset: Callable[[FormContext], None] | None = None,
    visible: Callable[[FormContext], bool] | bool = True,
    enabled: Callable[[FormContext], bool] | bool = True,
    **kwargs: Any,
) -> FieldSpec[FormContext]:
    """分辨率选择字段，带「恢复分辨率」按钮。

    ``on_reset`` 是点击「恢复分辨率」时的回调，由 controller 注入。
    """
    field_actions: dict[str, Callable[[FormContext], None]] = {}
    if on_reset is not None:
        field_actions['reset'] = on_reset
    return register_field(
        FieldSpec(
            key=key,
            kind='resolution_select',
            label=label,
            ref=ref,
            options=options,
            visible=visible,
            enabled=enabled,
            actions=field_actions,
            **kwargs,
        )
    )


def build_settings_form(
    mumu_instances: list[dict[str, Any]],
    *,
    language: str = 'zh_CN',
    on_mumu_refresh: Callable[[FormContext], None] | None = None,
    on_reset_resolution: Callable[[FormContext], None] | None = None,
) -> tuple[FormSpec[FormContext], list[Callable[[FormContext], None]]]:
    def tr(key: str) -> str:
        return _tr(language, key)

    lifecycle_options = [
        {'value': 'mumu_v5', 'label': 'MuMu 12 (v5)'},
        {'value': 'mumu', 'label': 'MuMu 12 (v4)'},
        {'value': 'custom', 'label': tr('settings.option.lifecycle.custom')},
        {'value': 'none', 'label': tr('settings.option.lifecycle.none')},
        {'value': 'playcover', 'label': 'PlayCover'},
    ]
    lifecycle_options = [
        option for option in lifecycle_options
        if not (option['value'] in {'mumu', 'mumu_v5'} and platform.system() != 'Windows')
        and not (option['value'] == 'playcover' and platform.system() != 'Darwin')
    ]
    control_impl_options = [
        {'value': 'nemu_ipc', 'label': 'Nemu IPC'},
        {'value': 'adb', 'label': 'ADB'},
        {'value': 'uiautomator', 'label': 'UIAutomator2'},
        {'value': 'scrcpy', 'label': 'Scrcpy'},
    ]
    challenge_char_groups = challenge_character_groups_for_ui(language)
    challenge_awards = challenge_awards_for_ui(language)
    event_shop_items = [{'value': item.value, 'label': _shop_item_label(item, language)} for item in ShopItem]
    server_options = [
        {'value': 'jp', 'label': tr('settings.option.server.jp')},
        {'value': 'tw', 'label': tr('settings.option.server.tw')},
        {'value': 'cn', 'label': tr('settings.option.server.cn')},
        {'value': 'en', 'label': tr('settings.option.server.en')},
    ]
    link_options = [
        {'value': 'no', 'label': tr('settings.option.link.no')},
        {'value': 'google', 'label': tr('settings.option.link.google')},
        {'value': 'google_play', 'label': 'Google Play'},
    ]
    connection_options = [
        {'value': 'usb', 'label': 'USB'},
        {'value': 'tcp', 'label': tr('settings.option.connection.tcp')},
    ]
    resolution_options = [
        {'value': 'auto', 'label': tr('settings.option.resolution.auto')},
        {'value': 'keep', 'label': tr('settings.option.resolution.keep')},
        {'value': 'wm_size', 'label': tr('settings.option.resolution.wm_size')},
    ]
    song_options = [
        {'value': SONG_KEEP_UNCHANGED, 'label': tr('settings.option.live.song.keep')},
        *[
            {'value': song, 'label': song}
            for song in SONG_NAME_OPTIONS
            if song != SONG_KEEP_UNCHANGED
        ],
    ]
    ap_keep = '保持现状'
    ap_maximum = '最大值'
    ap_options = [
        {'value': ap_keep, 'label': tr('settings.option.live.ap.keep')},
        {'value': ap_maximum, 'label': tr('settings.option.live.ap.maximum')},
        *[str(i) for i in range(0, 11)],
    ]

    with FormPage(tr('settings.title')) as page:
        with Group(tr('settings.group.game')):
            Segmented(
                key='game.server',
                label=tr('settings.field.game.server'),
                ref=ref(ctx.conf.game.server),
                options=server_options,
                on_change=_on_server_change,
                help_text=tr('settings.help.server'),
            )
            Segmented(
                key='game.linkAccount',
                label=tr('settings.field.game.link_account'),
                ref=ref(ctx.conf.game.link_account),
                visible=lambda s: s.conf.game.server == 'jp',
                options=link_options,
                help_text=tr('settings.help.link_account'),
            )

        with Group(tr('settings.group.device')):
            Segmented(
                key='device.lifecycleType',
                label=tr('settings.field.device.lifecycle_type'),
                ref=custom_ref(_get_lifecycle_type, _set_lifecycle_type),
                options=lifecycle_options,
            )
            # MuMu 专属
            Select(
                key='device.mumuInstanceId',
                label=tr('settings.field.device.mumu_instance'),
                ref=custom_ref(_get_mumu_instance_id, _set_mumu_instance_id),
                visible=_lifecycle_is(MuMuDevice),
                options=mumu_instances,
                refresh=on_mumu_refresh,
                props={
                    'refreshText': tr('settings.action.refresh'),
                    'loadingText': tr('settings.action.loading'),
                },
            )
            Checkbox(
                key='device.checkAndStart',
                label=tr('settings.field.device.check_and_start'),
                ref=custom_ref(_get_check_and_start, _set_check_and_start),
                visible=_lifecycle_is(MuMuDevice, CustomDevice, PlayCoverDevice),
            )
            # 自定义专属
            Text(
                key='device.customStartCommand',
                label=tr('settings.field.device.custom_start_command'),
                ref=custom_ref(_get_custom_start_command, _set_custom_start_command),
                visible=_lifecycle_is(CustomDevice),
                validators=[_validate_start_command],
                help_text=tr('settings.help.custom_start_command'),
            )
            Checkbox(
                key='device.customWaitStartCommand',
                label=tr('settings.field.device.custom_wait_start_command'),
                ref=custom_ref(_get_custom_wait_start_command, _set_custom_wait_start_command),
                visible=_lifecycle_is(CustomDevice),
            )
            Text(
                key='device.customStopCommand',
                label=tr('settings.field.device.custom_stop_command'),
                ref=custom_ref(_get_custom_stop_command, _set_custom_stop_command),
                visible=_lifecycle_is(CustomDevice),
                placeholder=tr('settings.placeholder.custom_stop_command'),
            )
            Text(
                key='device.customRunningCommand',
                label=tr('settings.field.device.custom_running_command'),
                ref=custom_ref(_get_custom_running_command, _set_custom_running_command),
                visible=_lifecycle_is(CustomDevice),
                placeholder=tr('settings.placeholder.custom_running_command'),
            )

        with Group(tr('settings.group.connection'), visible=_show_connection_section):
            Segmented(
                key='device.connectionType',
                label=tr('settings.field.device.connection_type'),
                ref=custom_ref(_get_connection_type, _set_connection_type),
                visible=_show_connection_section,
                options=connection_options,
            )
            # USB 字段
            Text(
                key='device.usbSerial',
                label=tr('settings.field.device.serial'),
                ref=custom_ref(_get_usb_serial, _set_usb_serial),
                visible=_show_usb_serial,
                placeholder=tr('settings.placeholder.usb_serial'),
            )
            # TCP 字段
            Text(
                key='device.tcpIp',
                label=tr('settings.field.device.tcp_ip'),
                ref=custom_ref(_get_tcp_ip, _set_tcp_ip),
                visible=_show_tcp_fields,
            )
            Text(
                key='device.tcpPort',
                label=tr('settings.field.device.tcp_port'),
                ref=custom_ref(_get_tcp_port, _set_tcp_port),
                visible=_show_tcp_fields,
                validators=[_validate_tcp_port],
            )
            Checkbox(
                key='device.tcpRunAdbConnect',
                label=tr('settings.field.device.tcp_run_adb_connect'),
                ref=custom_ref(_get_tcp_run_adb_connect, _set_tcp_run_adb_connect),
                visible=_show_tcp_fields,
                help_text=tr('settings.help.tcp_run_adb_connect'),
            )
            Text(
                key='device.tcpDeviceSerial',
                label=tr('settings.field.device.serial'),
                ref=custom_ref(_get_tcp_device_serial, _set_tcp_device_serial),
                visible=_show_tcp_fields,
                placeholder=tr('settings.placeholder.tcp_device_serial'),
            )

        with Group(tr('settings.group.control'), visible=lambda s: not _is_playcover(s)):
            Segmented(
                key='device.controlImpl',
                label=tr('settings.field.device.control_impl'),
                ref=ref(ctx.conf.device.control_impl),
                options=lambda s: [
                    o for o in control_impl_options
                    if not (o['value'] == 'nemu_ipc' and not isinstance(s.conf.device.lifecycle, MuMuDevice))
                ],
                help_text=tr('settings.help.control_impl'),
            )
            NoticeBlock(
                content=tr('settings.notice.nemu_ipc_tip'),
                style='tip',
                visible=lambda s: _is_mumu(s) and s.conf.device.control_impl != 'nemu_ipc'
            )
            Checkbox(
                key='device.scrcpyVirtualDisplay',
                label=tr('settings.field.device.scrcpy_virtual_display'),
                ref=ref(ctx.conf.device.scrcpy_virtual_display),
                visible=lambda s: s.conf.device.control_impl == 'scrcpy',
            )
            ResolutionSelect(
                key='device.resolutionMethod',
                label=tr('settings.field.device.resolution_method'),
                ref=ref(ctx.conf.device.resolution_method),
                options=resolution_options,
                on_reset=on_reset_resolution,
                props={'resetText': tr('settings.action.reset_resolution')},
            )

        with Group(tr('settings.group.live')):
            Select(
                key='live.songName',
                label=tr('settings.field.live.song_name'),
                ref=ref(ctx.conf.live.song_name).map(
                    to_ui=lambda v: v or SONG_KEEP_UNCHANGED,
                    from_ui=lambda v: normalize_song_name_input(str(v)),
                ),
                options=song_options,
            )
            Select(
                key='live.apMultiplier',
                label=tr('settings.field.live.ap_multiplier'),
                ref=ref(ctx.conf.live.ap_multiplier).map(
                    to_ui=lambda v: ap_keep if v is None else (ap_maximum if v == 'maximum' else str(v)),
                    from_ui=lambda v: (
                        None
                        if str(v) == ap_keep
                        else ('maximum' if str(v) == ap_maximum else int(str(v)))
                    ),
                ),
                options=ap_options,
            )
            Checkbox(
                key='live.autoSetUnit',
                label=tr('settings.field.live.auto_set_unit'),
                ref=ref(ctx.conf.live.auto_set_unit),
            )
            Checkbox(
                key='live.appendFc',
                label=tr('settings.field.live.append_fc'),
                ref=ref(ctx.conf.live.append_fc),
            )
            Checkbox(
                key='live.appendRandom',
                label=tr('settings.field.live.append_random'),
                ref=ref(ctx.conf.live.prepend_random),
            )

        with Group(tr('settings.group.challenge_live')):
            IconItemPicker(
                key='challengeLive.characters',
                label=tr('settings.field.challenge.characters'),
                ref=ref(ctx.conf.challenge_live.characters).map(
                    to_ui=lambda values: values[0].value if values else None,
                    from_ui=lambda v: [GameCharacter(str(v))],
                ),
                options=challenge_char_groups,
                cell_size=100,
                icon_size=70,
            )
            IconItemPicker(
                key='challengeLive.award',
                label=tr('settings.field.challenge.award'),
                ref=ref(ctx.conf.challenge_live.award).map(
                    to_ui=lambda v: v.value,
                    from_ui=lambda v: ChallengeLiveAward(str(v)),
                ),
                options=challenge_awards,
                cell_size=80,
                icon_size=56,
            )

        with Group(tr('settings.group.cm')):
            Text(
                key='cm.watchAdWaitSec',
                label=tr('settings.field.cm.watch_ad_wait_sec'),
                ref=custom_ref(_get_watch_ad_wait_sec, _set_watch_ad_wait_sec),
                validators=[_validate_watch_ad_wait_sec],
            )

        with Group(tr('settings.group.event_shop')):
            TransferList(
                key='eventShop.selectedItems',
                label=None,
                ref=ref(ctx.conf.event_shop.purchase_items).map(
                    to_ui=lambda values: [item.value for item in values],
                    from_ui=lambda values: [ShopItem(str(v)) for v in values],
                ),
                options=event_shop_items,
                reorderable=True,
                height=220,
                props={
                    'addText': tr('settings.action.add'),
                    'removeText': tr('settings.action.remove'),
                    'moveUpText': tr('settings.action.move_up'),
                    'moveDownText': tr('settings.action.move_down'),
                },
            )

        with Group(tr('settings.group.developer')):
            Checkbox(
                key='scheduler.dumpSekaiHomeEnabled',
                label=tr('settings.field.developer.dump_sekai_home'),
                ref=ref(ctx.conf.scheduler.dump_sekai_home_enabled),
            )
            Checkbox(
                key='developer.sekaiDumpPostProcess',
                label=tr('settings.field.developer.sekai_dump_post_process'),
                ref=ref(ctx.conf.developer.sekai_dump_post_process),
            )
            Checkbox(
                key='developer.screenRecordingEnabled',
                label=tr('settings.field.developer.screen_recording'),
                ref=ref(ctx.conf.developer.screen_recording_enabled),
                help_text=tr('settings.help.screen_recording'),
            )

    return (
        cast(FormSpec[FormContext], page.spec),
        cast(list[Callable[[FormContext], None]], page.hooks),
    )
