import tkinter as tk

import ttkbootstrap as tb
from tkinter import messagebox
from tkinter import filedialog
import os
import shutil

from .index import DesktopApp


def build_control_tab(app: DesktopApp, parent: tk.Misc) -> None:
  # 启停区域
  lf_power = tb.Labelframe(parent, text="启停")
  lf_power.pack(fill=tk.X, padx=8, pady=(8, 12))

  # 单一启停按钮
  btn_toggle = tb.Button(
    lf_power,
    text="启动",
    bootstyle="success",  # type: ignore[call-arg]
    width=10,
  )

  lbl_current = tb.Label(lf_power, text="正在执行：-")

  # 预定义单任务运行按钮（稍后创建）
  btn_run_start_game = None
  btn_run_single_live = None
  btn_run_challenge_live = None
  btn_run_activity_story = None
  btn_run_cm = None
  btn_run_gift = None
  btn_run_area_convos = None
  btn_run_ten_songs = None

  def _on_export_report() -> None:
    try:
      tmp_zip = app.service.export_report_zip()
    except Exception as e:  # noqa: BLE001
      messagebox.showerror("导出失败", f"生成报告失败：{e}", parent=app.root)
      return
    try:
      initial_name = os.path.basename(tmp_zip)
      save_path = filedialog.asksaveasfilename(
        title="保存报告",
        defaultextension=".zip",
        initialfile=initial_name,
        filetypes=[("Zip 文件", "*.zip")],
        parent=app.root,
      )
      if not save_path:
        return
      shutil.copyfile(tmp_zip, save_path)
      messagebox.showinfo("导出成功", "报告已保存。", parent=app.root)
    except Exception as e:  # noqa: BLE001
      messagebox.showerror("保存失败", f"保存报告失败：{e}", parent=app.root)

  # 右侧导出按钮
  btn_export = tb.Button(lf_power, text="导出报告", bootstyle="secondary", command=_on_export_report)  # type: ignore[call-arg]

  def _refresh_power_button() -> None:
    sch = app.service.scheduler
    is_transition = sch.is_starting or sch.is_stopping
    btn_toggle.configure(state=(tk.DISABLED if is_transition else tk.NORMAL))
    if sch.running:
      btn_toggle.configure(text="停止", bootstyle="danger")  # type: ignore[call-arg]
    else:
      btn_toggle.configure(text="启动", bootstyle="success")  # type: ignore[call-arg]
    # 刷新当前任务
    lbl_current.configure(text=f"正在执行：{sch.current_task_name or '-'}")
    # 刷新单任务运行按钮状态
    try:
      is_run_disabled = is_transition or sch.running
      for b in (btn_run_start_game, btn_run_single_live, btn_run_challenge_live, btn_run_activity_story, btn_run_cm, btn_run_gift, btn_run_area_convos, btn_run_ten_songs):
        if b is not None:
          b.configure(state=(tk.DISABLED if is_run_disabled else tk.NORMAL))
    except Exception:
      pass

  def _on_toggle() -> None:
    sch = app.service.scheduler
    if sch.is_starting or sch.is_stopping:
      return
    if sch.running:
      app.on_stop()
    else:
      app.on_start()
    # 触发一次 UI 刷新，随后用 after 循环持续刷新几次以反映状态变化
    _refresh_power_button()

  btn_toggle.configure(command=_on_toggle)
  btn_toggle.pack(side=tk.LEFT, padx=(12, 8), pady=10)
  lbl_current.pack(side=tk.LEFT, padx=(8, 12))
  btn_export.pack(side=tk.RIGHT, padx=(12, 12), pady=10)

  def _schedule_refresh_loop() -> None:
    try:
      _refresh_power_button()
      # 周期性刷新按钮状态（窗口仍存在时才继续）
      if parent.winfo_exists():
        parent.after(300, _schedule_refresh_loop)
    except tk.TclError:
      # 窗口销毁后可能触发异常，安全忽略
      pass

  _schedule_refresh_loop()

  # 任务区域
  lf_tasks = tb.Labelframe(parent, text="任务")
  lf_tasks.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

  # 采用 grid 简单排版
  conf = app.service.config.conf
  var_start_game = tk.BooleanVar(value=bool(conf.scheduler.start_game_enabled))
  var_single_live = tk.BooleanVar(value=bool(conf.scheduler.solo_live_enabled))
  var_challenge_live = tk.BooleanVar(value=bool(conf.scheduler.challenge_live_enabled))
  var_activity_story = tk.BooleanVar(value=bool(getattr(conf.scheduler, 'activity_story_enabled', True)))
  var_auto_cm = tk.BooleanVar(value=bool(conf.scheduler.cm_enabled))
  var_gift = tk.BooleanVar(value=bool(getattr(conf.scheduler, 'gift_enabled', True)))
  var_area_convos = tk.BooleanVar(value=bool(getattr(conf.scheduler, 'area_convos_enabled', True)))
  app.store.var_start_game = var_start_game
  app.store.var_single_live = var_single_live
  app.store.var_challenge_live = var_challenge_live
  app.store.var_activity_story = var_activity_story
  app.store.var_auto_cm = var_auto_cm
  app.store.var_gift = var_gift
  app.store.var_area_convos = var_area_convos

  def _save_scheduler() -> None:
    conf.scheduler.start_game_enabled = bool(var_start_game.get())
    conf.scheduler.solo_live_enabled = bool(var_single_live.get())
    conf.scheduler.challenge_live_enabled = bool(var_challenge_live.get())
    conf.scheduler.activity_story_enabled = bool(var_activity_story.get())
    conf.scheduler.cm_enabled = bool(var_auto_cm.get())
    conf.scheduler.gift_enabled = bool(var_gift.get())
    conf.scheduler.area_convos_enabled = bool(var_area_convos.get())
    app.service.config.save()

  def _on_run(task_id: str) -> None:
    sch = app.service.scheduler
    if sch.is_starting or sch.is_stopping or sch.running:
      return
    sch.run_single(task_id, run_in_thread=True)
    _refresh_power_button()

  cb_start_game = tb.Checkbutton(lf_tasks, text="启动游戏", variable=var_start_game, command=_save_scheduler)
  cb_single = tb.Checkbutton(lf_tasks, text="单人演出", variable=var_single_live, command=_save_scheduler)
  cb_challenge = tb.Checkbutton(lf_tasks, text="挑战演出", variable=var_challenge_live, command=_save_scheduler)
  cb_activity_story = tb.Checkbutton(lf_tasks, text="活动剧情", variable=var_activity_story, command=_save_scheduler)
  cb_cm = tb.Checkbutton(lf_tasks, text="自动 CM", variable=var_auto_cm, command=_save_scheduler)
  cb_gift = tb.Checkbutton(lf_tasks, text="领取礼物", variable=var_gift, command=_save_scheduler)
  cb_area_convos = tb.Checkbutton(lf_tasks, text="区域对话", variable=var_area_convos, command=_save_scheduler)

  # 将每个复选框与其后的“▶”按钮并排放置
  cb_start_game.grid(row=0, column=0, sticky=tk.W, padx=20, pady=(16, 8))
  btn_run_start_game = tb.Button(lf_tasks, text="▶", width=2, padding=0, bootstyle="secondary-toolbutton", command=lambda: _on_run("start_game"))  # type: ignore[call-arg]
  btn_run_start_game.grid(row=0, column=1, sticky=tk.W, padx=(4, 12), pady=(16, 8))

  cb_single.grid(row=0, column=2, sticky=tk.W, padx=20, pady=(16, 8))
  btn_run_single_live = tb.Button(lf_tasks, text="▶", width=2, padding=0, bootstyle="secondary-toolbutton", command=lambda: _on_run("solo_live"))  # type: ignore[call-arg]
  btn_run_single_live.grid(row=0, column=3, sticky=tk.W, padx=(4, 12), pady=(16, 8))

  cb_challenge.grid(row=0, column=4, sticky=tk.W, padx=20, pady=(16, 8))
  btn_run_challenge_live = tb.Button(lf_tasks, text="▶", width=2, padding=0, bootstyle="secondary-toolbutton", command=lambda: _on_run("challenge_live"))  # type: ignore[call-arg]
  btn_run_challenge_live.grid(row=0, column=5, sticky=tk.W, padx=(4, 12), pady=(16, 8))

  cb_activity_story.grid(row=0, column=6, sticky=tk.W, padx=20, pady=(16, 8))
  btn_run_activity_story = tb.Button(lf_tasks, text="▶", width=2, padding=0, bootstyle="secondary-toolbutton", command=lambda: _on_run("activity_story"))  # type: ignore[call-arg]
  btn_run_activity_story.grid(row=0, column=7, sticky=tk.W, padx=(4, 12), pady=(16, 8))

  cb_cm.grid(row=0, column=8, sticky=tk.W, padx=20, pady=(16, 8))
  btn_run_cm = tb.Button(lf_tasks, text="▶", width=2, padding=0, bootstyle="secondary-toolbutton", command=lambda: _on_run("cm"))  # type: ignore[call-arg]
  btn_run_cm.grid(row=0, column=9, sticky=tk.W, padx=(4, 12), pady=(16, 8))

  cb_gift.grid(row=1, column=0, sticky=tk.W, padx=20, pady=(8, 8))
  btn_run_gift = tb.Button(lf_tasks, text="▶", width=2, padding=0, bootstyle="secondary-toolbutton", command=lambda: _on_run("gift"))  # type: ignore[call-arg]
  btn_run_gift.grid(row=1, column=1, sticky=tk.W, padx=(4, 12), pady=(8, 8))

  cb_area_convos.grid(row=1, column=2, sticky=tk.W, padx=20, pady=(8, 8))
  btn_run_area_convos = tb.Button(lf_tasks, text="▶", width=2, padding=0, bootstyle="secondary-toolbutton", command=lambda: _on_run("area_convos"))  # type: ignore[call-arg]
  btn_run_area_convos.grid(row=1, column=3, sticky=tk.W, padx=(4, 12), pady=(8, 8))

  def _on_ten_songs() -> None:
    sch = app.service.scheduler
    if sch.is_starting or sch.is_stopping:
      return
    confirm = messagebox.askyesno(
      "确认开始",
      "即将开始列表循环 AUTO 歌单（最多 10 次）。AUTO 次数用完或体力不足时将会停止，也可以中途手动停止。是否继续？",
      parent=app.root,
    )
    if not confirm:
      return
    sch.run_single("ten_songs", run_in_thread=True)
    _refresh_power_button()

  sep_ten_songs = tb.Separator(lf_tasks, orient=tk.HORIZONTAL)
  sep_ten_songs.grid(row=2, column=0, columnspan=13, sticky=tk.EW, padx=20, pady=(8, 0))

  lbl_ten_songs = tb.Label(lf_tasks, text="刷完成歌曲次数")
  lbl_ten_songs.grid(row=3, column=0, sticky=tk.W, padx=20, pady=(8, 16))
  btn_run_ten_songs = tb.Button(lf_tasks, text="▶", width=2, padding=0, bootstyle="secondary-toolbutton", command=_on_ten_songs)  # type: ignore[call-arg]
  btn_run_ten_songs.grid(row=3, column=1, sticky=tk.W, padx=(4, 12), pady=(8, 16))

  # 让容器在放大时保留边距（拉伸占位到最右侧）
  lf_tasks.grid_columnconfigure(12, weight=1)
