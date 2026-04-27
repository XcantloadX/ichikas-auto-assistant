import time
from threading import Lock
from dataclasses import dataclass
from typing import Any, Callable, Literal

ProgressEventType = Literal[
    'task_started',
    'message',
    'step',
    'task_finished',
    'task_failed',
]


@dataclass(frozen=True)
class TaskProgressEvent:
    run_id: str
    task_id: str
    task_name: str
    timestamp: float
    type: ProgressEventType
    payload: dict[str, Any]


@dataclass(frozen=True)
class TaskProgressSnapshot:
    run_id: str
    task_id: str
    task_name: str
    timestamp: float
    status: Literal['running', 'finished', 'failed']
    percent: int | None = None
    message: str | None = None
    current_steps: int | None = None
    total_steps: int | None = None
    phase: str | None = None
    phase_path: list[dict[str, Any]] | None = None
    error: str | None = None


class ProgressHub:
    def __init__(self) -> None:
        self._lock = Lock()
        self._subscribers: list[Callable[[TaskProgressEvent], None]] = []
        self._latest_by_task: dict[str, TaskProgressSnapshot] = {}

    def publish(self, event: TaskProgressEvent) -> None:
        subscribers: list[Callable[[TaskProgressEvent], None]]
        with self._lock:
            self._latest_by_task[event.task_id] = _next_snapshot(self._latest_by_task.get(event.task_id), event)
            subscribers = list(self._subscribers)
        for callback in subscribers:
            try:
                callback(event)
            except Exception:
                continue

    def subscribe(self, callback: Callable[[TaskProgressEvent], None]) -> Callable[[], None]:
        with self._lock:
            self._subscribers.append(callback)

        def _unsubscribe() -> None:
            with self._lock:
                try:
                    self._subscribers.remove(callback)
                except ValueError:
                    pass

        return _unsubscribe

    def snapshot(self) -> dict[str, TaskProgressSnapshot]:
        with self._lock:
            return dict(self._latest_by_task)


@dataclass
class _PhaseState:
    name: str
    current_steps: int = 0
    total_steps: int | None = None


class TaskReporter:
    def __init__(self, hub: ProgressHub, run_id: str, task_id: str, task_name: str) -> None:
        self.hub = hub
        self.run_id = run_id
        self.task_id = task_id
        self.task_name = task_name
        self._phase_stack: list[_PhaseState] = []

    def message(self, text: str, *, extra: dict[str, Any] | None = None) -> None:
        payload: dict[str, Any] = {'message': text}
        payload['phase_path'] = self._phase_path()
        current_phase = self._current_phase()
        if current_phase is not None:
            payload['phase'] = current_phase.name
            payload['current_steps'] = current_phase.current_steps
            if current_phase.total_steps is not None:
                payload['total_steps'] = current_phase.total_steps
                payload['percent'] = _compute_percent(current_phase.current_steps, current_phase.total_steps)
        if extra:
            payload['extra'] = extra
        self._publish('message', payload)

    def phase(self, name: str, total: int | None = None) -> 'Phase':
        return Phase(self, name=name, total=total)

    def _push_phase(self, name: str, total: int | None) -> _PhaseState:
        state = _PhaseState(name=name, current_steps=0, total_steps=total)
        self._phase_stack.append(state)
        payload: dict[str, Any] = {'message': f'开始阶段：{name}', 'phase': name, 'phase_path': self._phase_path()}
        if total is not None:
            payload['total_steps'] = total
            payload['current_steps'] = 0
            payload['percent'] = 0
        self._publish('message', payload)
        return state

    def _pop_phase(self, state: _PhaseState, failed: bool) -> None:
        phase_path = self._phase_path()
        if not phase_path or phase_path[-1].get('name') != state.name:
            entry: dict[str, Any] = {'name': state.name}
            if state.total_steps is not None:
                entry['current'] = state.current_steps
                entry['total'] = state.total_steps
            phase_path = phase_path + [entry]
        if self._phase_stack and self._phase_stack[-1] is state:
            self._phase_stack.pop()
        elif state in self._phase_stack:
            self._phase_stack.remove(state)

        message = f'阶段失败：{state.name}' if failed else f'阶段完成：{state.name}'
        payload: dict[str, Any] = {
            'message': message,
            'phase': state.name,
            'current_steps': state.current_steps,
            'phase_path': phase_path,
        }
        if state.total_steps is not None:
            payload['total_steps'] = state.total_steps
            payload['percent'] = _compute_percent(state.current_steps, state.total_steps)
        self._publish('message', payload)

    def _phase_step(
        self,
        state: _PhaseState,
        *,
        advance: int = 1,
        message: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        if advance < 0:
            raise ValueError('advance must be >= 0')
        state.current_steps += advance
        if state.total_steps is not None and state.current_steps > state.total_steps:
            state.current_steps = state.total_steps

        payload: dict[str, Any] = {
            'phase': state.name,
            'current_steps': state.current_steps,
            'phase_path': self._phase_path(),
        }
        if message:
            payload['message'] = message
        if state.total_steps is not None:
            payload['total_steps'] = state.total_steps
            payload['percent'] = _compute_percent(state.current_steps, state.total_steps)
        if extra:
            payload['extra'] = extra
        self._publish('step', payload)

    def _current_phase(self) -> _PhaseState | None:
        if not self._phase_stack:
            return None
        return self._phase_stack[-1]

    def _phase_path(self) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for phase in self._phase_stack:
            entry: dict[str, Any] = {'name': phase.name}
            if phase.total_steps is not None:
                entry['current'] = phase.current_steps
                entry['total'] = phase.total_steps
            result.append(entry)
        return result

    def _publish(self, event_type: ProgressEventType, payload: dict[str, Any]) -> None:
        self.hub.publish(
            TaskProgressEvent(
                run_id=self.run_id,
                task_id=self.task_id,
                task_name=self.task_name,
                timestamp=time.time(),
                type=event_type,
                payload=payload,
            )
        )


class Phase:
    def __init__(self, reporter: TaskReporter, *, name: str, total: int | None) -> None:
        if total is not None and total <= 0:
            raise ValueError('total must be > 0')
        self._reporter = reporter
        self._name = name
        self._total = total
        self._state: _PhaseState | None = None

    def __enter__(self) -> 'Phase':
        self._state = self._reporter._push_phase(self._name, self._total)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
        if self._state is None:
            return
        self._reporter._pop_phase(self._state, failed=(exc is not None))

    def step(self, message: str | None = None, *, advance: int = 1, extra: dict[str, Any] | None = None) -> None:
        if self._state is None:
            raise RuntimeError('Phase is not active. Use "with reporter.phase(...):"')
        self._reporter._phase_step(self._state, advance=advance, message=message, extra=extra)


class DummyPhase:
    def __enter__(self) -> 'DummyPhase':
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
        return None

    def step(self, message: str | None = None, *, advance: int = 1, extra: dict[str, Any] | None = None) -> None:
        return None


class DummyTaskReporter:
    def message(self, text: str, *, extra: dict[str, Any] | None = None) -> None:
        return None

    def phase(self, name: str, total: int | None = None) -> DummyPhase:
        return DummyPhase()


def _compute_percent(current_steps: int, total_steps: int) -> int:
    if total_steps <= 0:
        return 0
    return int(max(0, min(100, current_steps * 100 / total_steps)))


def _next_snapshot(prev: TaskProgressSnapshot | None, event: TaskProgressEvent) -> TaskProgressSnapshot:
    payload = event.payload
    status: Literal['running', 'finished', 'failed'] = prev.status if prev else 'running'  # type: ignore[union-attr]
    if event.type == 'task_started':
        status = 'running'
    elif event.type == 'task_finished':
        status = 'finished'
    elif event.type == 'task_failed':
        status = 'failed'

    percent = payload.get('percent')
    message = payload.get('message')
    current_steps = payload.get('current_steps')
    total_steps = payload.get('total_steps')
    phase = payload.get('phase')
    phase_path = payload.get('phase_path')
    error = payload.get('error')

    if prev:
        if percent is None:
            percent = prev.percent
        if message is None:
            message = prev.message
        if current_steps is None:
            current_steps = prev.current_steps
        if total_steps is None:
            total_steps = prev.total_steps
        if phase is None:
            phase = prev.phase
        if phase_path is None:
            phase_path = prev.phase_path
        if error is None:
            error = prev.error

    if event.type == 'task_started':
        percent = 0
        message = payload.get('message', '任务开始')
        current_steps = None
        total_steps = None
        phase = None
        phase_path = None
        error = None
    elif event.type == 'task_finished':
        if percent is None:
            percent = 100
        if message is None:
            message = '任务完成'
        error = None
    elif event.type == 'task_failed':
        if message is None:
            message = '任务失败'
        if error is None:
            error = message

    return TaskProgressSnapshot(
        run_id=event.run_id,
        task_id=event.task_id,
        task_name=event.task_name,
        timestamp=event.timestamp,
        status=status,
        percent=percent,
        message=message,
        current_steps=current_steps,
        total_steps=total_steps,
        phase=phase,
        phase_path=phase_path,
        error=error,
    )