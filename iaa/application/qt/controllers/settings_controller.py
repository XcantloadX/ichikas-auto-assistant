from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot
from PySide6.QtQml import QJSValue

from iaa.application.framework.dsl import RuntimeEngine, SnapshotState
from iaa.application.framework.dsl.specs import ActionSpec
from ..forms.context import FormContext
from ..forms.settings_form import build_settings_form

if TYPE_CHECKING:
    from iaa.application.service.iaa_service import IaaService

logger = logging.getLogger(__name__)

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
    # 内部信号，用于从工作线程安全回到主线程
    _actionDone = Signal(object, object)  # (action, error_or_None)

    def __init__(self, iaa_service: 'IaaService', parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._iaa = iaa_service
        self._spec, self._form_hooks = build_settings_form(
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
        # 连接内部信号到主线程槽
        self._actionDone.connect(self._on_action_done)

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

    def _dispatch_action(self, action: ActionSpec) -> None:
        """在线程池中执行 action，完成后通过内部信号回到主线程更新 runtime。"""
        ctx = self._state.context
        action._state.loading = True
        action._state.error = ''
        self._recompute_runtime()
        self.runtimeChanged.emit()

        signal = self._actionDone

        class _Runner(QRunnable):
            def run(self) -> None:
                error: Exception | None = None
                try:
                    result = action.fn(ctx)
                    action._state.result = result
                    action._state.error = ''
                except Exception as exc:  # noqa: BLE001
                    error = exc
                    action._state.error = str(exc)
                finally:
                    action._state.loading = False
                # 通过信号安全地回到 Qt 主线程
                signal.emit(action, error)

        QThreadPool.globalInstance().start(_Runner())

    @Slot(object, object)
    def _on_action_done(self, action: ActionSpec, error: Exception | None) -> None:
        """工作线程完成后，在主线程中更新 runtime 并通知 UI。"""
        self._sync_context_back()
        self._recompute_runtime()
        self.runtimeChanged.emit()
        if error is not None:
            self.operationFailed.emit(f'刷新失败：{error}')
        else:
            self.operationSucceeded.emit('已刷新')

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
    def triggerAction(self, field_id: str, action_name: str, payload_json: str = '{}') -> None:
        _ = payload_json
        field = self._engine.find_field(field_id)
        if field is None:
            self.operationFailed.emit(f'未知字段: {field_id}')
            return
        action = next((a for a in field.actions if a.name == action_name), None)
        if action is None:
            self.operationFailed.emit(f'不支持的动作: {field_id}.{action_name}')
            return
        if not action.threaded:
            try:
                action.fn(self._state.context)
            except Exception as exc:  # noqa: BLE001
                self.operationFailed.emit(str(exc))
        else:
            self._dispatch_action(action)

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
