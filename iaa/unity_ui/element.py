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
        """元素中心的屏幕坐标（像素，与 ``input tap`` 同一坐标系）。

        由 agent dump 的 RectTransform 世界坐标经画布比例换算得到
        （见 :func:`iaa.unity_ui.tree.build_forest`）。

        :return: (cx, cy)；节点无 RectTransform 时返回 None
        """
        rect = self.node.screen_rect
        if not rect:
            return None
        return rect[0], rect[1]

    def click(self) -> None:
        """点击元素中心（走模拟点击，不走 hook）。

        :raises RuntimeError: 节点无 RectTransform 无法换算坐标时
        """
        c = self.center()
        if c is None:
            raise RuntimeError(f'no rect for element: {self.node.path}')
        from kotonebot import device  # 局部导入避免循环依赖

        device.click(int(c[0]), int(c[1]))

    def __repr__(self) -> str:
        """调试表示。"""
        return f'<UIElement {self.node.path!r} active={self.node.active}>'
