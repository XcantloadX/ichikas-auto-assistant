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
  btn_run_main_story = None

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
      for b in (btn_run_start_game, btn_run_single_live, btn_run_challenge_live, btn_run_activity_story, btn_run_cm, btn_run_gift, btn_run_area_convos, btn_run_ten_songs, btn_run_main_story):
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

  def _on_auto_live() -> None:
    sch = app.service.scheduler
    if sch.is_starting or sch.is_stopping or sch.running:
      return

    win = tk.Toplevel(app.root)
    win.title("自动演出")
    win.transient(app.root)
    win.grab_set()
    win.resizable(False, False)

    body = tb.Frame(win, padding=16)
    body.pack(fill=tk.BOTH, expand=True)
    body.grid_columnconfigure(0, weight=1)

    count_mode_var = tk.StringVar(value="specify")
    count_var = tk.StringVar(value="10")
    loop_mode_var = tk.StringVar(value="list")
    auto_mode_var = tk.StringVar(value="game_auto")
    debug_enabled_var = tk.BooleanVar(value=False)

    def _center_window() -> None:
      win.update_idletasks()
      w = win.winfo_width()
      h = win.winfo_height()
      root_x = app.root.winfo_rootx()
      root_y = app.root.winfo_rooty()
      root_w = app.root.winfo_width()
      root_h = app.root.winfo_height()
      if root_w > 1 and root_h > 1:
        x = root_x + (root_w - w) // 2
        y = root_y + (root_h - h) // 2
      else:
        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
      win.geometry(f"+{max(0, x)}+{max(0, y)}")

    def _apply_preset_clear() -> None:
      count_mode_var.set("specify")
      count_var.set("10")
      loop_mode_var.set("list")
      auto_mode_var.set("game_auto")
      _sync_count_state()

    def _apply_preset_fc() -> None:
      count_mode_var.set("specify")
      count_var.set("10")
      loop_mode_var.set("single")
      auto_mode_var.set("script_auto")
      _sync_count_state()

    def _apply_preset_leader() -> None:
      count_mode_var.set("specify")
      count_var.set("30")
      loop_mode_var.set("single")
      auto_mode_var.set("script_auto")
      _sync_count_state()

    row_preset = tb.Frame(body)
    row_preset.grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
    tb.Label(row_preset, text="预设：", width=8, anchor=tk.W).pack(side=tk.LEFT)
    tb.Button(row_preset, text="CLEAR 10 首歌", command=_apply_preset_clear).pack(side=tk.LEFT, padx=(8, 8))
    tb.Button(row_preset, text="FC 10 次", command=_apply_preset_fc).pack(side=tk.LEFT, padx=(0, 8))
    tb.Button(row_preset, text="队长次数", command=_apply_preset_leader).pack(side=tk.LEFT)

    sep = tb.Separator(body, orient=tk.HORIZONTAL)
    sep.grid(row=1, column=0, sticky=tk.EW, pady=(0, 10))

    row_count = tb.Frame(body)
    row_count.grid(row=2, column=0, sticky=tk.W, pady=(0, 10))
    tb.Label(row_count, text="演出次数：", width=8, anchor=tk.W).pack(side=tk.LEFT)
    rb_count_specify = tb.Radiobutton(row_count, text="指定次数", value="specify", variable=count_mode_var, command=lambda: _sync_count_state())
    rb_count_specify.pack(side=tk.LEFT, padx=(8, 6))
    ent_count = tb.Entry(row_count, textvariable=count_var, width=8)
    ent_count.pack(side=tk.LEFT, padx=(0, 10))
    rb_count_all = tb.Radiobutton(row_count, text="直到 AP 耗尽", value="all", variable=count_mode_var, command=lambda: _sync_count_state())
    rb_count_all.pack(side=tk.LEFT)

    row_loop = tb.Frame(body)
    row_loop.grid(row=3, column=0, sticky=tk.W, pady=(0, 10))
    tb.Label(row_loop, text="循环模式：", width=8, anchor=tk.W).pack(side=tk.LEFT)
    tb.Radiobutton(row_loop, text="单曲循环", value="single", variable=loop_mode_var).pack(side=tk.LEFT, padx=(8, 12))
    tb.Radiobutton(row_loop, text="列表循环", value="list", variable=loop_mode_var).pack(side=tk.LEFT)

    row_song = tb.Frame(body)
    row_song.grid(row=4, column=0, sticky=tk.W, pady=(0, 10))
    tb.Label(row_song, text="演出歌曲：", width=8, anchor=tk.W).pack(side=tk.LEFT)
    cmb_song = tb.Combobox(row_song, values=["当前选中歌曲"], state="disabled", width=24)
    cmb_song.set("当前选中歌曲")
    cmb_song.pack(side=tk.LEFT, padx=(8, 0))

    row_auto = tb.Frame(body)
    row_auto.grid(row=5, column=0, sticky=tk.W, pady=(0, 10))
    tb.Label(row_auto, text="自动模式：", width=8, anchor=tk.W).pack(side=tk.LEFT)
    tb.Radiobutton(row_auto, text="无", value="none", variable=auto_mode_var).pack(side=tk.LEFT, padx=(8, 12))
    tb.Radiobutton(row_auto, text="游戏自动", value="game_auto", variable=auto_mode_var).pack(side=tk.LEFT, padx=(0, 12))
    tb.Radiobutton(row_auto, text="脚本自动", value="script_auto", variable=auto_mode_var).pack(side=tk.LEFT)

    row_debug = tb.Frame(body)
    row_debug.grid(row=6, column=0, sticky=tk.W, pady=(0, 12))
    tb.Checkbutton(row_debug, text="调试显示（脚本自动）", variable=debug_enabled_var).pack(side=tk.LEFT)

    btn_bar = tb.Frame(body)
    btn_bar.grid(row=7, column=0, sticky=tk.E)

    def _sync_count_state() -> None:
      if count_mode_var.get() == "specify":
        ent_count.configure(state=tk.NORMAL)
      else:
        ent_count.configure(state=tk.DISABLED)

    last_auto_mode = auto_mode_var.get()

    def _on_auto_mode_change(*_args) -> None:
      nonlocal last_auto_mode
      current = auto_mode_var.get()
      if current == "script_auto" and last_auto_mode != "script_auto":
        messagebox.showwarning(
          "提示",
          "使用“脚本自动”时必须满足：\n1.当前选中演出歌曲为 EASY 难度\n2. 流速为 1，特效为轻量\n3.使用 MuMu 模拟器且控制方法选择「nemu_ipc」\n4. 使用脚本自动演出带来的一切风险与后果由使用者自行承担",
          parent=win,
        )
      last_auto_mode = current

    auto_mode_var.trace_add("write", _on_auto_mode_change)

    def _on_start() -> None:
      count: int | None = None
      if count_mode_var.get() == "specify":
        value = count_var.get().strip()
        if not value.isdigit() or int(value) <= 0:
          messagebox.showerror("参数错误", "指定次数必须为正整数。", parent=win)
          return
        count = int(value)
      kwargs = {
        "count_mode": ("specify" if count_mode_var.get() == "specify" else "all"),
        "count": count,
        "loop_mode": ("single" if loop_mode_var.get() == "single" else "list"),
        "auto_mode": (
          "none"
          if auto_mode_var.get() == "none"
          else ("script_auto" if auto_mode_var.get() == "script_auto" else "game_auto")
        ),
        "debug_enabled": bool(debug_enabled_var.get()),
      }
      win.destroy()
      sch.run_single("auto_live", run_in_thread=True, kwargs=kwargs)
      _refresh_power_button()

    tb.Button(btn_bar, text="开始", bootstyle="primary", command=_on_start).pack(side=tk.LEFT, padx=(0, 8))  # type: ignore[call-arg]
    tb.Button(btn_bar, text="取消", command=win.destroy).pack(side=tk.LEFT)

    _sync_count_state()
    _center_window()

  def _on_main_story() -> None:
    sch = app.service.scheduler
    if sch.is_starting or sch.is_stopping:
      return
    confirm = messagebox.askyesno(
      "确认开始",
      "即将开始刷往期剧情，脚本会无限执行（即使所有剧情都已完成），需要手动停止。是否继续？",
      parent=app.root,
    )
    if not confirm:
      return
    sch.run_single("main_story", run_in_thread=True)
    _refresh_power_button()

  sep_ten_songs = tb.Separator(lf_tasks, orient=tk.HORIZONTAL)
  sep_ten_songs.grid(row=2, column=0, columnspan=13, sticky=tk.EW, padx=20, pady=(8, 0))

  lbl_ten_songs = tb.Label(lf_tasks, text="自动演出")
  lbl_ten_songs.grid(row=3, column=0, sticky=tk.W, padx=20, pady=(8, 16))
  btn_run_ten_songs = tb.Button(lf_tasks, text="▶", width=2, padding=0, bootstyle="secondary-toolbutton", command=_on_auto_live)  # type: ignore[call-arg]
  btn_run_ten_songs.grid(row=3, column=1, sticky=tk.W, padx=(4, 12), pady=(8, 16))

  lbl_main_story = tb.Label(lf_tasks, text="刷往期剧情")
  lbl_main_story.grid(row=4, column=0, sticky=tk.W, padx=20, pady=(0, 16))
  btn_run_main_story = tb.Button(lf_tasks, text="▶", width=2, padding=0, bootstyle="secondary-toolbutton", command=_on_main_story)  # type: ignore[call-arg]
  btn_run_main_story.grid(row=4, column=1, sticky=tk.W, padx=(4, 12), pady=(0, 16))

  # 让容器在放大时保留边距（拉伸占位到最右侧）
  lf_tasks.grid_columnconfigure(12, weight=1)
