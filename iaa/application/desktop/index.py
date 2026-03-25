import tkinter as tk
from dataclasses import dataclass
import os

import ttkbootstrap as tb
from ..service.iaa_service import IaaService
from tkinter import messagebox


@dataclass
class Store:
    var_start_game: tk.BooleanVar | None = None
    var_single_live: tk.BooleanVar | None = None
    var_challenge_live: tk.BooleanVar | None = None
    var_activity_story: tk.BooleanVar | None = None
    var_auto_cm: tk.BooleanVar | None = None
    var_gift: tk.BooleanVar | None = None
    var_area_convos: tk.BooleanVar | None = None
    var_event_shop: tk.BooleanVar | None = None
    logo_image: tk.PhotoImage | None = None # LOGO 组件图片。防止被 GC

class DesktopApp:
    def __init__(self) -> None:
        self.root = tb.Window(themename="flatly")
        self.root.title("一歌小助手")
        self.root.geometry("900x520")
        self.store = Store()

        # 服务聚合
        self.service = IaaService()
        
        # 设置包含版本号的窗口标题
        try:
            self.root.title(f"一歌小助手 v{self.service.version}")
        except Exception:
            pass
        
        # 设置窗口图标
        try:
            icon_path = os.path.join(self.service.root, 'assets', 'icon_round.ico')
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception:
            pass  # 如果图标设置失败，不影响程序运行
        
        # 绑定错误回调：在 UI 线程弹出提示
        def _on_scheduler_error(e: Exception) -> None:
            try:
                # 使用 after 确保在主线程执行 UI 操作
                self.root.after(0, lambda: messagebox.showerror("运行错误", str(e), parent=self.root))
            except Exception:
                pass
        self.service.scheduler.on_error = _on_scheduler_error

        # 绑定窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Notebook 作为主容器
        self.notebook = tb.Notebook(self.root)
        self._build_tabs()
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

    # -------------------- UI 构建 --------------------
    def _build_tabs(self) -> None:
        self.tab_control = tb.Frame(self.notebook)
        self.tab_settings = tb.Frame(self.notebook)
        self.tab_about = tb.Frame(self.notebook)

        self.notebook.add(self.tab_control, text="控制")
        self.notebook.add(self.tab_settings, text="配置")
        self.notebook.add(self.tab_about, text="关于")

        # 延迟导入避免循环导入
        from .tab_main import build_control_tab
        from .tab_conf import build_settings_tab
        from .tab_about import build_about_tab
        build_control_tab(self, self.tab_control)
        build_settings_tab(self, self.tab_settings)
        build_about_tab(self, self.tab_about)

    # -------------------- 事件处理 --------------------
    def on_start(self) -> None:
        self.service.scheduler.start_regular(run_in_thread=True)

    def on_stop(self) -> None:
        self.service.scheduler.stop(block=False)

    def _collect_selected_tasks(self) -> list[str]:
        tasks: list[str] = []
        if self.store.var_single_live and self.store.var_single_live.get():
            tasks.append("单人演出")
        if self.store.var_challenge_live and self.store.var_challenge_live.get():
            tasks.append("挑战演出")
        if self.store.var_activity_story and self.store.var_activity_story.get():
            tasks.append("活动剧情")
        if self.store.var_auto_cm and self.store.var_auto_cm.get():
            tasks.append("自动 CM")
        if self.store.var_gift and self.store.var_gift.get():
            tasks.append("领取礼物")
        if self.store.var_area_convos and self.store.var_area_convos.get():
            tasks.append("区域对话")
        if self.store.var_event_shop and self.store.var_event_shop.get():
            tasks.append("活动商店")
        return tasks

    def _on_close(self) -> None:
        sch = self.service.scheduler
        if sch.running:
            confirm = messagebox.askyesno(
                "确认退出",
                "当前仍在执行任务，确定要退出吗？退出将先停止任务。",
                parent=self.root,
            )
            if not confirm:
                return
            try:
                sch.stop(block=True)
            except Exception:
                pass
        try:
            self.root.destroy()
        except Exception:
            pass

    # -------------------- 入口 --------------------
    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    app = DesktopApp()
    app.run()


if __name__ == "__main__":
    main()
