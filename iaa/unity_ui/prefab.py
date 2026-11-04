"""把 Unity UI 树接入 kotonebot 的 Prefab 协议。

让 ``R.*`` 的调用面（``find/exists/wait/click/q/AnyOf``）无改动地跑在
UI 树上：实现 :class:`UIPrefab` 后，kotonebot 的全部查找/等待 machinery
（BoundPrefab、AnyOf、Loop 轮询）原样可用。

唯一性约定（借鉴 Playwright）：
- 优先用 ``ui_path``（从 ``/CanvasRoot`` 起锚定的完整路径或前缀路径）
- 其次 ``ui_path_re``（正则，用于带 ``(Clone)`` 后缀或动态层的节点）
- ``ui_name`` 仅在全局唯一时使用
- 动作语义（click）用 ``require``（0 或多匹配均抛错），查询可用 ``find``
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

from kotonebot.core import FindQuery, Prefab
from kotonebot.primitives import Rect

from .client import UnityUITree
from .tree import UINode, flat_nodes

logger = logging.getLogger(__name__)

#: 共享客户端单例（懒创建；同进程内游戏进程唯一）
_default_client: UnityUITree | None = None


def get_default_client() -> UnityUITree:
    """获取共享的 :class:`UnityUITree` 客户端（懒创建）。

    :return: 客户端单例
    """
    global _default_client
    if _default_client is None:
        _default_client = UnityUITree('com.sega.pjsekai')
    return _default_client


def set_default_client(client: UnityUITree) -> None:
    """替换共享客户端（测试/多设备用）。

    :param client: 客户端实例
    """
    global _default_client
    _default_client = client


@dataclass(frozen=True, slots=True)
class UIQuery(FindQuery[Any]):
    """UI 树查找条件。全部条件之间为与关系。"""

    path: str | None = None
    """完整路径精确匹配（如 ``/CanvasRoot/Layer_UI/.../Live``）。"""

    path_re: str | None = None
    """路径正则（``re.search`` 语义）。"""

    name: str | None = None
    """GameObject 名精确匹配。"""

    name_re: str | None = None
    """GameObject 名正则。"""

    text: str | None = None
    """TMP 文本精确匹配。"""

    text_re: str | None = None
    """TMP 文本正则。"""

    has_text: str | None = None
    """自身或任一子孙节点的文本包含该子串（playwright ``has-text`` 语义）。"""

    has_text_re: str | None = None
    """自身或任一子孙节点的文本匹配该正则。"""

    interactable: bool | None = None
    """Selectable.interactable 过滤。"""

    include_inactive: bool = False
    """是否包含激活链断开的节点（当前 agent 只 dump 激活节点，恒为 False）。"""


class UIGameObject:
    """UI 树查找结果（对齐 kotonebot GameObject 协议）。"""

    def __init__(self, node: UINode) -> None:
        """由 UINode 构造。

        :param node: 匹配到的 UI 树节点（须有 screen_rect）
        :raises ValueError: 节点无 RectTransform 时
        """
        if node.screen_rect is None:
            raise ValueError(f'node has no RectTransform: {node.path}')
        cx, cy, w, h = node.screen_rect
        self.rect = Rect(x=int(cx - w / 2), y=int(cy - h / 2), w=int(w), h=int(h))
        """屏幕矩形（kotonebot Rect，input tap 同坐标系）。"""
        self.ui_node = node
        """原始 UI 树节点。"""

    @property
    def name(self) -> str:
        """GameObject 名称。"""
        return self.ui_node.name

    @property
    def center(self) -> tuple[int, int]:
        """中心点（screen rect 中心）。"""
        return self.rect.center

    @property
    def path(self) -> str:
        """完整路径。"""
        return self.ui_node.path

    @property
    def text(self) -> str | None:
        """TMP 文本。"""
        return self.ui_node.text

    @property
    def interactable(self) -> bool | None:
        """Selectable.interactable。"""
        return self.ui_node.interactable

    def click(self) -> None:
        """点击中心（走模拟点击）。"""
        from kotonebot import device

        device.click(self.rect.center)

    def __repr__(self) -> str:
        """调试表示。"""
        return f'<UIGameObject {self.ui_node.path!r} rect={self.rect}>'


def _make_query(**kwargs: Any) -> 'UIQuery':
    """把 q() kwargs 组装为 UIQuery（容忍模板 API 的参数并忽略）。

    ``enabled`` 是 ``interactable`` 的模板 API 别名（Selectable.enabled 与
    interactable 在 UI 树语境下同义）。
    """
    if 'enabled' in kwargs and 'interactable' not in kwargs:
        kwargs['interactable'] = kwargs.pop('enabled')
    ignored = {k: v for k, v in kwargs.items()
               if k in ('threshold', 'colored', 'region') and v is not None}
    if ignored:
        logger.debug('UIPrefab ignores template-only query args: %s', ignored)
    fields = {k: v for k, v in kwargs.items() if k in UIQuery.__dataclass_fields__}
    return UIQuery(**fields)


def _snapshot_resilient() -> list[UINode] | None:
    """取一次快照；失败时重建一次会话再试，仍失败返回 None。

    游戏重启/加载期/白屏时 dump 不可用，返回 None 让调用方按"未找到"处理
    （与模板匹配行为对齐，任务轮询循环可自然重试）。

    :return: 快照森林；不可用返回 None
    """
    ui = get_default_client()
    try:
        return ui.snapshot()
    except Exception as e:  # noqa: BLE001 基础设施故障降级为"未找到"
        logger.warning('snapshot failed (%s), rebuilding once', e)
    try:
        ui._bootstrapped = False
        ui.ensure_ready()
        return ui.snapshot()
    except Exception as e:  # noqa: BLE001
        logger.warning('snapshot still failing after rebuild: %s', e)
        return None


def _suppressed(cls: type['UIPrefab'], roots: list[UINode]) -> bool:
    """跨节点否定判定：快照中存在 ``ui_not_exists_re`` 匹配的节点时为 True。"""
    if cls.ui_not_exists_re is None:
        return False
    return any(re.search(cls.ui_not_exists_re, n.path) for n in roots for n in n.iter_descendants())


class UIPrefab(Prefab[UIGameObject]):
    """Unity UI 树 Prefab 基类。

    子类/动态生成的类设置 ``ui_*`` 类属性描述定位条件；kotonebot 的
    ``find/exists/wait/try_wait/click/try_click/require/q/AnyOf`` 全部可用。
    """

    Query = UIQuery

    ui_path: str | None = None
    """完整路径精确匹配。"""

    ui_path_re: str | None = None
    """路径正则。"""

    ui_name: str | None = None
    """GameObject 名精确匹配。"""

    ui_text: str | None = None
    """TMP 文本精确匹配（节点自身）。"""

    ui_has_text: str | None = None
    """自身或任一子孙节点的文本包含该子串。"""

    ui_has_text_re: str | None = None
    """自身或任一子孙节点的文本匹配该正则。"""

    ui_interactable: bool | None = None
    """interactable 过滤。"""

    ui_not_exists_re: str | None = None
    """跨节点否定：快照中存在路径匹配该正则的节点时，本 prefab 一律视为
    未找到。用于"底层 screen 层仍 active 但被上层覆盖"的场景（如剧情播放时
    ScreenLayerStorySelect 仍在树中），对齐模板匹配"被覆盖即不可见"语义。"""

    display_name: str | None = None

    @classmethod
    def q(cls, query: UIQuery | None = None, **kwargs: Any):  # type: ignore[override]
        """开启一次查找；kwargs 为 UIQuery 字段（容忍 threshold 等模板参数）。

        :param query: 直接给 UIQuery 实例
        :param kwargs: UIQuery 字段（path/path_re/name/name_re/text/text_re/interactable）
        :return: BoundPrefab
        """
        if query is not None:
            return super().q(query)
        return super().q(_make_query(**kwargs))

    @classmethod
    def _matches(cls, node: UINode, query: UIQuery) -> bool:
        """节点是否满足类属性条件与 query 条件。"""
        if not (query.include_inactive or node.active):
            return False
        if cls.ui_path is not None and node.path != cls.ui_path:
            return False
        if cls.ui_path_re is not None:
            if not re.search(cls.ui_path_re, node.path):
                return False
        if cls.ui_name is not None and node.name != cls.ui_name:
            return False
        if cls.ui_text is not None and node.text != cls.ui_text:
            return False
        if cls.ui_has_text is not None and not _has_text(node, cls.ui_has_text):
            return False
        if cls.ui_has_text_re is not None and not _has_text_re(node, cls.ui_has_text_re):
            return False
        if cls.ui_interactable is not None and node.interactable != cls.ui_interactable:
            return False
        return _query_matches(node, query)

    @classmethod
    def _find_all_impl(cls, query: UIQuery) -> list[UIGameObject]:
        """在当前 UI 树快照中查找全部匹配。

        与模板匹配语义对齐：agent 不可用时（游戏重启中/白屏等）返回空列表
        而非抛异常，让上层轮询循环自然重试。
        """
        roots = _snapshot_resilient()
        if roots is None or _suppressed(cls, roots):
            return []
        results: list[UIGameObject] = []
        for node in flat_nodes(roots):
            if node.screen_rect is None:
                continue
            if cls._matches(node, query):
                results.append(UIGameObject(node))
        return results

    @classmethod
    def _find_impl(cls, query: UIQuery) -> UIGameObject | None:
        """查找第一个匹配（先序）；agent 不可用时返回 None（语义同模板匹配）。"""
        roots = _snapshot_resilient()
        if roots is None or _suppressed(cls, roots):
            logger.debug('%s.find -> None', cls.__name__)
            return None
        for node in flat_nodes(roots):
            if node.screen_rect is None:
                continue
            if cls._matches(node, query):
                obj = UIGameObject(node)
                logger.debug('%s.find -> %s', cls.__name__, node.path)
                return obj
        logger.debug('%s.find -> None', cls.__name__)
        return None

    @classmethod
    def _require_impl(cls, query: UIQuery) -> UIGameObject:
        """要求恰好一个匹配。

        :raises LookupError: 0 个或多于 1 个匹配时
        """
        results = cls._find_all_impl(query)
        if len(results) != 1:
            raise LookupError(
                f'{cls.__name__}: expected exactly 1 match, got {len(results)} '
                f'(path={cls.ui_path!r}, path_re={cls.ui_path_re!r}, name={cls.ui_name!r})'
            )
        return results[0]


def _query_matches(node: UINode, query: UIQuery) -> bool:
    """UIQuery 条件求值。"""
    if query.path is not None and node.path != query.path:
        return False
    if query.path_re is not None and not re.search(query.path_re, node.path):
        return False
    if query.name is not None and node.name != query.name:
        return False
    if query.name_re is not None and not re.search(query.name_re, node.name):
        return False
    if query.text is not None and node.text != query.text:
        return False
    if query.text_re is not None and (node.text is None or not re.search(query.text_re, node.text)):
        return False
    if query.has_text is not None and not _has_text(node, query.has_text):
        return False
    if query.has_text_re is not None and not _has_text_re(node, query.has_text_re):
        return False
    if query.interactable is not None and node.interactable != query.interactable:
        return False
    if query.predicate is not None and not query.predicate(node):
        return False
    return True


def _has_text(node: UINode, needle: str) -> bool:
    """自身或任一子孙节点的文本是否包含 ``needle``。

    :param node: 起始节点
    :param needle: 子串
    :return: 包含时 True
    """
    if node.text is not None and needle in node.text:
        return True
    return any(_has_text(c, needle) for c in node.children)


def _has_text_re(node: UINode, pattern: str) -> bool:
    """自身或任一子孙节点的文本是否匹配正则 ``pattern``。

    :param node: 起始节点
    :param pattern: 正则
    :return: 匹配时 True
    """
    if node.text is not None and re.search(pattern, node.text):
        return True
    return any(_has_text_re(c, pattern) for c in node.children)
