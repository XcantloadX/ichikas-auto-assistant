"""UI 树数据模型。

agent 的 ``dump`` 返回平铺节点列表（含 ``parent`` Transform 指针），
这里还原为 :class:`UINode` 森林，供定位器查询。节点带 RectTransform
信息时同时给出世界坐标与屏幕坐标（后者用于点击）。
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
    """agent 侧 Transform 对象地址（十进制字符串，调试/建树用）。"""

    gameobject_ptr: str = ''
    """agent 侧 GameObject 对象地址。"""

    path: str = ''
    """从根到本节点的路径，如 ``/CanvasRoot/Layer_UI/ButtonLive``。"""

    text: str | None = None
    """节点上 TMP_Text/Text 的文本（无文本组件为 None）。"""

    sprite: str | None = None
    """节点上 Image 的 sprite 名（图标身份；重名图标节点的唯一区分手段）。"""

    interactable: bool | None = None
    """Selectable.interactable（非 Selectable 为 None）。"""

    rect: tuple[float, float, float, float] | None = None
    """世界坐标 (cx, cy, w, h)（中心点+宽高，Canvas 世界单位）；未知为 None。"""

    screen_rect: tuple[float, float, float, float] | None = None
    """屏幕坐标 (cx, cy, w, h)（像素，中心点+宽高，与 ``input tap`` 同一坐标系）；
    无 RectTransform 或未提供视口时为 None。"""

    def iter_descendants(self):
        """先序遍历自身与全部后代。"""
        yield self
        for c in self.children:
            yield from c.iter_descendants()

    def is_leaf(self) -> bool:
        """是否叶子节点。"""
        return not self.children


def build_forest(dump: dict, viewport: tuple[int, int] | None = None) -> list[UINode]:
    """把 agent ``dump`` 的 JSON 还原为 :class:`UINode` 森林。

    dump 是平铺节点列表（``{"ok":true,"n":N,"nodes":[...]}``），节点间以
    ``parent`` Transform 指针关联；``parent`` 不在列表中的节点即根。

    :param dump: agent ``dump`` 命令的原始响应
    :param viewport: 屏幕逻辑分辨率 (w, h)；提供时为每个节点换算 ``screen_rect``
    :return: 根节点列表（每棵场景层级树一个根；UI 画布通常为 ``CanvasRoot``）
    """
    nodes = dump.get('nodes', [])
    by_t = {nd['t']: nd for nd in nodes}
    roots_raw = [nd for nd in nodes if nd['parent'] not in by_t]

    scale = _canvas_scale(roots_raw, viewport) if viewport else None
    converted: dict[str, UINode] = {}

    def convert(d: dict, parent: UINode | None, prefix: str) -> UINode:
        node = UINode(
            name=d.get('name', ''),
            active=bool(d.get('active', True)),
            parent=parent,
            transform_ptr=d.get('t', ''),
            gameobject_ptr=d.get('go', ''),
        )
        node.path = prefix + '/' + node.name
        converted[d['t']] = node
        # 像素级矩形（agent 端 GetWorldCorners+WorldToScreenPoint，仅 Camera
        # Canvas 产出）：真实屏幕像素，y 自底部起（Unity 屏幕坐标）。
        px = d.get('px')
        if px and viewport is not None:
            x, y, w, h = px
            vw, vh = viewport
            node.screen_rect = (x + w / 2, vh - (y + h / 2), w, h)
        rect = d.get('rect')
        if rect:
            node.rect = tuple(rect)  # type: ignore[assignment]
            if scale is not None and px is None:
                w, h = viewport  # type: ignore[misc]
                node.screen_rect = (
                    rect[0] * scale + w / 2,
                    h / 2 - rect[1] * scale,
                    rect[2] * scale,
                    rect[3] * scale,
                )
        node.text = d.get('text')
        node.sprite = d.get('spr')
        ia = d.get('ia')
        node.interactable = None if ia is None else bool(ia)
        for c in d.get('children', []):
            node.children.append(convert(c, node, node.path))
        return node

    # 平铺 → children 挂接（在原始 dict 上做，再走 convert 递归）
    for nd in nodes:
        p = by_t.get(nd['parent'])
        if p is not None:
            p.setdefault('children', []).append(nd)
    for nd in roots_raw:
        nd.setdefault('children', [])
    return [convert(r, None, '') for r in roots_raw]


def _canvas_scale(roots_raw: list[dict], viewport: tuple[int, int]) -> float:
    """从根画布的世界尺寸推算 world→pixel 比例。

    Screen Space - Overlay 画布的世界高度 = 屏幕像素高 / scaleFactor，
    故 ``scale = viewport_h / canvas_world_h``。

    :param roots_raw: 原始根节点 dict 列表
    :param viewport: (w, h)
    :return: 比例；找不到画布根时按 720p 基准退化
    """
    vh = viewport[1]
    for r in roots_raw:
        rect = r.get('rect')
        if rect and rect[3] >= 1.0:
            return vh / rect[3]
    return vh / 720.0


def flat_nodes(roots: list[UINode]) -> list[UINode]:
    """拍平森林为列表（先序）。"""
    out: list[UINode] = []
    for r in roots:
        out.extend(r.iter_descendants())
    return out
