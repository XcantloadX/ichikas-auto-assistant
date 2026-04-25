import ctypes
import os
import sys
from ctypes import wintypes
from pathlib import Path
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

WNDCA_ACCENT_POLICY = 19

ACCENT_DISABLED = 0
ACCENT_ENABLE_BLURBEHIND = 3
ACCENT_ENABLE_ACRYLICBLURBEHIND = 4


class ACCENT_POLICY(ctypes.Structure):
    _fields_ = [
        ("AccentState", ctypes.c_uint),
        ("AccentFlags", ctypes.c_uint),
        ("GradientColor", ctypes.c_uint),
        ("AnimationId", ctypes.c_uint),
    ]


class WINDOWCOMPOSITIONATTRIBDATA(ctypes.Structure):
    _fields_ = [
        ("Attrib", ctypes.c_uint),
        ("pvData", ctypes.c_void_p),
        ("cbData", ctypes.c_size_t),
    ]


def is_windows_11() -> bool:
    return sys.getwindowsversion().build >= 22000


def is_windows_10_1803() -> bool:
    return sys.getwindowsversion().build >= 17134


def enable_mica(hwnd: int) -> int:
    dwmapi = ctypes.windll.dwmapi

    value = ctypes.c_int(DWM_SYSTEMBACKDROP_MAINWINDOW)
    return dwmapi.DwmSetWindowAttribute(
        wintypes.HWND(hwnd),
        ctypes.c_uint(DWMWA_SYSTEMBACKDROP_TYPE),
        ctypes.byref(value),
        ctypes.sizeof(value)
    )


def enable_blur(hwnd: int) -> int:
    user32 = ctypes.windll.user32
    set_window_composition = user32.SetWindowCompositionAttribute
    set_window_composition.argtypes = [wintypes.HWND, ctypes.POINTER(WINDOWCOMPOSITIONATTRIBDATA)]
    set_window_composition.restype = ctypes.c_bool

    accent = ACCENT_POLICY(ACCENT_ENABLE_BLURBEHIND, 0, 0, 0)
    data = WINDOWCOMPOSITIONATTRIBDATA(WNDCA_ACCENT_POLICY, ctypes.addressof(accent), ctypes.sizeof(accent))

    return 0 if set_window_composition(wintypes.HWND(hwnd), ctypes.byref(data)) else -1


def enable_acrylic(hwnd: int) -> int:
    user32 = ctypes.windll.user32
    set_window_composition = user32.SetWindowCompositionAttribute
    set_window_composition.argtypes = [wintypes.HWND, ctypes.POINTER(WINDOWCOMPOSITIONATTRIBDATA)]
    set_window_composition.restype = ctypes.c_bool

    accent = ACCENT_POLICY(ACCENT_ENABLE_ACRYLICBLURBEHIND, 0, 0, 0)
    data = WINDOWCOMPOSITIONATTRIBDATA(WNDCA_ACCENT_POLICY, ctypes.addressof(accent), ctypes.sizeof(accent))

    return 0 if set_window_composition(wintypes.HWND(hwnd), ctypes.byref(data)) else -1


def disable_blur(hwnd: int) -> int:
    user32 = ctypes.windll.user32
    set_window_composition = user32.SetWindowCompositionAttribute
    set_window_composition.argtypes = [wintypes.HWND, ctypes.POINTER(WINDOWCOMPOSITIONATTRIBDATA)]
    set_window_composition.restype = ctypes.c_bool

    accent = ACCENT_POLICY(ACCENT_DISABLED, 0, 0, 0)
    data = WINDOWCOMPOSITIONATTRIBDATA(WNDCA_ACCENT_POLICY, ctypes.addressof(accent), ctypes.sizeof(accent))

    return 0 if set_window_composition(wintypes.HWND(hwnd), ctypes.byref(data)) else -1


def resolve_window_style(style: str) -> str:
    if style in ('mica', 'acrylic', 'blur', 'solid'):
        return style
    if is_windows_11():
        return 'mica'
    return 'solid'


def apply_window_style(hwnd: int, style: str) -> None:
    resolved = resolve_window_style(style)
    if resolved == 'mica':
        enable_mica(hwnd)
    elif resolved == 'acrylic':
        enable_acrylic(hwnd)
    elif resolved == 'blur':
        enable_blur(hwnd)
    elif resolved == 'solid':
        disable_blur(hwnd)


def main() -> None:
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

    from iaa.config.manager import read_shared
    shared = read_shared()
    apply_window_style(hwnd, shared.interface.window_style)

    exit_code = app.exec()
    controller.shutdown()
    raise SystemExit(exit_code)
