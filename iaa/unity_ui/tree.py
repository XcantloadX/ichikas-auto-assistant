"""UI 树数据模型。

snapshot 由 agent 的 ``dump`` 产生（JSON），这里还原为 :class:`UINode` 森林，
供定位器查询。节点带 transform 信息时包含世界坐标（用于点击）。
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class UINode:
    """UI 树节点（对应一个 Unity GameObject/Transform）。

    跨字段约束：``children`` 中的节点其 ``parent`` 必为本节点（森林一致性）；
    ``active`` 为 activeInHierarchy（含父链）。
    """

    name: str
    """GameObject 名称。"""

    active: bool = True
    """activeInHierarchy（父链全激活才为真）。"""

    parent: 'UINode | None' = None
    """父节点；根节点为 None。"""

    children: list['UINode'] = field(default_factory=list)
    """子节点列表。"""

    transform_ptr: str = ''
    """agent 侧 Transform 对象地址（调试/去重用）。"""

    gameobject_ptr: str = ''
    """agent 侧 GameObject 对象地址。"""

    path: str = ''
    """从根到本节点的路径，如 ``/Canvas/HomeRoot/ButtonLive``。"""

    text: str | None = None
    """节点上 TMP_Text/Text 的文本（无文本组件为 None）。"""

    interactable: bool | None = None
    """Selectable.interactable（非 Selectable 为 None）。"""

    rect: tuple[float, float, float, float] | None = None
    """世界坐标 (left, top, width, height)，逻辑分辨率；未知为 None。"""

    def iter_descendants(self):
        """先序遍历自身与全部后代。"""
        yield self
        for c in self.children:
            yield from c.iter_descendants()

    def is_leaf(self) -> bool:
        """是否叶子节点。"""
        return not self.children


def build_forest(dump: dict) -> list[UINode]:
    """把 agent dump 的 JSON 还原为 UINode 森林。

    :param dump: agent ``dump`` 返回的 ``tree`` 字段
    :return: 根节点列表
    """
    def convert(d: dict, parent: UINode | None, prefix: str) -> UINode:
        node = UINode(
            name=d.get('name', ''),
            active=bool(d.get('active', True)),
            parent=parent,
            transform_ptr=d.get('t', ''),
            gameobject_ptr=d.get('go', ''),
        )
        node.path = prefix + '/' + node.name
        for c in d.get('children', []):
            node.children.append(convert(c, node, node.path))
        return node

    return [convert(r, None, '') for r in dump.get('roots', [])]


def flat_nodes(roots: list[UINode]) -> list[UINode]:
    """拍平森林为列表（先序）。"""
    out: list[UINode] = []
    for r in roots:
        out.extend(r.iter_descendants())
    return out
