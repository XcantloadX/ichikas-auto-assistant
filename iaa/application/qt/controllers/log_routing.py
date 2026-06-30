# iaa/application/qt/controllers/log_routing.py

import logging


class ContextVarLogHandler(logging.Handler):
    """将 Python logging 记录路由到当前线程绑定的 per-tab LogBridge。

    调度器线程在 on_thread_start 中调用 set_tab_log_bridge() 设置目标；
    未设置的线程（UI 线程等）emit 的日志不会被此 handler 处理。
    """

    def emit(self, record: logging.LogRecord) -> None:
        from iaa.context import _g_log_bridge
        bridge = _g_log_bridge.get()
        if bridge is None:
            return
        try:
            msg = self.format(record) + '\n'
            bridge.write_text(msg, 'normal')
        except Exception:
            self.handleError(record)


class TabNameFilter(logging.Filter):
    """为每条日志记录注入当前线程的 tab 名（_g_tab_name ContextVar）。

    安装在控制台 handler 上后，格式串可使用 %(tab_name)s；
    未设置的线程（UI 线程等）tab_name 为 '-'。
    """

    def filter(self, record: logging.LogRecord) -> bool:
        from iaa.context import _g_tab_name
        record.tab_name = _g_tab_name.get() or '-'  # type: ignore[attr-defined]
        return True
