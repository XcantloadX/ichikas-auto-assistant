from __future__ import annotations

from threading import Lock
from typing import Callable

import cv2
from PySide6.QtCore import QObject, Property, QTimer, Signal, Slot
from PySide6.QtGui import QImage
from PySide6.QtQuick import QQuickImageProvider

from iaa.i18n import translate

from ..models import DisplayMapping, map_canvas_to_image


class _ScrcpyImageProvider(QQuickImageProvider):
    def __init__(self) -> None:
        super().__init__(QQuickImageProvider.Image)
        self._image = QImage()
        self._lock = Lock()

    def update_image(self, image: QImage) -> None:
        with self._lock:
            self._image = image

    def requestImage(self, _id: str, size, requested_size):  # type: ignore[override]
        with self._lock:
            if self._image.isNull():
                image = QImage(2, 2, QImage.Format_RGB32)
                image.fill(0)
            else:
                image = self._image.copy()
        if size is not None:
            size.setWidth(image.width())
            size.setHeight(image.height())
        if requested_size.width() > 0 and requested_size.height() > 0:
            image = image.scaled(requested_size)
        return image


class ScrcpyController(QObject):
    frameChanged = Signal()
    activeChanged = Signal()
    visibleChanged = Signal()
    statusTextChanged = Signal()

    def __init__(
        self,
        scheduler,
        config_service,
        get_language: Callable[[], str],
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._scheduler = scheduler
        self._config_service = config_service
        self._get_language = get_language
        self._provider = _ScrcpyImageProvider()
        self._frame_token = 0
        self._status_text = ''
        self._waiting = True
        self._waiting_error: str | None = None
        self._visible = False
        self._active = False
        self._mapping: DisplayMapping | None = None
        self._touch_active = False
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(33)
        self._refresh_timer.timeout.connect(self._refresh_frame)
        self.refresh_status_text()

    def _tr(self, key: str, **kwargs: object) -> str:
        text = translate(self._get_language(), key)
        return text.format(**kwargs) if kwargs else text

    def refresh_status_text(self) -> None:
        if self._waiting:
            if self._waiting_error:
                self._status_text = self._tr('scrcpy.waiting_frame_error', error=self._waiting_error)
            else:
                self._status_text = self._tr('scrcpy.waiting_frame')
            self.statusTextChanged.emit()

    @property
    def image_provider(self) -> _ScrcpyImageProvider:
        return self._provider

    def _get_frame_token(self) -> int:
        return self._frame_token

    def _get_active(self) -> bool:
        return self._active

    def _get_visible(self) -> bool:
        return self._visible

    def _get_status_text(self) -> str:
        return self._status_text

    frameToken = Property(int, _get_frame_token, notify=frameChanged)
    active = Property(bool, _get_active, notify=activeChanged)
    visible = Property(bool, _get_visible, notify=visibleChanged)
    statusText = Property(str, _get_status_text, notify=statusTextChanged)

    def sync_visibility(self) -> None:
        scheduler = self._scheduler
        should_open = (
            self._config_service.conf.device.control_impl == 'scrcpy'
            and scheduler.device is not None
            and (scheduler.running or scheduler.is_starting or scheduler.is_stopping)
        )
        self.set_visible(should_open)

    def set_visible(self, visible: bool) -> None:
        if self._visible == visible:
            if visible and not self._refresh_timer.isActive():
                self._refresh_timer.start()
            return
        self._visible = visible
        self.visibleChanged.emit()
        if visible:
            self._active = True
            self.activeChanged.emit()
            self._refresh_timer.start()
        else:
            self._touch_active = False
            self._mapping = None
            self._waiting = True
            self._waiting_error = None
            self.refresh_status_text()
            self._refresh_timer.stop()

    def _refresh_frame(self) -> None:
        if not self._visible or self._scheduler.device is None:
            return
        try:
            frame = self._scheduler.device.screenshot()
            height, width = frame.shape[:2]
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            qimage = QImage(
                rgb.data,
                width,
                height,
                width * 3,
                QImage.Format_RGB888,
            ).copy()
            self._provider.update_image(qimage)
            self._frame_token += 1
            self.frameChanged.emit()
            self._waiting = False
            self._waiting_error = None
            self._status_text = f'{width}x{height}'
            self.statusTextChanged.emit()
        except Exception as exc:  # noqa: BLE001
            self._waiting = True
            self._waiting_error = str(exc)
            self.refresh_status_text()

    @Slot(int, int, int, int, int, int)
    def updateDisplayMetrics(
        self,
        view_width: int,
        view_height: int,
        image_width: int,
        image_height: int,
        painted_width: int,
        painted_height: int,
    ) -> None:
        offset_x = max(0, int((view_width - painted_width) / 2))
        offset_y = max(0, int((view_height - painted_height) / 2))
        self._mapping = DisplayMapping(
            offset_x=offset_x,
            offset_y=offset_y,
            display_width=max(1, painted_width),
            display_height=max(1, painted_height),
            image_width=max(1, image_width),
            image_height=max(1, image_height),
        )

    def _logic_to_physical(self, x: int, y: int) -> tuple[int, int]:
        if self._scheduler.device is None:
            raise RuntimeError('No device bound to scrcpy viewer')
        real_x, real_y = self._scheduler.device.scaler.logic_to_physical((x, y))
        return int(real_x), int(real_y)

    @Slot(int, int)
    def touchDown(self, x: int, y: int) -> None:
        if self._scheduler.device is None:
            return
        point = map_canvas_to_image(self._mapping, x, y)
        if point is None:
            return
        px, py = self._logic_to_physical(*point)
        self._scheduler.device.input.touch_driver.touch_down(px, py, contact_id=0)
        self._touch_active = True

    @Slot(int, int)
    def touchMove(self, x: int, y: int) -> None:
        if self._scheduler.device is None or not self._touch_active:
            return
        point = map_canvas_to_image(self._mapping, x, y)
        if point is None:
            return
        px, py = self._logic_to_physical(*point)
        self._scheduler.device.input.touch_driver.touch_move(px, py, contact_id=0)

    @Slot(int, int)
    def touchUp(self, x: int, y: int) -> None:
        if self._scheduler.device is None or not self._touch_active:
            return
        point = map_canvas_to_image(self._mapping, x, y)
        if point is None:
            self._touch_active = False
            return
        px, py = self._logic_to_physical(*point)
        self._scheduler.device.input.touch_driver.touch_up(px, py, contact_id=0)
        self._touch_active = False