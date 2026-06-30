from __future__ import annotations

import sys
from typing import TYPE_CHECKING, cast
from pynput import keyboard
from PySide6.QtCore import QObject, QMetaObject, Qt

from iaa.config import manager as config_manager

if TYPE_CHECKING:
    from .tab_manager import TabManager
    from .preferences_controller import PreferencesController

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
