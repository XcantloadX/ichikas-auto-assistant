from __future__ import annotations

from typing import Any, Callable, Literal, cast
import platform

from iaa.application.framework.dsl import (
    Checkbox,
    FieldSpec,
    FormPage,
    FormSpec,
    Group,
    Hook,
    IconItemPicker,
    NoticeBlock,
    Segmented,
    Select,
    Text,
    SortableChecklist,
    register_field,
    bind,
    custom_ref,
)
from .context import FormContext
from ..models import (
    SONG_KEEP_UNCHANGED,
    normalize_song_name_input,
    LIFECYCLE_TYPE_DISPLAY_MAP,
    CONNECTION_TYPE_DISPLAY_MAP,
    SERVER_DISPLAY_MAP,
    LINK_DISPLAY_MAP,
    CONTROL_IMPL_DISPLAY_MAP,
    RESOLUTION_METHOD_DISPLAY_MAP,
    SONG_NAME_OPTIONS,
    challenge_character_groups_for_ui,
    challenge_awards_for_ui,
)
from iaa.config.schemas import (
    MuMuDevice,
    CustomDevice,
    NoDevice,
    PlayCoverDevice,
    AvdDevice,
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

def _is_avd(s: FormContext) -> bool:
    return isinstance(s.conf.device.lifecycle, AvdDevice)

def _is_tcp(s: FormContext) -> bool:
    return isinstance(s.conf.device.connection, TcpConnection)

def _show_connection_section(s: FormContext) -> bool:
    return not _is_mumu(s) and not _is_playcover(s) and not _is_avd(s)

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
        return '端口不能为空'
    if not port.isdigit():
        return '端口必须是数字'
    return None

def _validate_start_command(value: object, state: FormContext) -> str | None:
    if not _is_custom(state):
        return None
    if not str(value or '').strip():
        return '启动命令不能为空'
    return None

def _validate_watch_ad_wait_sec(value: object, _state: FormContext) -> str | None:
    text = str(value or '').strip()
    if not text:
        return 'CM 广告等待秒数不能为空'
    if not text.isdigit():
        return 'CM 广告等待秒数必须是数字'
    if int(text) <= 0:
        return 'CM 广告等待秒数必须大于 0'
    return None


# ── lifecycle type ────────────────────────────────────────────────────────────

def _get_lifecycle_type(state: FormContext) -> str:
    lc = state.conf.device.lifecycle
    if isinstance(lc, MuMuDevice):
        return lc.type
    if isinstance(lc, CustomDevice):
        return 'custom'
    if isinstance(lc, AvdDevice):
        return 'avd'
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
    elif val == 'custom':
        if isinstance(current, CustomDevice):
            return
        state.conf.device.lifecycle = CustomDevice(type='custom')
    elif val == 'none':
        if isinstance(current, NoDevice):
            return
        state.conf.device.lifecycle = NoDevice(type='none')
    elif val == 'avd':
        if isinstance(current, AvdDevice):
            return
        state.conf.device.lifecycle = AvdDevice(type='avd')
    elif val == 'playcover':
        if isinstance(current, PlayCoverDevice):
            return
        state.conf.device.lifecycle = PlayCoverDevice(type='playcover')


def _set_control_impl(state: FormContext, value: object) -> None:
    state.conf.device.control_impl = str(value)  # type: ignore[assignment]


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
    return lc.check_and_start if isinstance(lc, (MuMuDevice, CustomDevice, PlayCoverDevice, AvdDevice)) else False

def _set_check_and_start(state: FormContext, value: object) -> None:
    lc = state.conf.device.lifecycle
    if isinstance(lc, (MuMuDevice, CustomDevice, PlayCoverDevice, AvdDevice)):
        lc.check_and_start = bool(value)



# ── AVD fields ────────────────────────────────────────────────────────────────

def _get_avd_name(state: FormContext) -> str:
    lc = state.conf.device.lifecycle
    if isinstance(lc, AvdDevice):
        return lc.avd_name or ''
    return ''

def _set_avd_name(state: FormContext, value: object) -> None:
    lc = state.conf.device.lifecycle
    if isinstance(lc, AvdDevice):
        lc.avd_name = str(value or '').strip() or None

def _get_avd_sdk_path(state: FormContext) -> str:
    lc = state.conf.device.lifecycle
    if isinstance(lc, AvdDevice):
        return lc.sdk_path or ''
    return ''

def _set_avd_sdk_path(state: FormContext, value: object) -> None:
    lc = state.conf.device.lifecycle
    if isinstance(lc, AvdDevice):
        lc.sdk_path = str(value or '').strip() or None

def _get_avd_extra_args(state: FormContext) -> str:
    lc = state.conf.device.lifecycle
    if isinstance(lc, AvdDevice):
        return lc.extra_args
    return ''

def _set_avd_extra_args(state: FormContext, value: object) -> None:
    lc = state.conf.device.lifecycle
    if isinstance(lc, AvdDevice):
        lc.extra_args = str(value or '').strip()


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

# ── 归一化钩子 ────────────────────────────────────────────────────────────────

def _normalize_game(ctx: FormContext) -> None:
    if ctx.conf.game.server != 'jp':
        ctx.conf.game.link_account = 'no'

def _normalize_device(ctx: FormContext) -> None:
    lc = ctx.conf.device.lifecycle

    # connection 约束
    if isinstance(lc, (MuMuDevice, AvdDevice)):
        if not isinstance(ctx.conf.device.connection, AutoConnection):
            ctx.conf.device.connection = AutoConnection(type='auto')
    elif isinstance(lc, CustomDevice):
        if isinstance(ctx.conf.device.connection, AutoConnection):
            ctx.conf.device.connection = TcpConnection(type='tcp')
    elif isinstance(lc, NoDevice):
        if isinstance(ctx.conf.device.connection, AutoConnection):
            ctx.conf.device.connection = UsbConnection(type='usb')

    # control_impl 约束：nemu_ipc 仅 MuMu，qemu_grpc 仅 AVD
    impl = ctx.conf.device.control_impl
    if impl == 'nemu_ipc' and not isinstance(lc, MuMuDevice):
        ctx.conf.device.control_impl = 'adb'
        impl = 'adb'
    elif impl == 'qemu_grpc' and not isinstance(lc, AvdDevice):
        ctx.conf.device.control_impl = 'adb'
        impl = 'adb'

    # resolution_method 约束：qemu_grpc 强制 keep
    if impl == 'qemu_grpc':
        ctx.conf.device.resolution_method = 'keep'


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
    avd_instances: list[dict[str, Any]] | None = None,
    *,
    on_mumu_refresh: Callable[[FormContext], None] | None = None,
    on_avd_refresh: Callable[[FormContext], None] | None = None,
    on_reset_resolution: Callable[[FormContext], None] | None = None,
) -> tuple[FormSpec[FormContext], list[Callable[[FormContext], None]]]:
    if avd_instances is None:
        avd_instances = []

    lifecycle_options = [
        {'value': k, 'label': v} for k, v in LIFECYCLE_TYPE_DISPLAY_MAP.items()
        if not (k in {'mumu', 'mumu_v5'} and platform.system() != 'Windows')
        and not (k == 'playcover' and platform.system() != 'Darwin')
    ]
    control_impl_options = [{'value': k, 'label': v} for k, v in CONTROL_IMPL_DISPLAY_MAP.items()]
    challenge_char_groups = challenge_character_groups_for_ui()
    challenge_awards = challenge_awards_for_ui()
    event_shop_items = [{'value': item.value, 'label': item.display('cn')} for item in ShopItem]

    with FormPage('配置') as page:
        Hook(_normalize_game)
        Hook(_normalize_device)
        with Group('游戏设置'):
            Segmented(
                key='game.server',
                label='服务器',
                ref=ref(ctx.conf.game.server),
                options=[{'value': k, 'label': v} for k, v in SERVER_DISPLAY_MAP.items()],
                help_text='''广告：现招募维护者维护除日服以外的服务器适配~ 如果你有兴趣参与维护，请联系作者。
<hr>
维护者：
<ul>
<li>日服：作者本人</li>
<li>台服：空缺</li>
<li>国服：空缺</li>
<li>国际服：空缺</li>
<li>韩服：空缺</li>
</ul>
'''
            )
            Segmented(
                key='game.linkAccount',
                label='引继账号',
                ref=ref(ctx.conf.game.link_account),
                visible=lambda s: s.conf.game.server == 'jp',
                options=[{'value': k, 'label': v} for k, v in LINK_DISPLAY_MAP.items()],
                help_text='每次启动游戏的时候是否使用引继账号登录（仅限日服）',
            )

        with Group('设备设置'):
            Segmented(
                key='device.lifecycleType',
                label='设备类型',
                ref=custom_ref(_get_lifecycle_type, _set_lifecycle_type),
                options=lifecycle_options,
            )
            # MuMu 专属
            Select(
                key='device.mumuInstanceId',
                label='多开实例',
                ref=custom_ref(_get_mumu_instance_id, _set_mumu_instance_id),
                visible=_lifecycle_is(MuMuDevice),
                options=mumu_instances,
                refresh=on_mumu_refresh,
            )
            # AVD 专属
            Text(
                key='device.avdSdkPath',
                label='SDK 路径',
                ref=custom_ref(_get_avd_sdk_path, _set_avd_sdk_path),
                visible=_lifecycle_is(AvdDevice),
                placeholder='留空自动查找',
                help_text=(
                    'Android SDK 路径。自动查找顺序：<ol>'
                    '<li>环境变量 <code>ANDROID_HOME</code> / <code>ANDROID_SDK_ROOT</code></li>'
                    '<li>Windows：<code>%LOCALAPPDATA%\\Android\\Sdk</code></li>'
                    '<li>macOS：<code>~/Library/Android/sdk</code></li>'
                    '<li>Linux：<code>~/Android/Sdk</code></li>'
                    '<li><code>PATH</code> 中的 <code>emulator</code></li>'
                    '</ol>'
                    '填写后将只在该目录下查找，忽略以上自动查找逻辑。'
                ),
            )
            Text(
                key='device.avdExtraArgs',
                label='额外启动参数',
                ref=custom_ref(_get_avd_extra_args, _set_avd_extra_args),
                visible=_lifecycle_is(AvdDevice),
                placeholder='可选，例如 -gpu swiftshader_indirect -no-audio',
                help_text='追加到 emulator 命令行末尾的参数，以空格分隔。',
            )
            Select(
                key='device.avdName',
                label='AVD 实例',
                ref=custom_ref(_get_avd_name, _set_avd_name),
                visible=_lifecycle_is(AvdDevice),
                options=avd_instances,
                refresh=on_avd_refresh,
            )
            Checkbox(
                key='device.checkAndStart',
                label='检查并启动',
                ref=custom_ref(_get_check_and_start, _set_check_and_start),
                visible=_lifecycle_is(MuMuDevice, CustomDevice, PlayCoverDevice, AvdDevice),
            )
            # 自定义专属
            Text(
                key='device.customStartCommand',
                label='启动命令',
                ref=custom_ref(_get_custom_start_command, _set_custom_start_command),
                visible=_lifecycle_is(CustomDevice),
                validators=[_validate_start_command],
                help_text='将会通过 shell 方式执行。因此编写时请注意转义等问题。<br>下面两个命令也是一样的。'
            )
            Checkbox(
                key='device.customWaitStartCommand',
                label='等待启动命令退出后才继续',
                ref=custom_ref(_get_custom_wait_start_command, _set_custom_wait_start_command),
                visible=_lifecycle_is(CustomDevice),
            )
            Text(
                key='device.customStopCommand',
                label='结束命令',
                ref=custom_ref(_get_custom_stop_command, _set_custom_stop_command),
                visible=_lifecycle_is(CustomDevice),
                placeholder='可选。如果为空，将会自动终止启动命令中的进程'
            )
            Text(
                key='device.customRunningCommand',
                label='运行检测命令',
                ref=custom_ref(_get_custom_running_command, _set_custom_running_command),
                visible=_lifecycle_is(CustomDevice),
                placeholder='可选。如果为空，将会使用默认的运行检测方式'
            )

        with Group('连接设置', visible=_show_connection_section):
            Segmented(
                key='device.connectionType',
                label='连接方式',
                ref=custom_ref(_get_connection_type, _set_connection_type),
                visible=_show_connection_section,
                options=[{'value': k, 'label': v} for k, v in CONNECTION_TYPE_DISPLAY_MAP.items()],
            )
            # USB 字段
            Text(
                key='device.usbSerial',
                label='设备序列号',
                ref=custom_ref(_get_usb_serial, _set_usb_serial),
                visible=_show_usb_serial,
                placeholder='留空自动选择第一个 USB 设备',
            )
            # TCP 字段
            Text(
                key='device.tcpIp',
                label='ADB IP',
                ref=custom_ref(_get_tcp_ip, _set_tcp_ip),
                visible=_show_tcp_fields,
            )
            Text(
                key='device.tcpPort',
                label='ADB 端口',
                ref=custom_ref(_get_tcp_port, _set_tcp_port),
                visible=_show_tcp_fields,
                validators=[_validate_tcp_port],
            )
            Checkbox(
                key='device.tcpRunAdbConnect',
                label='执行 adb connect',
                ref=custom_ref(_get_tcp_run_adb_connect, _set_tcp_run_adb_connect),
                visible=_show_tcp_fields,
                help_text='如果需要通过「IP:端口」的形式连接设备，需要勾选。'
            )
            Text(
                key='device.tcpDeviceSerial',
                label='设备序列号',
                ref=custom_ref(_get_tcp_device_serial, _set_tcp_device_serial),
                visible=_show_tcp_fields,
                placeholder='留空则默认使用 IP:端口 作为序列号'
            )

        with Group('控制方式', visible=lambda s: not _is_playcover(s)):
            Segmented(
                key='device.controlImpl',
                label='控制方式',
                ref=custom_ref(
                    lambda s: s.conf.device.control_impl,
                    _set_control_impl,
                ),
                options=lambda s: [
                    o for o in control_impl_options
                    # nemu_ipc 仅 MuMu 可用
                    if not (o['value'] == 'nemu_ipc' and not isinstance(s.conf.device.lifecycle, MuMuDevice))
                    # qemu_grpc 仅 AVD 可用
                    and not (o['value'] == 'qemu_grpc' and not isinstance(s.conf.device.lifecycle, AvdDevice))
                ],
                help_text=(
                    '对于 MuMu 模拟器，推荐使用 <b>Nemu IPC</b> 方式；'
                    '对于 AVD，推荐使用 <b>QEMU gRPC</b>（直接读取模拟器帧缓冲，速度最快）或 <b>ADB</b>；'
                    '对于其他模拟器与物理机，推荐使用 <b>Scrcpy</b> 方式'
                ),
            )
            NoticeBlock(
                content='MuMu 模拟器选择 NemuIPC 效果最佳',
                style='tip',
                visible=lambda s: _is_mumu(s) and s.conf.device.control_impl != 'nemu_ipc'
            )
            Checkbox(
                key='device.scrcpyVirtualDisplay',
                label='使用虚拟显示器',
                ref=ref(ctx.conf.device.scrcpy_virtual_display),
                visible=lambda s: s.conf.device.control_impl == 'scrcpy',
            )
            ResolutionSelect(
                key='device.resolutionMethod',
                label='分辨率设置',
                ref=ref(ctx.conf.device.resolution_method),
                options=lambda s: (
                    # qemu_grpc 只展示保持不变
                    [{'value': 'keep', 'label': RESOLUTION_METHOD_DISPLAY_MAP['keep']}]
                    if s.conf.device.control_impl == 'qemu_grpc'
                    # 其他的正常展示
                    else [{'value': k, 'label': v} for k, v in RESOLUTION_METHOD_DISPLAY_MAP.items()]
                ),
                enabled=lambda s: s.conf.device.control_impl != 'qemu_grpc',
                on_reset=on_reset_resolution,
                help_text=(
                    '<b>自动</b>：物理设备执行 <code>wm size</code>；其他模拟器不修改。<br>'
                    '<b>强制修改分辨率</b>：对所有设备执行 <code>wm size</code>。<br>'
                    '<b>保持原始分辨率</b>：不做任何修改。'
                ),
            )
            NoticeBlock(
                content=(
                    '使用 QEMU gRPC 控制方式时，'
                    '请在 Android Studio AVD Manager 中预先将分辨率配置为 <b>1280x720</b>。'
                ),
                style='tip',
                visible=lambda s: _is_avd(s) and s.conf.device.control_impl == 'qemu_grpc',
            )

        with Group('演出设置'):
            Select(
                key='live.songName',
                label='歌曲名称',
                ref=ref(ctx.conf.live.song_name).map(
                    to_ui=lambda v: v or SONG_KEEP_UNCHANGED,
                    from_ui=lambda v: normalize_song_name_input(str(v)),
                ),
                options=SONG_NAME_OPTIONS,
            )
            Select(
                key='live.apMultiplier',
                label='AP 倍率',
                ref=ref(ctx.conf.live.ap_multiplier).map(
                    to_ui=lambda v: '保持现状' if v is None else str(v),
                    from_ui=lambda v: None if str(v) == '保持现状' else int(str(v)),
                ),
                options=['保持现状', *[str(i) for i in range(0, 11)]],
            )
            Checkbox(
                key='live.autoSetUnit',
                label='自动编队',
                ref=ref(ctx.conf.live.auto_set_unit),
            )
            Checkbox(
                key='live.appendFc',
                label='追加一次 FullCombo 演出',
                ref=ref(ctx.conf.live.append_fc),
            )
            Checkbox(
                key='live.appendRandom',
                label='追加一首随机歌曲',
                ref=ref(ctx.conf.live.prepend_random),
            )

        with Group('挑战演出设置'):
            IconItemPicker(
                key='challengeLive.characters',
                label='角色',
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
                label='奖励',
                ref=ref(ctx.conf.challenge_live.award).map(
                    to_ui=lambda v: v.value,
                    from_ui=lambda v: ChallengeLiveAward(str(v)),
                ),
                options=challenge_awards,
                cell_size=80,
                icon_size=56,
            )

        with Group('CM 设置'):
            Text(
                key='cm.watchAdWaitSec',
                label='广告等待秒数',
                ref=custom_ref(_get_watch_ad_wait_sec, _set_watch_ad_wait_sec),
                validators=[_validate_watch_ad_wait_sec],
            )

        with Group('活动商店设置'):
            SortableChecklist(
                key='eventShop.selectedItems',
                label=None,
                ref=ref(ctx.conf.event_shop.purchase_items).map(
                    to_ui=lambda values: [item.value for item in values],
                    from_ui=lambda values: [ShopItem(str(v)) for v in values],
                ),
                options=event_shop_items,
                height=300,
            )

        with Group('开发者设置（仅供开发使用！）'):
            Checkbox(
                key='scheduler.dumpSekaiHomeEnabled',
                label='dump 烤森',
                ref=ref(ctx.conf.scheduler.dump_sekai_home_enabled),
            )
            Checkbox(
                key='developer.sekaiDumpPostProcess',
                label='dump 烤森 - 后处理与预打标',
                ref=ref(ctx.conf.developer.sekai_dump_post_process),
            )
            Checkbox(
                key='developer.screenRecordingEnabled',
                label='自动录屏（需安装 ffmpeg）',
                ref=ref(ctx.conf.developer.screen_recording_enabled),
                help_text='脚本启动时自动录屏，结束时自动结束。输出到 dumps/screen_records/ 目录。',
            )

    return (
        cast(FormSpec[FormContext], page.spec),
        cast(list[Callable[[FormContext], None]], page.hooks),
    )
