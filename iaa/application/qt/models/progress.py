from __future__ import annotations

from dataclasses import dataclass

from iaa.progress import TaskProgressEvent


@dataclass(slots=True)
class ProgressState:
    status_text: str = '就绪'
    progress_percent: int = 0
    last_error_text: str = ''
    stop_requested: bool = False
    stopped: bool = False


def _to_int(value: object) -> int | None:
    try:
        return int(value)  # type: ignore[arg-type]
    except Exception:
        return None


def progress_event_to_state(event: TaskProgressEvent, prev: ProgressState | None = None) -> ProgressState:
    state = ProgressState(
        status_text=(prev.status_text if prev else '就绪'),
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
    if not isinstance(message, str):
        message = ''
    phase_path = payload.get('phase_path')
    phase_parts: list[str] = []
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
            state.status_text = '已停止'
            return state
        error_text = f'执行「{event.task_name}」时出错：{err_msg or "未知错误"}'
        state.last_error_text = error_text
        state.stopped = False
        state.status_text = error_text
        return state

    if event.type == 'task_started':
        state.last_error_text = ''
        state.stopped = False

    parts = [event.task_name, *phase_parts]
    if message:
        parts.append(message)
    display_text = ' > '.join([part for part in parts if part])
    if display_text:
        state.status_text = display_text
    return state
