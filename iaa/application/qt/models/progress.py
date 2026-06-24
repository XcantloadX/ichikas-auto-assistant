from __future__ import annotations

from dataclasses import dataclass, field

from iaa.progress import TaskProgressEvent, Translatable
from iaa.application.qt.i18n import TStr, tstr

StatusT = list[Translatable | str] | Translatable | str


@dataclass(slots=True)
class ProgressState:
    status_text: StatusT = field(default_factory=lambda: tstr('status.ready'))
    progress_percent: int = 0
    last_error_text: StatusT = ''
    stop_requested: bool = False
    stopped: bool = False


def _to_int(value: object) -> int | None:
    try:
        return int(value)  # type: ignore[arg-type]
    except Exception:
        return None


def progress_event_to_state(event: TaskProgressEvent, prev: ProgressState | None = None) -> ProgressState:
    state = ProgressState(
        status_text=(prev.status_text if prev else tstr('status.ready')),
        progress_percent=(prev.progress_percent if prev else 0),
        last_error_text=(prev.last_error_text if prev else ''),
        stop_requested=(prev.stop_requested if prev else False),
        stopped=(prev.stopped if prev else False),
    )
    payload = event.payload or {}

    current = _to_int(payload.get('current_steps'))
    total = _to_int(payload.get('total_steps'))
    percent = _to_int(payload.get('percent'))
    run_total_tasks = _to_int(payload.get('run_total_tasks'))
    run_completed_tasks = _to_int(payload.get('run_completed_tasks'))

    if run_total_tasks is not None and run_total_tasks > 0 and run_completed_tasks is not None:
        completed = max(0, min(run_total_tasks, run_completed_tasks))
        task_progress = 0
        if percent is not None:
            task_progress = max(0, min(100, percent))
        percent = int(((completed + (task_progress / 100.0)) / run_total_tasks) * 100)

    if percent is None and current is not None and total is not None and total > 0:
        percent = int(current * 100 / total)
    if event.type == 'task_started' and percent is None:
        percent = 0
    elif event.type == 'task_finished' and percent is None:
        percent = 100
    if percent is not None:
        state.progress_percent = max(0, min(100, percent))

    message = payload.get('message')
    phase_path = payload.get('phase_path')
    phase_parts: list[Translatable | str] = []
    if isinstance(phase_path, list):
        for item in phase_path:
            if not isinstance(item, dict):
                continue
            name = str(item.get('name') or '')
            p_current = item.get('current')
            p_total = item.get('total')
            if isinstance(p_current, int) and isinstance(p_total, int):
                phase_parts.append(f'{name} ({p_current}/{p_total})')
            elif name:
                phase_parts.append(name)

    if event.type == 'task_failed':
        err = payload.get('error')
        err_msg = str(err) if err is not None else ''
        if err_msg.lower() == 'keyboardinterrupt':
            state.stopped = True
            state.last_error_text = ''
            state.status_text = tstr('status.stopped')
            return state
        task_tstr = tstr(f'task.{event.task_id}')
        unknown_error = tstr('progress.unknown_error')
        error_text = TStr(
            zh_CN=tstr('progress.task_error').zh_CN.format(
                task=task_tstr.zh_CN,
                error=err_msg or unknown_error.zh_CN,
            ),
            en_US=tstr('progress.task_error').en_US.format(
                task=task_tstr.en_US,
                error=err_msg or unknown_error.en_US,
            ),
        )
        state.last_error_text = error_text
        state.stopped = False
        state.status_text = error_text
        return state

    if event.type == 'task_started':
        state.last_error_text = ''
        state.stopped = False

    parts: list[Translatable | str] = [tstr(f'task.{event.task_id}'), *phase_parts]
    if isinstance(message, Translatable):
        parts.append(message)
    elif isinstance(message, str) and message:
        parts.append(message)
    if parts:
        state.status_text = parts
    return state
