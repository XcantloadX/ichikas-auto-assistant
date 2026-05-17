from __future__ import annotations

from typing import Callable, Literal
import platform

from iaa.application.framework.dsl import (
    Checkbox,
    Custom,
    FormContext,
    FormPage,
    FormSpec,
    Group,
    Segmented,
    Select,
    Text,
    TransferList,
    custom_ref,
    of,
    ref,
)
from ..models import SONG_KEEP_UNCHANGED, normalize_song_name_input
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

CTX = of(FormContext)


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

def build_settings_form() -> tuple[FormSpec, list]:
    with FormPage('配置') as page:
        with Group('游戏设置'):
            Segmented(
                key='game.server',
                label='服务器',
                ref=ref(CTX.conf.game.server),
                options=lambda s: s.meta.servers,
                on_change=_on_server_change,
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
                ref=ref(CTX.conf.game.link_account),
                visible=lambda s: s.conf.game.server == 'jp',
                options=lambda s: s.meta.linkAccounts,
                help_text='每次启动游戏的时候是否使用引继账号登录（仅限日服）',
            )

        with Group('设备设置'):
            Segmented(
                key='device.lifecycleType',
                label='设备类型',
                ref=custom_ref(_get_lifecycle_type, _set_lifecycle_type),
                options=lambda s: [
                    o for o in s.meta.lifecycleTypes
                    if not (o['value'] in {'mumu', 'mumu_v5'} and platform.system() != 'Windows')
                    and not (o['value'] == 'playcover' and platform.system() != 'Darwin')
                ],
            )
            # MuMu 专属
            Custom(
                key='device.mumuInstanceId',
                label='多开实例',
                kind='mumu_picker',
                ref=custom_ref(_get_mumu_instance_id, _set_mumu_instance_id),
                visible=_lifecycle_is(MuMuDevice),
                options=lambda s: s.meta.mumuInstances,
                props={'refreshable': True},
            )
            Checkbox(
                key='device.checkAndStart',
                label='检查并启动',
                ref=custom_ref(_get_check_and_start, _set_check_and_start),
                visible=_lifecycle_is(MuMuDevice, CustomDevice, PlayCoverDevice),
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
                options=lambda s: s.meta.connectionTypes,
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
                ref=ref(CTX.conf.device.control_impl),
                options=lambda s: [
                    o for o in s.meta.controlImpls
                    if not (o['value'] == 'nemu_ipc' and not isinstance(s.conf.device.lifecycle, MuMuDevice))
                ],
                help_text='对于 MuMu 模拟器，推荐使用 <b>Nemu IPC</b> 方式，对于其他模拟器与物理机，推荐使用 <b>scrcpy</b> 方式',
            )
            Checkbox(
                key='device.scrcpyVirtualDisplay',
                label='使用虚拟显示器',
                ref=ref(CTX.conf.device.scrcpy_virtual_display),
                visible=lambda s: s.conf.device.control_impl == 'scrcpy',
            )
            Select(
                key='device.resolutionMethod',
                label='分辨率设置',
                ref=ref(CTX.conf.device.resolution_method),
                options=lambda s: s.meta.resolutionMethods,
                with_reset_button=True,
            )

        with Group('演出设置'):
            Select(
                key='live.songName',
                label='歌曲名称',
                ref=ref(CTX.conf.live.song_name).map(
                    to_ui=lambda v: v or SONG_KEEP_UNCHANGED,
                    from_ui=lambda v: normalize_song_name_input(str(v)),
                ),
                options=lambda s: s.meta.songNames,
            )
            Select(
                key='live.apMultiplier',
                label='AP 倍率',
                ref=ref(CTX.conf.live.ap_multiplier).map(
                    to_ui=lambda v: '保持现状' if v is None else str(v),
                    from_ui=lambda v: None if str(v) == '保持现状' else int(str(v)),
                ),
                options=lambda s: s.meta.apMultipliers,
            )
            Checkbox(
                key='live.autoSetUnit',
                label='自动编队',
                ref=ref(CTX.conf.live.auto_set_unit),
            )
            Checkbox(
                key='live.appendFc',
                label='追加一次 FullCombo 演出',
                ref=ref(CTX.conf.live.append_fc),
            )
            Checkbox(
                key='live.appendRandom',
                label='追加一首随机歌曲',
                ref=ref(CTX.conf.live.prepend_random),
            )

        with Group('挑战演出设置'):
            Select(
                key='challengeLive.characters',
                label='角色',
                ref=ref(CTX.conf.challenge_live.characters).map(
                    to_ui=lambda values: [item.value for item in values],
                    from_ui=lambda values: [GameCharacter(str(v)) for v in values],
                ),
                options=lambda s: s.meta.challengeCharacters,
                props={'singleFromList': True},
            )
            Select(
                key='challengeLive.award',
                label='奖励',
                ref=ref(CTX.conf.challenge_live.award).map(
                    to_ui=lambda v: v.value,
                    from_ui=lambda v: ChallengeLiveAward(str(v)),
                ),
                options=lambda s: s.meta.challengeAwards,
            )

        with Group('CM 设置'):
            Text(
                key='cm.watchAdWaitSec',
                label='广告等待秒数',
                ref=custom_ref(_get_watch_ad_wait_sec, _set_watch_ad_wait_sec),
                validators=[_validate_watch_ad_wait_sec],
            )

        with Group('活动商店设置'):
            TransferList(
                key='eventShop.selectedItems',
                label=None,
                ref=ref(CTX.conf.event_shop.purchase_items).map(
                    to_ui=lambda values: [item.value for item in values],
                    from_ui=lambda values: [ShopItem(str(v)) for v in values],
                ),
                options=lambda s: s.meta.eventShopItems,
                reorderable=True,
                height=220,
            )

        with Group('开发者设置（仅供开发使用！）'):
            Checkbox(
                key='scheduler.dumpSekaiHomeEnabled',
                label='dump 烤森',
                ref=ref(CTX.conf.scheduler.dump_sekai_home_enabled),
            )
            Checkbox(
                key='developer.sekaiDumpPostProcess',
                label='dump 烤森 - 后处理与预打标',
                ref=ref(CTX.conf.developer.sekai_dump_post_process),
            )
            Checkbox(
                key='developer.screenRecordingEnabled',
                label='自动录屏（需安装 ffmpeg）',
                ref=ref(CTX.conf.developer.screen_recording_enabled),
                help_text='脚本启动时自动录屏，结束时自动结束。输出到 dumps/screen_records/ 目录。',
            )

    return page.spec, page.hooks
