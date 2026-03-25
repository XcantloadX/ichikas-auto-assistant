from dataclasses import dataclass
from typing import ClassVar
from collections.abc import Iterator

import cv2
import numpy as np
from cv2.typing import MatLike
from kotonebot import device, sleep
from kotonebot.primitives import Rect

RectLike = Rect | tuple[int, int, int, int]


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _coerce_rect(rect: RectLike) -> Rect:
    if isinstance(rect, Rect):
        return rect
    return Rect(*rect)


@dataclass(slots=True)
class ScrollProgress:
    DEFAULT_TOLERANCE: ClassVar[float] = 0.04

    """
    一次滚动条解析结果。

    :ivar track_rect: 解析出的滚动轨道区域。
    :ivar thumb_rect: 解析出的 thumb 区域。
    :ivar progress: 当前进度，范围 ``[0, 1]``。
    :ivar center_ratio: thumb 中心点在轨道内的归一化位置。
    :ivar visible_ratio: thumb 高度占轨道高度的比例。
    :ivar confidence: 当前解析结果的粗略置信度。
    """

    track_rect: Rect
    """滚动轨道区域。"""

    thumb_rect: Rect
    """滚动 thumb 区域。"""

    progress: float | None
    """测量边界后的当前进度；未测量时为 ``None``。"""

    center_ratio: float
    """thumb 中心点在轨道中的相对位置。"""

    visible_ratio: float
    """thumb 高度占轨道高度的比例。"""

    confidence: float
    """当前解析结果的粗略置信度。"""

    raw_progress: float | None = None
    """未测量时按粗略轨道计算出的原始进度。"""

    def is_top(self, tolerance: float | None = None) -> bool:
        """
        判断当前是否位于顶部附近。

        :param tolerance: 顶部容差。
        :return: 若当前进度不大于 ``tolerance``，则返回 ``True``。
        """
        tolerance = self.DEFAULT_TOLERANCE if tolerance is None else tolerance
        return self.progress is not None and self.progress <= tolerance

    def is_bottom(self, tolerance: float | None = None) -> bool:
        """
        判断当前是否位于底部附近。

        :param tolerance: 底部容差。
        :return: 若当前进度不小于 ``1 - tolerance``，则返回 ``True``。
        """
        tolerance = self.DEFAULT_TOLERANCE if tolerance is None else tolerance
        return self.progress is not None and self.progress >= 1 - tolerance


class Scrollable:
    """
    基于滚动条 thumb 拖拽的可滚动容器控制器。

    构造时传入一个大致的 ``scrollbar_rect`` 即可。
    运行时会在该区域内解析 thumb，并据此完成单步滚动或目标进度拖拽。

    :param scrollbar_rect: 滚动条所在的大致区域。
    :param drag_duration: 单次拖拽持续时间，单位秒。
    :param drag_delay: 拖拽后等待界面稳定的时间，单位秒。
    """

    # Thumb detection
    THUMB_HSV_LOWER: ClassVar[tuple[int, int, int]] = (100, 30, 60)
    THUMB_HSV_UPPER: ClassVar[tuple[int, int, int]] = (140, 180, 170)
    MIN_THUMB_HEIGHT: ClassVar[int] = 24
    MAX_THUMB_HEIGHT: ClassVar[int | None] = None
    DEFAULT_TRACK_WIDTH: ClassVar[int] = 24
    DEFAULT_THUMB_MAX_WIDTH: ClassVar[int] = 32
    DEFAULT_THUMB_MIN_AREA: ClassVar[int] = 60
    DEFAULT_MORPHOLOGY_KERNEL: ClassVar[tuple[int, int]] = (3, 3)

    # Generic drag tuning
    DEFAULT_PROGRESS_TOLERANCE: ClassVar[float] = ScrollProgress.DEFAULT_TOLERANCE
    DEFAULT_DRAG_DURATION_SCALE_MAX: ClassVar[float] = 2.4
    DEFAULT_EDGE_DRAG_DURATION_BOOST: ClassVar[float] = 1.35

    # Measurement tuning
    DEFAULT_MEASUREMENT_STEP: ClassVar[float] = 3.0
    DEFAULT_MEASUREMENT_EDGE_DRAG_BOOST: ClassVar[float] = 1.45
    DEFAULT_MEASUREMENT_DRAG_DELAY: ClassVar[float] = 0.45
    DEFAULT_EDGE_STALL_DELTA: ClassVar[int] = 2
    DEFAULT_EDGE_STALL_REPEAT: ClassVar[int] = 1
    DEFAULT_EDGE_OVERDRAG_DISTANCE: ClassVar[int] = 72

    # Edge settle
    DEFAULT_EDGE_CONTENT_SWIPE_X_OFFSET: ClassVar[int] = 16
    DEFAULT_EDGE_CONTENT_SWIPE_START_RATIO: ClassVar[float] = 0.80
    DEFAULT_EDGE_CONTENT_SWIPE_END_RATIO: ClassVar[float] = 0.64
    DEFAULT_EDGE_CONTENT_SWIPE_DURATION: ClassVar[float] = 0.20
    DEFAULT_EDGE_CONTENT_SWIPE_DELAY: ClassVar[float] = 0.80

    def __init__(
        self,
        scrollbar_rect: RectLike,
        *,
        drag_duration: float = 0.25,
        drag_delay: float = 1.0,
    ) -> None:
        self.scrollbar_rect = _coerce_rect(scrollbar_rect)
        """滚动条所在的大致区域。"""

        self.drag_duration = drag_duration
        """单次拖拽持续时间，单位秒。"""

        self.drag_delay = drag_delay
        """拖拽后等待界面稳定的时间，单位秒。"""

        self.progress: ScrollProgress | None = None
        """最近一次解析得到的滚动进度。"""

        self.last_screenshot: MatLike | None = None
        """最近一次用于解析的截图。"""

        self.measured_top_y1: int | None = None
        """交互测量得到的顶部 thumb y1。"""

        self.measured_bottom_y1: int | None = None
        """交互测量得到的底部 thumb y1。"""

    def walk_down(self, *, step: float = 1.0) -> Iterator[ScrollProgress]:
        """
        向下逐步滚动，并在每一步产出当前状态。

        :param step: 单步滚动倍率。
        """
        current = self.refresh()
        if current is None:
            return

        while current is not None:
            yield current

            if step == 0:
                return
            if self.has_measured_bounds and current.is_bottom():
                return

            before_y = current.thumb_rect.y1
            self.down(step=abs(step))

            current = self.progress
            if current is None:
                return
            if abs(current.thumb_rect.y1 - before_y) <= self.DEFAULT_EDGE_STALL_DELTA:
                return

    def walk_up(self, *, step: float = 1.0) -> Iterator[ScrollProgress]:
        """
        向上逐步滚动，并在每一步产出当前状态。

        :param step: 单步滚动倍率。
        """
        current = self.refresh()
        if current is None:
            return

        while current is not None:
            yield current

            if step == 0:
                return
            if self.has_measured_bounds and current.is_top():
                return

            before_y = current.thumb_rect.y1
            self.up(step=abs(step))

            current = self.progress
            if current is None:
                return
            if abs(current.thumb_rect.y1 - before_y) <= self.DEFAULT_EDGE_STALL_DELTA:
                return

    def parse_progress(self, image: MatLike | None = None) -> ScrollProgress | None:
        """
        解析当前滚动条进度。

        :param image: 可选截图。不传时会自动截图。
        :return: 解析成功时返回 :class:`ScrollProgress`，否则返回 ``None``。
        """
        screenshot = device.screenshot() if image is None else image
        self.last_screenshot = screenshot

        rough_rect = self.scrollbar_rect
        roi = screenshot[rough_rect.y1:rough_rect.y2, rough_rect.x1:rough_rect.x2]
        if roi.size == 0:
            self.progress = None
            return None

        mask = self._build_thumb_mask(roi)
        thumb_rect, confidence = self._find_thumb(rough_rect, mask)
        if thumb_rect is None:
            self.progress = None
            return None

        track_rect = self._refine_track_rect(rough_rect, thumb_rect)
        travel = max(track_rect.h - thumb_rect.h, 1)
        raw_progress = _clamp((thumb_rect.y1 - track_rect.y1) / travel, 0.0, 1.0)
        progress = self._measured_progress_from_y1(thumb_rect.y1)
        center_ratio = _clamp((thumb_rect.y1 + thumb_rect.h / 2 - track_rect.y1) / track_rect.h, 0.0, 1.0)
        visible_ratio = _clamp(thumb_rect.h / track_rect.h, 0.0, 1.0)
        self.progress = ScrollProgress(
            track_rect=track_rect,
            thumb_rect=thumb_rect,
            progress=progress,
            center_ratio=center_ratio,
            visible_ratio=visible_ratio,
            confidence=confidence,
            raw_progress=raw_progress,
        )
        return self.progress

    def refresh(self) -> ScrollProgress | None:
        """
        刷新当前滚动进度。

        :return: 最新的滚动进度；若解析失败则返回 ``None``。
        """
        return self.parse_progress()

    def down(
        self,
        *,
        step: float = 1.0,
        duration: float | None = None,
        drag_delay: float | None = None,
    ) -> ScrollProgress | None:
        """
        向下滚动一步。

        :param step: 单步滚动尺度，相对于当前 ``visible_ratio`` 的倍率。
        :param duration: 可选拖拽时长；不传则使用实例默认值。
        :param drag_delay: 可选稳定等待时间；不传则使用实例默认值。
        :return: 滚动后的最新进度；若解析失败则返回 ``None``。
        """
        current = self.progress or self.refresh()
        if current is None:
            return None
        delta = current.visible_ratio * _clamp(step, 0.1, 1.0)
        baseline = current.progress if current.progress is not None else current.raw_progress
        if baseline is None:
            return None
        updated = self._drag_to_progress(
            target=baseline + delta,
            duration=duration,
            drag_delay=drag_delay,
        )
        return self._maybe_settle_edge(updated)

    def up(
        self,
        *,
        step: float = 1.0,
        duration: float | None = None,
        drag_delay: float | None = None,
    ) -> ScrollProgress | None:
        """
        向上滚动一步。

        :param step: 单步滚动尺度，相对于当前 ``visible_ratio`` 的倍率。
        :param duration: 可选拖拽时长；不传则使用实例默认值。
        :param drag_delay: 可选稳定等待时间；不传则使用实例默认值。
        :return: 滚动后的最新进度；若解析失败则返回 ``None``。
        """
        current = self.progress or self.refresh()
        if current is None:
            return None
        delta = current.visible_ratio * _clamp(step, 0.1, 1.0)
        baseline = current.progress if current.progress is not None else current.raw_progress
        if baseline is None:
            return None
        updated = self._drag_to_progress(
            target=baseline - delta,
            duration=duration,
            drag_delay=drag_delay,
        )
        return self._maybe_settle_edge(updated)

    def to_top(self, *, max_steps: int = 12) -> ScrollProgress | None:
        """
        逐步移动到顶部附近。

        :param max_steps: 最大尝试次数。
        :return: 最终进度；若解析失败则返回 ``None``。
        """
        if not self.has_measured_bounds:
            measured = self.measure_bounds(max_steps=max_steps, return_to_top=True)
            if measured is None:
                return None
            return measured
        return self._seek_edge('up', max_steps=max_steps)

    def to_bottom(self, *, max_steps: int = 12) -> ScrollProgress | None:
        """
        逐步移动到底部附近。

        :param max_steps: 最大尝试次数。
        :return: 最终进度；若解析失败则返回 ``None``。
        """
        if not self.has_measured_bounds:
            measured = self.measure_bounds(max_steps=max_steps, return_to_top=False)
            if measured is None:
                return None
            return measured
        return self._seek_edge('down', max_steps=max_steps)

    @property
    def has_measured_bounds(self) -> bool:
        return (
            self.measured_top_y1 is not None
            and self.measured_bottom_y1 is not None
            and self.measured_bottom_y1 > self.measured_top_y1
        )

    def measure_bounds(
        self,
        *,
        max_steps: int = 12,
        return_to_top: bool = True,
    ) -> ScrollProgress | None:
        """
        通过真实拖拽交互测量顶部与底部的 thumb 位置范围。

        :param max_steps: 单边测量的最大尝试次数。
        :param return_to_top: 完成后是否返回顶部附近。
        :return: 测量结束后的最新进度。
        """
        current = self.refresh()
        if current is None:
            return None
        top = current
        if current.raw_progress is None or current.raw_progress > 0.15:
            top = self._seek_edge(
                'up',
                max_steps=max_steps,
                step=self.DEFAULT_MEASUREMENT_STEP,
                settle_edge=False,
            )
            if top is None:
                return None
        self.measured_top_y1 = top.thumb_rect.y1

        bottom = self._seek_edge(
            'down',
            max_steps=max_steps,
            step=self.DEFAULT_MEASUREMENT_STEP,
            settle_edge=False,
        )
        if bottom is None:
            self.measured_top_y1 = None
            return None
        self.measured_bottom_y1 = bottom.thumb_rect.y1

        if return_to_top:
            return self._seek_edge(
                'up',
                max_steps=max_steps,
                step=self.DEFAULT_MEASUREMENT_STEP,
                settle_edge=True,
            )
        return bottom

    def to(
        self,
        target: float,
        *,
        tolerance: float | None = None,
        max_steps: int = 12,
        duration: float | None = None,
        drag_delay: float | None = None,
    ) -> ScrollProgress | None:
        """
        逐步移动到指定进度附近。

        :param target: 目标进度，范围 ``[0, 1]``。
        :param tolerance: 目标容差；不传则使用实例默认值。
        :param max_steps: 最大尝试次数。
        :param duration: 可选拖拽时长；不传则使用实例默认值。
        :param drag_delay: 可选稳定等待时间；不传则使用实例默认值。
        :return: 最终进度；若解析失败则返回 ``None``。
        """
        self._require_measured_bounds('to')
        target = _clamp(target, 0.0, 1.0)
        tolerance = self.DEFAULT_PROGRESS_TOLERANCE if tolerance is None else tolerance

        current = self.progress or self.refresh()
        for _ in range(max_steps):
            if current is None:
                return None
            if current.progress is not None and abs(target - current.progress) <= tolerance:
                return current
            current = self._drag_to_progress(
                target=target,
                duration=duration,
                drag_delay=drag_delay,
            )
        return current

    def at_top(self, *, image: MatLike | None = None) -> bool:
        """
        判断当前是否位于顶部附近。

        :param image: 可选截图。不传时使用缓存进度，必要时自动刷新。
        :return: 是否位于顶部附近。
        """
        self._require_measured_bounds('at_top')
        progress = self.parse_progress(image) if image is not None else (self.progress or self.refresh())
        return progress.is_top() if progress is not None else False

    def at_bottom(self, *, image: MatLike | None = None) -> bool:
        """
        判断当前是否位于底部附近。

        :param image: 可选截图。不传时使用缓存进度，必要时自动刷新。
        :return: 是否位于底部附近。
        """
        self._require_measured_bounds('at_bottom')
        progress = self.parse_progress(image) if image is not None else (self.progress or self.refresh())
        return progress.is_bottom() if progress is not None else False

    def _maybe_settle_edge(self, progress: ScrollProgress | None) -> ScrollProgress | None:
        # PJSK 的滚动条有一个 bug，如果仅通过拖拽滚动条而不是拖拽内容，
        # 拖到最上面或者最下面后，此时内容全部展示，但是容器内上边缘或内下边缘
        # 的渐变效果依旧存在，导致后续识别可能出现问题。
        # 解决方法就是此时再拖拽一下内容即可。
        
        if progress is None:
            return None

        direction: str | None = None
        if progress.is_top():
            direction = 'top'
        elif progress.is_bottom():
            direction = 'bottom'
        if direction is None:
            return progress

        x = self.scrollbar_rect.x1 - self.DEFAULT_EDGE_CONTENT_SWIPE_X_OFFSET
        x = max(1, x)
        start_y = self.scrollbar_rect.y1 + int(round(self.scrollbar_rect.h * self.DEFAULT_EDGE_CONTENT_SWIPE_START_RATIO))
        end_y = self.scrollbar_rect.y1 + int(round(self.scrollbar_rect.h * self.DEFAULT_EDGE_CONTENT_SWIPE_END_RATIO))
        start_y = max(self.scrollbar_rect.y1 + 8, min(start_y, self.scrollbar_rect.y2 - 8))
        end_y = max(self.scrollbar_rect.y1 + 8, min(end_y, self.scrollbar_rect.y2 - 8))

        if direction == 'top':
            device.swipe(x, end_y, x, start_y, self.DEFAULT_EDGE_CONTENT_SWIPE_DURATION)
        else:
            device.swipe(x, start_y, x, end_y, self.DEFAULT_EDGE_CONTENT_SWIPE_DURATION)

        sleep(self.DEFAULT_EDGE_CONTENT_SWIPE_DELAY)
        refreshed = self.refresh()
        return refreshed if refreshed is not None else progress

    def _measured_progress_from_y1(self, thumb_y1: int) -> float | None:
        if not self.has_measured_bounds:
            return None
        top_y1, bottom_y1 = self._measured_bounds
        travel = max(bottom_y1 - top_y1, 1)
        return _clamp((thumb_y1 - top_y1) / travel, 0.0, 1.0)

    def _require_measured_bounds(self, method_name: str) -> None:
        if not self.has_measured_bounds:
            raise RuntimeError(
                f'{method_name}() requires measured bounds. '
                'Call measure_bounds() first or use to_top()/to_bottom() for auto measurement.'
            )

    @property
    def _measured_bounds(self) -> tuple[int, int]:
        self._require_measured_bounds('measured_bounds')
        top_y1 = self.measured_top_y1
        bottom_y1 = self.measured_bottom_y1
        assert top_y1 is not None
        assert bottom_y1 is not None
        return top_y1, bottom_y1

    def _seek_edge(
        self,
        direction: str,
        *,
        max_steps: int,
        step: float | None = None,
        settle_edge: bool = True,
    ) -> ScrollProgress | None:
        current = self.progress or self.refresh()
        if current is None:
            return None

        multiplier = self.DEFAULT_MEASUREMENT_STEP if step is None else step
        prev_y = current.thumb_rect.y1
        stall = 0
        last = current
        for _ in range(max_steps):
            if self._is_effectively_at_edge(last, direction):
                return self._maybe_settle_edge(last) if settle_edge else last
            last = self._step_by_multiplier(direction, multiplier)
            if last is None:
                return None
            y = last.thumb_rect.y1
            if abs(y - prev_y) <= self.DEFAULT_EDGE_STALL_DELTA:
                stall += 1
            else:
                stall = 0
            prev_y = y
            if stall >= self.DEFAULT_EDGE_STALL_REPEAT:
                return self._maybe_settle_edge(last) if settle_edge else last
        return self._maybe_settle_edge(last) if settle_edge else last

    def _step_by_multiplier(self, direction: str, multiplier: float) -> ScrollProgress | None:
        current = self.progress or self.refresh()
        if current is None:
            return None
        delta = current.visible_ratio * max(0.1, multiplier)
        baseline = current.progress if current.progress is not None else current.raw_progress
        if baseline is None:
            return None
        target = baseline - delta if direction == 'up' else baseline + delta
        duration: float | None = None
        drag_delay: float | None = None
        if multiplier >= self.DEFAULT_MEASUREMENT_STEP:
            drag_delay = self.DEFAULT_MEASUREMENT_DRAG_DELAY
            if target <= 0.0 or target >= 1.0:
                duration = self.drag_duration * self.DEFAULT_MEASUREMENT_EDGE_DRAG_BOOST
                return self._drag_beyond_edge(direction, duration=duration, drag_delay=drag_delay)
        return self._drag_to_progress(target=target, duration=duration, drag_delay=drag_delay)

    def _drag_beyond_edge(
        self,
        direction: str,
        *,
        duration: float | None = None,
        drag_delay: float | None = None,
    ) -> ScrollProgress | None:
        current = self.progress or self.refresh()
        if current is None:
            return None

        track = current.track_rect
        thumb = current.thumb_rect
        x = max(track.x1 + 1, thumb.x2 - 2)
        start_y = thumb.center[1]
        overdrag = self.DEFAULT_EDGE_OVERDRAG_DISTANCE
        if direction == 'up':
            end_y = track.y1 - overdrag
        else:
            end_y = track.y2 + overdrag

        base_duration = duration or self.drag_duration
        distance_ratio = abs(end_y - start_y) / max(track.h, 1)
        duration_scale = (1.0 + distance_ratio) * self.DEFAULT_EDGE_DRAG_DURATION_BOOST
        swipe_duration = base_duration * _clamp(duration_scale, 1.2, self.DEFAULT_DRAG_DURATION_SCALE_MAX)

        before_progress = current.progress if current.progress is not None else current.raw_progress
        updated = self._swipe_and_refresh(
            x,
            start_y,
            end_y,
            duration=swipe_duration,
            drag_delay=drag_delay,
        )
        if updated is None:
            return None
        if self._is_effectively_at_edge(updated, direction):
            return updated
        updated_progress = updated.progress if updated.progress is not None else updated.raw_progress
        if (
            updated_progress is not None
            and before_progress is not None
            and abs(updated_progress - before_progress) <= 0.01
        ):
            retry_duration = min(swipe_duration * 1.2, base_duration * self.DEFAULT_DRAG_DURATION_SCALE_MAX)
            updated = self._swipe_and_refresh(
                x,
                start_y,
                end_y,
                duration=retry_duration,
                drag_delay=drag_delay,
            )
        return updated

    def _is_effectively_at_edge(self, progress: ScrollProgress, direction: str) -> bool:
        if direction == 'up':
            if progress.is_top():
                return True
            return progress.raw_progress is not None and progress.raw_progress <= self.DEFAULT_PROGRESS_TOLERANCE
        if progress.is_bottom():
            return True
        return progress.raw_progress is not None and progress.raw_progress >= 1.0 - self.DEFAULT_PROGRESS_TOLERANCE

    def _resolve_target_center_y(self, track: Rect, thumb: Rect, target: float) -> int:
        if self.has_measured_bounds:
            top_y1, bottom_y1 = self._measured_bounds
            target_thumb_y1 = int(round(top_y1 + target * (bottom_y1 - top_y1)))
            min_center_y = top_y1 + thumb.h / 2
            max_center_y = bottom_y1 + thumb.h / 2
            return int(_clamp(target_thumb_y1 + thumb.h / 2, min_center_y, max_center_y))

        travel = max(track.h - thumb.h, 1)
        target_thumb_y1 = int(round(track.y1 + target * travel))
        return int(_clamp(target_thumb_y1 + thumb.h / 2, track.y1 + thumb.h / 2, track.y2 - thumb.h / 2))

    def _swipe_and_refresh(
        self,
        x: int,
        start_y: int,
        end_y: int,
        *,
        duration: float,
        drag_delay: float | None = None,
    ) -> ScrollProgress | None:
        wait_time = self.drag_delay if drag_delay is None else drag_delay
        device.swipe(x, start_y, x, end_y, duration)
        sleep(wait_time)
        return self.refresh()

    def _drag_to_progress(
        self,
        *,
        target: float,
        duration: float | None = None,
        drag_delay: float | None = None,
    ) -> ScrollProgress | None:
        current = self.progress or self.refresh()
        if current is None:
            return None

        target = _clamp(target, 0.0, 1.0)
        track = current.track_rect
        thumb = current.thumb_rect
        x = max(track.x1 + 1, thumb.x2 - 2)
        start_y = thumb.center[1]
        end_y = self._resolve_target_center_y(track, thumb, target)
        base_duration = duration or self.drag_duration
        distance_ratio = abs(end_y - start_y) / max(track.h, 1)
        duration_scale = 1.0 + distance_ratio
        if target <= self.DEFAULT_PROGRESS_TOLERANCE or target >= 1.0 - self.DEFAULT_PROGRESS_TOLERANCE:
            duration_scale *= self.DEFAULT_EDGE_DRAG_DURATION_BOOST
        swipe_duration = base_duration * _clamp(duration_scale, 1.0, self.DEFAULT_DRAG_DURATION_SCALE_MAX)

        before_progress = current.progress if current.progress is not None else current.raw_progress
        updated = self._swipe_and_refresh(
            x,
            start_y,
            end_y,
            duration=swipe_duration,
            drag_delay=drag_delay,
        )
        if updated is None:
            return None
        updated_progress = updated.progress if updated.progress is not None else updated.raw_progress
        if updated_progress is not None and abs(updated_progress - target) <= self.DEFAULT_PROGRESS_TOLERANCE:
            return updated
        if (
            updated_progress is not None
            and before_progress is not None
            and abs(updated_progress - before_progress) <= 0.01
        ):
            thumb = updated.thumb_rect
            track = updated.track_rect
            x = max(track.x1 + 1, thumb.x2 - 2)
            start_y = thumb.center[1]
            end_y = self._resolve_target_center_y(track, thumb, target)
            retry_distance_ratio = abs(end_y - start_y) / max(track.h, 1)
            retry_duration_scale = 1.4 + retry_distance_ratio
            if target <= self.DEFAULT_PROGRESS_TOLERANCE or target >= 1.0 - self.DEFAULT_PROGRESS_TOLERANCE:
                retry_duration_scale *= self.DEFAULT_EDGE_DRAG_DURATION_BOOST
            retry_duration = base_duration * _clamp(retry_duration_scale, 1.4, self.DEFAULT_DRAG_DURATION_SCALE_MAX)
            updated = self._swipe_and_refresh(
                x,
                start_y,
                end_y,
                duration=retry_duration,
                drag_delay=drag_delay,
            )
        return updated

    def _build_thumb_mask(self, roi: MatLike) -> MatLike:
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(
            hsv,
            np.array(self.THUMB_HSV_LOWER, dtype=np.uint8),
            np.array(self.THUMB_HSV_UPPER, dtype=np.uint8),
        )
        kernel = np.ones(self.DEFAULT_MORPHOLOGY_KERNEL, dtype=np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        return mask

    def _find_thumb(self, rough_rect: Rect, mask: MatLike) -> tuple[Rect | None, float]:
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        best_rect: Rect | None = None
        best_score = -1.0
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = float(cv2.contourArea(contour))
            if h < self.MIN_THUMB_HEIGHT:
                continue
            if self.MAX_THUMB_HEIGHT is not None and h > self.MAX_THUMB_HEIGHT:
                continue
            if w > self.DEFAULT_THUMB_MAX_WIDTH:
                continue
            if area < self.DEFAULT_THUMB_MIN_AREA:
                continue

            rect = Rect(rough_rect.x1 + x, rough_rect.y1 + y, w, h)
            score = area + (x + w) * 4 + h * 2
            if score > best_score:
                best_rect = rect
                best_score = score

        if best_rect is None:
            return None, 0.0

        max_possible = max(rough_rect.h * max(rough_rect.w, 1), 1)
        confidence = _clamp(best_score / max_possible, 0.0, 1.0)
        return best_rect, confidence

    def _refine_track_rect(self, rough_rect: Rect, thumb_rect: Rect) -> Rect:
        width = min(self.DEFAULT_TRACK_WIDTH, rough_rect.w)
        x2 = min(rough_rect.x2, max(thumb_rect.x2, rough_rect.x1 + width))
        x1 = max(rough_rect.x1, x2 - width)
        return Rect(x1, rough_rect.y1, max(1, x2 - x1), rough_rect.h)


if __name__ == '__main__':
    import json
    from pathlib import Path

    from kotonebot.backend.context.context import init_context, manual_context
    from kotonebot.client.host import Mumu12V5Host
    from kotonebot.client.host.mumu12_host import MuMu12HostConfig

    from iaa.config.base import IaaConfig

    def format_progress(progress: ScrollProgress | None) -> str:
        if progress is None:
            return 'progress=None'
        progress_text = 'None' if progress.progress is None else f'{progress.progress:.3f}'
        return (
            f'progress={progress_text}, '
            f'visible={progress.visible_ratio:.3f}, '
            f'confidence={progress.confidence:.3f}, '
            f'thumb={progress.thumb_rect.xyxy}'
        )

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

    scrollable = Scrollable(
        scrollbar_rect=(1247, 60, 8, 650),
        # drag_duration=0.35,
        # drag_delay=0.7,
    )

    print('Connected device screen size:', debug_device.screen_size)

    with manual_context('manual'):
        for index, current in enumerate(scrollable.walk_down(), start=1):
            print(f'[step {index}]', format_progress(current))
            if index >= 5:
                break
