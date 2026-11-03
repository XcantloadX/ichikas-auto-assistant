"""UI 元素：定位结果的可操作封装。

点击不走 hook——仍然用宿主已有的模拟点击（kotonebot ``device.click``），
元素只负责把 UI 树中的节点换算成屏幕坐标。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from .tree import UINode

if TYPE_CHECKING:
    from .client import UnityUITree


class UIElement:
    """快照中的一个 UI 节点。"""

    def __init__(self, ui: 'UnityUITree', node: UINode) -> None:
        """绑定客户端与节点。

        :param ui: 客户端
        :param node: 匹配到的节点
        """
        self.ui = ui
        self.node = node

    @property
    def name(self) -> str:
        """GameObject 名称。"""
        return self.node.name

    @property
    def path(self) -> str:
        """完整路径。"""
        return self.node.path

    @property
    def text(self) -> str | None:
        """TMP 文本。"""
        return self.node.text

    @property
    def interactable(self) -> bool | None:
        """是否可交互（非 Selectable 为 None）。"""
        return self.node.interactable

    def is_active(self) -> bool:
        """是否处于激活链。"""
        return self.node.active

    def center(self) -> tuple[float, float] | None:
        """估算元素中心（逻辑分辨率坐标，如 1280x720）。

        agent dump 提供 {cx, cy, w, h}（世界坐标，Screen Space - Overlay 画布
        且画布分辨率等于逻辑分辨率时即为屏幕坐标）。

        :return: (cx, cy)；信息不足返回 None
        """
        rect = self.node.rect
        if not rect:
            return None
        return rect['cx'], rect['cy']

    def click(self) -> None:
        """点击元素中心（走模拟点击，不走 hook）。

        :raises RuntimeError: 无法换算坐标时
        """
        c = self.center()
        if c is None:
            raise RuntimeError(f'no rect for element: {self.node.path}')
        from kotonebot import device  # 局部导入避免循环依赖

        device.click(c[0], c[1])

    def __repr__(self) -> str:
        """调试表示。"""
        return f'<UIElement {self.node.path!r} active={self.node.active}>'
