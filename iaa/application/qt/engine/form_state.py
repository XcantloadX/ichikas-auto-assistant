from __future__ import annotations

import json
from typing import Any

from ..dsl import FormContext


class FormState:
    """表单状态快照管理。

    这里不再保存 dict DTO，而是直接基于原始配置模型（conf/shared）做快照与回滚。
    """

    def __init__(self, context: FormContext) -> None:
        self._context = context
        self._saved_conf = context.conf.model_copy(deep=True)
        self._saved_shared = context.shared.model_copy(deep=True)

    @property
    def context(self) -> FormContext:
        return self._context

    def reset(self, context: FormContext) -> None:
        self._context = context
        self._saved_conf = context.conf.model_copy(deep=True)
        self._saved_shared = context.shared.model_copy(deep=True)

    def mark_saved(self) -> None:
        self._saved_conf = self._context.conf.model_copy(deep=True)
        self._saved_shared = self._context.shared.model_copy(deep=True)

    @property
    def dirty(self) -> bool:
        current = self._stable_dump(self._context.conf, self._context.shared)
        saved = self._stable_dump(self._saved_conf, self._saved_shared)
        return current != saved

    def discard(self) -> None:
        self._context.conf = self._saved_conf.model_copy(deep=True)
        self._context.shared = self._saved_shared.model_copy(deep=True)

    def _stable_dump(self, conf: Any, shared: Any) -> str:
        payload = {
            'conf': conf.model_dump(mode='json'),
            'shared': shared.model_dump(mode='json'),
        }
        return json.dumps(payload, sort_keys=True, ensure_ascii=False)
