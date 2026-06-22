from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtQml import QJSValue

from iaa.application.framework.dsl import RuntimeEngine, SnapshotState
from ..forms.context import PreferencesContext
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
    languageChanged = Signal(str)
    runtimeChanged = Signal()
    dirtyChanged = Signal(bool)
    fieldUpdated = Signal(str, str)  # (field_id, field_json)
    groupUpdated = Signal(int, bool)  # (group_index, visible)

    def __init__(self, iaa_service: 'IaaService', parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._iaa = iaa_service
        self._rebuild_form()
        self._state = SnapshotState(
            self._make_context(),
            snapshot_fn=self._snapshot_context,
            restore_fn=self._restore_context,
            stable_dump_fn=self._stable_dump_snapshot,
        )
        self._runtime: dict[str, Any] = {}
        self._recompute_runtime()

    def _rebuild_form(self) -> None:
        language = self._iaa.config.shared.interface.language
        self._spec, self._form_hooks = build_preferences_form(language)
        self._engine = RuntimeEngine(self._spec)

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
        self._rebuild_form()
        self._recompute_runtime()
        self.runtimeChanged.emit()
        self.dirtyChanged.emit(self._state.dirty)

    def _recompute_runtime(self) -> None:
        runtime = self._engine.build_runtime(self._state.context)
        runtime['dirty'] = self._state.dirty
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
            old_language = self._state.context.shared.interface.language
            field.ref.set(self._state.context, value)
            if field.on_change:
                field.on_change(self._state.context, value)
            for hook in self._form_hooks:
                hook(self._state.context)

            self._sync_context_back()
            old_runtime = self._runtime
            language_changed = self._state.context.shared.interface.language != old_language
            if language_changed:
                self._rebuild_form()
            self._recompute_runtime()
            if language_changed:
                self.runtimeChanged.emit()
                self.languageChanged.emit(self._state.context.shared.interface.language)
                self.dirtyChanged.emit(self._state.dirty)
            else:
                self._emit_updates(old_runtime)
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
        old_language = self._iaa.config.shared.interface.language
        self._state.discard()
        self._sync_context_back()
        language_changed = self._iaa.config.shared.interface.language != old_language
        if language_changed:
            self._rebuild_form()
        self._recompute_runtime()
        self.runtimeChanged.emit()
        self.dirtyChanged.emit(self._state.dirty)
        if language_changed:
            self.languageChanged.emit(self._iaa.config.shared.interface.language)
        return True

    @Slot(result=str)
    def hotkeyStart(self) -> str:
        return self._iaa.config.shared.hotkeys.start or ''

    @Slot(result=str)
    def hotkeyStop(self) -> str:
        return self._iaa.config.shared.hotkeys.stop or ''
