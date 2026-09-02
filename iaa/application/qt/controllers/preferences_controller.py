from __future__ import annotations

import json
import logging
from typing import Any

from PySide6.QtCore import Property, QObject, Signal, Slot

from iaa.config import manager as config_manager
from iaa.config.shared import SharedConfig

from .config_draft import ConfigDraft
from .settings_controller import _normalize_qt_value

logger = logging.getLogger(__name__)


class PreferencesController(QObject):
    """偏好控制器：草稿模式（kaa 风格表单）。

    偏好页 QML 直写 shared 表单字段：``config`` 暴露 base+dirty 合并视图，
    ``setField`` 写入草稿，``save`` 校验+写盘。
    """

    configChanged = Signal()
    dirtyChanged = Signal(bool)
    operationSucceeded = Signal(str)
    operationFailed = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._base: dict[str, Any] = config_manager.read_shared().model_dump(mode='json')
        self._draft = ConfigDraft(self._base)
        self._last_issues: list[dict[str, Any]] = []

    def _reload(self) -> None:
        """外部变更 shared 后重建草稿。"""
        self._base = config_manager.read_shared().model_dump(mode='json')
        self._draft = ConfigDraft(self._base)
        self._last_issues = []
        self.configChanged.emit()
        self.dirtyChanged.emit(False)

    # ── 表单读写 ─────────────────────────────────────────────────────────────

    @Property('QVariantMap', notify=configChanged)
    def config(self) -> dict[str, Any]:
        """草稿视图：base + dirty 合并。"""
        return self._draft.view()

    @Slot(str, 'QVariant')
    def setField(self, path: str, value) -> None:
        """字段进草稿。path 为完整 dot path（相对 shared 根）。"""
        self._draft.set(path, _normalize_qt_value(value))
        self.configChanged.emit()
        self.dirtyChanged.emit(self._draft.is_dirty())

    @Slot(str, 'QVariant')
    def setValue(self, path: str, value) -> None:
        """兼容旧接口：等价于 setField（供 AppController 等非 QML 侧调用）。"""
        self.setField(path, value)

    @Slot(result=bool)
    def isDirty(self) -> bool:
        return self._draft.is_dirty()

    @Slot(result=bool)
    def discard(self) -> bool:
        """丢弃未保存编辑。"""
        self._draft.discard()
        self.configChanged.emit()
        self.dirtyChanged.emit(False)
        return True

    @Slot(result=bool)
    def save(self) -> bool:
        """提交草稿：校验 + 写盘。"""
        if not self._draft.is_dirty():
            self.operationSucceeded.emit('没有需要保存的更改')
            return True
        merged = self._draft.view()
        try:
            candidate = SharedConfig.model_validate(merged)
        except Exception as exc:  # noqa: BLE001
            logger.warning('Preferences draft validation failed: %s', exc)
            self.operationFailed.emit(f'配置结构无效：{exc}')
            return False
        try:
            config_manager.write_shared(candidate)
        except Exception as exc:  # noqa: BLE001
            logger.exception('Failed to save preferences')
            self.operationFailed.emit(f'保存失败：{exc}')
            return False
        self._base = candidate.model_dump(mode='json')
        self._draft = ConfigDraft(self._base)
        self._last_issues = []
        self.configChanged.emit()
        self.dirtyChanged.emit(False)
        self.operationSucceeded.emit('保存成功')
        return True

    @Slot(result=str)
    def validateJson(self) -> str:
        """校验当前草稿，返回 issue 列表 JSON。不提交、不写盘。"""
        try:
            SharedConfig.model_validate(self._draft.view())
            return json.dumps([], ensure_ascii=False)
        except Exception as exc:  # noqa: BLE001
            logger.exception('Failed to validate preferences draft')
            return json.dumps(
                [{'severity': 'error', 'field': None, 'message': f'配置结构无效：{exc}'}],
                ensure_ascii=False,
            )

    # ── 快捷键读取（供全局热键模块使用）────────────────────────────────────────

    @Slot(result=str)
    def hotkeyStart(self) -> str:
        return self._draft.get('hotkeys.start') or ''

    @Slot(result=str)
    def hotkeyStop(self) -> str:
        return self._draft.get('hotkeys.stop') or ''
