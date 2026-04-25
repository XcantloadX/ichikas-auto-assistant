import os
import sys
import ctypes
from pathlib import Path
from ctypes import wintypes
from typing import cast

from PySide6.QtCore import QUrl
from PySide6.QtGui import QFont, QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow
from PySide6.QtWidgets import QApplication
from PySide6.QtQuickControls2 import QQuickStyle

from .controllers import AppController

DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_SYSTEMBACKDROP_TYPE = 38

# 常见值：
# 1 = None
# 2 = MainWindow (Mica)
# 3 = TransientWindow (Acrylic-like)
# 4 = TabbedWindow
DWM_SYSTEMBACKDROP_MAINWINDOW = 2

def enable_mica(hwnd: int) -> int:
    dwmapi = ctypes.windll.dwmapi

    value = ctypes.c_int(DWM_SYSTEMBACKDROP_MAINWINDOW)
    return dwmapi.DwmSetWindowAttribute(
        wintypes.HWND(hwnd),
        ctypes.c_uint(DWMWA_SYSTEMBACKDROP_TYPE),
        ctypes.byref(value),
        ctypes.sizeof(value)
    )

def main() -> None:
    # Keep Fluent controls while making transparent + Mica rendering stable on resize/maximize.
    os.environ.setdefault("QSG_RHI_BACKEND", "opengl")
    QQuickWindow.setDefaultAlphaBuffer(True)

    app = QApplication(sys.argv)
    QQuickStyle.setStyle("FluentWinUI3")
    app.setFont(QFont("Microsoft YaHei UI"))
    controller = AppController()
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty('appController', controller)
    engine.rootContext().setContextProperty('runController', controller.runController)
    engine.rootContext().setContextProperty('settingsController', controller.settingsController)
    engine.rootContext().setContextProperty('preferencesController', controller.preferencesController)
    engine.rootContext().setContextProperty('profileStoreBackend', controller.profileStoreBackend)
    engine.rootContext().setContextProperty('progressBridge', controller.progressBridge)
    engine.rootContext().setContextProperty('scrcpyController', controller.scrcpyController)
    engine.addImageProvider('scrcpy', controller.scrcpyController.image_provider)

    icon_path = Path(controller.service.root) / 'assets' / 'icon_round.ico'
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    qml_path = Path(__file__).resolve().parent / 'qml' / 'MainWindow.qml'
    engine.load(QUrl.fromLocalFile(str(qml_path)))
    if not engine.rootObjects():
        raise RuntimeError('Failed to load Qt desktop UI.')
    window = cast(QQuickWindow, engine.rootObjects()[0])
    hwnd = int(window.winId())
    enable_mica(hwnd)
    exit_code = app.exec()
    controller.shutdown()
    raise SystemExit(exit_code)
