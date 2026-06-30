import threading
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from PySide6.QtWidgets import QApplication

from iaa.application.qt.controllers.scrcpy_image_provider import ScrcpyImageProvider
from iaa.application.qt.controllers.virtual_device_session import VirtualDeviceSession
from iaa.application.service.device_factory import DeviceFactory


class VirtualDeviceSessionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def _make_session(self) -> VirtualDeviceSession:
        config_service = SimpleNamespace(
            conf=SimpleNamespace(
                device=SimpleNamespace(control_impl='scrcpy', scrcpy_virtual_display=True),
                game=SimpleNamespace(server='jp'),
            )
        )
        device_factory = DeviceFactory(config_service)
        return VirtualDeviceSession(
            'test-config',
            config_service,
            ScrcpyImageProvider(),
            device_factory=device_factory,
        )

    def test_ensure_started_is_idempotent(self) -> None:
        session = self._make_session()
        fake_device = MagicMock()
        start_threads: list[int] = []

        def fake_worker_start() -> None:
            start_threads.append(threading.get_ident())
            with session._device_lock:
                session._device = fake_device
            session._notify_device_running(True)

        try:
            with patch.object(session, '_worker_start', side_effect=fake_worker_start):
                session.ensure_started()
                session.ensure_started()
                self.assertTrue(session.is_device_running())
                self.assertEqual(len(start_threads), 2)
        finally:
            session.shutdown()

    def test_start_and_stop_toggle_state(self) -> None:
        session = self._make_session()
        fake_device = MagicMock()

        def fake_worker_start() -> None:
            with session._device_lock:
                session._device = fake_device
            session._notify_device_running(True)

        def fake_worker_stop() -> None:
            with session._device_lock:
                session._device = None
            session._notify_device_running(False)

        try:
            with (
                patch.object(session, '_worker_start', side_effect=fake_worker_start),
                patch.object(session, '_worker_stop', side_effect=fake_worker_stop),
            ):
                session.ensure_started()
                self.assertTrue(session.is_device_running())
                session._submit('stop', wait=True)
                self.assertFalse(session.is_device_running())
        finally:
            session.shutdown()

    def test_start_stop_run_on_same_worker_thread(self) -> None:
        session = self._make_session()
        worker_thread_ids: list[int] = []
        fake_device = MagicMock()
        def recording_start() -> None:
            worker_thread_ids.append(threading.get_ident())
            with session._device_lock:
                session._device = fake_device
            session._notify_device_running(True)

        def recording_stop() -> None:
            worker_thread_ids.append(threading.get_ident())
            with session._device_lock:
                session._device = None
            session._notify_device_running(False)

        try:
            with (
                patch.object(
                    session._device_factory,
                    'create_scrcpy_preview_device',
                    return_value=fake_device,
                ),
                patch.object(session, '_worker_start', side_effect=recording_start),
                patch.object(session, '_worker_stop', side_effect=recording_stop),
            ):
                session.ensure_started()
                session._submit('stop', wait=True)
        finally:
            session.shutdown()

        self.assertEqual(len(worker_thread_ids), 2)
        self.assertEqual(worker_thread_ids[0], worker_thread_ids[1])
        self.assertNotEqual(worker_thread_ids[0], threading.get_ident())


if __name__ == '__main__':
    unittest.main()