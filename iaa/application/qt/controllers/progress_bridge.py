from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QObject, Property, Signal

from iaa.context import hub as progress_hub
<<<<<<< HEAD
from iaa.progress import ProgressHub, TaskProgressEvent
=======
from iaa.progress import TaskProgressEvent, Translatable
>>>>>>> feat/en-server

from ..models import ProgressState, progress_event_to_state


class ProgressBridge(QObject):
    changed = Signal()

<<<<<<< HEAD
    def __init__(self, parent: QObject | None = None, hub: ProgressHub | None = None) -> None:
=======
    def __init__(self, get_language: Callable[[], str], parent: QObject | None = None) -> None:
>>>>>>> feat/en-server
        super().__init__(parent)
        self._get_language = get_language
        self._state = ProgressState()
        _hub = hub if hub is not None else progress_hub()
        self._unsubscribe = _hub.subscribe(self._on_event)

    def close(self) -> None:
        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None

    def _on_event(self, event: TaskProgressEvent) -> None:
        self._state = progress_event_to_state(event, self._state)
        self.changed.emit()

    def on_language_changed(self) -> None:
        self.changed.emit()

    def _resolve(self, value: 'list | Translatable | str') -> str:
        lang = self._get_language()
        if isinstance(value, list):
            parts = []
            for p in value:
                r = p.resolve(lang) if isinstance(p, Translatable) else p
                if r:
                    parts.append(r)
            return ' > '.join(parts)
        if isinstance(value, Translatable):
            return value.resolve(lang)
        return value

    def _get_status_text(self) -> str:
        return self._resolve(self._state.status_text)

    def _get_progress_percent(self) -> int:
        return self._state.progress_percent

    def _get_last_error_text(self) -> str:
        return self._resolve(self._state.last_error_text)

    statusText = Property(str, _get_status_text, notify=changed)
    progressPercent = Property(int, _get_progress_percent, notify=changed)
    lastErrorText = Property(str, _get_last_error_text, notify=changed)
