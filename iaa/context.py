import contextvars
from typing import Optional, Any


from .config.base import IaaConfig
from .errors import ContextNotInitializedError
from iaa.progress import DummyTaskReporter, ProgressHub, TaskReporter

g_conf: contextvars.ContextVar[Optional[IaaConfig]] = contextvars.ContextVar('g_conf', default=None)
g_task_reporter: contextvars.ContextVar[Optional[Any]] = contextvars.ContextVar('g_task_reporter', default=None)
_hub = ProgressHub()
_dummy_reporter = DummyTaskReporter()

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
    return _hub

def task_reporter() -> TaskReporter | DummyTaskReporter:
    reporter = g_task_reporter.get()
    if reporter is None:
        return _dummy_reporter
    return reporter
