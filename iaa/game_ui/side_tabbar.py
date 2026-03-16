from dataclasses import dataclass

import cv2
import numpy as np
from cv2.typing import MatLike
from kotonebot import device, sleep
from kotonebot.primitives import Rect

DEBUG = False


def _union_rect(rects: list[Rect]) -> Rect:
    x1 = min(rect.x1 for rect in rects)
    y1 = min(rect.y1 for rect in rects)
    x2 = max(rect.x2 for rect in rects)
    y2 = max(rect.y2 for rect in rects)
    return Rect(x1, y1, max(1, x2 - x1), max(1, y2 - y1))


def _debug_show(name: str, image: MatLike) -> None:
    if not DEBUG:
        return
    display = image
    if len(display.shape) == 2:
        display = cv2.cvtColor(display, cv2.COLOR_GRAY2BGR)
    cv2.imshow(name, display)
    cv2.waitKey(1)


@dataclass(slots=True)
class SideTabbarParseConfig:
    """
    侧边栏颜色解析参数。

    用于控制激活项和 badge 的颜色分割范围。
    """

    active_hsv_lower: tuple[int, int, int] = (74, 45, 125)
    active_hsv_upper: tuple[int, int, int] = (105, 255, 255)
    badge_red1_lower: tuple[int, int, int] = (0, 110, 160)
    badge_red1_upper: tuple[int, int, int] = (15, 255, 255)
    badge_red2_lower: tuple[int, int, int] = (170, 110, 160)
    badge_red2_upper: tuple[int, int, int] = (179, 255, 255)


@dataclass(slots=True)
class SideTabInfo:
    """
    单个侧边栏 tab 的解析结果。
    """

    index: int
    rect: Rect
    center_y: int
    is_active: bool = False
    has_badge: bool = False
    badge_rect: Rect | None = None

    @property
    def center(self) -> tuple[int, int]:
        """
        返回 tab 点击中心点。

        :return: ``(x, y)`` 形式的中心点坐标。
        """
        return self.rect.center


@dataclass(slots=True)
class SideTabbarState:
    """
    一次侧边栏解析结果。
    """

    container_rect: Rect
    tabs: list[SideTabInfo]
    active_index: int | None

    @property
    def active_tab(self) -> SideTabInfo | None:
        """
        返回当前激活的 tab。

        :return: 激活 tab；若未识别到则返回 ``None``。
        """
        if self.active_index is None:
            return None
        if 0 <= self.active_index < len(self.tabs):
            return self.tabs[self.active_index]
        return None

    @property
    def badge_indices(self) -> list[int]:
        """
        返回带有 badge 的 tab 索引列表。

        :return: badge 索引列表。
        """
        return [tab.index for tab in self.tabs if tab.has_badge]

    def __getitem__(self, target: int) -> SideTabInfo:
        """
        按索引获取 tab。

        :param target: 目标索引。
        :return: 命中的 tab。
        :raises IndexError: 索引越界时抛出。
        """
        if 0 <= target < len(self.tabs):
            return self.tabs[target]
        raise IndexError(target)


class SideTabbar:
    """
    带侧边栏 tab 的页面控制器。

    默认假定当前已经位于包含侧边栏的页面，只负责识别可见 tab、
    判断激活态与 badge，并执行 tab 切换。
    """

    DEFAULT_SETTLE_TIME = 0.55
    DEFAULT_SWITCH_RETRIES = 3
    DEFAULT_SWITCH_POLL_INTERVAL = 0.2
    DEFAULT_SWITCH_POLL_STEPS = 6

    ACTIVE_MASK_KERNEL = (5, 5)
    MIN_ACTIVE_AREA = 2_000
    MIN_ACTIVE_WIDTH = 100
    MIN_ACTIVE_HEIGHT = 44
    MAX_ACTIVE_HEIGHT = 120
    ACTIVE_SCORE_WIDTH = 170
    ACTIVE_SCORE_MIN_RATIO = 0.18

    SAME_TAB_MERGE_GAP = 26
    MIN_TAB_HEIGHT = 54
    MAX_TAB_HEIGHT = 120
    TAB_VERTICAL_PADDING = 8

    VISUAL_INSET_LEFT = 12
    VISUAL_INSET_RIGHT = 36
    VISUAL_CANNY_LOWER = 80
    VISUAL_CANNY_UPPER = 180
    MIN_VISUAL_AREA = 80
    MIN_VISUAL_WIDTH = 55
    MIN_VISUAL_HEIGHT = 16
    MAX_VISUAL_WIDTH = 140
    MAX_VISUAL_HEIGHT = 120
    VISUAL_MERGE_GAP = 40
    TOP_FRAGMENT_MAX_HEIGHT = 28
    TOP_FRAGMENT_MAX_GAP = 18

    BADGE_KERNEL = (3, 3)
    BADGE_SEARCH_SIZE = 48
    MIN_BADGE_AREA = 80

    def __init__(
        self,
        tabbar_rect: Rect | None = None,
        *,
        parse_config: SideTabbarParseConfig | None = None,
        settle_time: float = DEFAULT_SETTLE_TIME,
    ) -> None:
        """
        初始化侧边栏控制器。

        :param tabbar_rect: 侧边栏的大致区域；不传则按屏幕比例估算。
        :param parse_config: 解析参数。
        :param settle_time: 切换 tab 后首次等待时间。
        """
        self.tabbar_rect = tabbar_rect
        self.parse_config = parse_config or SideTabbarParseConfig()
        self.settle_time = settle_time
        self.state: SideTabbarState | None = None
        self.last_screenshot: MatLike | None = None

    def _parse(self, image: MatLike | None = None) -> SideTabbarState:
        """
        解析当前侧边栏状态。

        :param image: 可选截图；不传时自动截图。
        :return: 最新的侧边栏解析结果。
        """
        screenshot = device.screenshot() if image is None else image
        self.last_screenshot = screenshot
        hsv = cv2.cvtColor(screenshot, cv2.COLOR_BGR2HSV)

        if self.tabbar_rect is not None:
            container_rect = self.tabbar_rect
        else:
            height, width = screenshot.shape[:2]
            container_rect = Rect(
                0,
                int(round(height * 0.10)),
                int(round(width * 0.145)),
                int(round(height * 0.78)),
            )
        active_mask = cv2.inRange(
            hsv,
            np.array(self.parse_config.active_hsv_lower, dtype=np.uint8),
            np.array(self.parse_config.active_hsv_upper, dtype=np.uint8),
        )
        active_rect = self._find_active_rect(active_mask, container_rect)
        visual_rects = self._find_visual_rects(screenshot, container_rect)
        tabs = self._build_tabs(container_rect, visual_rects)

        active_index = self._find_active_index(tabs, active_mask, active_rect)
        if active_index is not None:
            tabs[active_index].is_active = True

        for tab in tabs:
            badge_rect = self._find_badge_rect(screenshot, tab.rect)
            tab.badge_rect = badge_rect
            tab.has_badge = badge_rect is not None

        self.state = SideTabbarState(
            container_rect=container_rect,
            tabs=tabs,
            active_index=active_index,
        )
        if DEBUG:
            debug_image = screenshot.copy()
            cv2.rectangle(
                debug_image,
                (container_rect.x1, container_rect.y1),
                (container_rect.x2, container_rect.y2),
                (255, 255, 0),
                2,
            )
            for tab in tabs:
                color = (0, 255, 0) if tab.is_active else (255, 120, 0)
                cv2.rectangle(debug_image, (tab.rect.x1, tab.rect.y1), (tab.rect.x2, tab.rect.y2), color, 2)
                cv2.putText(
                    debug_image,
                    f'{tab.index}{"*" if tab.is_active else ""}',
                    (tab.rect.x1 + 6, tab.rect.y1 + 22),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65,
                    color,
                    2,
                    cv2.LINE_AA,
                )
                if tab.badge_rect is not None:
                    cv2.rectangle(
                        debug_image,
                        (tab.badge_rect.x1, tab.badge_rect.y1),
                        (tab.badge_rect.x2, tab.badge_rect.y2),
                        (0, 0, 255),
                        2,
                    )
            _debug_show('SideTabbar/final', debug_image)
        return self.state

    def update(self) -> SideTabbarState:
        """
        刷新当前侧边栏状态。

        :return: 最新解析结果。
        """
        return self._parse()

    def switch_to(
        self,
        target: int | SideTabInfo,
        *,
        retries: int = DEFAULT_SWITCH_RETRIES,
        settle_time: float | None = None,
    ) -> SideTabbarState:
        """
        切换到目标 tab。

        :param target: 目标索引或 tab 对象。
        :param retries: 最多重试次数。
        :param settle_time: 首次点击后的等待时间。
        :return: 切换完成后的侧边栏状态。
        :raises ValueError: 目标 tab 不存在时抛出。
        :raises RuntimeError: 多次尝试后仍未切换成功时抛出。
        """
        state = self.state or self.update()
        tab = self._resolve_target(state, target)
        if tab is None:
            raise ValueError(f'Tab not found: {target!r}')
        if tab.is_active:
            return state

        wait_time = self.settle_time if settle_time is None else settle_time
        for _ in range(max(1, retries)):
            device.click(tab.rect.center)
            state = self._wait_for_switch(target, initial_wait=wait_time)
            updated = self._resolve_target(state, target)
            if updated is not None and updated.is_active:
                return state
        raise RuntimeError(f'Failed to switch tab: {target!r}')

    def click(self, target: int | SideTabInfo) -> None:
        """
        点击目标 tab，但不等待切换完成。

        :param target: 目标索引或 tab 对象。
        :raises ValueError: 目标 tab 不存在时抛出。
        """
        state = self.state or self.update()
        tab = self._resolve_target(state, target)
        if tab is None:
            raise ValueError(f'Tab not found: {target!r}')
        device.click(tab.rect)

    def _resolve_target(
        self,
        state: SideTabbarState,
        target: int | SideTabInfo,
    ) -> SideTabInfo | None:
        """
        将目标参数解析为当前状态中的 tab 对象。

        :param state: 当前侧边栏状态。
        :param target: 目标索引或 tab 对象。
        :return: 命中的 tab；未命中时返回 ``None``。
        """
        try:
            if isinstance(target, SideTabInfo):
                return state[target.index]
            return state[target]
        except IndexError:
            return None

    def _wait_for_switch(
        self,
        target: int | SideTabInfo,
        *,
        initial_wait: float,
    ) -> SideTabbarState:
        """
        点击切换后等待状态稳定。

        :param target: 目标 tab。
        :param initial_wait: 首次轮询前等待时间。
        :return: 在轮询窗口内命中目标且 tab 数最多的状态；若未命中则返回最后一次状态。
        """
        best_state: SideTabbarState | None = None
        best_count = -1
        for _ in range(self.DEFAULT_SWITCH_POLL_STEPS):
            sleep(initial_wait if best_state is None else self.DEFAULT_SWITCH_POLL_INTERVAL)
            state = self.update()
            updated = self._resolve_target(state, target)
            if updated is not None and updated.is_active:
                if len(state.tabs) >= best_count:
                    best_state = state
                    best_count = len(state.tabs)
        return best_state or state

    def _build_tabs(
        self,
        container_rect: Rect,
        candidate_rects: list[Rect],
    ) -> list[SideTabInfo]:
        """
        根据候选矩形构造最终 tab 列表。

        :param container_rect: 侧边栏整体区域。
        :param candidate_rects: 视觉候选矩形列表。
        :return: 构造得到的 tab 列表。
        """
        candidates = [*candidate_rects]
        if not candidates:
            return []

        candidates.sort(key=lambda rect: rect.center_y)
        merged: list[Rect] = []
        for rect in candidates:
            if not merged:
                merged.append(rect)
                continue
            last = merged[-1]
            if abs(rect.center_y - last.center_y) <= self.SAME_TAB_MERGE_GAP:
                merged[-1] = _union_rect([last, rect])
            else:
                merged.append(rect)

        merged = self._keep_dense_cluster(merged)
        if not merged:
            return []

        centers = [rect.center_y for rect in merged]
        if len(centers) >= 2:
            gaps = [b - a for a, b in zip(centers, centers[1:])]
            default_height = int(round(np.median(gaps)))
        else:
            default_height = self.MIN_TAB_HEIGHT
        default_height = int(max(self.MIN_TAB_HEIGHT, min(default_height, self.MAX_TAB_HEIGHT)))

        tabs: list[SideTabInfo] = []
        for index, rect in enumerate(merged):
            center_y = rect.center_y
            if index == 0:
                top = center_y - default_height // 2
            else:
                top = (centers[index - 1] + center_y) // 2
            if index == len(merged) - 1:
                bottom = center_y + default_height // 2
            else:
                bottom = (center_y + centers[index + 1]) // 2

            top = min(top, rect.y1 - self.TAB_VERTICAL_PADDING)
            bottom = max(bottom, rect.y2 + self.TAB_VERTICAL_PADDING)
            top = max(container_rect.y1, top)
            bottom = min(container_rect.y2, bottom)
            height = max(self.MIN_TAB_HEIGHT, bottom - top)
            bottom = min(container_rect.y2, top + height)
            tab_rect = Rect(container_rect.x1, top, container_rect.w, max(1, bottom - top))

            tabs.append(
                SideTabInfo(
                    index=index,
                    rect=tab_rect,
                    center_y=center_y,
                )
            )
        return tabs

    def _keep_dense_cluster(self, rects: list[Rect]) -> list[Rect]:
        """
        从候选中保留最像 tab 列的一段稠密簇。

        :param rects: 已排序候选矩形。
        :return: 保留下来的候选簇。
        """
        if len(rects) <= 1:
            return rects

        max_gap = int(self.MAX_TAB_HEIGHT * 1.45)
        clusters: list[list[Rect]] = [[rects[0]]]
        for rect in rects[1:]:
            if rect.center_y - clusters[-1][-1].center_y <= max_gap:
                clusters[-1].append(rect)
            else:
                clusters.append([rect])

        clusters.sort(key=len, reverse=True)
        return clusters[0]

    def _find_active_index(
        self,
        tabs: list[SideTabInfo],
        active_mask: MatLike,
        active_rect: Rect | None,
    ) -> int | None:
        """
        根据各 tab 内的激活色得分判断当前激活项。

        :param tabs: 当前识别出的 tab 列表。
        :param active_mask: 整张截图上的激活色二值图。
        :param active_rect: 激活色轮廓法得到的背景矩形。
        :return: 激活 tab 的索引；未命中时返回 ``None``。
        """
        best_index: int | None = None
        best_ratio = 0.0
        for tab in tabs:
            score_rect = Rect(
                tab.rect.x1,
                tab.rect.y1,
                max(1, min(self.ACTIVE_SCORE_WIDTH, tab.rect.w)),
                tab.rect.h,
            )
            roi = active_mask[score_rect.y1:score_rect.y2, score_rect.x1:score_rect.x2]
            if roi.size == 0:
                continue
            ratio = float(np.count_nonzero(roi)) / float(roi.shape[0] * roi.shape[1])
            if ratio > best_ratio:
                best_ratio = ratio
                best_index = tab.index

        if best_index is not None and best_ratio >= self.ACTIVE_SCORE_MIN_RATIO:
            return best_index

        if active_rect is None:
            return None
        for tab in tabs:
            if tab.rect.contains_point(active_rect.center):
                return tab.index
        return None

    def _find_active_rect(self, active_mask: MatLike, container_rect: Rect) -> Rect | None:
        """
        通过激活项底色查找当前激活 tab 的背景区域。

        :param active_mask: 当前截图的激活色二值图。
        :param container_rect: 侧边栏整体区域。
        :return: 激活项矩形；未命中时返回 ``None``。
        """
        roi = active_mask[container_rect.y1:container_rect.y2, container_rect.x1:container_rect.x2]
        if roi.size == 0:
            return None

        kernel = np.ones(self.ACTIVE_MASK_KERNEL, dtype=np.uint8)
        mask = cv2.morphologyEx(roi, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        best_rect: Rect | None = None
        best_score = -1.0
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = int(cv2.contourArea(contour))
            if area < self.MIN_ACTIVE_AREA:
                continue
            if w < self.MIN_ACTIVE_WIDTH:
                continue
            if h < self.MIN_ACTIVE_HEIGHT or h > self.MAX_ACTIVE_HEIGHT:
                continue

            rect = Rect(container_rect.x1 + x, container_rect.y1 + y, w, h)
            score = float(area + w * 10 - abs(rect.x1 - container_rect.x1) * 4)
            if score > best_score:
                best_rect = rect
                best_score = score
        if DEBUG:
            debug_mask = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
            if best_rect is not None:
                cv2.rectangle(
                    debug_mask,
                    (best_rect.x1 - container_rect.x1, best_rect.y1 - container_rect.y1),
                    (best_rect.x2 - container_rect.x1, best_rect.y2 - container_rect.y1),
                    (0, 255, 0),
                    2,
                )
            _debug_show('SideTabbar/active_mask', debug_mask)
        return best_rect

    def _find_visual_rects(self, image: MatLike, container_rect: Rect) -> list[Rect]:
        """
        通过边缘密度查找侧边栏中的视觉候选。

        :param image: 当前截图。
        :param container_rect: 侧边栏整体区域。
        :return: 候选矩形列表。
        """
        search_rect = Rect(
            container_rect.x1 + self.VISUAL_INSET_LEFT,
            container_rect.y1,
            max(1, container_rect.w - self.VISUAL_INSET_LEFT - self.VISUAL_INSET_RIGHT),
            container_rect.h,
        )
        roi = image[search_rect.y1:search_rect.y2, search_rect.x1:search_rect.x2]
        if roi.size == 0:
            return []

        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(
            gray,
            self.VISUAL_CANNY_LOWER,
            self.VISUAL_CANNY_UPPER,
        )
        edges = cv2.dilate(edges, np.ones((5, 5), dtype=np.uint8), iterations=1)

        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        visual_rects: list[Rect] = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = int(cv2.contourArea(contour))
            if area < self.MIN_VISUAL_AREA:
                continue
            if w < self.MIN_VISUAL_WIDTH or w > self.MAX_VISUAL_WIDTH:
                continue
            if h < self.MIN_VISUAL_HEIGHT or h > self.MAX_VISUAL_HEIGHT:
                continue
            visual_rects.append(Rect(search_rect.x1 + x, search_rect.y1 + y, w, h))

        visual_rects.sort(key=lambda rect: rect.center_y)
        merged: list[Rect] = []
        for rect in visual_rects:
            if not merged:
                merged.append(rect)
                continue
            last = merged[-1]
            if rect.center_y - last.center_y <= self.VISUAL_MERGE_GAP:
                merged[-1] = _union_rect([last, rect])
            else:
                merged.append(rect)
        if len(merged) >= 2:
            first = merged[0]
            second = merged[1]
            vertical_gap = second.y1 - first.y2
            horizontal_overlap = min(first.x2, second.x2) - max(first.x1, second.x1)
            overlap_ratio = horizontal_overlap / max(1, min(first.w, second.w))
            if (
                first.y1 <= container_rect.y1 + 2
                and first.h <= self.TOP_FRAGMENT_MAX_HEIGHT
                and vertical_gap <= self.TOP_FRAGMENT_MAX_GAP
                and overlap_ratio >= 0.75
            ):
                merged = [_union_rect([first, second]), *merged[2:]]

        if DEBUG:
            debug_edges = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
            for rect in merged:
                cv2.rectangle(
                    debug_edges,
                    (rect.x1 - search_rect.x1, rect.y1 - search_rect.y1),
                    (rect.x2 - search_rect.x1, rect.y2 - search_rect.y1),
                    (0, 255, 0),
                    2,
                )
            _debug_show('SideTabbar/visual_edges', debug_edges)
        return merged

    def _find_badge_rect(self, image: MatLike, tab_rect: Rect) -> Rect | None:
        """
        在 tab 右上角搜索红色 badge。

        :param image: 当前截图。
        :param tab_rect: 目标 tab 矩形。
        :return: badge 矩形；未命中时返回 ``None``。
        """
        search_size = self.BADGE_SEARCH_SIZE
        x1 = max(tab_rect.x1, tab_rect.x2 - search_size)
        y1 = tab_rect.y1
        search_height = min(max(search_size, tab_rect.h // 2), tab_rect.h)
        search_rect = Rect(x1, y1, max(1, tab_rect.x2 - x1), max(1, search_height))
        roi = image[search_rect.y1:search_rect.y2, search_rect.x1:search_rect.x2]
        if roi.size == 0:
            return None

        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        mask1 = cv2.inRange(
            hsv,
            np.array(self.parse_config.badge_red1_lower, dtype=np.uint8),
            np.array(self.parse_config.badge_red1_upper, dtype=np.uint8),
        )
        mask2 = cv2.inRange(
            hsv,
            np.array(self.parse_config.badge_red2_lower, dtype=np.uint8),
            np.array(self.parse_config.badge_red2_upper, dtype=np.uint8),
        )
        mask = cv2.bitwise_or(mask1, mask2)
        kernel = np.ones(self.BADGE_KERNEL, dtype=np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        best_rect: Rect | None = None
        best_score = -1.0
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = int(cv2.contourArea(contour))
            if area < self.MIN_BADGE_AREA:
                continue
            if w < 10 or h < 10:
                continue

            rect = Rect(search_rect.x1 + x, search_rect.y1 + y, w, h)
            score = float(area - abs(w - h) * 8)
            if score > best_score:
                best_rect = rect
                best_score = score
        if DEBUG:
            debug_mask = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
            if best_rect is not None:
                cv2.rectangle(
                    debug_mask,
                    (best_rect.x1 - search_rect.x1, best_rect.y1 - search_rect.y1),
                    (best_rect.x2 - search_rect.x1, best_rect.y2 - search_rect.y1),
                    (0, 255, 0),
                    2,
                )
            _debug_show(f'SideTabbar/badge_{tab_rect.y1}', debug_mask)
        return best_rect


if __name__ == '__main__':
    import json
    from pathlib import Path
    import sys

    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from kotonebot.backend.context.context import init_context, manual_context
    from kotonebot.client.host import Mumu12V5Host
    from kotonebot.client.host.mumu12_host import MuMu12HostConfig

    from iaa.config.base import IaaConfig

    def format_state(state: SideTabbarState) -> str:
        """
        将解析结果格式化为调试输出字符串。

        :param state: 当前侧边栏解析结果。
        :return: 便于打印的摘要字符串。
        """
        parts = [
            f'container={state.container_rect.xyxy}',
            f'active={state.active_index}',
            f'badges={state.badge_indices}',
            f'count={len(state.tabs)}',
        ]
        return ', '.join(parts)

    config_path = Path('conf/default.json')
    config = IaaConfig.model_validate(json.loads(config_path.read_text(encoding='utf-8')))
    hosts = Mumu12V5Host.list()
    if not hosts:
        raise RuntimeError('No MuMu v5 instance found.')

    host = hosts[0]
    if not host.running() and config.game.check_emulator:
        host.start()
        host.wait_available()

    debug_device = host.create_device('nemu_ipc', MuMu12HostConfig())
    debug_device.orientation = 'landscape'
    init_context(target_device=debug_device, force=True)

    tabbar = SideTabbar()
    print('Connected device screen size:', debug_device.screen_size)

    with manual_context('manual'):
        initial = tabbar.update()
        print('[initial]', format_state(initial))
        for tab in initial.tabs:
            print(
                f'  - tab[{tab.index}] rect={tab.rect.xyxy} '
                f'active={tab.is_active} badge={tab.has_badge} '
                f'badge_rect={tab.badge_rect.xyxy if tab.badge_rect else None}'
            )

        for index in range(len(initial.tabs)):
            current = tabbar.update()
            if index >= len(current.tabs):
                print(f'[switch_to {index}] skipped: current count={len(current.tabs)}')
                continue
            state = tabbar.switch_to(index)
            print(f'[switch_to {index}]', format_state(state))

    cv2.waitKey(0)
