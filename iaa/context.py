import contextvars
from typing import TYPE_CHECKING, Optional, Any

from iaa.input import AdbKeyboardInput

from .config.base import IaaConfig
from .definitions.errors import ContextNotInitializedError
from iaa.progress import DummyTaskReporter, ProgressHub, TaskReporter

if TYPE_CHECKING:
    from iaa.application.qt.controllers.log_bridge import LogBridge

g_conf: contextvars.ContextVar[Optional[IaaConfig]] = contextvars.ContextVar('g_conf', default=None)
g_task_reporter: contextvars.ContextVar[Optional[Any]] = contextvars.ContextVar('g_task_reporter', default=None)
g_adb_keyboard_input: contextvars.ContextVar[Optional[AdbKeyboardInput]] = contextvars.ContextVar('g_adb_keyboard_input', default=None)

_hub = ProgressHub()
_dummy_reporter = DummyTaskReporter()

# Per-tab ContextVar：每个调度器线程在线程启动时（on_thread_start）设置自己的 hub、log bridge 和 tab 名。
# UI 线程及其他未设置的线程回退到 _hub（全局默认 hub）和 None（不路由日志）。
_g_hub: contextvars.ContextVar[Optional[ProgressHub]] = contextvars.ContextVar('_g_hub', default=None)
_g_log_bridge: contextvars.ContextVar[Optional[Any]] = contextvars.ContextVar('_g_log_bridge', default=None)
_g_tab_name: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar('_g_tab_name', default=None)


def init(config: IaaConfig) -> None:
    """初始化全局配置。"""
    g_conf.set(config)


def conf() -> IaaConfig:
    """获取当前上下文中的配置。"""
    config = g_conf.get()
    if config is None:
        raise ContextNotInitializedError()
    return config

def server():
    return conf().game.server


def set_task_reporter(reporter: Any | None):
    return g_task_reporter.set(reporter)


def reset_task_reporter(token: contextvars.Token):
    g_task_reporter.reset(token)

def hub() -> ProgressHub:
    """返回当前线程的 ProgressHub。调度器线程返回 per-tab hub，其他线程返回全局默认 hub。"""
    h = _g_hub.get()
    return h if h is not None else _hub

def set_tab_hub(h: ProgressHub) -> None:
    """在调度器线程的 __prepare_context 中调用，将当前线程绑定到 per-tab hub。"""
    _g_hub.set(h)

def set_tab_log_bridge(bridge: 'LogBridge | None') -> None:
    """在调度器线程启动时调用，将当前线程绑定到 per-tab log bridge。"""
    _g_log_bridge.set(bridge)

def set_tab_name(name: str) -> None:
    """在调度器线程启动时调用，记录当前线程对应的 tab 名（用于控制台日志前缀）。"""
    _g_tab_name.set(name)

def task_reporter() -> TaskReporter | DummyTaskReporter:
    reporter = g_task_reporter.get()
    if reporter is None:
        return _dummy_reporter
    return reporter

def set_adb_keyboard(ins: AdbKeyboardInput):
    return g_adb_keyboard_input.set(ins)

def keyboard() -> AdbKeyboardInput:
    ins = g_adb_keyboard_input.get()
    if ins is None:
        ins = AdbKeyboardInput()
        g_adb_keyboard_input.set(ins)
    return ins
