import os
import sys
import platform

from PySide6.QtCore import QObject, Property, Signal, Slot, QUrl
from PySide6.QtGui import QDesktopServices

from iaa.config import manager as config_manager
from iaa.application.service.iaa_service import IaaService
from iaa.telemetry import setup as setup_telemetry


from .log_bridge import LogBridge
from .scrcpy_image_provider import ScrcpyImageProvider
from .tab_manager import TabManager
from .preferences_controller import PreferencesController
from .help_controller import HelpController
from .global_hotkey_controller import GlobalHotkeyController


class AppController(QObject):
    notificationRaised = Signal(str, str)
    errorDialogRequested = Signal(str, str)    # title, message
    globalErrorChanged = Signal()
    telemetryConsentRequiredChanged = Signal()
    sentryEnabledChanged = Signal()
    screenshotEnabledChanged = Signal()
    staticsEnabledChanged = Signal()
    windowStyleChanged = Signal()
    pathWarningRequired = Signal(str)  # 路径问题警告

    def __init__(self, log_bridge: LogBridge) -> None:
        super().__init__(None)
        self.logBridge = log_bridge
        self.scrcpyImageProvider = ScrcpyImageProvider()

        self.tabManager = TabManager(self, image_provider=self.scrcpyImageProvider)

        self.preferencesController = PreferencesController(self)
        self.helpController = HelpController(self)
        self.globalHotkeyController = GlobalHotkeyController(
            self.tabManager,
            self.preferencesController,
            self,
        )

        self._global_error = ''
        telemetry_cfg = config_manager.read_shared().telemetry
        self._sentry_enabled = telemetry_cfg.sentry is True
        self._screenshot_enabled = telemetry_cfg.upload_screenshot is True
        self._statics_enabled = telemetry_cfg.statics is True
        self._telemetry_consent_required = (
            telemetry_cfg.sentry is None
            or telemetry_cfg.upload_screenshot is None
            or telemetry_cfg.statics is None
        )
        setup_telemetry()

        # 转发活跃 tab 的操作信号到 AppController
        self.tabManager.operationSucceeded.connect(lambda text: self.notificationRaised.emit('success', text))
        self.tabManager.operationFailed.connect(self.reportError)
        self.tabManager.errorDialogRequested.connect(self.errorDialogRequested)
        self.preferencesController.operationSucceeded.connect(lambda text: self.notificationRaised.emit('success', text))
        self.preferencesController.operationFailed.connect(self.reportError)

    def _get_version(self) -> str:
        return IaaService.app_version()

    def _get_window_title(self) -> str:
        if platform.system() == 'Windows':
            return '一歌小助手'
        elif platform.system() == 'Darwin':
            return '一歌小助手 (on macOS)'
        elif platform.system() == 'Linux':
            return '一歌小助手 (on Linux)'
        else:
            return '一歌小助手'

    def _get_assets_root_path(self) -> str:
        return os.path.join(IaaService.app_root(), 'assets').replace('\\', '/')

    def _get_global_error(self) -> str:
        return self._global_error

    def _get_telemetry_consent_required(self) -> bool:
        return self._telemetry_consent_required

    def _get_sentry_enabled(self) -> bool:
        return self._sentry_enabled

    def _get_screenshot_enabled(self) -> bool:
        return self._screenshot_enabled

    def _get_statics_enabled(self) -> bool:
        return self._statics_enabled

    def _get_window_style(self) -> str:
        style = config_manager.read_shared().interface.window_style
        if platform.system() != 'Windows':
            return 'solid'

        if style in ('mica', 'acrylic', 'blur', 'solid'):
            return style
        if sys.getwindowsversion().build >= 22000:
            return 'mica'
        return 'solid'

    def _get_startup_page(self) -> str:
        return config_manager.read_shared().interface.startup_page

    version = Property(str, _get_version, constant=True)
    windowTitle = Property(str, _get_window_title, constant=True)
    assetsRootPath = Property(str, _get_assets_root_path, constant=True)
    globalError = Property(str, _get_global_error, notify=globalErrorChanged)
    telemetryConsentRequired = Property(bool, _get_telemetry_consent_required, notify=telemetryConsentRequiredChanged)
    sentryEnabled = Property(bool, _get_sentry_enabled, notify=sentryEnabledChanged)
    screenshotEnabled = Property(bool, _get_screenshot_enabled, notify=screenshotEnabledChanged)
    staticsEnabled = Property(bool, _get_statics_enabled, notify=staticsEnabledChanged)
    windowStyle = Property(str, _get_window_style, notify=windowStyleChanged)
    startupPage = Property(str, _get_startup_page, constant=True)

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

    @Slot(bool, bool, bool)
    def setTelemetryConsent(self, sentry: bool, screenshot: bool, statics: bool) -> None:
        """写入用户对三个开关的选择，并清除"待同意"状态。

        :param sentry: True 允许匿名错误上报。
        :param screenshot: True 允许错误上报时附带截图。
        :param statics: True 允许匿名收集统计数据。
        """
        from iaa.telemetry import set_consent  # noqa: PLC0415
        set_consent(bool(sentry), bool(screenshot), bool(statics))
        self._sentry_enabled = bool(sentry)
        self._screenshot_enabled = bool(screenshot)
        self._statics_enabled = bool(statics)
        self._telemetry_consent_required = False
        self.sentryEnabledChanged.emit()
        self.screenshotEnabledChanged.emit()
        self.staticsEnabledChanged.emit()
        self.telemetryConsentRequiredChanged.emit()
        self.notificationRaised.emit('success', '数据收集设置将于下次启动时生效。')

    @Slot()
    def refreshWindowStyle(self) -> None:
        self.windowStyleChanged.emit()

    @Slot(result=bool)
    def checkPathIssues(self) -> bool:
        """检查程序路径或工作目录是否存在问题。

        :return: 如果程序路径或工作目录包含 ``Program Files`` 或 ``OneDrive``，返回 True。
        """
        app_root = IaaService.app_root().lower()
        cwd = os.getcwd().lower()

        for path in (app_root, cwd):
            if 'program files' in path or 'onedrive' in path:
                return True

        return False

    @Slot(result=bool)
    def confirmClose(self) -> bool:
        for entry in self.tabManager._tabs:
            if entry.scheduler.running:
                try:
                    entry.scheduler.stop(block=True)
                except Exception:
                    pass
        return True

    @Slot(result=str)
    def checkMigrationMessages(self) -> str:
        from iaa.config.migration import get_deferred_messages
        messages = get_deferred_messages()
        if not messages:
            return ''

        version = self._get_version()
        html = [f'<b>配置文件已升级到 v{version}。</b>']
        html.append('<ol>')
        for msg in messages:
            if msg.old_version and msg.new_version:
                html.append(f'<li>v{msg.old_version} → v{msg.new_version}：{msg.text}</li>')
            else:
                html.append(f'<li>{msg.text}</li>')
        html.append('</ol>')

        return ''.join(html)

    @Slot()
    def shutdown(self) -> None:
        self.tabManager.shutdown_device_sessions()
        self.globalHotkeyController.shutdown()
        self.logBridge.close()
