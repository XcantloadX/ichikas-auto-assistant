from __future__ import annotations

import json
import shutil
import threading
from pathlib import Path

from PySide6.QtCore import QObject, Property, QTimer, Signal, Slot
from PySide6.QtWidgets import QFileDialog

from iaa.i18n import translate
from iaa.config.live_presets import AutoLivePreset, LivePresetManager
from iaa.tasks.registry import REGULAR_TASKS, TASK_INFOS

from ..models import auto_live_payload_to_plan, builtin_auto_presets, preset_to_payload


class RunController(QObject):
    stateChanged = Signal()
    tasksChanged = Signal()
    operationSucceeded = Signal(str)
    operationFailed = Signal(str)
    scriptAutoWarningRequested = Signal(str)
    exportReady = Signal(str)

    def __init__(self, iaa_service, progress_bridge, scrcpy_controller, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._iaa = iaa_service
        self._progress = progress_bridge
        self._scrcpy = scrcpy_controller
        self._export_busy = False
        self._timer = QTimer(self)
        self._timer.setInterval(300)
        self._timer.timeout.connect(self._refresh_state)
        self._timer.start()
        self.exportReady.connect(self._show_save_dialog)

    def _tr(self, key: str, **kwargs: object) -> str:
        text = translate(self._iaa.config.shared.interface.language, key)
        return text.format(**kwargs) if kwargs else text

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
        self._scrcpy.sync_visibility()

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

    def _get_export_busy(self) -> bool:
        return self._export_busy

    running = Property(bool, _get_running, notify=stateChanged)
    isStarting = Property(bool, _get_is_starting, notify=stateChanged)
    isStopping = Property(bool, _get_is_stopping, notify=stateChanged)
    currentTaskId = Property(str, _get_current_task_id, notify=stateChanged)
    currentTaskName = Property(str, _get_current_task_name, notify=stateChanged)
    exportBusy = Property(bool, _get_export_busy, notify=stateChanged)

    @Slot(result=str)
    def tasksStateJson(self) -> str:
        scheduler_conf = self._iaa.config.conf.scheduler
        items: list[dict[str, object]] = []
        ordered_ids = [
            'start_game',
            'solo_live',
            'challenge_live',
            'activity_story',
            'cm',
            'gift',
            'area_convos',
            'event_shop',
            'mission_rewards',
            'auto_live',
            'main_story',
        ]
        checkable_ids = {
            'start_game',
            'solo_live',
            'challenge_live',
            'activity_story',
            'cm',
            'gift',
            'area_convos',
            'event_shop',
            'mission_rewards',
        }
        for task_id in ordered_ids:
            info = TASK_INFOS[task_id]
            items.append(
                {
                    'id': task_id,
                    'name': info.display_name,
                    'kind': info.kind,
                    'enabled': scheduler_conf.is_enabled(task_id) if task_id in checkable_ids else False,
                    'runnable': True,
                    'checkable': task_id in checkable_ids,
                }
            )
        return json.dumps(items, ensure_ascii=False)

    @Slot(str, bool)
    def setRegularTaskEnabled(self, task_id: str, enabled: bool) -> None:
        scheduler_conf = self._iaa.config.conf.scheduler
        if task_id == 'start_game':
            scheduler_conf.start_game_enabled = enabled
        elif task_id == 'solo_live':
            scheduler_conf.solo_live_enabled = enabled
        elif task_id == 'challenge_live':
            scheduler_conf.challenge_live_enabled = enabled
        elif task_id == 'activity_story':
            scheduler_conf.activity_story_enabled = enabled
        elif task_id == 'cm':
            scheduler_conf.cm_enabled = enabled
        elif task_id == 'gift':
            scheduler_conf.gift_enabled = enabled
        elif task_id == 'area_convos':
            scheduler_conf.area_convos_enabled = enabled
        elif task_id == 'event_shop':
            scheduler_conf.event_shop_enabled = enabled
        elif task_id == 'mission_rewards':
            scheduler_conf.mission_rewards_enabled = enabled
        else:
            return
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
        LivePresetManager().save_last_auto(AutoLivePreset(name='上次设定', plan=plan))
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
