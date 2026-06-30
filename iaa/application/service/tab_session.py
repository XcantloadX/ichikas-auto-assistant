# iaa/application/service/tab_session.py

from iaa.progress import ProgressHub
from .iaa_service import IaaService


class TabSession:
    """一个 Tab 的完整服务层实例。

    包含独立的 IaaService（含 ConfigService 和 SchedulerService）、
    per-tab ProgressHub 和 LogBridge。
    多个 TabSession 可以并发运行，彼此通过 ContextVar 隔离。
    """

    def __init__(self, config_name: str) -> None:
        self.config_name = config_name
        self.progress_hub = ProgressHub()

        # 延迟导入避免循环引用；LogBridge 不调用 install()，仅作为路由目标
        from iaa.application.qt.controllers.log_bridge import LogBridge
        self.log_bridge = LogBridge(None)

        def _thread_start() -> None:
            from iaa.context import set_tab_hub, set_tab_log_bridge, set_tab_name
            set_tab_hub(self.progress_hub)
            set_tab_log_bridge(self.log_bridge)
            set_tab_name(config_name)

        self.iaa = IaaService(config_name=config_name, scheduler_thread_start_hook=_thread_start)

    @property
    def scheduler(self):
        return self.iaa.scheduler

    @property
    def config(self):
        return self.iaa.config
