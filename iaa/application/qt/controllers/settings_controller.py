from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtQml import QJSValue

from iaa.application.framework.dsl import RuntimeEngine, SnapshotState
from ..forms.context import FormContext
from ..forms.settings_form import build_settings_form
from ..models import DEFAULT_MUMU_INSTANCE_LABEL

if TYPE_CHECKING:
    from iaa.application.service.iaa_service import IaaService


def _normalize_qt_value(value: Any) -> Any:
    """Convert QML-passed values into plain Python containers/scalars."""
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
    operationSucceeded = Signal(str)
    operationFailed = Signal(str)
    configSwitched = Signal()
    currentProfileChanged = Signal(str)
    profilesChanged = Signal()
    runtimeChanged = Signal()
    dirtyChanged = Signal(bool)
    fieldUpdated = Signal(str, str)  # (field_id, field_json)
    groupUpdated = Signal(int, bool)  # (group_index, visible)

    def __init__(self, iaa_service: 'IaaService', parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._iaa = iaa_service
        self._mumu_instances: list[dict[str, Any]] = [{'value': '', 'label': DEFAULT_MUMU_INSTANCE_LABEL}]
        self._spec, self._form_hooks = build_settings_form(
            self._mumu_instances,
            on_mumu_refresh=self._action_mumu_refresh,
            on_reset_resolution=self._action_reset_resolution,
        )
        self._engine = RuntimeEngine(self._spec)
        self._state = SnapshotState(
            self._make_context(),
            snapshot_fn=self._snapshot_context,
            restore_fn=self._restore_context,
            stable_dump_fn=self._stable_dump_snapshot,
        )
        self._runtime: dict[str, Any] = {}
        self._recompute_runtime()

    @staticmethod
    def _snapshot_context(context: FormContext) -> dict[str, Any]:
        return {
            'conf': context.conf.model_copy(deep=True),
            'shared': context.shared.model_copy(deep=True),
        }

    @staticmethod
    def _restore_context(context: FormContext, snapshot: dict[str, Any]) -> None:
        context.conf = snapshot['conf']
        context.shared = snapshot['shared']

    @staticmethod
    def _stable_dump_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
        conf = snapshot['conf']
        shared = snapshot['shared']
        return {
            'conf': conf.model_dump(mode='json'),
            'shared': shared.model_dump(mode='json'),
        }

    def _make_context(self) -> FormContext:
        return FormContext(
            conf=self._iaa.config.conf,
            shared=self._iaa.config.shared,
        )

    def _sync_context_back(self) -> None:
        self._iaa.config.conf = self._state.context.conf
        self._iaa.config.shared = self._state.context.shared

    def _reload(self) -> None:
        self._mumu_instances[:] = [{'id': '', 'label': DEFAULT_MUMU_INSTANCE_LABEL}]
        self._state.reset(self._make_context())
        self._recompute_runtime()
        self.runtimeChanged.emit()
        self.dirtyChanged.emit(self._state.dirty)

    def _recompute_runtime(self) -> None:
        runtime = self._engine.build_runtime(self._state.context)
        runtime['dirty'] = self._state.dirty
        runtime['profileName'] = self._iaa.config.current_config_name
        self._runtime = runtime

    def _emit_updates(self, old_runtime: dict[str, Any]) -> None:
        """比较新旧 runtime，逐字段发 fieldUpdated，逐分组发 groupUpdated。"""
        new_field_map: dict[str, Any] = self._runtime.get('fieldMap', {})
        old_field_map: dict[str, Any] = old_runtime.get('fieldMap', {})
        new_groups: list[dict[str, Any]] = self._runtime.get('groups', [])
        old_groups: list[dict[str, Any]] = old_runtime.get('groups', [])

        for i, (old_g, new_g) in enumerate(zip(old_groups, new_groups)):
            if old_g.get('visible', True) != new_g.get('visible', True):
                self.groupUpdated.emit(i, bool(new_g.get('visible', True)))

        for field_id, new_field in new_field_map.items():
            if old_field_map.get(field_id) != new_field:
                self.fieldUpdated.emit(field_id, json.dumps(new_field, ensure_ascii=False))

        self.dirtyChanged.emit(self._state.dirty)

    def _get_mumu_instance_id(self) -> str:
        from iaa.config.schemas import MuMuDevice
        lc = self._state.context.conf.device.lifecycle
        if isinstance(lc, MuMuDevice):
            return lc.instance_id or ''
        return ''

    def _set_mumu_instance_id(self, selected_id: str) -> None:
        from iaa.config.schemas import MuMuDevice
        lc = self._state.context.conf.device.lifecycle
        if isinstance(lc, MuMuDevice):
            lc.instance_id = selected_id or None

    def _refresh_mumu_runtime(self, preferred_id: str = '', show_notice: bool = True) -> None:
        from iaa.config.schemas import MuMuDevice
        lc = self._state.context.conf.device.lifecycle
        emulator = lc.type if isinstance(lc, MuMuDevice) else ''
        payload = json.loads(self._build_mumu_instances_payload(emulator, preferred_id))
        self._mumu_instances[:] = payload.get(
            'items', [{'value': '', 'label': DEFAULT_MUMU_INSTANCE_LABEL}]
        )

        selected_id = str(payload.get('selectedId', '') or '')
        if selected_id != self._get_mumu_instance_id():
            self._set_mumu_instance_id(selected_id)

        self._sync_context_back()
        self._recompute_runtime()
        self.runtimeChanged.emit()
        self.dirtyChanged.emit(self._state.dirty)

        if show_notice:
            if payload.get('ok'):
                self.operationSucceeded.emit(str(payload.get('statusText', '已刷新 MuMu 实例')))
            else:
                self.operationFailed.emit(str(payload.get('statusText', '刷新 MuMu 实例失败')))

    def _build_mumu_instances_payload(self, emulator: str, preferred_id: str = '') -> str:
        if emulator not in {'mumu', 'mumu_v5'}:
            return json.dumps(
                {
                    'ok': True,
                    'items': [{'value': '', 'label': DEFAULT_MUMU_INSTANCE_LABEL}],
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
            conf = self._state.context.conf
            lc = conf.device.lifecycle
            from iaa.config.schemas import MuMuDevice
            if (
                isinstance(lc, MuMuDevice)
                and lc.type == emulator
                and lc.instance_id
            ):
                saved_id = lc.instance_id
            items = [{'value': '', 'label': DEFAULT_MUMU_INSTANCE_LABEL}] + [
                {'value': str(instance.id), 'label': f'[{instance.id}] {instance.name}'}
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
                    'items': [{'value': '', 'label': DEFAULT_MUMU_INSTANCE_LABEL}],
                    'selectedId': '',
                    'statusText': f'刷新失败：{exc}',
                },
                ensure_ascii=False,
            )

    @Slot(result=str)
    def getRuntime(self) -> str:
        return json.dumps(self._runtime, ensure_ascii=False)

    @Slot(result=bool)
    def isDirty(self) -> bool:
        return self._state.dirty

    @Slot(result=str)
    def currentProfileName(self) -> str:
        return self._iaa.config.current_config_name

    @Slot(result=str)
    def profilesJson(self) -> str:
        profiles = [{'value': name, 'label': name} for name in self._iaa.config.list()]
        return json.dumps({'profiles': profiles}, ensure_ascii=False)

    @Slot(str, 'QVariant')
    def setValue(self, field_id: str, value: Any) -> None:
        try:
            field = self._engine.find_field(field_id)
            if field is None:
                raise KeyError(f'Unknown field id: {field_id}')

            value = _normalize_qt_value(value)
            field.ref.set(self._state.context, value)
            if field.on_change:
                field.on_change(self._state.context, value)
            for hook in self._form_hooks:
                hook(self._state.context)

            self._sync_context_back()
            old_runtime = self._runtime
            self._recompute_runtime()
            self._emit_updates(old_runtime)
        except Exception as exc:  # noqa: BLE001
            self.operationFailed.emit(f'设置字段失败：{exc}')

    @Slot(str, str, str)
    def triggerAction(self, field_id: str, action: str, payload_json: str = '{}') -> None:
        _ = payload_json
        field = self._engine.find_field(field_id)
        if field is None:
            self.operationFailed.emit(f'未知字段: {field_id}')
            return
        callback = field.actions.get(action)
        if callback is None:
            self.operationFailed.emit(f'不支持的动作: {field_id}.{action}')
            return
        try:
            callback(self._state.context)
        except Exception as exc:  # noqa: BLE001
            self.operationFailed.emit(str(exc))

    def _action_mumu_refresh(self, _ctx: object) -> None:
        preferred_id = self._get_mumu_instance_id()
        self._refresh_mumu_runtime(preferred_id=preferred_id, show_notice=True)

    def _action_reset_resolution(self, _ctx: object) -> None:
        self.resetResolution()

    @Slot(result=bool)
    def save(self) -> bool:
        try:
            self._sync_context_back()
            self._iaa.config.save()
            self._state.mark_saved()
            self._recompute_runtime()
            self.runtimeChanged.emit()
            self.dirtyChanged.emit(self._state.dirty)
            self.operationSucceeded.emit('保存成功')
            return True
        except Exception as exc:  # noqa: BLE001
            self.operationFailed.emit(f'保存失败：{exc}')
            return False

    @Slot(result=bool)
    def discard(self) -> bool:
        self._state.discard()
        self._sync_context_back()
        self._recompute_runtime()
        self.runtimeChanged.emit()
        self.dirtyChanged.emit(self._state.dirty)
        return True

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
