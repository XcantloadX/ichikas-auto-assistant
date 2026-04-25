from __future__ import annotations

import sys

from PySide6.QtCore import QObject, Property, Signal, Slot, QUrl, QCoreApplication
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QMessageBox

from iaa.application.service.iaa_service import IaaService
from iaa.application.service.config_service import DEFAULT_CONFIG_NAME
from iaa.config.manager import ConfigValidationError
from iaa.telemetry import setup as setup_telemetry

from .progress_bridge import ProgressBridge
from .profile_store_backend import ProfileStoreBackend
from .run_controller import RunController
from .scrcpy_controller import ScrcpyController
from .settings_controller import SettingsController
from .preferences_controller import PreferencesController


def _resolve_window_style(style: str) -> str:
    if style in ('mica', 'acrylic', 'blur', 'solid'):
        return style
    if sys.getwindowsversion().build >= 22000:
        return 'mica'
    return 'solid'


class AppController(QObject):
    notificationRaised = Signal(str, str)
    globalErrorChanged = Signal()
    telemetryConsentRequiredChanged = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        try:
            self.service = IaaService()
        except ConfigValidationError as e:
            from iaa.config import manager

            field_list = '\n'.join(f'  - {f}' for f in e.invalid_fields)
            msg = f"以下配置项校验失败：\n{field_list}\n\n错误详情：\n{e.error_details}\n\n是否重置这些为默认值？"

            reply = QMessageBox.question(
                None,
                "一歌小助手",
                msg,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                manager.fallback_invalid_fields(DEFAULT_CONFIG_NAME, e.invalid_fields)
                self.service = IaaService()
            else:
                QMessageBox.warning(
                    None,
                    "一歌小助手",
                    "配置校验失败，未重置。程序即将退出。",
                    QMessageBox.StandardButton.Ok
                )
                QCoreApplication.exit(1)
        
        self.progressBridge = ProgressBridge(self)
        self.scrcpyController = ScrcpyController(self.service.scheduler, self.service.config, self)
        self.runController = RunController(self.service, self.progressBridge, self.scrcpyController, self)
        self.settingsController = SettingsController(self.service, self)
        self.preferencesController = PreferencesController(self.service, self)
        self.profileStoreBackend = ProfileStoreBackend(self.settingsController, self)
        self._global_error = ''
        self._telemetry_consent_required = self.service.config.shared.telemetry.sentry is None
        setup_telemetry()

        self.runController.operationSucceeded.connect(lambda text: self.notificationRaised.emit('success', text))
        self.runController.operationFailed.connect(self.reportError)
        self.settingsController.operationSucceeded.connect(lambda text: self.notificationRaised.emit('success', text))
        self.settingsController.operationFailed.connect(self.reportError)
        self.settingsController.configSwitched.connect(self._on_config_switched)
        self.preferencesController.operationSucceeded.connect(lambda text: self.notificationRaised.emit('success', text))
        self.preferencesController.operationFailed.connect(self.reportError)
        self.service.scheduler.on_error = self._on_scheduler_error

    def _on_config_switched(self) -> None:
        self.runController.tasksChanged.emit()

    def _on_scheduler_error(self, exc: Exception) -> None:
        self.reportError(str(exc))

    def _get_version(self) -> str:
        return self.service.version

    def _get_window_title(self) -> str:
        return f'一歌小助手 v{self.service.version}'

    def _get_assets_root_path(self) -> str:
        return self.service.assets.assets_root_path.replace('\\', '/')

    def _get_global_error(self) -> str:
        return self._global_error

    def _get_telemetry_consent_required(self) -> bool:
        return self._telemetry_consent_required

    def _get_window_style(self) -> str:
        return _resolve_window_style(self.service.config.shared.interface.window_style)

    version = Property(str, _get_version, constant=True)
    windowTitle = Property(str, _get_window_title, constant=True)
    assetsRootPath = Property(str, _get_assets_root_path, constant=True)
    globalError = Property(str, _get_global_error, notify=globalErrorChanged)
    telemetryConsentRequired = Property(bool, _get_telemetry_consent_required, notify=telemetryConsentRequiredChanged)
    windowStyle = Property(str, _get_window_style, constant=True)

    @Slot(str)
    def openExternalUrl(self, url: str) -> None:
        QDesktopServices.openUrl(QUrl(url))

    @Slot(str)
    def reportError(self, message: str) -> None:
        self._global_error = message
        self.globalErrorChanged.emit()
        self.notificationRaised.emit('error', message)

    @Slot()
    def clearGlobalError(self) -> None:
        if not self._global_error:
            return
        self._global_error = ''
        self.globalErrorChanged.emit()

    @Slot(bool)
    def setTelemetryConsent(self, allowed: bool) -> None:
        self.service.config.shared.telemetry.sentry = allowed
        self.service.config.save_shared()
        self._telemetry_consent_required = False
        self.telemetryConsentRequiredChanged.emit()
        self.notificationRaised.emit('success', '数据收集设置将于下次启动时生效。')

    @Slot(result=bool)
    def confirmClose(self) -> bool:
        scheduler = self.service.scheduler
        if not scheduler.running:
            return True
        try:
            scheduler.stop(block=True)
        except Exception:
            pass
        return True

    @Slot()
    def shutdown(self) -> None:
        self.progressBridge.close()
        self.scrcpyController.set_visible(False)
