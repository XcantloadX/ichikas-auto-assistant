from __future__ import annotations

import json
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal, Slot

from iaa.config.schemas import (
    ChallengeLiveAward,
    CustomEmulatorData,
    GameCharacter,
    MuMuEmulatorData,
    PhysicalAndroidData,
    ShopItem,
)

from ..models import (
    CONTROL_IMPL_DISPLAY_MAP,
    DEFAULT_MUMU_INSTANCE_LABEL,
    EMULATOR_DISPLAY_MAP,
    LINK_DISPLAY_MAP,
    RESOLUTION_METHOD_DISPLAY_MAP,
    SERVER_DISPLAY_MAP,
    SONG_KEEP_UNCHANGED,
    SONG_NAME_OPTIONS,
    challenge_awards_for_ui,
    challenge_character_groups_for_ui,
    challenge_characters_for_ui,
    normalize_song_name_input,
)
if TYPE_CHECKING:
    from iaa.application.service.iaa_service import IaaService


class SettingsController(QObject):
    operationSucceeded = Signal(str)
    operationFailed = Signal(str)
    configSwitched = Signal()

    def __init__(self, iaa_service: 'IaaService', parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._iaa = iaa_service

    def _build_mumu_instances_payload(self, emulator: str, preferred_id: str = '') -> str:
        if emulator not in {'mumu', 'mumu_v5'}:
            return json.dumps(
                {
                    'ok': True,
                    'items': [{'id': '', 'label': DEFAULT_MUMU_INSTANCE_LABEL}],
                    'selectedId': '',
                    'statusText': '当前模拟器无需选择实例',
                },
                ensure_ascii=False,
            )
        try:
            from kotonebot.client.host import Mumu12Host, Mumu12V5Host

            host_cls = Mumu12Host if emulator == 'mumu' else Mumu12V5Host
            instances = host_cls.list()
            saved_id = ''
            conf = self._iaa.config.conf
            if (
                conf.game.emulator == emulator
                and isinstance(conf.game.emulator_data, MuMuEmulatorData)
                and conf.game.emulator_data.instance_id
            ):
                saved_id = conf.game.emulator_data.instance_id
            items = [{'id': '', 'label': DEFAULT_MUMU_INSTANCE_LABEL}] + [
                {'id': str(instance.id), 'label': f'[{instance.id}] {instance.name}'}
                for instance in instances
            ]
            ids = {item['id'] for item in items}
            selected_id = ''
            if preferred_id and preferred_id in ids:
                selected_id = preferred_id
            elif saved_id and saved_id in ids:
                selected_id = saved_id
            status = f'已载入 {len(instances)} 个实例'
            if not instances:
                status = '未找到可用实例'
            elif selected_id:
                status += f'，当前选择 ID: {selected_id}'
            return json.dumps(
                {
                    'ok': True,
                    'items': items,
                    'selectedId': selected_id,
                    'statusText': status,
                },
                ensure_ascii=False,
            )
        except Exception as exc:  # noqa: BLE001
            return json.dumps(
                {
                    'ok': False,
                    'items': [{'id': '', 'label': DEFAULT_MUMU_INSTANCE_LABEL}],
                    'selectedId': '',
                    'statusText': f'刷新失败：{exc}',
                },
                ensure_ascii=False,
            )

    @Slot(result=str)
    def optionsJson(self) -> str:
        options = {
            'profiles': [{'value': name, 'label': name} for name in self._iaa.config.list()],
            'emulators': [{'value': key, 'label': label} for key, label in EMULATOR_DISPLAY_MAP.items()],
            'servers': [{'value': key, 'label': label} for key, label in SERVER_DISPLAY_MAP.items()],
            'linkAccounts': [{'value': key, 'label': label} for key, label in LINK_DISPLAY_MAP.items()],
            'controlImpls': [{'value': key, 'label': label} for key, label in CONTROL_IMPL_DISPLAY_MAP.items()],
            'resolutionMethods': [
                {'value': key, 'label': label} for key, label in RESOLUTION_METHOD_DISPLAY_MAP.items()
            ],
            'songNames': SONG_NAME_OPTIONS,
            'apMultipliers': ['保持现状', *[str(i) for i in range(0, 11)]],
            'challengeCharacterGroups': challenge_character_groups_for_ui(),
            'challengeCharacters': challenge_characters_for_ui(),
            'challengeAwards': challenge_awards_for_ui(),
            'eventShopItems': [{'value': item.value, 'label': item.display('cn')} for item in ShopItem],
            'mumuInstances': [{'id': '', 'label': DEFAULT_MUMU_INSTANCE_LABEL}],
        }
        return json.dumps(options, ensure_ascii=False)

    @Slot(result=str)
    def stateJson(self) -> str:
        conf = self._iaa.config.conf
        emulator_data = conf.game.emulator_data
        state = {
            'profileName': self._iaa.config.current_config_name,
            'game': {
                'emulator': conf.game.emulator,
                'server': conf.game.server,
                'linkAccount': conf.game.link_account,
                'controlImpl': conf.game.control_impl,
                'checkEmulator': bool(conf.game.check_emulator),
                'scrcpyVirtualDisplay': bool(conf.game.scrcpy_virtual_display),
                'resolutionMethod': conf.game.resolution_method,
                'mumuInstanceId': (
                    emulator_data.instance_id
                    if conf.game.emulator in {'mumu', 'mumu_v5'} and isinstance(emulator_data, MuMuEmulatorData)
                    else ''
                ),
                'physicalAndroidSerial': (
                    (emulator_data.adb_serial or '').strip()
                    if conf.game.emulator == 'physical_android' and isinstance(emulator_data, PhysicalAndroidData)
                    else ''
                ),
                'customAdbIp': (
                    emulator_data.adb_ip
                    if conf.game.emulator == 'custom' and isinstance(emulator_data, CustomEmulatorData)
                    else '127.0.0.1'
                ),
                'customAdbPort': str(
                    emulator_data.adb_port
                    if conf.game.emulator == 'custom' and isinstance(emulator_data, CustomEmulatorData)
                    else 5555
                ),
                'customEmulatorPath': (
                    emulator_data.emulator_path
                    if conf.game.emulator == 'custom' and isinstance(emulator_data, CustomEmulatorData)
                    else ''
                ),
                'customEmulatorArgs': (
                    emulator_data.emulator_args
                    if conf.game.emulator == 'custom' and isinstance(emulator_data, CustomEmulatorData)
                    else ''
                ),
            },
            'live': {
                'songName': conf.live.song_name or SONG_KEEP_UNCHANGED,
                'autoSetUnit': bool(conf.live.auto_set_unit),
                'apMultiplier': '保持现状' if conf.live.ap_multiplier is None else str(conf.live.ap_multiplier),
                'appendFc': bool(conf.live.append_fc),
                'appendRandom': bool(conf.live.prepend_random),
            },
            'challengeLive': {
                'characters': [character.value for character in conf.challenge_live.characters],
                'award': conf.challenge_live.award.value,
            },
            'cm': {'watchAdWaitSec': str(int(conf.cm.watch_ad_wait_sec))},
            'eventShop': {'selectedItems': [item.value for item in conf.event_shop.purchase_items]},
            'telemetry': {'sentry': bool(self._iaa.config.shared.telemetry.sentry)},
        }
        return json.dumps(state, ensure_ascii=False)

    @Slot(result=str)
    def refreshMumuInstancesJson(self) -> str:
        conf = self._iaa.config.conf
        return self._build_mumu_instances_payload(conf.game.emulator)

    @Slot(str, str, result=str)
    def refreshMumuInstancesJsonFor(self, emulator: str, preferred_id: str) -> str:
        return self._build_mumu_instances_payload(str(emulator or ''), str(preferred_id or ''))

    @Slot(str)
    def saveJson(self, state_json: str) -> None:
        try:
            state = json.loads(state_json)
            conf = self._iaa.config.conf
            game = state['game']
            live = state['live']
            challenge = state['challengeLive']
            cm = state['cm']
            event_shop = state['eventShop']
            telemetry = state['telemetry']

            conf.game.emulator = game['emulator']
            conf.game.server = game['server']
            conf.game.link_account = 'no' if conf.game.server == 'tw' else game['linkAccount']
            conf.game.control_impl = game['controlImpl']
            conf.game.check_emulator = bool(game['checkEmulator'])
            conf.game.scrcpy_virtual_display = bool(game['scrcpyVirtualDisplay'])
            conf.game.resolution_method = game['resolutionMethod']

            if conf.game.emulator in {'mumu', 'mumu_v5'}:
                conf.game.emulator_data = MuMuEmulatorData(instance_id=(game.get('mumuInstanceId') or '') or None)
            elif conf.game.emulator == 'custom':
                raw_port = str(game.get('customAdbPort') or '').strip() or '5555'
                conf.game.emulator_data = CustomEmulatorData(
                    adb_ip=(game.get('customAdbIp') or '').strip() or '127.0.0.1',
                    adb_port=int(raw_port),
                    emulator_path=(game.get('customEmulatorPath') or '').strip(),
                    emulator_args=(game.get('customEmulatorArgs') or '').strip(),
                )
            elif conf.game.emulator == 'physical_android':
                conf.game.emulator_data = PhysicalAndroidData(
                    adb_serial=(game.get('physicalAndroidSerial') or '').strip()
                )
            else:
                conf.game.emulator_data = None

            conf.live.song_name = normalize_song_name_input(live['songName'])
            conf.live.auto_set_unit = bool(live['autoSetUnit'])
            conf.live.ap_multiplier = None if live['apMultiplier'] == '保持现状' else int(live['apMultiplier'])
            conf.live.append_fc = bool(live['appendFc'])
            conf.live.prepend_random = bool(live['appendRandom'])

            conf.challenge_live.characters = [GameCharacter(character) for character in challenge['characters']]
            conf.challenge_live.award = ChallengeLiveAward(challenge['award'])

            raw_wait_sec = str(cm['watchAdWaitSec']).strip()
            if not raw_wait_sec:
                raise ValueError('CM 广告等待秒数不能为空')
            wait_sec = int(raw_wait_sec)
            if wait_sec <= 0:
                raise ValueError('CM 广告等待秒数必须大于 0')
            conf.cm.watch_ad_wait_sec = wait_sec

            conf.event_shop.purchase_items = [ShopItem(item_id) for item_id in event_shop.get('selectedItems', [])]
            self._iaa.config.shared.telemetry.sentry = bool(telemetry['sentry'])
            self._iaa.config.save_shared()
            self.operationSucceeded.emit('保存成功')
        except Exception as exc:  # noqa: BLE001
            self.operationFailed.emit(f'保存失败：{exc}')

    @Slot()
    def resetResolution(self) -> None:
        device = self._iaa.scheduler.device
        if device is None:
            def on_success() -> None:
                self._do_reset_resolution()

            def on_error(exc: Exception) -> None:
                self.operationFailed.emit(f'连接失败：{exc}')

            self._iaa.scheduler.connect_device(on_success=on_success, on_error=on_error)
            return
        self._do_reset_resolution()

    def _do_reset_resolution(self) -> None:
        device = self._iaa.scheduler.device
        if device is None:
            self.operationFailed.emit('设备尚未连接')
            return
        try:
            device.commands.adb_shell('wm size reset')
            self.operationSucceeded.emit('已恢复分辨率')
        except Exception as exc:  # noqa: BLE001
            self.operationFailed.emit(f'恢复失败：{exc}')

    @Slot(str, result=bool)
    def switchProfile(self, name: str) -> bool:
        try:
            self._iaa.config.switch_config(name)
            self.configSwitched.emit()
            self.operationSucceeded.emit(f'已切换到配置: {name}')
            return True
        except RuntimeError as e:
            self.operationFailed.emit(str(e))
            return False
        except Exception as exc:  # noqa: BLE001
            self.operationFailed.emit(f'切换失败：{exc}')
            return False

    @Slot(str, result=bool)
    def createProfile(self, name: str) -> bool:
        try:
            self._iaa.config.create(name)
            self.configSwitched.emit()
            self.operationSucceeded.emit(f'已创建并切换到配置: {name}')
            return True
        except Exception as exc:  # noqa: BLE001
            self.operationFailed.emit(f'创建失败：{exc}')
            return False

    @Slot(str, result=bool)
    def deleteProfile(self, name: str) -> bool:
        try:
            deleted_current = self._iaa.config.delete(name)
            if deleted_current:
                self.configSwitched.emit()
            self.operationSucceeded.emit(f'已删除配置: {name}')
            return True
        except FileNotFoundError:
            self.operationFailed.emit(f'配置不存在: {name}')
            return False
        except RuntimeError as e:
            self.operationFailed.emit(str(e))
            return False
        except Exception as exc:  # noqa: BLE001
            self.operationFailed.emit(f'删除失败：{exc}')
            return False

    @Slot(str, str, result=bool)
    def renameProfile(self, old_name: str, new_name: str) -> bool:
        try:
            renamed_current = self._iaa.config.rename(old_name, new_name)
            if renamed_current:
                self.configSwitched.emit()
            self.operationSucceeded.emit(f'已重命名为: {new_name}')
            return True
        except FileNotFoundError:
            self.operationFailed.emit(f'配置不存在: {old_name}')
            return False
        except FileExistsError:
            self.operationFailed.emit(f'配置名称已存在: {new_name}')
            return False
        except Exception as exc:  # noqa: BLE001
            self.operationFailed.emit(f'重命名失败：{exc}')
            return False
