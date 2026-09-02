"""配置草稿模型：base（显示快照）+ dirty（编辑覆盖层）。

供设置页 / 偏好页在 QML 直写表单场景下使用：
- ``set()`` 只进 dirty，不碰 live 配置与磁盘。
- ``view()`` 返回 base + dirty 合并后的 dict 视图，供 FormBinder.data 显示。
- ``commit()`` 由 controller 在保存时合并、归一化并整体校验后替换 live。
"""

from __future__ import annotations

import copy
from typing import Any


def _set_dict_path(data: dict[str, Any], path: str, value: Any) -> None:
    """按 dot path 写入嵌套 dict（自动创建中间 dict）。"""
    parts = path.split('.')
    obj = data
    for part in parts[:-1]:
        obj = obj.setdefault(part, {})
    obj[parts[-1]] = value


def _get_dict_path(data: dict[str, Any], path: str) -> Any:
    """按 dot path 读取嵌套 dict 值，缺失返回 None。"""
    obj: Any = data
    for part in path.split('.'):
        if isinstance(obj, dict):
            obj = obj.get(part)
        else:
            return None
    return obj


class ConfigDraft:
    """dict 视图 + dirty overlay 的配置草稿。

    用于 kaa 风格表单（QML 直写表单字段，controller 暴露 config 只读视图 +
    setField 写入草稿）。保存时才合并并做类型归一化与整体校验。
    """

    def __init__(self, base: dict[str, Any]) -> None:
        self._base: dict[str, Any] = base
        self._dirty: dict[str, Any] = {}

    def view(self) -> dict[str, Any]:
        """base + dirty 合并后的视图，供表单绑定展示。"""
        merged = copy.deepcopy(self._base)
        for path, value in self._dirty.items():
            _set_dict_path(merged, path, value)
        return merged

    def get(self, path: str) -> Any:
        """读取字段值：dirty 优先，fallback 到 base。"""
        if path in self._dirty:
            return self._dirty[path]
        return _get_dict_path(self._base, path)

    def set(self, path: str, value: Any) -> None:
        """编辑字段：只进 dirty。

        写入时清除与新路径冲突的祖先/后代 dirty 项，避免
        整体对象替换（如切换 lifecycle 类型）与子字段编辑互相覆盖。
        """
        for key in list(self._dirty):
            if path != key and (path.startswith(key + '.') or key.startswith(path + '.')):
                del self._dirty[key]
        self._dirty[path] = value

    def is_dirty(self) -> bool:
        """是否存在未保存编辑。"""
        return bool(self._dirty)

    def discard(self) -> None:
        """丢弃所有未保存编辑。"""
        self._dirty.clear()
