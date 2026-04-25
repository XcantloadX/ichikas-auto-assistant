from __future__ import annotations

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
    CustomEmulatorData,
    MuMuEmulatorData,
    PhysicalAndroidData,
)
from iaa.definitions.enums import (
    ChallengeLiveAward,
    GameCharacter,
    ShopItem,
)

CTX = of(FormContext)


def _emulator_is(*values: str):
    return lambda s: s.conf.game.emulator in values


def _validate_port(value: object, _state: FormContext) -> str | None:
    port = str(value or '').strip()
    if not port:
        return '端口不能为空'
    if not port.isdigit():
        return '端口必须是数字'
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


def _on_server_change(state: FormContext, value: object) -> None:
    if value != 'jp':
        state.conf.game.link_account = 'no'


def _get_mumu_instance_id(state: FormContext) -> str:
    if state.conf.game.emulator in {'mumu', 'mumu_v5'} and isinstance(state.conf.game.emulator_data, MuMuEmulatorData):
        return state.conf.game.emulator_data.instance_id or ''
    return ''


def _set_mumu_instance_id(state: FormContext, value: object) -> None:
    if state.conf.game.emulator not in {'mumu', 'mumu_v5'}:
        return
    if not isinstance(state.conf.game.emulator_data, MuMuEmulatorData):
        state.conf.game.emulator_data = MuMuEmulatorData()
    state.conf.game.emulator_data.instance_id = (str(value or '').strip() or None)


def _get_physical_android_serial(state: FormContext) -> str:
    if state.conf.game.emulator == 'physical_android' and isinstance(state.conf.game.emulator_data, PhysicalAndroidData):
        return (state.conf.game.emulator_data.adb_serial or '').strip()
    return ''


def _set_physical_android_serial(state: FormContext, value: object) -> None:
    if state.conf.game.emulator != 'physical_android':
        return
    if not isinstance(state.conf.game.emulator_data, PhysicalAndroidData):
        state.conf.game.emulator_data = PhysicalAndroidData()
    state.conf.game.emulator_data.adb_serial = str(value or '').strip()


def _ensure_custom_data(state: FormContext) -> CustomEmulatorData:
    if not isinstance(state.conf.game.emulator_data, CustomEmulatorData):
        state.conf.game.emulator_data = CustomEmulatorData()
    return state.conf.game.emulator_data


def _get_custom_adb_ip(state: FormContext) -> str:
    if state.conf.game.emulator == 'custom' and isinstance(state.conf.game.emulator_data, CustomEmulatorData):
        return state.conf.game.emulator_data.adb_ip
    return '127.0.0.1'


def _set_custom_adb_ip(state: FormContext, value: object) -> None:
    if state.conf.game.emulator != 'custom':
        return
    data = _ensure_custom_data(state)
    data.adb_ip = str(value or '').strip() or '127.0.0.1'


def _get_custom_adb_port(state: FormContext) -> str:
    if state.conf.game.emulator == 'custom' and isinstance(state.conf.game.emulator_data, CustomEmulatorData):
        return str(state.conf.game.emulator_data.adb_port)
    return '5555'


def _set_custom_adb_port(state: FormContext, value: object) -> None:
    if state.conf.game.emulator != 'custom':
        return
    text = str(value or '').strip()
    if not text.isdigit():
        return
    data = _ensure_custom_data(state)
    data.adb_port = int(text)


def _get_custom_path(state: FormContext) -> str:
    if state.conf.game.emulator == 'custom' and isinstance(state.conf.game.emulator_data, CustomEmulatorData):
        return state.conf.game.emulator_data.emulator_path
    return ''


def _set_custom_path(state: FormContext, value: object) -> None:
    if state.conf.game.emulator != 'custom':
        return
    data = _ensure_custom_data(state)
    data.emulator_path = str(value or '').strip()


def _get_custom_args(state: FormContext) -> str:
    if state.conf.game.emulator == 'custom' and isinstance(state.conf.game.emulator_data, CustomEmulatorData):
        return state.conf.game.emulator_data.emulator_args
    return ''


def _set_custom_args(state: FormContext, value: object) -> None:
    if state.conf.game.emulator != 'custom':
        return
    data = _ensure_custom_data(state)
    data.emulator_args = str(value or '').strip()


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


def build_settings_form() -> tuple[FormSpec, list]:
    with FormPage('配置') as page:
        with Group('游戏设置'):
            Segmented(
                key='game.emulator',
                label='模拟器类型',
                ref=ref(CTX.conf.game.emulator),
                options=lambda s: s.meta.emulators,
            )
            Custom(
                key='game.mumuInstanceId',
                label='多开实例',
                kind='mumu_picker',
                ref=custom_ref(_get_mumu_instance_id, _set_mumu_instance_id),
                visible=_emulator_is('mumu', 'mumu_v5'),
                options=lambda s: s.meta.mumuInstances,
                props={'refreshable': True},
            )
            Text(
                key='game.physicalAndroidSerial',
                label='ADB 序列号',
                ref=custom_ref(_get_physical_android_serial, _set_physical_android_serial),
                visible=_emulator_is('physical_android'),
                placeholder='留空自动选择第一个 USB 设备',
            )
            Text(
                key='game.customAdbIp',
                label='ADB IP',
                ref=custom_ref(_get_custom_adb_ip, _set_custom_adb_ip),
                visible=_emulator_is('custom'),
            )
            Text(
                key='game.customAdbPort',
                label='ADB 端口',
                ref=custom_ref(_get_custom_adb_port, _set_custom_adb_port),
                visible=_emulator_is('custom'),
                validators=[_validate_port],
            )
            Text(
                key='game.customEmulatorPath',
                label='模拟器路径',
                ref=custom_ref(_get_custom_path, _set_custom_path),
                visible=_emulator_is('custom'),
            )
            Text(
                key='game.customEmulatorArgs',
                label='启动参数',
                ref=custom_ref(_get_custom_args, _set_custom_args),
                visible=_emulator_is('custom'),
            )
            Segmented(
                key='game.server',
                label='服务器',
                ref=ref(CTX.conf.game.server),
                options=lambda s: s.meta.servers,
                on_change=_on_server_change,
            )
            Segmented(
                key='game.linkAccount',
                label='引继账号',
                ref=ref(CTX.conf.game.link_account),
                enabled=lambda s: s.conf.game.server == 'jp',
                options=lambda s: s.meta.linkAccounts,
            )
            Segmented(
                key='game.controlImpl',
                label='控制方式',
                ref=ref(CTX.conf.game.control_impl),
                options=lambda s: s.meta.controlImpls,
            )
            Checkbox(
                key='game.scrcpyVirtualDisplay',
                label='使用虚拟显示器',
                ref=ref(CTX.conf.game.scrcpy_virtual_display),
                visible=lambda s: s.conf.game.control_impl == 'scrcpy',
            )
            Select(
                key='game.resolutionMethod',
                label='分辨率设置',
                ref=ref(CTX.conf.game.resolution_method),
                options=lambda s: s.meta.resolutionMethods,
                with_reset_button=True,
            )
            Checkbox(
                key='game.checkEmulator',
                label='检查并启动模拟器',
                ref=ref(CTX.conf.game.check_emulator),
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

    return page.spec, page.hooks
