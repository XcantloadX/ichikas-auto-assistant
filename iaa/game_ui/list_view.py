from collections.abc import Iterator
from dataclasses import dataclass

import cv2
import numpy as np
from cv2.typing import MatLike
from kotonebot import device
from kotonebot.primitives import Rect

from .scrollable import ScrollProgress, Scrollable

DEBUG = False


def _clip_rect(rect: Rect, bounds: Rect) -> Rect | None:
    x1 = max(rect.x1, bounds.x1)
    y1 = max(rect.y1, bounds.y1)
    x2 = min(rect.x2, bounds.x2)
    y2 = min(rect.y2, bounds.y2)
    if x2 <= x1 or y2 <= y1:
        return None
    return Rect(x1, y1, x2 - x1, y2 - y1)


def _rect_iou(lhs: Rect, rhs: Rect) -> float:
    x1 = max(lhs.x1, rhs.x1)
    y1 = max(lhs.y1, rhs.y1)
    x2 = min(lhs.x2, rhs.x2)
    y2 = min(lhs.y2, rhs.y2)
    if x2 <= x1 or y2 <= y1:
        return 0.0
    inter = float((x2 - x1) * (y2 - y1))
    union = float(lhs.w * lhs.h + rhs.w * rhs.h - inter)
    if union <= 0:
        return 0.0
    return inter / union


def _ahash(image: MatLike | None, size: int = 8) -> int | None:
    if image is None or image.size == 0:
        return None
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
    resized = cv2.resize(gray, (size, size), interpolation=cv2.INTER_AREA)
    mean = float(resized.mean())
    bits = (resized >= mean).astype(np.uint8).flatten()
    value = 0
    for bit in bits:
        value = (value << 1) | int(bit)
    return value


def _hamming_distance(lhs: int | None, rhs: int | None) -> int | None:
    if lhs is None or rhs is None:
        return None
    return (lhs ^ rhs).bit_count()


def _extract_patch(screenshot: MatLike, rect: Rect | None) -> MatLike | None:
    if rect is None:
        return None
    bounds = Rect(0, 0, screenshot.shape[1], screenshot.shape[0])
    clipped = _clip_rect(rect, bounds)
    if clipped is None:
        return None
    patch = screenshot[clipped.y1:clipped.y2, clipped.x1:clipped.x2]
    return patch.copy() if patch.size > 0 else None


@dataclass(slots=True, frozen=True)
class ListViewItemHash:
    icon_hash: int | None
    price_hash: int | None

    def match_score(self, other: "ListViewItemHash") -> int | None:
        icon_distance = _hamming_distance(self.icon_hash, other.icon_hash)
        price_distance = _hamming_distance(self.price_hash, other.price_hash)

        if icon_distance is None:
            return None
        if price_distance is None:
            return icon_distance * 3 + 50
        return icon_distance * 3 + price_distance * 2


@dataclass(slots=True)
class ListViewItem:
    index: int
    rect: Rect
    icon_rect: Rect
    price_rect: Rect | None
    image: MatLike
    """卡片的完整截图。"""
    page_index: int | None = None
    item_hash: ListViewItemHash | None = None

    @property
    def icon_image(self) -> MatLike:
        """卡片图标的截图。"""
        x1 = self.icon_rect.x1 - self.rect.x1
        y1 = self.icon_rect.y1 - self.rect.y1
        x2 = self.icon_rect.x2 - self.rect.x1
        y2 = self.icon_rect.y2 - self.rect.y1
        return self.image[y1:y2, x1:x2]

    def __repr__(self) -> str:
        return f"ListViewItem(index={self.index}, rect={self.rect}, icon_rect={self.icon_rect}, price_rect={self.price_rect}, page_index={self.page_index})"


@dataclass(slots=True)
class ListViewPageState:
    container_rect: Rect
    items: list[ListViewItem]
    progress: ScrollProgress | None = None

    def __getitem__(self, target: int) -> ListViewItem:
        if 0 <= target < len(self.items):
            return self.items[target]
        raise IndexError(target)


@dataclass(slots=True)
class ListViewState:
    container_rect: Rect
    items: list[ListViewItem]
    pages: list[ListViewPageState]
    progress: ScrollProgress | None

    def __getitem__(self, target: int) -> ListViewItem:
        if 0 <= target < len(self.items):
            return self.items[target]
        raise IndexError(target)


class ListViewPage:
    """
    通用卡片列表的单页解析器。

    只负责当前可见区域中的：
    - item 矩形
    - item 内 icon 矩形
    - item 底部 price/button 矩形
    """

    PRICE_HSV_RANGE = ((100, 5, 205), (140, 35, 245))
    PRICE_OPEN_KERNEL = (5, 5)
    PRICE_ERODE_KERNEL = (5, 3)
    PRICE_CLOSE_KERNEL = (15, 5)
    MIN_PRICE_SIZE = (110, 24)
    MAX_PRICE_SIZE = (240, 60)
    MIN_PRICE_AREA = 2_200

    ITEM_HSV_RANGE = ((0, 0, 235), (179, 15, 255))
    ITEM_OPEN_KERNEL = (3, 3)
    ITEM_CLOSE_KERNEL = (9, 9)
    CARD_MIN_SIZE = (180, 160)
    CARD_MAX_SIZE = (320, 320)
    CARD_SEARCH_LEFT = 28
    CARD_SEARCH_RIGHT = 28
    CARD_SEARCH_UP = 230
    CARD_SEARCH_DOWN = 36
    CARD_DEDUP_IOU = 0.55
    ROW_MERGE_GAP = 48
    DEFAULT_LIST_RECT_RATIO = (0.14, 0.12, 0.84, 0.85)
    MIN_CARD_ASPECT_RATIO = 1.0

    ICON_WHITE_HSV_RANGE = ((0, 0, 220), (179, 35, 255))
    ICON_NONWHITE_OPEN_KERNEL = (3, 3)
    ICON_NONWHITE_CLOSE_KERNEL = (5, 5)
    MIN_ICON_SIZE = (35, 35)
    MIN_ICON_AREA = 500

    def __init__(self, list_rect: Rect | None = None) -> None:
        self.list_rect = list_rect
        self.state: ListViewPageState | None = None

    def update(
        self,
        *,
        screenshot: MatLike | None = None,
        progress: ScrollProgress | None = None,
    ) -> ListViewPageState:
        screenshot = device.screenshot() if screenshot is None else screenshot
        container_rect = self._resolve_container_rect(screenshot)

        # 搜索思路：
        #（Item=整个白色背景商品卡片，Price=灰色背景的价格，Icon=商品图标）
        # 先根据颜色定位到所有的 Price 区域，然后往外扩张一定范围，
        # 从这个范围过滤白色，反推出 Item 区域。
        # 此时已经得到了正确的 Item 区域，再过滤一次白色，Item 区域中间的、
        # 大块的非白色矩形区域就是 Icon 区域。

        price_candidates = self._find_price_candidates(screenshot, container_rect)

        items: list[ListViewItem] = []
        item_rects: list[Rect] = []
        for price_rect in price_candidates:
            item_rect = self._find_item_rect(screenshot, container_rect, price_rect)
            if item_rect is None:
                continue
            if any(_rect_iou(item_rect, existing) >= self.CARD_DEDUP_IOU for existing in item_rects):
                continue
            icon_rect = self._find_icon_rect(screenshot, item_rect)
            if icon_rect is None:
                raise RuntimeError(f"failed to detect icon_rect for item_rect={item_rect.xyxy}")
            image_patch = _extract_patch(screenshot, item_rect)
            if image_patch is None:
                raise RuntimeError(f"failed to extract item image for item_rect={item_rect.xyxy}")
            item_rects.append(item_rect)
            items.append(
                ListViewItem(
                    index=-1,
                    rect=item_rect,
                    icon_rect=icon_rect,
                    price_rect=self._find_price_rect(screenshot, item_rect) or price_rect,
                    image=image_patch,
                )
            )

        items = self._sort_items(items)
        for index, item in enumerate(items):
            item.index = index

        self.state = ListViewPageState(
            container_rect=container_rect,
            items=items,
            progress=progress,
        )
        if DEBUG:
            self._debug_show(screenshot, self.state)
        return self.state

    def _resolve_container_rect(self, screenshot: MatLike) -> Rect:
        if self.list_rect is not None:
            return self.list_rect
        height, width = screenshot.shape[:2]
        left_ratio, top_ratio, width_ratio, height_ratio = self.DEFAULT_LIST_RECT_RATIO
        return Rect(
            int(round(width * left_ratio)),
            int(round(height * top_ratio)),
            int(round(width * width_ratio)),
            int(round(height * height_ratio)),
        )

    def _find_price_candidates(self, image: MatLike, container_rect: Rect) -> list[Rect]:
        roi = image[container_rect.y1:container_rect.y2, container_rect.x1:container_rect.x2]
        if roi.size == 0:
            return []

        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(
            hsv,
            np.array(self.PRICE_HSV_RANGE[0], dtype=np.uint8),
            np.array(self.PRICE_HSV_RANGE[1], dtype=np.uint8),
        )
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones(self.PRICE_OPEN_KERNEL, dtype=np.uint8))
        mask = cv2.erode(mask, np.ones(self.PRICE_ERODE_KERNEL, dtype=np.uint8), iterations=1)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones(self.PRICE_CLOSE_KERNEL, dtype=np.uint8))

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        rects: list[Rect] = []
        min_y = container_rect.y1 + int(round(container_rect.h * 0.18))
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = int(cv2.contourArea(contour))
            rect = Rect(container_rect.x1 + x, container_rect.y1 + y, w, h)
            if rect.y1 < min_y:
                continue
            if w < self.MIN_PRICE_SIZE[0] or w > self.MAX_PRICE_SIZE[0]:
                continue
            if h < self.MIN_PRICE_SIZE[1] or h > self.MAX_PRICE_SIZE[1]:
                continue
            if area < self.MIN_PRICE_AREA:
                continue
            rects.append(rect)
        rects.sort(key=lambda rect: (rect.y1, rect.x1))
        return rects

    def _find_item_rect(self, image: MatLike, container_rect: Rect, price_rect: Rect) -> Rect | None:
        local_rect = Rect(
            price_rect.x1 - self.CARD_SEARCH_LEFT,
            price_rect.y1 - self.CARD_SEARCH_UP,
            price_rect.w + self.CARD_SEARCH_LEFT + self.CARD_SEARCH_RIGHT,
            price_rect.h + self.CARD_SEARCH_UP + self.CARD_SEARCH_DOWN,
        )
        search_rect = _clip_rect(local_rect, container_rect)
        if search_rect is None:
            return None

        patch = image[search_rect.y1:search_rect.y2, search_rect.x1:search_rect.x2]
        if patch.size == 0:
            return None
        hsv = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(
            hsv,
            np.array(self.ITEM_HSV_RANGE[0], dtype=np.uint8),
            np.array(self.ITEM_HSV_RANGE[1], dtype=np.uint8),
        )
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones(self.ITEM_OPEN_KERNEL, dtype=np.uint8))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones(self.ITEM_CLOSE_KERNEL, dtype=np.uint8))

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        best_rect: Rect | None = None
        best_score = float("-inf")
        local_price_center = (price_rect.center_x - search_rect.x1, price_rect.center_y - search_rect.y1)
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if w < self.CARD_MIN_SIZE[0] or w > self.CARD_MAX_SIZE[0]:
                continue
            if h < self.CARD_MIN_SIZE[1] or h > self.CARD_MAX_SIZE[1]:
                continue
            if h / max(w, 1) < self.MIN_CARD_ASPECT_RATIO:
                continue
            if not (x <= local_price_center[0] <= x + w and y <= local_price_center[1] <= y + h):
                continue

            rect = Rect(search_rect.x1 + x, search_rect.y1 + y, w, h)
            price_bottom_ratio = (price_rect.center_y - rect.y1) / max(1, rect.h)
            if price_bottom_ratio < 0.55 or price_bottom_ratio > 1.05:
                continue

            area = float(cv2.contourArea(contour))
            fill_ratio = area / max(1.0, float(w * h))
            score = (
                area
                + fill_ratio * 5_000.0
                - abs(w - 245) * 120.0
                - abs(h - 235) * 90.0
                - abs(rect.center_x - price_rect.center_x) * 18.0
            )
            if score > best_score:
                best_rect = rect
                best_score = score
        return best_rect

    def _find_price_rect(self, image: MatLike, item_rect: Rect) -> Rect | None:
        search_rect = Rect(
            item_rect.x1 + int(round(item_rect.w * 0.05)),
            item_rect.y1 + int(round(item_rect.h * 0.70)),
            int(round(item_rect.w * 0.90)),
            max(1, item_rect.y2 - (item_rect.y1 + int(round(item_rect.h * 0.70)))),
        )
        search_rect = _clip_rect(search_rect, item_rect)
        if search_rect is None:
            return None

        patch = image[search_rect.y1:search_rect.y2, search_rect.x1:search_rect.x2]
        if patch.size == 0:
            return None
        hsv = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(
            hsv,
            np.array(self.PRICE_HSV_RANGE[0], dtype=np.uint8),
            np.array(self.PRICE_HSV_RANGE[1], dtype=np.uint8),
        )
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), dtype=np.uint8))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((9, 5), dtype=np.uint8))

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        best_rect: Rect | None = None
        best_score = float("-inf")
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = float(cv2.contourArea(contour))
            if w < int(item_rect.w * 0.42) or w > int(item_rect.w * 0.94):
                continue
            if h < self.MIN_PRICE_SIZE[1] or h > self.MAX_PRICE_SIZE[1]:
                continue
            rect = Rect(search_rect.x1 + x, search_rect.y1 + y, w, h)
            score = area - abs(rect.center_x - item_rect.center_x) * 10.0
            if score > best_score:
                best_rect = rect
                best_score = score
        return best_rect

    def _find_icon_rect(self, image: MatLike, item_rect: Rect) -> Rect | None:
        patch = image[item_rect.y1:item_rect.y2, item_rect.x1:item_rect.x2]
        if patch.size == 0:
            return None
        hsv = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV)
        white_mask = cv2.inRange(
            hsv,
            np.array(self.ICON_WHITE_HSV_RANGE[0], dtype=np.uint8),
            np.array(self.ICON_WHITE_HSV_RANGE[1], dtype=np.uint8),
        )
        nonwhite_mask = cv2.bitwise_not(white_mask)
        nonwhite_mask = cv2.morphologyEx(
            nonwhite_mask,
            cv2.MORPH_OPEN,
            np.ones(self.ICON_NONWHITE_OPEN_KERNEL, dtype=np.uint8),
        )
        nonwhite_mask = cv2.morphologyEx(
            nonwhite_mask,
            cv2.MORPH_CLOSE,
            np.ones(self.ICON_NONWHITE_CLOSE_KERNEL, dtype=np.uint8),
        )

        contours, _ = cv2.findContours(nonwhite_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        best_rect: Rect | None = None
        best_score = float("-inf")
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = float(cv2.contourArea(contour))
            if w < self.MIN_ICON_SIZE[0] or h < self.MIN_ICON_SIZE[1]:
                continue
            if area < self.MIN_ICON_AREA:
                continue
            if w > int(item_rect.w * 0.72) or h > int(item_rect.h * 0.52):
                continue
            aspect_ratio = w / max(h, 1)
            if aspect_ratio < 0.7 or aspect_ratio > 1.35:
                continue

            rect = Rect(item_rect.x1 + x, item_rect.y1 + y, w, h)
            score = (
                area
                - abs(rect.center_x - item_rect.center_x) * 8.0
                - max(0, rect.y1 - (item_rect.y1 + int(round(item_rect.h * 0.38)))) * 8.0
                - max(0, rect.y2 - (item_rect.y1 + int(round(item_rect.h * 0.62)))) * 10.0
                - abs(w - h) * 20.0
            )
            if score > best_score:
                best_rect = rect
                best_score = score
        return best_rect

    def _sort_items(self, items: list[ListViewItem]) -> list[ListViewItem]:
        if not items:
            return []
        items = sorted(items, key=lambda item: (item.rect.center_y, item.rect.x1))
        rows: list[list[ListViewItem]] = [[items[0]]]
        for item in items[1:]:
            if abs(item.rect.center_y - rows[-1][0].rect.center_y) <= self.ROW_MERGE_GAP:
                rows[-1].append(item)
            else:
                rows.append([item])

        ordered: list[ListViewItem] = []
        for row in rows:
            ordered.extend(sorted(row, key=lambda item: item.rect.x1))
        return ordered

    def _debug_show(self, image: MatLike, state: ListViewPageState) -> None:
        debug_image = render_debug_image(image, state)
        cv2.imshow("ListView/debug", debug_image)
        cv2.waitKey(1)


class ListView:
    """
    带滚动采集能力的完整列表读取器。
    """

    DEFAULT_STEP = 0.5
    DEFAULT_MAX_PAGES = 20
    DEFAULT_DUPLICATE_SCORE_THRESHOLD = 20
    def __init__(
        self,
        list_rect: Rect | None = None,
        *,
        scrollbar_rect: Rect | tuple[int, int, int, int] | None = None,
        step: float = DEFAULT_STEP,
        max_pages: int = DEFAULT_MAX_PAGES,
        duplicate_score_threshold: int = DEFAULT_DUPLICATE_SCORE_THRESHOLD,
    ) -> None:
        self.page = ListViewPage(list_rect=list_rect)
        self.scrollable = Scrollable(scrollbar_rect) if scrollbar_rect is not None else None
        self.step = step
        self.max_pages = max_pages
        self.duplicate_score_threshold = duplicate_score_threshold
        self.state: ListViewState | None = None

    def walk(
        self,
        *,
        max_pages: int | None = None,
        step: float | None = None,
        reset_to_top: bool = True,
    ) -> Iterator[ListViewItem]:
        max_pages = self.max_pages if max_pages is None else max_pages
        step = self.step if step is None else step

        if self.scrollable is None:
            screenshot = device.screenshot()
            page_state = self.page.update(screenshot=screenshot)
            items = self._clone_items(page_state.items, page_index=0, screenshot=screenshot)
            self._reindex(items)
            self.state = ListViewState(
                container_rect=page_state.container_rect,
                items=items,
                pages=[page_state],
                progress=page_state.progress,
            )
            for item in items:
                yield item
            return

        if reset_to_top:
            self.scrollable.to_top()

        pages: list[ListViewPageState] = []
        collected: list[ListViewItem] = []
        settled_bottom = False

        for page_index in range(max_pages):
            screenshot = device.screenshot()
            progress = self.scrollable.parse_progress(screenshot)
            page_state = self.page.update(screenshot=screenshot, progress=progress)
            pages.append(page_state)
            before_merge = len(collected)
            self._merge_page(collected, page_state, screenshot, page_index=page_index)
            self._reindex(collected)
            for item in collected[before_merge:]:
                yield item

            if progress is not None and progress.is_bottom():
                if not settled_bottom:
                    settled_bottom = True
                    continue
                break

            moved = self.scrollable.down(step=step)
            if moved is None:
                break
            if progress is not None and moved.thumb_rect.y1 == progress.thumb_rect.y1:
                break

        self._reindex(collected)
        final_progress = self.scrollable.refresh()
        container_rect = pages[0].container_rect if pages else self.page.update().container_rect
        self.state = ListViewState(
            container_rect=container_rect,
            items=collected,
            pages=pages,
            progress=final_progress,
        )
        return

    def _merge_page(
        self,
        collected: list[ListViewItem],
        page_state: ListViewPageState,
        screenshot: MatLike,
        *,
        page_index: int,
    ) -> int:
        added = 0
        for item in page_state.items:
            cloned = self._clone_item(item, page_index=page_index, screenshot=screenshot)
            if self._is_duplicate(collected, cloned):
                continue
            collected.append(cloned)
            added += 1
        return added

    def _is_duplicate(self, collected: list[ListViewItem], candidate: ListViewItem) -> bool:
        if candidate.item_hash is None:
            return False
        best_score: int | None = None
        for existing in collected:
            if existing.item_hash is None:
                continue
            score = candidate.item_hash.match_score(existing.item_hash)
            if score is None:
                continue
            best_score = score if best_score is None else min(best_score, score)
        return best_score is not None and best_score <= self.duplicate_score_threshold

    def _clone_items(self, items: list[ListViewItem], *, page_index: int, screenshot: MatLike) -> list[ListViewItem]:
        return [self._clone_item(item, page_index=page_index, screenshot=screenshot) for item in items]

    def _clone_item(self, item: ListViewItem, *, page_index: int, screenshot: MatLike) -> ListViewItem:
        icon_patch = _extract_patch(screenshot, item.icon_rect)
        if icon_patch is None:
            raise RuntimeError(f"failed to extract icon patch for item_rect={item.rect.xyxy}, icon_rect={item.icon_rect.xyxy}")
        return ListViewItem(
            index=item.index,
            rect=item.rect,
            icon_rect=item.icon_rect,
            price_rect=item.price_rect,
            image=item.image.copy(),
            page_index=page_index,
            item_hash=ListViewItemHash(
                icon_hash=_ahash(icon_patch),
                price_hash=_ahash(_extract_patch(screenshot, item.price_rect)),
            ),
        )

    def _reindex(self, items: list[ListViewItem]) -> None:
        for index, item in enumerate(items):
            item.index = index


def render_debug_image(image: MatLike, state: ListViewPageState) -> MatLike:
    debug_image = image.copy()
    cv2.rectangle(
        debug_image,
        (state.container_rect.x1, state.container_rect.y1),
        (state.container_rect.x2, state.container_rect.y2),
        (255, 255, 0),
        2,
    )
    for item in state.items:
        cv2.rectangle(debug_image, (item.rect.x1, item.rect.y1), (item.rect.x2, item.rect.y2), (0, 255, 0), 2)
        cv2.putText(
            debug_image,
            str(item.index),
            (item.rect.x1 + 4, item.rect.y1 + 22),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 0, 255),
            2,
            cv2.LINE_AA,
        )
        if item.icon_rect is not None:
            cv2.rectangle(
                debug_image,
                (item.icon_rect.x1, item.icon_rect.y1),
                (item.icon_rect.x2, item.icon_rect.y2),
                (255, 128, 0),
                2,
            )
        if item.price_rect is not None:
            cv2.rectangle(
                debug_image,
                (item.price_rect.x1, item.price_rect.y1),
                (item.price_rect.x2, item.price_rect.y2),
                (255, 0, 255),
                2,
            )
    return debug_image


def render_item_gallery(items: list[ListViewItem]) -> MatLike:
    valid_items = [item for item in items if item.image.size > 0]
    if not valid_items:
        return np.full((120, 320, 3), 32, dtype=np.uint8)

    cell_width = 220
    cell_height = 280
    title_height = 36
    columns = min(4, max(1, len(valid_items)))
    rows = (len(valid_items) + columns - 1) // columns
    canvas = np.full((rows * cell_height, columns * cell_width, 3), 28, dtype=np.uint8)

    for index, item in enumerate(valid_items):
        row = index // columns
        col = index % columns
        x1 = col * cell_width
        y1 = row * cell_height
        # slice intentionally unused here; write directly into `canvas`

        image = item.image
        scale = min(
            (cell_width - 16) / max(image.shape[1], 1),
            (cell_height - title_height - 16) / max(image.shape[0], 1),
        )
        resized = cv2.resize(
            image,
            (
                max(1, int(round(image.shape[1] * scale))),
                max(1, int(round(image.shape[0] * scale))),
            ),
            interpolation=cv2.INTER_AREA,
        )
        image_x = x1 + (cell_width - resized.shape[1]) // 2
        image_y = y1 + title_height + (cell_height - title_height - resized.shape[0]) // 2
        canvas[image_y:image_y + resized.shape[0], image_x:image_x + resized.shape[1]] = resized

        cv2.rectangle(canvas, (x1, y1), (x1 + cell_width - 1, y1 + cell_height - 1), (90, 90, 90), 1)
        cv2.putText(
            canvas,
            f'#{item.index} p={item.page_index}',
            (x1 + 8, y1 + 24),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (220, 220, 220),
            2,
            cv2.LINE_AA,
        )
    return canvas


if __name__ == "__main__":
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

    def format_rect(rect: Rect | None) -> tuple[int, int, int, int] | None:
        return None if rect is None else rect.xyxy

    config = IaaConfig.model_validate(json.loads(Path("conf/default.json").read_text(encoding="utf-8")))
    hosts = Mumu12V5Host.list()
    if not hosts:
        raise RuntimeError("No MuMu v5 instance found.")

    host = hosts[0]
    if not host.running() and config.game.check_emulator:
        host.start()
        host.wait_available()

    debug_device = host.create_device("nemu_ipc", MuMu12HostConfig())
    debug_device.orientation = "landscape"
    init_context(target_device=debug_device, force=True)

    list_view = ListView(
        scrollbar_rect=(1247, 60, 8, 650),
    )
    with manual_context("manual"):
        for item in list_view.walk():
            print(
                f"item[{item.index}] page={item.page_index} "
                f"rect={format_rect(item.rect)} "
                f"icon={format_rect(item.icon_rect)} "
                f"price={format_rect(item.price_rect)}"
            )

        state = list_view.state
        if state is None:
            raise RuntimeError("ListView iteration finished without state.")
        print("container=", state.container_rect.xyxy, "count=", len(state.items), "pages=", len(state.pages))

        current_page = list_view.page.state
        if current_page is not None:
            screenshot = debug_device.screenshot()
            output_dir = Path("logs/list_view_main")
            output_dir.mkdir(parents=True, exist_ok=True)
            screenshot_path = output_dir / "00_screenshot.png"
            debug_path = output_dir / "01_debug.png"
            gallery_path = output_dir / "02_items_gallery.png"
            cv2.imwrite(str(screenshot_path), screenshot)
            cv2.imwrite(str(debug_path), render_debug_image(screenshot, current_page))
            cv2.imwrite(str(gallery_path), render_item_gallery(state.items))
            print("saved screenshot to", screenshot_path)
            print("saved debug image to", debug_path)
            print("saved item gallery to", gallery_path)

    cv2.waitKey(0)
