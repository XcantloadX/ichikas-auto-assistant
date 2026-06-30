from __future__ import annotations

import logging
import queue
import threading
import time
from typing import TYPE_CHECKING, Any

import cv2
from PySide6.QtCore import (
    QObject,
    Property,
    QTimer,
    Signal,
    Slot,
    QMetaObject,
    Qt,
    Q_ARG,
)
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

from iaa.application.qt.models import DisplayMapping, map_canvas_to_image
from iaa.application.service.device_factory import DeviceFactory

from .scrcpy_image_provider import ScrcpyImageProvider

if TYPE_CHECKING:
    from kotonebot.client.device import Device

logger = logging.getLogger(__name__)


class _WorkerTask:
    __slots__ = ('done', 'error')

    def __init__(self) -> None:
        self.done = threading.Event()
        self.error: BaseException | None = None


class VirtualDeviceSession(QObject):
    frameChanged = Signal()
    deviceStateChanged = Signal()
    statusTextChanged = Signal()

    def __init__(
        self,
        config_name: str,
        config_service: Any,
        image_provider: ScrcpyImageProvider,
        *,
        device_factory: DeviceFactory,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._config_name = config_name
        self._config_service = config_service
        self._device_factory = device_factory
        self._provider = image_provider
        self._device: Device | None = None
        self._device_lock = threading.Lock()
        self._device_running = False
        self._frame_token = 0
        self._status_text = '设备未启动'
        self._view_visible = False
        self._mapping: DisplayMapping | None = None
        self._touch_active = False
        self._shutdown = False
        self._queue: queue.Queue[tuple[str, _WorkerTask | None]] = queue.Queue()
        self._worker = threading.Thread(
            target=self._worker_loop, name=f'VDSession-{config_name}', daemon=True
        )
        self._worker.start()
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(33)
        self._refresh_timer.timeout.connect(self._refresh_frame)

    @property
    def image_key(self) -> str:
        return self._config_name

    def _get_frame_token(self) -> int:
        return self._frame_token

    def _get_device_running(self) -> bool:
        return self._device_running

    def _get_status_text(self) -> str:
        return self._status_text

    frameToken = Property(int, _get_frame_token, notify=frameChanged)
    deviceRunning = Property(bool, _get_device_running, notify=deviceStateChanged)
    statusText = Property(str, _get_status_text, notify=statusTextChanged)

    def _get_image_key(self) -> str:
        return self._config_name

    imageKey = Property(str, _get_image_key, constant=True)

    def is_device_running(self) -> bool:
        return self._device_running

    def _get_device(self) -> Device | None:
        with self._device_lock:
            return self._device

    @Slot(str)
    def _apply_status_text(self, text: str) -> None:
        if self._status_text == text:
            return
        self._status_text = text
        self.statusTextChanged.emit()

    def _notify_status_text(self, text: str) -> None:
        QMetaObject.invokeMethod(
            self,
            '_apply_status_text',
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(str, text),
        )

    @Slot(bool)
    def _apply_device_running(self, running: bool) -> None:
        if self._device_running == running:
            self._sync_refresh_timer()
            return
        self._device_running = running
        self.deviceStateChanged.emit()
        if not running:
            self._touch_active = False
            self._mapping = None
            self._apply_status_text('设备未启动')
            self._provider.remove_image(self._config_name)
            self._frame_token += 1
            self.frameChanged.emit()
        self._sync_refresh_timer()

    def _notify_device_running(self, running: bool) -> None:
        QMetaObject.invokeMethod(
            self,
            '_apply_device_running',
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(bool, running),
        )

    @Slot()
    def _sync_refresh_timer(self) -> None:
        if self._device_running and self._view_visible and self._has_application():
            if not self._refresh_timer.isActive():
                self._refresh_timer.start()
        elif self._refresh_timer.isActive():
            self._refresh_timer.stop()

    def _has_application(self) -> bool:
        return QApplication.instance() is not None

    def _worker_loop(self) -> None:
        while not self._shutdown:
            try:
                command, task = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue
            try:
                if command == 'start':
                    self._worker_start()
                elif command == 'stop':
                    self._worker_stop()
                elif command == 'shutdown':
                    self._worker_stop()
                    self._shutdown = True
            except BaseException as exc:  # noqa: BLE001
                if task is not None:
                    task.error = exc
                else:
                    logger.exception(
                        'Virtual device session worker failed: %s', command
                    )
                    QMetaObject.invokeMethod(
                        self,
                        '_report_start_error',
                        Qt.ConnectionType.QueuedConnection,
                        Q_ARG(str, str(exc)),
                    )
            finally:
                if task is not None:
                    task.done.set()

    def _worker_start(self) -> None:
        if self._device is not None and self._device_running:
            return
        device_conf = self._config_service.conf.device
        game_server = self._config_service.conf.game.server
        device = self._device_factory.create_scrcpy_preview_device(
            device_conf, game_server
        )
        device.orientation = 'landscape'
        device.start()
        with self._device_lock:
            self._device = device
        self._notify_device_running(True)
        self._notify_status_text('设备已启动')

    def _worker_stop(self) -> None:
        with self._device_lock:
            device = self._device
            self._device = None
        self._notify_device_running(False)
        if device is not None:
            try:
                device.stop()
            except Exception:
                logger.exception('Failed to stop UI device for %s', self._config_name)
    def _wait_for_worker_task(
        self, task: _WorkerTask, *, timeout: float = 30.0
    ) -> None:
        deadline = time.monotonic() + timeout
        app = QApplication.instance()
        on_main_thread = (
            app is not None and threading.current_thread() is threading.main_thread()
        )
        while not task.done.is_set():
            if time.monotonic() > deadline:
                raise TimeoutError(
                    f'Virtual device session command timed out after {timeout}s'
                )
            if on_main_thread:
                app.processEvents()  # type: ignore[union-attr]
                task.done.wait(timeout=0.01)
            else:
                task.done.wait(timeout=max(0.0, deadline - time.monotonic()))
        if on_main_thread:
            app.processEvents()  # type: ignore[union-attr]
        if task.error is not None:
            raise task.error

    def _submit(self, command: str, *, wait: bool) -> None:
        task = _WorkerTask() if wait else None
        self._queue.put((command, task))
        if task is not None:
            self._wait_for_worker_task(task)

    @Slot(str)
    def _report_start_error(self, message: str) -> None:
        self._apply_status_text(f'启动失败: {message}')

    @Slot()
    def start_device(self) -> None:
        if self._device_running:
            return
        self._submit('start', wait=False)

    @Slot()
    def stop_device(self) -> None:
        if not self._device_running:
            return
        self._submit('stop', wait=False)

    def ensure_started(self) -> None:
        self._submit('start', wait=True)

    @Slot(bool)
    def setViewVisible(self, visible: bool) -> None:
        self._view_visible = visible
        self._sync_refresh_timer()

    def shutdown(self) -> None:
        if self._refresh_timer.isActive():
            self._refresh_timer.stop()
        self._submit('shutdown', wait=True)

    def _refresh_frame(self) -> None:
        if not self._view_visible or not self._device_running:
            return
        device = self._get_device()
        if device is None:
            return
        try:
            frame = device.screenshot()
            height, width = frame.shape[:2]
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            qimage = QImage(
                rgb.data,
                width,
                height,
                width * 3,
                QImage.Format_RGB888,
            ).copy()
            self._provider.update_image(self._config_name, qimage)
            self._frame_token += 1
            self.frameChanged.emit()
        except Exception as exc:  # noqa: BLE001
            self._apply_status_text(f'等待画面... {exc}')

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
        device = self._get_device()
        if device is None:
            raise RuntimeError('No device bound to virtual device session')
        real_x, real_y = device.scaler.logic_to_physical((x, y))
        return int(real_x), int(real_y)

    @Slot(int, int)
    def touchDown(self, x: int, y: int) -> None:
        device = self._get_device()
        if device is None:
            return
        point = map_canvas_to_image(self._mapping, x, y)
        if point is None:
            return
        px, py = self._logic_to_physical(*point)
        device.input.touch_driver.touch_down(px, py, contact_id=0)
        self._touch_active = True

    @Slot(int, int)
    def touchMove(self, x: int, y: int) -> None:
        if not self._touch_active or self._get_device() is None:
            return
        device = self._get_device()
        assert device is not None
        point = map_canvas_to_image(self._mapping, x, y)
        if point is None:
            return
        px, py = self._logic_to_physical(*point)
        device.input.touch_driver.touch_move(px, py, contact_id=0)

    @Slot(int, int)
    def touchUp(self, x: int, y: int) -> None:
        device = self._get_device()
        if device is None or not self._touch_active:
            return
        point = map_canvas_to_image(self._mapping, x, y)
        if point is None:
            self._touch_active = False
            return
        px, py = self._logic_to_physical(*point)
        device.input.touch_driver.touch_up(px, py, contact_id=0)
        self._touch_active = False
