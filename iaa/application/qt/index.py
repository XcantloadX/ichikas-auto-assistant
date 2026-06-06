# ruff: noqa: E402
import sys
from .controllers.log_bridge import LogBridge
log_bridge = LogBridge(None)
log_bridge.install()

import os
from pathlib import Path
from typing import cast

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QColor, QIcon, QPalette
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterSingletonType
from PySide6.QtQuick import QQuickWindow
from PySide6.QtWidgets import QApplication
from PySide6.QtQuickControls2 import QQuickStyle

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


def apply_color_scheme(app: QApplication, color_scheme: str) -> None:
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


def apply_theme_color(app: QApplication, color_value: str | None) -> None:
    if not color_value:
        # 清除自定义调色板覆盖，交由 Fluent/系统调色板驱动颜色。
        app.setPalette(QPalette())
        return

    color = QColor(color_value)
    if not color.isValid():
        return

    palette = QPalette(app.palette())
    palette.setColor(QPalette.ColorRole.Highlight, color)
    accent_role = getattr(QPalette.ColorRole, 'Accent', None)
    if accent_role is not None:
        palette.setColor(accent_role, color)
    app.setPalette(palette)


def main() -> None:
    os.environ.setdefault("QSG_RHI_BACKEND", "opengl")
    QQuickWindow.setDefaultAlphaBuffer(True)

    app = QApplication(sys.argv)
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
    # maxHoverBridge / tabBarBridge 平台条件可为 None，保留 context property
    engine.rootContext().setContextProperty('maxHoverBridge', max_hover_bridge)
    engine.rootContext().setContextProperty('tabBarBridge', tab_bar_bridge)

    root_path = Path(IaaService.app_root())
    icon_path = root_path / 'assets' / 'icon_round.ico'
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    qml_path = Path(__file__).resolve().parent / 'qml' / 'MainWindow.qml'
    engine.load(QUrl.fromLocalFile(str(qml_path)))
    if not engine.rootObjects():
        raise RuntimeError('Failed to load Qt desktop UI.')
    window = cast(QQuickWindow, engine.rootObjects()[0])
    hwnd = int(window.winId())

    if sys.platform == 'win32':
        setup_frameless_window(hwnd)
        _win_event_filter = WindowEventFilter(window, max_hover_bridge, tab_bar_bridge)
        app.installNativeEventFilter(_win_event_filter)

    def apply_interface_preferences() -> None:
        interface_conf = config_manager.read_shared().interface
        apply_color_scheme(app, interface_conf.color_scheme)
        apply_theme_color(app, interface_conf.theme_color)
        if sys.platform == 'win32':
            apply_window_style(hwnd, interface_conf.window_style)
        controller.refreshWindowStyle()

    controller.preferencesController.runtimeChanged.connect(apply_interface_preferences)
    apply_interface_preferences()

    exit_code = app.exec()
    controller.shutdown()
    raise SystemExit(exit_code)
