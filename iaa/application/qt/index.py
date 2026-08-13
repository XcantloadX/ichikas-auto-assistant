# ruff: noqa: E402
import sys
from .controllers.log_bridge import LogBridge
log_bridge = LogBridge(None)
log_bridge.install()

import os
from pathlib import Path
from typing import cast

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QColor, QGuiApplication, QIcon, QPalette
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterSingletonType
from PySide6.QtQuick import QQuickWindow
from PySide6.QtQuickControls2 import QQuickStyle

from iaa.platform import env
from iaa.config import manager as config_manager
from iaa.application.service.iaa_service import IaaService
from .controllers import (
    AppController,
    HelpController,
    PreferencesController,
    ProfileStoreBackend,
)
from .controllers.tab_manager import TabManager

if sys.platform == 'win32':
    from .platform_win32 import (
        _MaxHoverBridge,
        TabBarHitTestBridge,
        WindowEventFilter,
        apply_window_style,
        setup_frameless_window,
    )


def _create_app() -> QGuiApplication:
    """按平台创建 Qt 应用实例。

    桌面的无边框窗口/原生事件过滤依赖 ``QtWidgets.QApplication``,保持
    ``QApplication``;Android 的 PySide6 环境不提供 ``QtWidgets``（QML 下
    仅 ``QGuiApplication`` 可用）,只能使用 ``QGuiApplication``。

    :return: 已创建的 Qt 应用实例。
    """
    if env.IS_ANDROID:
        return QGuiApplication(sys.argv)
    from PySide6.QtWidgets import QApplication
    return QApplication(sys.argv)


def _resolve_qml_path() -> Path:
    """解析 MainWindow.qml 的绝对路径（供 ``QUrl.fromLocalFile`` 使用）。

    桌面保持基于 ``__file__`` 的既有推导;Android 上源码随包打进 p4a 私有
    根目录（``env.app_root()``）,按包相对布局 ``iaa/application/qt/qml`` 定位
    （qml 目录原样进包,qmldir 相对 import 语义不变）。

    :return: MainWindow.qml 的绝对路径。
    """
    if env.IS_ANDROID:
        return Path(env.app_root()) / 'iaa' / 'application' / 'qt' / 'qml' / 'MainWindow.qml'
    return Path(__file__).resolve().parent / 'qml' / 'MainWindow.qml'


def apply_color_scheme(app: QGuiApplication, color_scheme: str) -> None:
    if color_scheme not in ('auto', 'light', 'dark'):
        return

    style_hints = app.styleHints()
    unset_color_scheme = getattr(style_hints, 'unsetColorScheme', None)
    set_color_scheme = getattr(style_hints, 'setColorScheme', None)
    if not callable(set_color_scheme) and not callable(unset_color_scheme):
        return

    if color_scheme == 'auto':
        if callable(unset_color_scheme):
            unset_color_scheme()
        elif callable(set_color_scheme):
            set_color_scheme(Qt.ColorScheme.Unknown)
    elif color_scheme == 'light':
        if callable(set_color_scheme):
            set_color_scheme(Qt.ColorScheme.Light)
    else:
        if callable(set_color_scheme):
            set_color_scheme(Qt.ColorScheme.Dark)


def apply_theme_color(app: QGuiApplication, color_value: str | None) -> None:
    palette = QPalette()
    if color_value:
        color = QColor(color_value)
        if color.isValid():
            palette.setColor(QPalette.ColorRole.Highlight, color)
            accent_role = getattr(QPalette.ColorRole, 'Accent', None)
            if accent_role is not None:
                palette.setColor(accent_role, color)
    app.setPalette(palette)


def main() -> None:
    if not env.IS_ANDROID:
        # QSG_RHI_BACKEND 是桌面 QML 渲染调优点;Android 由 Qt/p4a 按设备自动选择
        os.environ.setdefault("QSG_RHI_BACKEND", "opengl")
    QQuickWindow.setDefaultAlphaBuffer(True)

    app = _create_app()
    QQuickStyle.setStyle("FluentWinUI3")

    controller = AppController(log_bridge=log_bridge)

    interface = config_manager.read_shared().interface
    apply_color_scheme(app, interface.color_scheme)

    profileStoreBackend = ProfileStoreBackend(controller.tabManager, controller)

    max_hover_bridge = _MaxHoverBridge() if sys.platform == 'win32' else None
    tab_bar_bridge = TabBarHitTestBridge() if sys.platform == 'win32' else None

    # PySide6 stub 把 qml_name 标注为 bytes，但运行时实际接受 str，故忽略类型错误
    _URI, _VER = "IaaApp", (1, 0)
    qmlRegisterSingletonType(AppController,        _URI, *_VER, "AppController",        lambda _: controller)           # type: ignore[arg-type]
    qmlRegisterSingletonType(TabManager,           _URI, *_VER, "TabManager",           lambda _: controller.tabManager)  # type: ignore[arg-type]
    qmlRegisterSingletonType(ProfileStoreBackend,  _URI, *_VER, "ProfileStoreBackend",  lambda _: profileStoreBackend)    # type: ignore[arg-type]
    qmlRegisterSingletonType(PreferencesController,_URI, *_VER, "PreferencesController",lambda _: controller.preferencesController)  # type: ignore[arg-type]
    qmlRegisterSingletonType(HelpController,       _URI, *_VER, "HelpController",       lambda _: controller.helpController)  # type: ignore[arg-type]

    engine = QQmlApplicationEngine()
    engine.addImageProvider('scrcpy', controller.scrcpyImageProvider)
    # maxHoverBridge / tabBarBridge 平台条件可为 None，保留 context property
    engine.rootContext().setContextProperty('maxHoverBridge', max_hover_bridge)
    engine.rootContext().setContextProperty('tabBarBridge', tab_bar_bridge)

    root_path = Path(IaaService.app_root())
    icon_path = root_path / 'assets' / 'ichika.ico'
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    qml_path = _resolve_qml_path()
    engine.load(QUrl.fromLocalFile(str(qml_path)))
    if not engine.rootObjects():
        raise RuntimeError('Failed to load Qt desktop UI.')
    window = cast(QQuickWindow, engine.rootObjects()[0])
    hwnd = int(window.winId())

    if sys.platform == 'win32':
        setup_frameless_window(hwnd)
        _win_event_filter = WindowEventFilter(window, max_hover_bridge, tab_bar_bridge)
        app.installNativeEventFilter(_win_event_filter)

    _startup_iface = config_manager.read_shared().interface
    _startup_color_scheme = _startup_iface.color_scheme
    _startup_theme_color = _startup_iface.theme_color

    def apply_interface_preferences() -> None:
        interface_conf = config_manager.read_shared().interface
        apply_color_scheme(app, interface_conf.color_scheme)
        apply_theme_color(app, interface_conf.theme_color)
        if sys.platform == 'win32':
            apply_window_style(hwnd, interface_conf.window_style)
        controller.refreshWindowStyle()

    def apply_runtime_preferences() -> None:
        interface_conf = config_manager.read_shared().interface
        if sys.platform == 'win32':
            apply_window_style(hwnd, interface_conf.window_style)
        controller.refreshWindowStyle()
        if (interface_conf.color_scheme != _startup_color_scheme
                or interface_conf.theme_color != _startup_theme_color):
            controller.notificationRaised.emit('info', '配色方案将在重启后生效。')

    controller.preferencesController.runtimeChanged.connect(apply_runtime_preferences)
    apply_interface_preferences()

    exit_code = app.exec()
    controller.shutdown()
    raise SystemExit(exit_code)


def android_main() -> None:
    """Android 专用入口。

    平台分支已在 :func:`main` 内按 ``env.IS_ANDROID`` 处理,这里只是语义更
    明确的别名,供 p4a 的 ``main.py`` 直接调用::

        from iaa.application.qt.index import android_main
        android_main()
    """
    main()
