# iaa/application/qt/controllers/tab_manager.py

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Property, Signal, Slot, QMetaObject, Qt, Q_ARG

from iaa.config.manager import ConfigValidationError

if TYPE_CHECKING:
    from iaa.application.service.tab_session import TabSession
    from .run_controller import RunController
    from .settings_controller import SettingsController
    from .progress_bridge import ProgressBridge
    from .log_bridge import LogBridge

logger = logging.getLogger(__name__)


@dataclass
class _TabEntry:
    bundle: 'TabSession'
    run_ctrl: 'RunController'
    settings_ctrl: 'SettingsController'
    progress_bridge: 'ProgressBridge'

    @property
    def config_name(self) -> str:
        return self.bundle.config_name

    @property
    def log_bridge(self) -> 'LogBridge':
        return self.bundle.log_bridge

    @property
    def scheduler(self):
        return self.bundle.iaa.scheduler

    @property
    def is_running(self) -> bool:
        return self.scheduler.running


class TabManager(QObject):
    """管理多配置 Tab 的生命周期，并向 QML 暴露当前激活 Tab 的 controller。"""

    tabsChanged = Signal()
    activeTabChanged = Signal()
    anyBusyChanged = Signal()
    batchModeChanged = Signal()
    closeTabBlocked = Signal(str)          # reason: str，tab 正在运行或是最后一个
    readyToCloseTab = Signal(int)          # index: int，可以关闭（QML 负责 dirty 检查后调 closeTab）
    tabOpenFailed = Signal(str)            # error: str
    # 配置校验失败：(config_name, invalid_fields_json, error_details)
    configValidationFailed = Signal(str, str, str)
    operationSucceeded = Signal(str)
    operationFailed = Signal(str)
    errorDialogRequested = Signal(str, str)    # title, message — 用于需要弹窗的错误
    scriptAutoWarningRequested = Signal(str)   # 转发任意 tab 的同名信号
    # 转发活跃 tab 的 settings 信号，供 ProfileStoreBackend 使用
    activeProfileChanged = Signal(str)
    activeProfilesChanged = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._tabs: list[_TabEntry] = []
        self._active_index: int = 0
        self._batch_mode: str = ''        # '' | 'sequential' | 'parallel'
        self._stop_all_busy: bool = False
        self._seq_cancel = None           # threading.Event，用于取消连续执行循环
        self._restore_tabs()

    # ── 内部工具 ──────────────────────────────────────────────────────────────

    def _create_entry(self, config_name: str) -> _TabEntry:
        from iaa.application.service.tab_session import TabSession
        from .run_controller import RunController
        from .settings_controller import SettingsController
        from .progress_bridge import ProgressBridge

        bundle = TabSession(config_name)
        pb = ProgressBridge(self, hub=bundle.progress_hub)
        rc = RunController(bundle.iaa, pb, None, self)
        sc = SettingsController(bundle.iaa, self)
        bundle.iaa.scheduler.on_error = lambda exc: QMetaObject.invokeMethod(
            self, '_on_scheduler_error', Qt.ConnectionType.QueuedConnection, Q_ARG(str, str(exc))
        )
        return _TabEntry(bundle=bundle, run_ctrl=rc, settings_ctrl=sc, progress_bridge=pb)

    def _destroy_entry(self, entry: _TabEntry) -> None:
        try:
            entry.run_ctrl._timer.stop()
        except Exception:
            pass
        try:
            entry.progress_bridge.close()
        except Exception:
            pass

    def _save_tabs(self) -> None:
        if not self._tabs:
            return
        try:
            from iaa.config import manager
            shared = manager.read_shared()
            shared.profiles.open_tabs = [t.config_name for t in self._tabs]
            active = self._active_entry()
            shared.profiles.last_used = active.config_name if active is not None else None
            manager.write_shared(shared)
        except Exception:
            logger.exception('Failed to save tab list')

    def _restore_tabs(self) -> None:
        try:
            from iaa.config import manager
            shared = manager.read_shared()
            names = shared.profiles.open_tabs or []
            last_used = shared.profiles.last_used
            available = set(manager.list())

            # 过滤掉已被删除的配置
            names = [n for n in names if n in available]

            if not names:
                if not available:
                    # 初次启动，没有任何配置文件，保持 tab 列表为空
                    return
                # 兜底：用 last_used 或第一个可用配置
                fallback = last_used if last_used in available else manager.list()[0]
                names = [fallback]

            for name in names:
                try:
                    entry = self._create_entry(name)
                    self._wire_entry_signals(entry)
                    self._tabs.append(entry)
                except ConfigValidationError as e:
                    logger.warning('Config validation failed for tab %s: %s', name, e)
                    fields_json = json.dumps(e.invalid_fields, ensure_ascii=False)
                    # 延迟 emit：等 Qt 事件循环启动后再弹对话框
                    from PySide6.QtCore import QTimer
                    QTimer.singleShot(0, lambda n=name, fj=fields_json, ed=e.error_details:
                        self.configValidationFailed.emit(n, fj, ed))
                except Exception:
                    logger.exception('Failed to restore tab: %s', name)

            # 决定激活哪个 tab
            if last_used and last_used in [t.config_name for t in self._tabs]:
                self._active_index = [t.config_name for t in self._tabs].index(last_used)
            else:
                self._active_index = 0

        except Exception:
            logger.exception('Failed to restore tabs')
            # 最终兜底
            if not self._tabs:
                try:
                    from iaa.config import manager
                    names = manager.list()
                    name = names[0] if names else 'default'
                    entry = self._create_entry(name)
                    self._wire_entry_signals(entry)
                    self._tabs.append(entry)
                    self._active_index = 0
                except Exception:
                    logger.exception('Failed to create fallback tab')

    def _wire_entry_signals(self, entry: _TabEntry) -> None:
        """将 entry 的信号连到 TabManager 的转发信号。"""
        entry.settings_ctrl.currentProfileChanged.connect(
            lambda name, e=entry: self._on_entry_profile_changed(e, name)
        )
        entry.settings_ctrl.profilesChanged.connect(
            lambda e=entry: self._on_entry_profiles_changed(e)
        )
        # 任意 tab 的脚本警告都转发，QML 统一处理
        entry.run_ctrl.scriptAutoWarningRequested.connect(self.scriptAutoWarningRequested)
        # 任意 tab 的状态变化都通知 anyBusy
        entry.run_ctrl.stateChanged.connect(self.anyBusyChanged)

    def _on_entry_profile_changed(self, entry: _TabEntry, name: str) -> None:
        if self._active_entry() is entry:
            self.activeProfileChanged.emit(name)

    def _on_entry_profiles_changed(self, entry: _TabEntry) -> None:
        if self._active_entry() is entry:
            self.activeProfilesChanged.emit()

    def _active_entry(self) -> _TabEntry | None:
        if 0 <= self._active_index < len(self._tabs):
            return self._tabs[self._active_index]
        return None

    @Slot(str)
    def _on_scheduler_error(self, message: str) -> None:
        self.errorDialogRequested.emit('脚本运行错误', message)

    # ── QML Slots ─────────────────────────────────────────────────────────────

    @Slot(str)
    def openTab(self, config_name: str) -> None:
        """在新 tab 中打开指定配置。同一配置不能重复打开。"""
        if any(t.config_name == config_name for t in self._tabs):
            self.operationFailed.emit(f'配置 "{config_name}" 已在某个 Tab 中打开')
            return
        try:
            entry = self._create_entry(config_name)
            self._wire_entry_signals(entry)
            self._tabs.append(entry)
            self._active_index = len(self._tabs) - 1
            self._save_tabs()
            self.tabsChanged.emit()
            self.activeTabChanged.emit()
        except ConfigValidationError as e:
            logger.warning('Config validation failed for tab %s: %s', config_name, e)
            fields_json = json.dumps(e.invalid_fields, ensure_ascii=False)
            self.configValidationFailed.emit(config_name, fields_json, e.error_details)
        except Exception as e:
            logger.exception('Failed to open tab: %s', config_name)
            self.tabOpenFailed.emit(str(e))

    @Slot(int)
    def setActiveTab(self, index: int) -> None:
        if index < 0 or index >= len(self._tabs):
            return
        if index == self._active_index:
            return
        self._active_index = index
        self._save_tabs()
        self.activeTabChanged.emit()

    @Slot(int)
    def requestCloseTab(self, index: int) -> None:
        """请求关闭 tab。若 running 或是最后一个则阻断；否则 emit readyToCloseTab 由 QML 处理 dirty 检查。"""
        if index < 0 or index >= len(self._tabs):
            return
        if len(self._tabs) <= 1:
            self.closeTabBlocked.emit('至少需要保留一个 Tab')
            return
        entry = self._tabs[index]
        if entry.is_running:
            self.closeTabBlocked.emit('请先停止正在运行的任务')
            return
        self.readyToCloseTab.emit(index)

    @Slot(int)
    def closeTab(self, index: int) -> None:
        """无条件关闭 tab（dirty 检查由 QML 层在调用前完成）。"""
        if index < 0 or index >= len(self._tabs):
            return
        if len(self._tabs) <= 1:
            return
        entry = self._tabs.pop(index)
        self._destroy_entry(entry)

        # 调整 active index
        if self._active_index >= len(self._tabs):
            self._active_index = len(self._tabs) - 1
        elif self._active_index > index:
            self._active_index -= 1

        self._save_tabs()
        self.tabsChanged.emit()
        self.activeTabChanged.emit()

    @Slot(str, result=bool)
    def closeTabForConfig(self, config_name: str) -> bool:
        """ConfigManagerDialog 删除配置前调用。若 tab 正在运行返回 False；否则强制关闭并返回 True。"""
        for i, entry in enumerate(self._tabs):
            if entry.config_name == config_name:
                if entry.is_running:
                    return False
                if len(self._tabs) <= 1:
                    return False
                removed = self._tabs.pop(i)
                self._destroy_entry(removed)
                if self._active_index >= len(self._tabs):
                    self._active_index = len(self._tabs) - 1
                elif self._active_index > i:
                    self._active_index -= 1
                self._save_tabs()
                self.tabsChanged.emit()
                self.activeTabChanged.emit()
                return True
        return True  # 未打开此配置，视为成功

    @Slot(str, str)
    def resetAndOpenTab(self, config_name: str, invalid_fields_json: str) -> None:
        """重置指定字段为默认值后重新打开 tab。由 QML 在用户确认后调用。"""
        from iaa.config import manager
        try:
            invalid_fields = json.loads(invalid_fields_json)
            manager.fallback_invalid_fields(config_name, invalid_fields)
        except Exception:
            logger.exception('Failed to reset invalid fields for %s', config_name)
            self.tabOpenFailed.emit('重置配置失败，请手动检查配置文件')
            return
        self.openTab(config_name)

    @Slot(str, result=bool)
    def isTabOpen(self, config_name: str) -> bool:
        return any(t.config_name == config_name for t in self._tabs)

    @Slot()
    def startAllSequential(self) -> None:
        """在后台线程中依次启动所有 tab，前一个完成后再启动下一个。"""
        import threading
        import time

        cancel = threading.Event()
        self._seq_cancel = cancel
        self._batch_mode = 'sequential'
        self.batchModeChanged.emit()

        tabs = list(self._tabs)
        for entry in tabs:
            if not entry.is_running and not entry.scheduler.is_starting:
                entry.run_ctrl._set_queued(True)

        def _run() -> None:
            for entry in tabs:
                if cancel.is_set():
                    break
                if entry.is_running or entry.scheduler.is_starting:
                    continue
                entry.run_ctrl._set_queued(False)
                entry.scheduler.start_regular(run_in_thread=True)
                time.sleep(0.5)
                while (entry.scheduler.running
                       or entry.scheduler.is_starting
                       or entry.scheduler.is_stopping):
                    if cancel.is_set():
                        break
                    time.sleep(0.5)

            # 清除剩余排队标记
            for e in tabs:
                if e.run_ctrl._queued:
                    e.run_ctrl._set_queued(False)

            # 自然结束时自行重置；取消时由 stopAll 线程负责重置
            if not cancel.is_set():
                self._batch_mode = ''
                self.batchModeChanged.emit()
                self.anyBusyChanged.emit()

        threading.Thread(target=_run, daemon=True).start()

    @Slot()
    def startAllParallel(self) -> None:
        """同时启动所有 tab，并在全部结束后重置 batchMode。"""
        import threading
        import time

        self._batch_mode = 'parallel'
        self.batchModeChanged.emit()

        tabs = list(self._tabs)
        for entry in tabs:
            if not entry.is_running and not entry.scheduler.is_starting:
                entry.scheduler.start_regular(run_in_thread=True)

        def _watch() -> None:
            while any(e.scheduler.running or e.scheduler.is_starting or e.scheduler.is_stopping
                      for e in tabs):
                time.sleep(0.5)
                if self._stop_all_busy:
                    return  # stopAll 线程负责重置
            self._batch_mode = ''
            self.batchModeChanged.emit()
            self.anyBusyChanged.emit()

        threading.Thread(target=_watch, daemon=True).start()

    @Slot()
    def stopAll(self) -> None:
        """停止所有 tab（含排队等待的），等待启动中的 tab 完成启动后再停止。"""
        if self._stop_all_busy:
            return
        self._stop_all_busy = True
        self.batchModeChanged.emit()

        # 取消连续执行循环
        if self._seq_cancel is not None:
            self._seq_cancel.set()

        # 清除所有排队标记
        for entry in self._tabs:
            if entry.run_ctrl._queued:
                entry.run_ctrl._set_queued(False)

        import threading
        import time

        tabs = list(self._tabs)

        def _run() -> None:
            # 等待启动中的 tab 完成启动，再发出停止
            for entry in tabs:
                while entry.scheduler.is_starting:
                    time.sleep(0.1)
                if entry.scheduler.running and not entry.scheduler.is_stopping:
                    entry.scheduler.stop(block=False)

            # 等待所有 tab 完全停止
            while any(e.scheduler.running or e.scheduler.is_stopping for e in tabs):
                time.sleep(0.2)

            self._batch_mode = ''
            self._stop_all_busy = False
            self.batchModeChanged.emit()
            self.anyBusyChanged.emit()

        threading.Thread(target=_run, daemon=True).start()

    @Slot(result=str)
    def allConfigsJson(self) -> str:
        """返回所有配置（含未打开的），带 tabIndex（-1 表示未打开）和 isActive。"""
        try:
            from iaa.config import manager
            all_names = manager.list()
            open_map = {t.config_name: i for i, t in enumerate(self._tabs)}
            return json.dumps([
                {
                    'configName': name,
                    'tabIndex': open_map.get(name, -1),
                    'isActive': open_map.get(name, -1) == self._active_index and name in open_map,
                }
                for name in all_names
            ], ensure_ascii=False)
        except Exception:
            return '[]'

    @Slot(result=str)
    def tabsJson(self) -> str:
        return json.dumps([
            {'configName': t.config_name, 'index': i, 'isActive': i == self._active_index}
            for i, t in enumerate(self._tabs)
        ], ensure_ascii=False)

    @Slot(result=str)
    def availableConfigsJson(self) -> str:
        """返回未在任何 tab 中打开的配置列表。"""
        try:
            from iaa.config import manager
            all_configs = manager.list()
            open_names = {t.config_name for t in self._tabs}
            available = [n for n in all_configs if n not in open_names]
            return json.dumps(available, ensure_ascii=False)
        except Exception:
            return '[]'

    # ── QML Properties ────────────────────────────────────────────────────────

    def _get_active_run_controller(self) -> QObject | None:
        e = self._active_entry()
        return e.run_ctrl if e else None

    def _get_active_settings_controller(self) -> QObject | None:
        e = self._active_entry()
        return e.settings_ctrl if e else None

    def _get_active_progress_bridge(self) -> QObject | None:
        e = self._active_entry()
        return e.progress_bridge if e else None

    def _get_active_log_bridge(self) -> QObject | None:
        e = self._active_entry()
        return e.log_bridge if e else None

    def _get_active_config_name(self) -> str:
        e = self._active_entry()
        return e.config_name if e else ''

    def _get_active_tab_index(self) -> int:
        return self._active_index

    activeRunController = Property(QObject, _get_active_run_controller, notify=activeTabChanged)
    activeSettingsController = Property(QObject, _get_active_settings_controller, notify=activeTabChanged)
    activeProgressBridge = Property(QObject, _get_active_progress_bridge, notify=activeTabChanged)
    activeLogBridge = Property(QObject, _get_active_log_bridge, notify=activeTabChanged)
    activeConfigName = Property(str, _get_active_config_name, notify=activeTabChanged)
    activeTabIndex = Property(int, _get_active_tab_index, notify=activeTabChanged)

    @Slot(int, result=QObject)
    def settingsControllerAt(self, index: int) -> 'QObject | None':
        """返回指定 index 的 tab 的 SettingsController。"""
        if 0 <= index < len(self._tabs):
            return self._tabs[index].settings_ctrl
        return None

    @Slot(int, result=QObject)
    def runControllerAt(self, index: int) -> 'QObject | None':
        """返回指定 index 的 tab 的 RunController。"""
        if 0 <= index < len(self._tabs):
            return self._tabs[index].run_ctrl
        return None

    @Slot(int, result=QObject)
    def progressBridgeAt(self, index: int) -> 'QObject | None':
        """返回指定 index 的 tab 的 ProgressBridge。"""
        if 0 <= index < len(self._tabs):
            return self._tabs[index].progress_bridge
        return None

    @Slot(int, result=QObject)
    def logBridgeAt(self, index: int) -> 'QObject | None':
        """返回指定 index 的 tab 的 LogBridge。"""
        if 0 <= index < len(self._tabs):
            return self._tabs[index].log_bridge
        return None

    def _get_any_running(self) -> bool:
        return any(t.is_running for t in self._tabs)

    def _get_any_busy(self) -> bool:
        return any(
            t.is_running or t.scheduler.is_starting or t.run_ctrl._queued
            for t in self._tabs
        )

    def _get_batch_mode(self) -> str:
        return self._batch_mode

    def _get_stop_all_busy(self) -> bool:
        return self._stop_all_busy

    anyRunning = Property(bool, _get_any_running, notify=tabsChanged)
    anyBusy = Property(bool, _get_any_busy, notify=anyBusyChanged)
    batchMode = Property(str, _get_batch_mode, notify=batchModeChanged)
    stopAllBusy = Property(bool, _get_stop_all_busy, notify=batchModeChanged)

