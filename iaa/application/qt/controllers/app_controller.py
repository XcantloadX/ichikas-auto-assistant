import os
import shutil
import sys
import platform
from importlib import resources

from PySide6.QtCore import QObject, Property, Signal, Slot, QUrl
from PySide6.QtGui import QDesktopServices

from iaa.platform import env
from iaa.config import manager as config_manager
from iaa.application.service.iaa_service import IaaService
from iaa.telemetry import setup as setup_telemetry


from .log_bridge import LogBridge
from .scrcpy_image_provider import ScrcpyImageProvider
from .tab_manager import TabManager
from .preferences_controller import PreferencesController
from .help_controller import HelpController
from .global_hotkey_controller import GlobalHotkeyController


# FontLoader/Image.source 需要文件系统真实路径（file://）。Android 端这组资源
# 的候选落点,按优先级排序。
_ANDROID_FONT_CONFIG = ('fonts', 'FluentSystemIcons-Regular.ttf')


def _android_assets_candidates() -> list[str]:
    """返回 Android 上可能的 assets 资源落点,按优先级排序。

    :return: 候选 assets 根目录绝对路径列表。
    """
    candidates: list[str] = [os.path.join(env.app_root(), 'assets')]
    for package in ('iaa', 'iaa.res'):
        try:
            candidates.append(str(resources.files(package) / 'assets'))
        except Exception:
            # 包不存在或无法解析时跳过
            continue
    return candidates


def _ensure_android_assets_dir() -> str:
    """确保 Android 上存在可写的 assets 目录并返回它。

    Android 没有独立的 assets 目录（``env.asset_dir()`` 抛 NotImplementedError）,
    QML 的 FontLoader 又需要真实文件路径,因此把打包携带的字体等资源复制到
    ``env.data_dir()/assets``。若所有候选源都未命中,仍返回（可能为空的）
    目录,避免 QML 侧拼接 ``file://`` 路径时崩溃。

    :return: 可写 assets 根目录绝对路径。
    """
    fonts_dir = os.path.join(*_ANDROID_FONT_CONFIG)
    target = os.path.join(env.data_dir(), 'assets')
    if os.path.isfile(os.path.join(target, fonts_dir)):
        return target
    os.makedirs(target, exist_ok=True)
    for candidate in _android_assets_candidates():
        src = os.path.join(candidate, fonts_dir)
        if os.path.isfile(src):
            os.makedirs(os.path.dirname(os.path.join(target, fonts_dir)), exist_ok=True)
            shutil.copyfile(src, os.path.join(target, fonts_dir))
            break
    return target


def _resolve_assets_root() -> str:
    """解析暴露给 QML 的 assets 根目录（QML 侧自行拼接 ``file://`` 前缀）。

    :return: assets 根目录绝对路径。
    """
    if env.IS_ANDROID:
        return _ensure_android_assets_dir()
    return os.path.join(IaaService.app_root(), 'assets')


class AppController(QObject):
    notificationRaised = Signal(str, str)
    errorDialogRequested = Signal(str, str)    # title, message
    globalErrorChanged = Signal()
    telemetryConsentRequiredChanged = Signal()
    windowStyleChanged = Signal()

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
        self._telemetry_consent_required = config_manager.read_shared().telemetry.sentry is None
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
        # Android(p4a) 下 platform.system() 仍返回 'Linux',须先用平台感知判定
        if env.IS_ANDROID:
            return '一歌小助手 (Android)'
        if platform.system() == 'Windows':
            return '一歌小助手'
        elif platform.system() == 'Darwin':
            return '一歌小助手 (on macOS)'
        elif platform.system() == 'Linux':
            return '一歌小助手 (on Linux)'
        else:
            return '一歌小助手'

    def _get_assets_root_path(self) -> str:
        return _resolve_assets_root().replace('\\', '/')

    def _get_global_error(self) -> str:
        return self._global_error

    def _get_telemetry_consent_required(self) -> bool:
        return self._telemetry_consent_required

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

    @Slot(bool)
    def setTelemetryConsent(self, allowed: bool) -> None:
        self.preferencesController.setValue('telemetry.sentry', allowed)
        self.preferencesController.save()
        self._telemetry_consent_required = False
        self.telemetryConsentRequiredChanged.emit()
        self.notificationRaised.emit('success', '数据收集设置将于下次启动时生效。')

    @Slot()
    def refreshWindowStyle(self) -> None:
        self.windowStyleChanged.emit()

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
