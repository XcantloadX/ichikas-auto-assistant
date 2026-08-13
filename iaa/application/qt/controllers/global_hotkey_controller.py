from __future__ import annotations

import importlib.util
import sys
from typing import TYPE_CHECKING, cast

from PySide6.QtCore import QObject, QMetaObject, Qt

from iaa.config import manager as config_manager
from iaa.platform import env

if TYPE_CHECKING:
    from .tab_manager import TabManager
    from .preferences_controller import PreferencesController


def _pynput_available() -> bool:
    """探测 pynput 是否可导入。

    Android 上 pynput 没有 p4a recipe、无法安装;测试环境也可能用
    ``sys.modules`` 置 None 或 ``sys.meta_path`` 钩子屏蔽它,两种都等价于不可用。

    :return: 可导入返回 True,否则返回 False。
    """
    try:
        return importlib.util.find_spec('pynput') is not None
    except (ImportError, AttributeError):
        return False


# 平台实现选择:Android（无法做全局按键）或未安装 pynput 时退化为空壳,
# 不启动任何监听线程;桌面（含 Windows/macOS）使用 pynput。在 import 期冻结,
# 避免运行期反复探测。
_HOTKEY_IMPL: str = 'noop' if env.IS_ANDROID or not _pynput_available() else 'pynput'

if _HOTKEY_IMPL == 'pynput':
    from pynput import keyboard

    if sys.platform == 'darwin':
        # macOS 14+ workaround for pynput EXC_BREAKPOINT in background thread
        # 缓存 context，避免跨线程调用 native api 导致 crash
        from pynput._util.darwin import keycode_context as original_keycode_context
        import pynput.keyboard._darwin
        import pynput._util.darwin
        import contextlib

        _cached_context = None
        try:
            with original_keycode_context() as ctx:
                _cached_context = ctx
        except Exception:
            pass

        @contextlib.contextmanager
        def _patched_keycode_context():
            yield _cached_context

        pynput.keyboard._darwin.keycode_context = _patched_keycode_context
        pynput._util.darwin.keycode_context = _patched_keycode_context


class GlobalHotkeyController(QObject):
    """全局快捷键控制器。

    当 ``_HOTKEY_IMPL`` 为 ``noop`` 时（Android / 未安装 pynput）不启动任何
    全局监听,``reload_hotkeys`` 直接返回,以保持与桌面一致的构造入口与信号协议。
    """

    def __init__(self, tab_manager: 'TabManager', preferences_controller: 'PreferencesController', parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._tab_manager = tab_manager
        self._prefs = preferences_controller
        self._listener: keyboard.GlobalHotKeys | None = None

        self._prefs.runtimeChanged.connect(self.reload_hotkeys)
        self.reload_hotkeys()

    def _resolve_run(self):
        """返回当前激活 tab 的 RunController。"""
        return self._tab_manager.activeRunController

    def reload_hotkeys(self) -> None:
        if _HOTKEY_IMPL == 'noop':
            # Android/未安装 pynput:无法做全局监听,直接忽略,保持接口与信号协议一致
            return
        hotkeys = config_manager.read_shared().hotkeys
        self._register_hotkeys(hotkeys.start or '', hotkeys.stop or '')

    def shutdown(self) -> None:
        self._stop_listener()

    def _register_hotkeys(self, start: str, stop: str) -> None:
        mapping = {}
        start_combo = self._qt_sequence_to_hotkey(start)
        stop_combo = self._qt_sequence_to_hotkey(stop)
        if start_combo:
            mapping[start_combo] = self._on_start
        if stop_combo:
            mapping[stop_combo] = self._on_stop

        self._stop_listener()
        if not mapping:
            return
        try:
            listener = keyboard.GlobalHotKeys(mapping)
            listener.start()
            self._listener = listener
        except Exception:
            self._listener = None

    def _stop_listener(self) -> None:
        if self._listener is None:
            return
        try:
            self._listener.stop()
        except Exception:
            pass
        self._listener = None

    def _qt_sequence_to_hotkey(self, sequence: str) -> str:
        if not sequence:
            return ''
        parts = sequence.split('+')
        mods: list[str] = []
        key = ''
        for part in parts:
            if part == 'Ctrl':
                mods.append('<ctrl>')
            elif part == 'Alt':
                mods.append('<alt>')
            elif part == 'Shift':
                mods.append('<shift>')
            elif part == 'Meta':
                mods.append('<cmd>')
            else:
                key = part

        if not key:
            return ''
        key = self._map_key_name(key)
        if not key:
            return ''
        return '+'.join(mods + [key])

    def _map_key_name(self, key: str) -> str:
        mapping = {
            'Return': '<enter>',
            'Enter': '<enter>',
            'Backspace': '<backspace>',
            'Del': '<delete>',
            'Tab': '<tab>',
            'Escape': '<esc>',
            'Space': '<space>',
            'Up': '<up>',
            'Down': '<down>',
            'Left': '<left>',
            'Right': '<right>',
            'Home': '<home>',
            'End': '<end>',
            'PgUp': '<page_up>',
            'PgDown': '<page_down>',
            'Ins': '<insert>',
        }
        mapped = mapping.get(key)
        if mapped:
            return mapped
        # Function keys F1–F35: pynput requires angle-bracket form <f1>, <f9>, etc.
        if len(key) >= 2 and key[0] == 'F' and key[1:].isdigit():
            return f'<{key.lower()}>'
        return key.lower()

    def _on_start(self) -> None:
        run = self._resolve_run()
        if run is not None:
            QMetaObject.invokeMethod(cast(QObject, run), 'startRegular', Qt.ConnectionType.QueuedConnection)

    def _on_stop(self) -> None:
        run = self._resolve_run()
        if run is not None:
            QMetaObject.invokeMethod(cast(QObject, run), 'stop', Qt.ConnectionType.QueuedConnection)
