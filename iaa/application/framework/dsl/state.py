from __future__ import annotations

import json
from copy import deepcopy
from typing import Any, Callable, Generic, TypeVar

TContext = TypeVar('TContext')
TSnapshot = TypeVar('TSnapshot')


class SnapshotState(Generic[TContext, TSnapshot]):
    def __init__(
        self,
        context: TContext,
        *,
        snapshot_fn: Callable[[TContext], TSnapshot],
        restore_fn: Callable[[TContext, TSnapshot], None],
        stable_dump_fn: Callable[[TSnapshot], Any] | None = None,
    ) -> None:
        self._context = context
        self._snapshot_fn = snapshot_fn
        self._restore_fn = restore_fn
        self._stable_dump_fn = stable_dump_fn
        self._saved_snapshot = self._snapshot_fn(self._context)

    @property
    def context(self) -> TContext:
        return self._context

    def reset(self, context: TContext) -> None:
        self._context = context
        self._saved_snapshot = self._snapshot_fn(self._context)

    def mark_saved(self) -> None:
        self._saved_snapshot = self._snapshot_fn(self._context)

    @property
    def dirty(self) -> bool:
        current = self._to_stable_text(self._snapshot_fn(self._context))
        saved = self._to_stable_text(self._saved_snapshot)
        return current != saved

    def discard(self) -> None:
        self._restore_fn(self._context, deepcopy(self._saved_snapshot))

    def _to_stable_text(self, snapshot: TSnapshot) -> str:
        payload = self._stable_dump_fn(snapshot) if self._stable_dump_fn is not None else snapshot
        return json.dumps(payload, sort_keys=True, ensure_ascii=False)
