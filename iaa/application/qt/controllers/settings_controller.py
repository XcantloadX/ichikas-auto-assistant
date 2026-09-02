from __future__ import annotations

import json
import logging
import threading
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtQml import QJSValue

from iaa.config.base import IaaConfig

from .config_draft import ConfigDraft

if TYPE_CHECKING:
    from iaa.application.service.iaa_service import IaaService

logger = logging.getLogger(__name__)


def _normalize_qt_value(value: Any) -> Any:
    """把 QML 传入的 QJSValue/QVariant 递归归一化为纯 Python 对象。"""
    if isinstance(value, QJSValue):
        return _normalize_qt_value(value.toVariant())
    if isinstance(value, list):
        return [_normalize_qt_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_normalize_qt_value(item) for item in value)
    if isinstance(value, dict):
        return {key: _normalize_qt_value(item) for key, item in value.items()}
    return value


class SettingsController(QObject):
    """设置控制器：草稿模式（kaa 风格表单）。

    设置页 QML 直写表单字段：``config`` 暴露 base+dirty 合并视图，
    ``setField``/``setListField`` 写入草稿，``save`` 归一化+校验+写盘。
    """

    configChanged = Signal()
    dirtyChanged = Signal(bool)
    operationSucceeded = Signal(str)
    operationFailed = Signal(str)
    configSwitched = Signal()
    currentProfileChanged = Signal(str)
    profilesChanged = Signal()
    emulatorInstancesReady = Signal(str, str)
    emulatorNotInstalled = Signal(str)

    def __init__(self, iaa_service: 'IaaService', parent=None) -> None:
        super().__init__(parent)
        self._iaa = iaa_service
        self._last_issues: list[dict[str, Any]] = []
        self._draft = ConfigDraft(self._base_config())

    def _base_config(self) -> dict[str, Any]:
        return self._iaa.config.conf.model_dump(mode='json')

    def _reload(self) -> None:
        """从 live 配置重建草稿（切换/新建/删除/重命名配置后调用）。"""
        self._draft = ConfigDraft(self._base_config())
        self._last_issues = []
        self.configChanged.emit()
        self.dirtyChanged.emit(False)

    # ── 表单读写 ─────────────────────────────────────────────────────────────

    @Property('QVariantMap', notify=configChanged)
    def config(self) -> dict[str, Any]:
        """草稿视图：base + dirty 合并。"""
        return self._draft.view()

    @Slot(str, 'QVariant')
    def setField(self, path: str, value) -> None:
        """字段进草稿。path 为完整 dot path（相对 conf 根）。"""
        self._draft.set(path, _normalize_qt_value(value))
        self.configChanged.emit()
        self.dirtyChanged.emit(self._draft.is_dirty())

    @Slot(str, 'QVariantList')
    def setListField(self, path: str, value) -> None:
        """列表字段进草稿。QML 数组应走此 Slot 以触发 Qt 类型转换。"""
        self._draft.set(path, list(_normalize_qt_value(value)))
        self.configChanged.emit()
        self.dirtyChanged.emit(self._draft.is_dirty())

    @Slot(result=bool)
    def isDirty(self) -> bool:
        return self._draft.is_dirty()

    @Slot(result=bool)
    def discard(self) -> bool:
        """丢弃未保存编辑。"""
        self._draft.discard()
        self.configChanged.emit()
        self.dirtyChanged.emit(False)
        return True

    @Slot(result=bool)
    def save(self) -> bool:
        """提交草稿：归一化 → 校验 → 写盘。"""
        if not self._draft.is_dirty():
            self.operationSucceeded.emit('没有需要保存的更改')
            return True
        merged = self._normalize(self._draft.view())
        issues = self._collect_issues(merged)
        errors = [i for i in issues if i.get('severity') == 'error']
        if errors:
            self._last_issues = issues
            self.operationFailed.emit('；'.join(i['message'] for i in errors))
            return False
        try:
            candidate = IaaConfig.model_validate(merged)
        except Exception as exc:  # noqa: BLE001
            logger.warning('Settings draft validation failed: %s', exc)
            self._last_issues = [{'severity': 'error', 'field': None, 'message': f'配置结构无效：{exc}'}]
            self.operationFailed.emit(f'配置结构无效：{exc}')
            return False
        try:
            self._iaa.config.conf = candidate
            self._iaa.config.save()
        except Exception as exc:  # noqa: BLE001
            logger.exception('Failed to save settings')
            self.operationFailed.emit(f'保存失败：{exc}')
            return False
        self._draft = ConfigDraft(candidate.model_dump(mode='json'))
        self._last_issues = []
        self.configChanged.emit()
        self.dirtyChanged.emit(False)
        self.operationSucceeded.emit('保存成功')
        return True

    @Slot(result=str)
    def validateJson(self) -> str:
        """校验当前草稿（归一化后），返回 issue 列表 JSON。不提交、不写盘。"""
        try:
            merged = self._normalize(self._draft.view())
            issues = self._collect_issues(merged)
            try:
                IaaConfig.model_validate(merged)
            except Exception as exc:  # noqa: BLE001
                issues = issues + [{'severity': 'error', 'field': None, 'message': f'配置结构无效：{exc}'}]
            return json.dumps(issues, ensure_ascii=False)
        except Exception as exc:  # noqa: BLE001
            logger.exception('Failed to validate settings draft')
            return json.dumps(
                [{'severity': 'error', 'field': None, 'message': f'校验失败：{exc}'}],
                ensure_ascii=False,
            )

    # ── 归一化与校验 ─────────────────────────────────────────────────────────

    @staticmethod
    def _normalize(data: dict[str, Any]) -> dict[str, Any]:
        """对合并后的草稿 dict 做跨字段归一化（在 copy 上操作）。"""
        device = data.get('device', {})
        lifecycle = device.get('lifecycle', {})
        connection = device.get('connection', {})
        lc_type = lifecycle.get('type', 'none')
        conn_type = connection.get('type', 'usb')

        # connection 约束：mumu/avd 强制 auto，custom 强制 tcp，none 强制 usb
        if lc_type in ('mumu', 'mumu_v5', 'avd'):
            if conn_type != 'auto':
                connection['type'] = 'auto'
        elif lc_type == 'custom':
            if conn_type == 'auto':
                connection['type'] = 'tcp'
        elif lc_type == 'none':
            if conn_type == 'auto':
                connection['type'] = 'usb'

        # control_impl 约束
        impl = device.get('control_impl', 'adb')
        if impl == 'nemu_ipc' and lc_type not in ('mumu', 'mumu_v5'):
            impl = 'adb'
        elif impl == 'qemu_grpc' and lc_type != 'avd':
            impl = 'adb'
        device['control_impl'] = impl
        if impl == 'qemu_grpc':
            device['resolution_method'] = 'keep'

        # game 联动约束
        game = data.get('game', {})
        if game.get('server', 'jp') != 'jp':
            game['link_account'] = 'no'

        # 字符串 → 类型归一化
        if connection.get('type') == 'tcp':
            port = connection.get('port')
            if port is not None and not isinstance(port, bool) and not isinstance(port, int):
                text = str(port).strip()
                if text.isdigit():
                    connection['port'] = int(text)
                elif text == '':
                    connection['port'] = None

        cm = data.get('tasks', {}).get('cm', {})
        wa = cm.get('watch_ad_wait_sec')
        if not isinstance(wa, bool) and not isinstance(wa, int):
            wtext = str(wa or '').strip()
            if wtext.isdigit():
                cm['watch_ad_wait_sec'] = int(wtext)

        # nullable 字符串兜底（QML 侧已处理，此处作为安全网）
        solo = data.get('tasks', {}).get('solo_live', {})
        if solo.get('song_name') in (None, '', '保持不变'):
            solo['song_name'] = None
        if solo.get('ap_multiplier') == '保持现状':
            solo['ap_multiplier'] = None
        if lc_type in ('mumu', 'mumu_v5') and lifecycle.get('instance_id') == '':
            lifecycle['instance_id'] = None
        if lc_type == 'avd':
            if lifecycle.get('avd_name') == '':
                lifecycle['avd_name'] = None
            if lifecycle.get('sdk_path') == '':
                lifecycle['sdk_path'] = None
        if lc_type == 'custom' and lifecycle.get('start_command') is not None:
            lifecycle['start_command'] = str(lifecycle['start_command']).strip()

        return data

    @staticmethod
    def _collect_issues(data: dict[str, Any]) -> list[dict[str, Any]]:
        """收集业务校验问题（归一化后的 dict）。"""
        issues: list[dict[str, Any]] = []
        device = data.get('device', {})
        lifecycle = device.get('lifecycle', {})
        connection = device.get('connection', {})

        if connection.get('type') == 'tcp':
            port = connection.get('port')
            text = '' if port is None else str(port).strip()
            if not text:
                issues.append({'severity': 'error', 'field': 'device.connection.port', 'message': '端口不能为空'})
            elif not text.isdigit():
                issues.append({'severity': 'error', 'field': 'device.connection.port', 'message': '端口必须是数字'})

        if lifecycle.get('type') == 'custom':
            start = str(lifecycle.get('start_command') or '').strip()
            if not start:
                issues.append({'severity': 'error', 'field': 'device.lifecycle.start_command', 'message': '启动命令不能为空'})

        cm = data.get('tasks', {}).get('cm', {})
        wa = cm.get('watch_ad_wait_sec')
        wtext = '' if wa is None else str(wa).strip()
        if not wtext:
            issues.append({'severity': 'error', 'field': 'tasks.cm.watch_ad_wait_sec', 'message': 'CM 广告等待秒数不能为空'})
        elif not wtext.isdigit():
            issues.append({'severity': 'error', 'field': 'tasks.cm.watch_ad_wait_sec', 'message': 'CM 广告等待秒数必须是数字'})
        elif int(wtext) <= 0:
            issues.append({'severity': 'error', 'field': 'tasks.cm.watch_ad_wait_sec', 'message': 'CM 广告等待秒数必须大于 0'})

        return issues

    # ── 表单选项数据 ─────────────────────────────────────────────────────────

    @Slot(result=str)
    def lifecycleOptionsJson(self) -> str:
        """平台过滤后的设备类型选项。"""
        import platform as _platform

        from ..models import LIFECYCLE_TYPE_DISPLAY_MAP

        options = [
            {'value': k, 'label': v}
            for k, v in LIFECYCLE_TYPE_DISPLAY_MAP.items()
            if not (k in {'mumu', 'mumu_v5'} and _platform.system() != 'Windows')
            and not (k == 'playcover' and _platform.system() != 'Darwin')
        ]
        return json.dumps(options, ensure_ascii=False)

    @Slot(result=str)
    def connectionOptionsJson(self) -> str:
        from ..models import CONNECTION_TYPE_DISPLAY_MAP
        return json.dumps(
            [{'value': k, 'label': v} for k, v in CONNECTION_TYPE_DISPLAY_MAP.items()],
            ensure_ascii=False,
        )

    @Slot(result=str)
    def serverOptionsJson(self) -> str:
        from ..models import SERVER_DISPLAY_MAP
        return json.dumps(
            [{'value': k, 'label': v} for k, v in SERVER_DISPLAY_MAP.items()],
            ensure_ascii=False,
        )

    @Slot(result=str)
    def linkOptionsJson(self) -> str:
        from ..models import LINK_DISPLAY_MAP
        return json.dumps(
            [{'value': k, 'label': v} for k, v in LINK_DISPLAY_MAP.items()],
            ensure_ascii=False,
        )

    @Slot(result=str)
    def controlImplOptionsJson(self) -> str:
        from ..models import CONTROL_IMPL_DISPLAY_MAP
        return json.dumps(
            [{'value': k, 'label': v} for k, v in CONTROL_IMPL_DISPLAY_MAP.items()],
            ensure_ascii=False,
        )

    @Slot(result=str)
    def resolutionOptionsJson(self) -> str:
        from ..models import RESOLUTION_METHOD_DISPLAY_MAP
        return json.dumps(
            [{'value': k, 'label': v} for k, v in RESOLUTION_METHOD_DISPLAY_MAP.items()],
            ensure_ascii=False,
        )

    @Slot(result=str)
    def challengeCharactersJson(self) -> str:
        from ..models import challenge_character_groups_for_ui
        return json.dumps(challenge_character_groups_for_ui(), ensure_ascii=False)

    @Slot(result=str)
    def challengeAwardsJson(self) -> str:
        from ..models import challenge_awards_for_ui
        return json.dumps(challenge_awards_for_ui(), ensure_ascii=False)

    @Slot(result=str)
    def eventShopItemsJson(self) -> str:
        from iaa.definitions.enums import ShopItem
        return json.dumps(
            [{'value': item.value, 'label': item.display('cn')} for item in ShopItem],
            ensure_ascii=False,
        )

    # ── 设备实例枚举 ─────────────────────────────────────────────────────────

    @Slot(str)
    def listEmulatorInstancesAsync(self, emulator_type: str) -> None:
        """后台枚举模拟器实例（mumu / mumu_v5 / avd），结果经信号返回。"""

        def _run() -> None:
            try:
                options = self._enumerate_instances(emulator_type)
                self.emulatorInstancesReady.emit(
                    emulator_type,
                    json.dumps(options, ensure_ascii=False),
                )
            except Exception as exc:  # noqa: BLE001
                logger.exception('Failed to enumerate instances for %s', emulator_type)
                self.operationFailed.emit(f'刷新失败：{exc}')
                self.emulatorInstancesReady.emit(emulator_type, '[]')

        threading.Thread(target=_run, daemon=True).start()

    def _enumerate_instances(self, emulator_type: str) -> list[dict[str, Any]]:
        """返回 {value, label} 选项列表（含默认占位项）。"""
        if emulator_type in ('mumu', 'mumu_v5'):
            from kotonebot.client.host import Mumu12Host, Mumu12V5Host

            from ..models import DEFAULT_MUMU_INSTANCE_LABEL

            host_cls = Mumu12V5Host if emulator_type == 'mumu_v5' else Mumu12Host
            instances = host_cls.list()
            return [{'value': '', 'label': DEFAULT_MUMU_INSTANCE_LABEL}] + [
                {'value': str(inst.id), 'label': f'[{inst.id}] {inst.name}'}
                for inst in instances
            ]
        if emulator_type == 'avd':
            from iaa.application.service.avd import AvdHost

            sdk_path = self._draft.get('device.lifecycle.sdk_path')
            host = AvdHost(sdk_path=sdk_path)
            instances = host.list()
            return [{'value': '', 'label': '（默认第一个）'}] + [
                {'value': inst._avd_name,
                 'label': f'{inst._avd_name}{"  [运行中]" if inst.adb_serial else ""}'}
                for inst in instances
            ]
        return []

    # ── 分辨率 ───────────────────────────────────────────────────────────────

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

    # ── 配置文件管理 ─────────────────────────────────────────────────────────

    @Slot(result=str)
    def currentProfileName(self) -> str:
        return self._iaa.config.current_config_name

    @Slot(result=str)
    def profilesJson(self) -> str:
        profiles = [{'value': name, 'label': name} for name in self._iaa.config.list()]
        return json.dumps({'profiles': profiles}, ensure_ascii=False)

    @Slot(str, result=bool)
    def switchProfile(self, name: str) -> bool:
        try:
            self._iaa.config.switch_config(name)
            self._reload()
            self.configSwitched.emit()
            self.currentProfileChanged.emit(self._iaa.config.current_config_name)
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
            self._reload()
            self.configSwitched.emit()
            self.profilesChanged.emit()
            self.currentProfileChanged.emit(self._iaa.config.current_config_name)
            self.operationSucceeded.emit(f'已创建并切换到配置: {name}')
            return True
        except Exception as exc:  # noqa: BLE001
            self.operationFailed.emit(f'创建失败：{exc}')
            return False

    @Slot(str, result=bool)
    def deleteProfile(self, name: str) -> bool:
        try:
            deleted_current = self._iaa.config.delete(name)
            self._reload()
            self.profilesChanged.emit()
            if deleted_current:
                self.configSwitched.emit()
                self.currentProfileChanged.emit(self._iaa.config.current_config_name)
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
            self._reload()
            self.profilesChanged.emit()
            if renamed_current:
                self.configSwitched.emit()
                self.currentProfileChanged.emit(self._iaa.config.current_config_name)
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
