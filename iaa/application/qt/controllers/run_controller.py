from __future__ import annotations

import json
import shutil
import threading
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QObject, Property, QTimer, Signal, Slot
from PySide6.QtWidgets import QFileDialog

from iaa.application.service.iaa_service import IaaService
from iaa.i18n import translate
from iaa.config.live_presets import AutoLivePreset, LivePresetManager
from iaa.tasks.registry import TASK_INFOS

from iaa.tasks.live.auto_live_constants import (
    AP_KEEP_UNCHANGED,
    LAST_PRESET_NAME,
    SONG_KEEP_UNCHANGED,
)

from ..models import (
    AutoLivePayloadError,
    auto_live_payload_to_plan,
    auto_live_preset_label_key,
    builtin_auto_presets,
    preset_to_payload,
)
from .progress_bridge import ProgressBridge


class RunController(QObject):
    stateChanged = Signal()
    tasksChanged = Signal()
    operationSucceeded = Signal(str)
    operationFailed = Signal(str)
    scriptAutoWarningRequested = Signal(str)
    exportReady = Signal(str)

    def __init__(
        self,
        iaa_service: IaaService,
        progress_bridge: ProgressBridge,
        parent: QObject | None = None,
        *,
        get_language: 'Callable[[], str] | None' = None,
    ) -> None:
        super().__init__(parent)
        self._iaa = iaa_service
        self._progress = progress_bridge
        # GUI 语言来源（注入 i18nController.language 的 getter）。
        # config.shared 在偏好保存后不会热更新，不能作为实时语言来源。
        self._get_language = get_language
        self._export_busy = False
        self._queued = False
        self._timer = QTimer(self)
        self._timer.setInterval(300)
        self._timer.timeout.connect(self._refresh_state)
        self._timer.start()
        self.exportReady.connect(self._show_save_dialog)

    def _language(self) -> str:
        if self._get_language is not None:
            return self._get_language()
        return self._iaa.config.shared.interface.language

    def _tr(self, key: str, **kwargs: object) -> str:
        text = translate(self._language(), key)
        return text.format(**kwargs) if kwargs else text

    def _get_ap_keep_value(self) -> str:
        return AP_KEEP_UNCHANGED

    def _get_song_keep_value(self) -> str:
        return SONG_KEEP_UNCHANGED

    apKeepValue = Property(str, _get_ap_keep_value, constant=True)
    songKeepValue = Property(str, _get_song_keep_value, constant=True)

    @Slot(str, result=str)
    def autoLivePresetLabel(self, name: str) -> str:
        """把预设稳定 ID 翻译为当前界面语言的展示名。

        :param name: 预设稳定 ID（``__preset_*__`` 等哨兵值）。
        :return: 界面语言下的展示名；未知 ID 原样返回。
        """
        key = auto_live_preset_label_key(name)
        return self._tr(key) if key is not None else name

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
        except AutoLivePayloadError as exc:
            # 任务层只携带错误键与参数（不感知界面语言），文本在此按当前语言渲染；
            # 其他 ValueError 原样透传。
            raise ValueError(self._tr(exc.key, **exc.params)) from exc
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
