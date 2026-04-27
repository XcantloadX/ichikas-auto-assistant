from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtQml import QJSValue

from iaa.application.framework.dsl import PreferencesContext, RuntimeEngine, SnapshotState
from ..forms.preferences_form import build_preferences_form

if TYPE_CHECKING:
    from iaa.application.service.iaa_service import IaaService


def _normalize_qt_value(value: Any) -> Any:
    if isinstance(value, QJSValue):
        return _normalize_qt_value(value.toVariant())
    if isinstance(value, list):
        return [_normalize_qt_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_normalize_qt_value(item) for item in value)
    if isinstance(value, dict):
        return {key: _normalize_qt_value(item) for key, item in value.items()}
    return value


class PreferencesController(QObject):
    operationSucceeded = Signal(str)
    operationFailed = Signal(str)
    runtimeChanged = Signal()
    dirtyChanged = Signal(bool)

    def __init__(self, iaa_service: 'IaaService', parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._iaa = iaa_service
        self._spec, self._form_hooks = build_preferences_form()
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
    def _snapshot_context(context: PreferencesContext) -> dict[str, Any]:
        return {'shared': context.shared.model_copy(deep=True)}

    @staticmethod
    def _restore_context(context: PreferencesContext, snapshot: dict[str, Any]) -> None:
        context.shared = snapshot['shared']

    @staticmethod
    def _stable_dump_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
        return {'shared': snapshot['shared'].model_dump(mode='json')}

    def _make_context(self) -> PreferencesContext:
        return PreferencesContext(shared=self._iaa.config.shared)

    def _sync_context_back(self) -> None:
        self._iaa.config.shared = self._state.context.shared

    def _reload(self) -> None:
        self._state.reset(self._make_context())
        self._recompute_runtime()
        self.runtimeChanged.emit()
        self.dirtyChanged.emit(self._state.dirty)

    def _recompute_runtime(self) -> None:
        runtime = self._engine.build_runtime(self._state.context)
        runtime['dirty'] = self._state.dirty
        self._runtime = runtime

    @Slot(result=str)
    def getRuntime(self) -> str:
        return json.dumps(self._runtime, ensure_ascii=False)

    @Slot(result=bool)
    def isDirty(self) -> bool:
        return self._state.dirty

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
            self._recompute_runtime()
            self.runtimeChanged.emit()
            self.dirtyChanged.emit(self._state.dirty)
        except Exception as exc:
            self.operationFailed.emit(f'设置字段失败：{exc}')

    @Slot(result=bool)
    def save(self) -> bool:
        try:
            self._sync_context_back()
            self._iaa.config.save_shared()
            self._state.mark_saved()
            self._recompute_runtime()
            self.runtimeChanged.emit()
            self.dirtyChanged.emit(self._state.dirty)
            self.operationSucceeded.emit('保存成功')
            return True
        except Exception as exc:
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
