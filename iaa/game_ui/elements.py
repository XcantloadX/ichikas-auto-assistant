import logging
from dataclasses import dataclass
from typing import Literal
from typing_extensions import override

import numpy as np
from cv2.typing import MatLike
from kotonebot.primitives import Rect
from kotonebot.core import GameObject, TemplateMatchPrefab, TemplateMatchQuery, BoundPrefab, Prefab, FindQuery
from kotonebot.devtools.project.schema import ChoiceProp, EditorMetadata, RectProp

from .scrollable import Scrollable
from .list_view import ListView

logger = logging.getLogger(__name__)

def hist_peak(image: MatLike, bin_count: int) -> int:
    """
    输入:
        image: numpy 数组，灰度图或彩色图都可以
        bin_count: 直方图箱数

    返回:
        peak_bin_index: 最高峰所在箱的索引
    """
    # 展平为一维
    values = np.asarray(image).ravel()

    # 计算直方图
    hist, bin_edges = np.histogram(values, bins=bin_count, range=(0, 256))

    # 找最高峰
    peak_bin_index = np.argmax(hist)

    return int(peak_bin_index)

class PjskButtonGameObject(GameObject):
    def __init__(self) -> None:
        super().__init__()
        self.enabled: bool | None = None

@dataclass(frozen=True, slots=True)
class PjskButtonQuery(TemplateMatchQuery[PjskButtonGameObject]):
    enabled: bool | None = None

class PjskButtonPrefab(TemplateMatchPrefab[PjskButtonGameObject]):
    Query = PjskButtonQuery

    button_type: Literal['primary', 'normal'] = 'primary'

    class _Editor(TemplateMatchPrefab._Editor):
        name = 'PJSK 按钮'
        shortcut = 'b'
        icon = 'widget-button'
        props = TemplateMatchPrefab._Editor.props | {
            'button_type': ChoiceProp(label='按钮类型', description='选择按钮的样式', default_value='primary', choices=[('蓝色按钮', 'primary'), ('灰色按钮', 'normal')])
        }

    @override
    @classmethod
    def _find_impl(cls, query: PjskButtonQuery) -> PjskButtonGameObject | None:
        res = super()._find_impl(query)
        if not res:
            return None
    
        # 判断按钮是否启用
        from kotonebot.backend.context import vars
        img = vars.screenshot_data
        assert img is not None
        x1, y1, x2, y2 = res.rect.xyxy
        button_slice = img[y1:y2, x1:x2]
        # 求蓝色最高峰
        peak = hist_peak(button_slice[:, :, 0], bin_count=5)
        if cls.button_type == 'normal':
            if peak == 4:
                res.enabled = True
            elif peak == 2:
                res.enabled = False
            else:
                logger.warning(f"Unexpected histogram peak {peak} for normal button at {res.rect}")
                res.enabled = None
        elif cls.button_type == 'primary':
            if peak == 4:
                res.enabled = True
            elif peak == 2:
                res.enabled = False
            else:
                logger.warning(f"Unexpected histogram peak {peak} for primary button at {res.rect}")
                res.enabled = None
        else:
            raise ValueError(f"Unknown button type {cls.button_type}")
        
        if query.enabled is not None and res.enabled is not None and query.enabled != res.enabled:
            return None
        else:
            return res

    @classmethod
    def q(cls, query: PjskButtonQuery | None = None, *, enabled: bool | None = None, threshold: float | None = None) -> BoundPrefab[PjskButtonGameObject, PjskButtonQuery]:
        actual_query: PjskButtonQuery
        if query is not None:
            actual_query = query
        else:
            actual_query = PjskButtonQuery(
                threshold=threshold,
                enabled=enabled
            )

        return BoundPrefab(cls, actual_query)

class PjskScrollBarGameObject(GameObject, Scrollable):
    pass

class PjskScrollBarPrefab(Prefab[PjskScrollBarGameObject]):
    rect: Rect

    class _Editor(EditorMetadata):
        name = 'PJSK 滚动条'
        shortcut = 's'
        primary_prop = 'rect'
        icon = 'double-caret-vertical'
        props = {
            'rect': RectProp(label='滚动条位置', description='在编辑器中框选滚动条所在的位置')
        }

    @override
    @classmethod
    def _find_impl(cls, query: FindQuery) -> PjskScrollBarGameObject | None:
        # 滚动条位置都是固定的，不需要 find 也不能 find
        return PjskScrollBarGameObject(scrollbar_rect=cls.rect)

class PjskListViewGameObject(GameObject, ListView):
    pass

class PjskListViewPrefab(Prefab[PjskListViewGameObject]):
    list_rect: Rect
    scrollbar_rect: Rect | None = None

    class _Editor(EditorMetadata):
        name = 'PJSK 列表视图'
        shortcut = 'l'
        primary_prop = 'list_rect'
        icon = 'list'
        props = {
            'list_rect': RectProp(label='容器范围', description='列表范围，包括右侧滚动条在内'),
            'scrollbar_rect': RectProp(label='滚动条范围', description='滚动条范围。若不设置，列表范围最右侧一小段视为滚动条。', default_value=None)
        }

    @override
    @classmethod
    def _find_impl(cls, query: FindQuery) -> PjskListViewGameObject | None:
        # 列表视图位置都是固定的，不需要 find 也不能 find
        if cls.scrollbar_rect is None:
            # 如果没有设置滚动条范围，默认把列表范围最右侧 7px 视为滚动条
            scrollbar_width = 7
            scrollbar_rect = Rect(
                x=cls.list_rect.x1 + cls.list_rect.w - scrollbar_width,
                y=cls.list_rect.y1,
                w=scrollbar_width,
                h=cls.list_rect.h
            )
        else:
            scrollbar_rect = cls.scrollbar_rect
        return PjskListViewGameObject(
            list_rect=cls.list_rect,
            scrollbar_rect=scrollbar_rect
        )

if __name__ == '__main__':
    from iaa.tasks import R
    R.Shop.AmountDialog.ButtonMinus.q(enabled=True)