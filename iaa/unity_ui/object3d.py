"""3D 场景对象定位（独立协议域，与 UI 定位 API 严格分离）。

数据来源不同：UI 定位走 snapshot 快照森林（RectTransform 域），3D 定位走
``find3d`` 协议命令（Renderer.bounds 经相机投影成屏幕像素）。二者不共用
查找代码、不共用元素类型——3D 对象用 :class:`Object3D`，UI 元素用
:class:`iaa.unity_ui.element.UIElement`。

用法::

    obj = ui.locator3d(name='Building_XXX').one()
    obj.center   # 屏幕坐标
    obj.click()  # 模拟点击
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from .client import UnityUITree


@dataclass(frozen=True)
class Object3D:
    """3D 场景对象（已投影到屏幕像素）。"""

    name: str
    """GameObject 名。"""

    px: tuple[float, float, float, float]
    """屏幕矩形 (x, y, w, h)，y 自底部起（agent 投影输出原值）。"""

    go: str
    """GameObject 对象指针（十进制字符串，调试用）。"""

    ui: 'UnityUITree' = field(repr=False, compare=False)
    """所属客户端（用于点击回连）。"""

    text: str | None = None
    """GO 上的 TMP 文本（世界空间标签，如地图区域名）；未读时为 None。"""

    path: str | None = None
    """父链路径（至多 5 层，含自身，如 ``Area1/AreaIcon/Enable``）；
    用于区分同名实例。未请求时为 None。"""

    @property
    def center(self) -> tuple[int, int]:
        """屏幕中心（input tap 坐标系，y 已翻转为自顶部起）。"""
        x, y, w, h = self.px
        return (int(x + w / 2), int(self.ui.viewport[1] - (y + h / 2)))

    def click(self) -> None:
        """点击对象中心（走模拟点击，不走 hook）。"""
        from kotonebot import device

        device.click(*self.center)

    def __repr__(self) -> str:
        """调试表示。"""
        return f'<Object3D {self.name!r} px={self.px}>'


@dataclass
class Locator3D:
    """3D 对象定位器（每次 resolve 实时发起 ``find3d`` 命令）。

    与 :class:`iaa.unity_ui.locator.Locator` 完全独立：不接受 snapshot、
    不读 UI 快照森林；仅 name/name_re/text/text_re 四个条件。
    """

    ui: 'UnityUITree'
    """所属客户端。"""

    name: str | None = None
    """GameObject 名子串过滤（传给 find3d，agent 侧执行）。"""

    name_re: str | None = None
    """名正则（host 侧执行：拉全量名再过滤，较慢）。"""

    text: str | None = None
    """GO 上 TMP 文本精确匹配（隐含 readtext=True，多一轮枚举，较慢）。"""

    text_re: str | None = None
    """GO 上 TMP 文本正则（隐含 readtext=True，多一轮枚举，较慢）。"""

    path_re: str | None = None
    """父链路径正则（如 ``Area1/AreaIcon$``），区分同名实例。"""

    extra: Callable[[Object3D], bool] | None = None
    """自定义谓词。"""

    def _wants_text(self) -> bool:
        """是否需要读取对象文本。"""
        return self.text is not None or self.text_re is not None

    def _accept(self, obj: Object3D) -> bool:
        """对象是否满足文本/路径条件与自定义谓词。"""
        if self.text is not None and obj.text != self.text:
            return False
        if self.text_re is not None and (obj.text is None or not re.search(self.text_re, obj.text)):
            return False
        if self.path_re is not None and (obj.path is None or not re.search(self.path_re, obj.path)):
            return False
        return self.extra is None or self.extra(obj)

    # -- 求值 ---------------------------------------------------------------

    def resolve(self) -> list[Object3D]:
        """求值并返回全部匹配对象。

        :return: 匹配的 :class:`Object3D` 列表
        """
        out: list[Object3D] = []
        if self.name_re is not None:
            # 正则：拉全量名（无投影，cheap），host 过滤后逐名精确查询
            all_items = self.ui.find3d('', max_results=500, readtext=self._wants_text())
            names = sorted({it['name'] for it in all_items})
            for nm in names:
                if re.search(self.name_re, nm):
                    for it in self.ui.find3d(nm, max_results=50, readtext=self._wants_text()):
                        obj = Object3D(name=it['name'], px=tuple(it['px']),
                                       go=it['go'], ui=self.ui,
                                       text=it.get('text'), path=it.get('p'))
                        if self._accept(obj):
                            out.append(obj)
        else:
            for it in self.ui.find3d(self.name or '', max_results=100,
                                     readtext=self._wants_text()):
                obj = Object3D(name=it['name'], px=tuple(it['px']),
                               go=it['go'], ui=self.ui,
                               text=it.get('text'), path=it.get('p'))
                if self._accept(obj):
                    out.append(obj)
        return out

    # -- 结果语义（与 UI Locator 同风格） -----------------------------------

    def count(self) -> int:
        """匹配数量。"""
        return len(self.resolve())

    def all(self) -> list[Object3D]:
        """全部匹配。"""
        return self.resolve()

    def first(self) -> Object3D:
        """第一个匹配。

        :raises LookupError: 无匹配时
        """
        objs = self.resolve()
        if not objs:
            raise LookupError(f'Locator3D matched nothing: name={self.name!r} name_re={self.name_re!r}')
        return objs[0]

    def one(self) -> Object3D:
        """恰好一个匹配。

        :raises LookupError: 0 个或多于 1 个匹配时
        """
        objs = self.resolve()
        if len(objs) != 1:
            raise LookupError(f'Locator3D expected 1 match, got {len(objs)}: name={self.name!r} name_re={self.name_re!r}')
        return objs[0]

    def exists(self) -> bool:
        """是否有匹配。"""
        return bool(self.resolve())
