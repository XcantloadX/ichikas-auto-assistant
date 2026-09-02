from __future__ import annotations

import json
import shutil
import threading
from pathlib import Path

from PySide6.QtCore import QObject, Property, QTimer, Signal, Slot
from PySide6.QtWidgets import QFileDialog

<<<<<<< HEAD
from iaa.application.service.iaa_service import IaaService
=======
from iaa.i18n import translate
>>>>>>> feat/en-server
from iaa.config.live_presets import AutoLivePreset, LivePresetManager
from iaa.tasks.registry import TASK_INFOS

<<<<<<< HEAD
from iaa.tasks.live.live import auto_live_payload_to_plan
from ..models import builtin_auto_presets, preset_to_payload
from .progress_bridge import ProgressBridge
=======
from iaa.tasks.live.auto_live_constants import (
    AP_KEEP_UNCHANGED,
    LAST_PRESET_NAME,
    PRESET_CLEAR_10,
    PRESET_FC_10,
    PRESET_LEADER_COUNT,
    SONG_KEEP_UNCHANGED,
    preset_name_matches,
)

from ..models import auto_live_payload_to_plan, builtin_auto_presets, preset_to_payload
>>>>>>> feat/en-server


class RunController(QObject):
    stateChanged = Signal()
    tasksChanged = Signal()
    operationSucceeded = Signal(str)
    operationFailed = Signal(str)
    scriptAutoWarningRequested = Signal(str)
    exportReady = Signal(str)

<<<<<<< HEAD
    def __init__(self, iaa_service: IaaService, progress_bridge: ProgressBridge, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._iaa = iaa_service
        self._progress = progress_bridge
=======
    def __init__(self, iaa_service, progress_bridge, scrcpy_controller, i18n_controller, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._iaa = iaa_service
        self._progress = progress_bridge
        self._scrcpy = scrcpy_controller
        self._i18n = i18n_controller
>>>>>>> feat/en-server
        self._export_busy = False
        self._queued = False
        self._timer = QTimer(self)
        self._timer.setInterval(300)
        self._timer.timeout.connect(self._refresh_state)
        self._timer.start()
        self.exportReady.connect(self._show_save_dialog)

    def _tr(self, key: str, **kwargs: object) -> str:
        text = translate(self._iaa.config.shared.interface.language, key)
        return text.format(**kwargs) if kwargs else text

    def _get_ap_keep_value(self) -> str:
        return AP_KEEP_UNCHANGED

    def _get_song_keep_value(self) -> str:
        return SONG_KEEP_UNCHANGED

    apKeepValue = Property(str, _get_ap_keep_value, constant=True)
    songKeepValue = Property(str, _get_song_keep_value, constant=True)

    # TODO: 遗留的展示名称作为配置值带来的问题
    @Slot(str, result=str)
    def autoLivePresetLabel(self, name: str) -> str:
        if preset_name_matches(name, PRESET_CLEAR_10):
            return self._tr('auto_live.preset.clear_10')
        if preset_name_matches(name, PRESET_FC_10):
            return self._tr('auto_live.preset.fc_10')
        if preset_name_matches(name, PRESET_LEADER_COUNT):
            return self._tr('auto_live.preset.leader_count')
        if preset_name_matches(name, LAST_PRESET_NAME):
            return self._tr('auto_live.preset.last')
        return name

    def _auto_live_error_text(self, message: str) -> str:
        if message == '指定次数必须为正整数。':
            return self._tr('auto_live.error.count_positive')
        if message.startswith('未知的次数模式：'):
            return self._tr('auto_live.error.unknown_count_mode', mode=message.removeprefix('未知的次数模式：'))
        if message == 'AP 倍率必须在 0 到 10 之间，或为 maximum。':
            return self._tr('auto_live.error.ap_multiplier')
        if message.startswith('未知的循环模式：'):
            return self._tr('auto_live.error.unknown_loop_mode', mode=message.removeprefix('未知的循环模式：'))
        return message

    def _refresh_state(self) -> None:
        self.stateChanged.emit()

    def _get_running(self) -> bool:
        return bool(self._iaa.scheduler.running)

    def _get_is_starting(self) -> bool:
        return bool(self._iaa.scheduler.is_starting)

    def _get_is_stopping(self) -> bool:
        return bool(self._iaa.scheduler.is_stopping)

    def _get_current_task_id(self) -> str:
        return self._iaa.scheduler.current_task_id or ''

    def _get_current_task_name(self) -> str:
        return self._iaa.scheduler.current_task_name or ''

    def _get_is_queued(self) -> bool:
        return self._queued

    def _set_queued(self, v: bool) -> None:
        self._queued = v
        self.stateChanged.emit()

    def _get_export_busy(self) -> bool:
        return self._export_busy

    running = Property(bool, _get_running, notify=stateChanged)
    isStarting = Property(bool, _get_is_starting, notify=stateChanged)
    isStopping = Property(bool, _get_is_stopping, notify=stateChanged)
    isQueued = Property(bool, _get_is_queued, notify=stateChanged)
    currentTaskId = Property(str, _get_current_task_id, notify=stateChanged)
    currentTaskName = Property(str, _get_current_task_name, notify=stateChanged)
    exportBusy = Property(bool, _get_export_busy, notify=stateChanged)

    @Slot(result=str)
    def tasksStateJson(self) -> str:
        conf = self._iaa.config.conf
        items: list[dict[str, object]] = []
        for info in TASK_INFOS.values():
            if info.task_id.startswith('_'):  # 内部任务，不在主界面展示
                continue
            items.append(
                {
                    'id': info.task_id,
                    'name': info.display_name,
                    'kind': info.kind,
                    'enabled': info.get_enabled(conf) if info.get_enabled is not None else False,
                    'runnable': True,
                    'checkable': info.get_enabled is not None,
                }
            )
        return json.dumps(items, ensure_ascii=False)

    @Slot(str, bool)
    def setRegularTaskEnabled(self, task_id: str, enabled: bool) -> None:
        tasks_conf = self._iaa.config.conf.tasks
        task_conf = getattr(tasks_conf, task_id, None)
        if task_conf is None or not hasattr(task_conf, 'enabled'):
            raise ValueError(f"Unknown or non-toggleable task: {task_id!r}")
        task_conf.enabled = enabled
        self._iaa.config.save()
        self.tasksChanged.emit()

    @Slot()
    def startRegular(self) -> None:
        if self._iaa.scheduler.is_starting or self._iaa.scheduler.is_stopping:
            return
        self._iaa.scheduler.start_regular(run_in_thread=True)
        self.stateChanged.emit()

    @Slot()
    def stop(self) -> None:
        if self._iaa.scheduler.is_starting or self._iaa.scheduler.is_stopping:
            return
        self._iaa.scheduler.stop(block=False)
        self.stateChanged.emit()

    @Slot(str)
    def runTask(self, task_id: str) -> None:
        if self._iaa.scheduler.is_starting or self._iaa.scheduler.is_stopping or self._iaa.scheduler.running:
            return
        self._iaa.scheduler.run_single(task_id, run_in_thread=True)
        self.stateChanged.emit()

    @Slot(str)
    def runAutoLive(self, payload_json: str) -> None:
        payload = json.loads(payload_json)
        try:
            plan = auto_live_payload_to_plan(payload)
        except ValueError as exc:
            raise ValueError(self._auto_live_error_text(str(exc))) from exc
        LivePresetManager().save_last_auto(AutoLivePreset(name=LAST_PRESET_NAME, plan=plan))
        if plan.play_mode == 'script_auto':
            self.scriptAutoWarningRequested.emit(self._tr('notice.script_auto_warning'))
        self._iaa.scheduler.run_single('auto_live', run_in_thread=True, kwargs={'plan': plan})
        self.stateChanged.emit()

    @Slot(result=str)
    def builtinAutoPresetsJson(self) -> str:
        return json.dumps(builtin_auto_presets(), ensure_ascii=False)

    @Slot(result=str)
    def lastAutoPresetJson(self) -> str:
        preset = LivePresetManager().load_last_auto()
        if preset is None:
            return ''
        return json.dumps(preset_to_payload(preset), ensure_ascii=False)

    @Slot()
    def exportReport(self) -> None:
        if self._export_busy:
            return
        self._export_busy = True
        self.stateChanged.emit()

        def _run() -> None:
            try:
                tmp_zip = self._iaa.export_report_zip()
            except Exception as exc:  # noqa: BLE001
                self._export_busy = False
                self.stateChanged.emit()
                self.operationFailed.emit(self._tr('notice.export_failed', error=exc))
                return
            self.exportReady.emit(tmp_zip)

        threading.Thread(target=_run, name='IAA-ExportReport', daemon=True).start()

    def _show_save_dialog(self, tmp_zip: str) -> None:
        save_path, _ = QFileDialog.getSaveFileName(
            None,
            self._tr('dialog.save_report.title'),
            str(Path(tmp_zip).name),
            self._tr('dialog.save_report.filter'),
        )
        try:
            if save_path:
                shutil.copyfile(tmp_zip, save_path)
                self.operationSucceeded.emit(self._tr('notice.report_saved'))
        except Exception as exc:  # noqa: BLE001
            self.operationFailed.emit(self._tr('notice.report_save_failed', error=exc))
        finally:
            self._export_busy = False
            self.stateChanged.emit()
