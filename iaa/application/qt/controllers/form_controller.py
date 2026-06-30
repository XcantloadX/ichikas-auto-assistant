import json
from typing import Any, Callable, TypeVar

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot
from PySide6.QtQml import QJSValue

from iaa.application.framework.dsl import RuntimeEngine, SnapshotState
from iaa.application.framework.dsl.specs import ActionSpec

TCtx = TypeVar('TCtx')


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


class FormController(QObject):
    """DSL 表单 controller 基类。

    封装 RuntimeEngine + SnapshotState 的通用生命周期，子类只需实现
    _make_context / _sync_context_back / save 等业务差异部分。
    """

    operationSucceeded = Signal(str)
    operationFailed = Signal(str)
    runtimeChanged = Signal()
    dirtyChanged = Signal(bool)
    fieldUpdated = Signal(str, str)   # (field_id, field_json)
    groupUpdated = Signal(int, bool)  # (group_index, visible)
    _actionDone = Signal(object, object)  # (action, error_or_None)

    def __init__(
        self,
        spec: Any,
        form_hooks: list[Callable],
        initial_context: Any,
        *,
        snapshot_fn: Callable,
        restore_fn: Callable,
        stable_dump_fn: Callable,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._engine = RuntimeEngine(spec)
        self._form_hooks = form_hooks
        self._state = SnapshotState(
            initial_context,
            snapshot_fn=snapshot_fn,
            restore_fn=restore_fn,
            stable_dump_fn=stable_dump_fn,
        )
        self._runtime: dict[str, Any] = {}
        self._recompute_runtime()
        self._actionDone.connect(self._on_action_done)

    # ── 子类实现点 ────────────────────────────────────────────────────────────

    def _make_context(self) -> Any:
        raise NotImplementedError

    def _sync_context_back(self) -> None:
        pass

    # ── 内部工具 ──────────────────────────────────────────────────────────────

    def _recompute_runtime(self) -> None:
        runtime = self._engine.build_runtime(self._state.context)
        runtime['dirty'] = self._state.dirty
        self._runtime = runtime

    def _emit_updates(self, old_runtime: dict[str, Any]) -> None:
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

    def _reload(self) -> None:
        self._state.reset(self._make_context())
        self._recompute_runtime()
        self.runtimeChanged.emit()
        self.dirtyChanged.emit(self._state.dirty)

    def _dispatch_action(self, action: ActionSpec) -> None:
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
                signal.emit(action, error)

        QThreadPool.globalInstance().start(_Runner())

    @Slot(object, object)
    def _on_action_done(self, action: ActionSpec, error: Exception | None) -> None:
        self._sync_context_back()
        self._recompute_runtime()
        self.runtimeChanged.emit()
        if error is not None:
            self.operationFailed.emit(f'刷新失败：{error}')
        else:
            self.operationSucceeded.emit('已刷新')

    # ── 通用 Slot ─────────────────────────────────────────────────────────────

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

    @Slot(result=bool)
    def discard(self) -> bool:
        self._state.discard()
        self._sync_context_back()
        self._recompute_runtime()
        self.runtimeChanged.emit()
        self.dirtyChanged.emit(self._state.dirty)
        return True
