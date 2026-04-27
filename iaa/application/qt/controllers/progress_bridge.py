from __future__ import annotations

from PySide6.QtCore import QObject, Property, Signal

from iaa.context import hub as progress_hub
from iaa.progress import TaskProgressEvent

from ..models import ProgressState, progress_event_to_state


class ProgressBridge(QObject):
    changed = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._state = ProgressState()
        self._unsubscribe = progress_hub().subscribe(self._on_event)

    def close(self) -> None:
        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None

    def _on_event(self, event: TaskProgressEvent) -> None:
        self._state = progress_event_to_state(event, self._state)
        self.changed.emit()

    def _get_status_text(self) -> str:
        return self._state.status_text

    def _get_progress_percent(self) -> int:
        return self._state.progress_percent

    def _get_last_error_text(self) -> str:
        return self._state.last_error_text

    statusText = Property(str, _get_status_text, notify=changed)
    progressPercent = Property(int, _get_progress_percent, notify=changed)
    lastErrorText = Property(str, _get_last_error_text, notify=changed)
