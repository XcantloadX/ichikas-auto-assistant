from __future__ import annotations

from typing import Any

from typing_extensions import override
from PySide6.QtCore import Slot

from iaa.config import manager as config_manager
from ..forms.context import PreferencesContext
from ..forms.preferences_form import build_preferences_form
from .form_controller import FormController


class PreferencesController(FormController):

    def __init__(self, parent=None) -> None:
        spec, form_hooks = build_preferences_form()
        super().__init__(
            spec,
            form_hooks,
            self._make_context(),
            snapshot_fn=self._snapshot_context,
            restore_fn=self._restore_context,
            stable_dump_fn=self._stable_dump_snapshot,
            parent=parent,
        )

    # ── context 生命周期 ───────────────────────────────────────────────────────

    @staticmethod
    def _snapshot_context(context: PreferencesContext) -> dict[str, Any]:
        return {'shared': context.shared.model_copy(deep=True)}

    @staticmethod
    def _restore_context(context: PreferencesContext, snapshot: dict[str, Any]) -> None:
        context.shared = snapshot['shared']

    @staticmethod
    def _stable_dump_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
        return {'shared': snapshot['shared'].model_dump(mode='json')}

    @override
    def _make_context(self) -> PreferencesContext:
        return PreferencesContext(shared=config_manager.read_shared())

    @override
    def _sync_context_back(self) -> None:
        config_manager.update_shared(self._state.context.shared)

    # ── Slot ──────────────────────────────────────────────────────────────────

    @Slot(result=bool)
    def save(self) -> bool:
        try:
            config_manager.write_shared(self._state.context.shared)
            self._state.mark_saved()
            self._recompute_runtime()
            self.runtimeChanged.emit()
            self.dirtyChanged.emit(self._state.dirty)
            self.operationSucceeded.emit('保存成功')
            return True
        except Exception as exc:  # noqa: BLE001
            self.operationFailed.emit(f'保存失败：{exc}')
            return False

    @Slot(result=str)
    def hotkeyStart(self) -> str:
        return config_manager.read_shared().hotkeys.start or ''

    @Slot(result=str)
    def hotkeyStop(self) -> str:
        return config_manager.read_shared().hotkeys.stop or ''
