from __future__ import annotations

import json
from typing import Any

from ..dsl import PreferencesContext


class PreferencesState:
    def __init__(self, context: PreferencesContext) -> None:
        self._context = context
        self._saved_shared = context.shared.model_copy(deep=True)

    @property
    def context(self) -> PreferencesContext:
        return self._context

    def reset(self, context: PreferencesContext) -> None:
        self._context = context
        self._saved_shared = context.shared.model_copy(deep=True)

    def mark_saved(self) -> None:
        self._saved_shared = self._context.shared.model_copy(deep=True)

    @property
    def dirty(self) -> bool:
        current = self._stable_dump(self._context.shared)
        saved = self._stable_dump(self._saved_shared)
        return current != saved

    def discard(self) -> None:
        self._context.shared = self._saved_shared.model_copy(deep=True)

    def _stable_dump(self, shared: Any) -> str:
        return json.dumps(shared.model_dump(mode='json'), sort_keys=True, ensure_ascii=False)
