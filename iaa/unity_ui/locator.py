"""Playwright 风格的 UI 元素定位器。

设计要点（借鉴 playwright/selenium 的元素唯一性语义）：

- 定位器是**惰性描述**，不持有快照；每次解析时基于最新 snapshot 匹配。
- 匹配条件可组合（name/path/text/active/interactable…），全部为"与"关系。
- ``first()``/``nth()``/``all()``/``count()`` 显式处理多匹配；
  ``one()`` 要求恰好一个匹配（消除脚本对偶然歧义的依赖）。
- 默认忽略 ``active=False`` 的节点（不可见元素不应被点击），
  ``include_inactive=True`` 可包含。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable

from .element import UIElement
from .tree import UINode, flat_nodes

if TYPE_CHECKING:
    from .client import UnityUITree


@dataclass
class Locator:
    """UI 元素定位器（对一棵 snapshot 森林求值）。

    所有过滤条件之间为与关系；空条件匹配全部（激活）节点。
    """

    ui: 'UnityUITree'
    """所属客户端（用于点击等操作回连）。"""

    name: str | None = None
    """GameObject 名称精确匹配。"""

    name_re: str | None = None
    """GameObject 名称正则。"""

    path: str | None = None
    """完整路径精确匹配（如 ``/Canvas/Home/ButtonLive``）。"""

    path_re: str | None = None
    """完整路径正则。"""

    text: str | None = None
    """TMP 文本内容精确匹配。"""

    text_re: str | None = None
    """TMP 文本内容正则。"""

    has_text: str | None = None
    """自身或任一子孙节点的文本包含该子串（playwright ``has-text`` 语义）。"""

    has_text_re: str | None = None
    """自身或任一子孙节点的文本匹配该正则。"""

    sprite: str | None = None
    """节点上 Image 的 sprite 名精确匹配（图标身份；仅 UI 定位域）。"""

    sprite_re: str | None = None
    """Image 的 sprite 名正则（仅 UI 定位域）。"""

    interactable: bool | None = None
    """Selectable.interactable 过滤（None 不过滤）。"""

    include_inactive: bool = False
    """是否包含激活链断开的节点。"""

    extra: Callable[[UINode], bool] | None = None
    """自定义谓词。"""

    _snapshot: list[UINode] | None = field(default=None, repr=False)
    """缓存的快照（None 表示解析时重新 dump）。"""

    # -- 求值 ---------------------------------------------------------------

    def use_snapshot(self, roots: list[UINode]) -> 'Locator':
        """用已有快照求解（避免重复 dump），返回自身。

        :param roots: :meth:`UnityUITree.snapshot` 的结果
        :return: self
        """
        self._snapshot = roots
        return self

    def _matches(self, node: UINode) -> bool:
        """节点是否满足全部条件。"""
        if not self.include_inactive and not node.active:
            return False
        if self.name is not None and node.name != self.name:
            return False
        if self.name_re is not None and not re.search(self.name_re, node.name):
            return False
        if self.path is not None and node.path != self.path:
            return False
        if self.path_re is not None and not re.search(self.path_re, node.path):
            return False
        if self.text is not None and (node.text or None) != self.text:
            return False
        if self.text_re is not None and (node.text is None or not re.search(self.text_re, node.text)):
            return False
        if self.has_text is not None and not _self_or_desc_text(node, lambda t: self.has_text in t):  # type: ignore[union-attr]
            return False
        if self.has_text_re is not None and not _self_or_desc_text(node, lambda t: re.search(self.has_text_re, t) is not None):  # type: ignore[arg-type]
            return False
        if self.sprite is not None and node.sprite != self.sprite:
            return False
        if self.sprite_re is not None and (node.sprite is None or not re.search(self.sprite_re, node.sprite)):
            return False
        if self.interactable is not None and node.interactable != self.interactable:
            return False
        if self.extra is not None and not self.extra(node):
            return False
        return True

    def resolve(self) -> list[UINode]:
        """求值并返回全部匹配节点。

        :return: 匹配的 UINode 列表（先序）
        """
        roots = self._snapshot if self._snapshot is not None else self.ui.snapshot()
        return [n for n in flat_nodes(roots) if self._matches(n)]

    # -- 结果语义（playwright 风格） ----------------------------------------

    def count(self) -> int:
        """匹配数量。"""
        return len(self.resolve())

    def all(self) -> list[UIElement]:
        """全部匹配，包装为元素列表。"""
        return [UIElement(self.ui, n) for n in self.resolve()]

    def first(self) -> UIElement:
        """第一个匹配。

        :raises LookupError: 无匹配时
        """
        nodes = self.resolve()
        if not nodes:
            raise LookupError(f'locator matched nothing: {self}')
        return UIElement(self.ui, nodes[0])

    def nth(self, index: int) -> UIElement:
        """第 index 个匹配（0 基）。

        :raises LookupError: 数量不足时
        """
        nodes = self.resolve()
        if index >= len(nodes):
            raise LookupError(f'locator matched {len(nodes)} nodes, need #{index}: {self}')
        return UIElement(self.ui, nodes[index])

    def one(self) -> UIElement:
        """恰好一个匹配。

        :raises LookupError: 0 个或多于 1 个匹配时
        """
        nodes = self.resolve()
        if len(nodes) != 1:
            raise LookupError(f'locator expected 1 match, got {len(nodes)}: {self}')
        return UIElement(self.ui, nodes[0])

    def exists(self) -> bool:
        """是否有匹配。"""
        return bool(self.resolve())


def _self_or_desc_text(node: UINode, pred: 'Callable[[str], bool]') -> bool:
    """自身或任一子孙节点的文本是否满足 ``pred``。

    :param node: 起始节点
    :param pred: 文本谓词
    :return: 任一文本满足时 True
    """
    if node.text is not None and pred(node.text):
        return True
    return any(_self_or_desc_text(c, pred) for c in node.children)
