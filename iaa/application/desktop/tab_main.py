import tkinter as tk
import queue
import threading

import ttkbootstrap as tb
from tkinter import messagebox
from tkinter import filedialog
import os
import shutil

from .index import DesktopApp
from .tab_conf import SONG_KEEP_UNCHANGED, SONG_NAME_OPTIONS, normalize_song_name_input
from iaa.context import hub as progress_hub
from iaa.progress import TaskProgressEvent
from iaa.tasks.live.live import SingleLoopPlan, ListLoopPlan
from iaa.config.live_presets import AutoLivePreset, LivePresetManager


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

  # 预定义单任务运行按钮（稍后创建）
  btn_run_start_game = None
  btn_run_single_live = None
  btn_run_challenge_live = None
  btn_run_activity_story = None
  btn_run_cm = None
  btn_run_gift = None
  btn_run_area_convos = None
  btn_run_event_shop = None
  btn_run_mission_rewards = None
  btn_run_ten_songs = None
  btn_run_main_story = None
  export_state = {"busy": False, "prev_cursor": ""}

  def _set_export_busy(busy: bool) -> None:
    export_state["busy"] = busy
    if busy:
      try:
        export_state["prev_cursor"] = str(app.root.cget("cursor"))
      except Exception:
        export_state["prev_cursor"] = ""
      try:
        app.root.configure(cursor="watch")
      except Exception:
        pass
      try:
        btn_export.configure(text="导出中...", state=tk.DISABLED)
      except Exception:
        pass
    else:
      try:
        app.root.configure(cursor=export_state["prev_cursor"] or "")
      except Exception:
        pass
      try:
        btn_export.configure(text="导出报告", state=tk.NORMAL)
      except Exception:
        pass

  def _on_export_report() -> None:
    if export_state["busy"]:
      return

    _set_export_busy(True)
    progress_text_var.set("正在导出报告并抓取截图...")

    def _run_export() -> None:
      try:
        tmp_zip = app.service.export_report_zip()
      except Exception as e:  # noqa: BLE001
        app.root.after(0, lambda: _finish_export_error("导出失败", f"生成报告失败：{e}"))
        return
      app.root.after(0, lambda: _finish_export_success(tmp_zip))

    def _finish_export_error(title: str, text: str) -> None:
      _set_export_busy(False)
      progress_text_var.set("就绪")
      messagebox.showerror(title, text, parent=app.root)

    def _finish_export_success(tmp_zip: str) -> None:
      _set_export_busy(False)
      progress_text_var.set("请选择报告保存位置")
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
          progress_text_var.set("就绪")
          return
        shutil.copyfile(tmp_zip, save_path)
        progress_text_var.set("就绪")
        messagebox.showinfo("导出成功", "报告已保存。", parent=app.root)
      except Exception as e:  # noqa: BLE001
        progress_text_var.set("就绪")
        messagebox.showerror("保存失败", f"保存报告失败：{e}", parent=app.root)

    threading.Thread(target=_run_export, name="IAA-ExportReport", daemon=True).start()

  # 右侧导出按钮
  btn_export = tb.Button(lf_power, text="导出报告", bootstyle="secondary", command=_on_export_report)  # type: ignore[call-arg]

  def _refresh_power_button() -> None:
    sch = app.service.scheduler
    is_transition = sch.is_starting or sch.is_stopping
    btn_toggle.configure(state=(tk.DISABLED if is_transition else tk.NORMAL))
    if sch.is_stopping:
      status_state["stop_requested"] = True
    if sch.is_starting:
      btn_toggle.configure(text="启动中", bootstyle="secondary")  # type: ignore[call-arg]
      progress_text_var.set("初始化脚本中...")
    elif sch.is_stopping:
      btn_toggle.configure(text="停止中", bootstyle="secondary")  # type: ignore[call-arg]
      progress_text_var.set("正在尝试停止...")
    elif sch.running:
      btn_toggle.configure(text="停止", bootstyle="danger")  # type: ignore[call-arg]
    else:
      btn_toggle.configure(text="启动", bootstyle="success")  # type: ignore[call-arg]
      if status_state["stop_requested"] or status_state["stopped"]:
        progress_text_var.set("已停止")
        status_state["stop_requested"] = False
        status_state["stopped"] = False
      elif status_state["error_text"]:
        progress_text_var.set(str(status_state["error_text"]))
      else:
        progress_text_var.set("就绪")

    if is_transition:
      if not progress_bar_state["indeterminate"]:
        progress_bar.configure(mode="indeterminate")
        progress_bar.start(10)
        progress_bar_state["indeterminate"] = True
    else:
      if progress_bar_state["indeterminate"]:
        progress_bar.stop()
        progress_bar.configure(mode="determinate")
        progress_bar_state["indeterminate"] = False

    # 刷新单任务运行按钮状态
    try:
      is_run_disabled = is_transition or sch.running
      for b in (btn_run_start_game, btn_run_single_live, btn_run_challenge_live, btn_run_activity_story, btn_run_cm, btn_run_gift, btn_run_area_convos, btn_run_event_shop, btn_run_mission_rewards, btn_run_ten_songs, btn_run_main_story):
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
  btn_export.pack(side=tk.RIGHT, padx=(12, 12), pady=10)

  progress_text_var = tk.StringVar(value="就绪")
  progress_percent_var = tk.IntVar(value=0)
  status_state = {
    "stop_requested": False,
    "stopped": False,
    "error_text": None,
  }

  progress_row = tb.Frame(lf_power)
  progress_row.pack(side=tk.BOTTOM, fill=tk.X, padx=12, pady=(0, 10))
  tb.Label(progress_row, textvariable=progress_text_var).pack(anchor=tk.W)
  progress_bar = tb.Progressbar(progress_row, maximum=100, variable=progress_percent_var, mode="determinate")
  progress_bar.pack(fill=tk.X, pady=(4, 2))
  progress_bar_state = {"indeterminate": False}

  progress_event_queue: queue.Queue[TaskProgressEvent] = queue.Queue()
  unsubscribe_progress = progress_hub().subscribe(lambda event: progress_event_queue.put(event))

  def _to_int(value: object) -> int | None:
    try:
      return int(value)  # type: ignore[arg-type]
    except Exception:
      return None

  def _render_progress_event(event: TaskProgressEvent) -> None:
    payload = event.payload or {}

    current = _to_int(payload.get("current_steps"))
    total = _to_int(payload.get("total_steps"))
    percent = _to_int(payload.get("percent"))

    run_total_tasks = _to_int(payload.get("run_total_tasks"))
    run_completed_tasks = _to_int(payload.get("run_completed_tasks"))
    if run_total_tasks is not None and run_total_tasks > 0 and run_completed_tasks is not None:
      completed = max(0, min(run_total_tasks, run_completed_tasks))
      task_progress = 0
      if percent is not None:
        task_progress = max(0, min(100, percent))
      # 全任务进度 = 已完成任务 + 当前任务内部进度，避免多任务时进度条反复归零
      percent = int(((completed + (task_progress / 100.0)) / run_total_tasks) * 100)

    if percent is None and current is not None and total is not None and total > 0:
      percent = int(current * 100 / total)
    if event.type == "task_started" and percent is None:
      percent = 0
    elif event.type == "task_finished" and percent is None:
      percent = 100
    if percent is not None:
      progress_percent_var.set(max(0, min(100, percent)))

    message = payload.get("message")
    if not isinstance(message, str):
      message = ""
    phase_path = payload.get("phase_path")
    phase_parts: list[str] = []
    if isinstance(phase_path, list):
      for p in phase_path:
        if isinstance(p, dict):
          name = p.get('name', '')
          p_current = p.get('current')
          p_total = p.get('total')
          if isinstance(p_current, int) and isinstance(p_total, int):
            phase_parts.append(f"{name} ({p_current}/{p_total})")
          elif name:
            phase_parts.append(str(name))

    if event.type == "task_failed":
      err = payload.get("error")
      err_msg = str(err) if err is not None else ""
      if err_msg.lower() == "keyboardinterrupt":
        status_state["stopped"] = True
        status_state["error_text"] = None
        progress_text_var.set("已停止")
      else:
        error_text = f"执行「{event.task_name}」时出错：{err_msg or '未知错误'}"
        status_state["error_text"] = error_text
        status_state["stopped"] = False
        progress_text_var.set(error_text)
      return

    if event.type == "task_started":
      status_state["error_text"] = None
      status_state["stopped"] = False

    parts: list[str] = [event.task_name]
    parts.extend(phase_parts)
    if message:
      parts.append(message)
    display_text = " > ".join([p for p in parts if p])

    if display_text:
      progress_text_var.set(display_text)

  def _drain_progress_events() -> None:
    while True:
      try:
        event = progress_event_queue.get_nowait()
      except queue.Empty:
        break
      _render_progress_event(event)

  def _schedule_refresh_loop() -> None:
    try:
      _drain_progress_events()
      _refresh_power_button()
      # 周期性刷新按钮状态（窗口仍存在时才继续）
      if parent.winfo_exists():
        parent.after(300, _schedule_refresh_loop)
    except tk.TclError:
      # 窗口销毁后可能触发异常，安全忽略
      pass

  progress_unsubscribed = False
  def _on_parent_destroy(event: tk.Event) -> None:
    nonlocal progress_unsubscribed
    if progress_unsubscribed:
      return
    if event.widget is parent:
      unsubscribe_progress()
      progress_unsubscribed = True

  parent.bind("<Destroy>", _on_parent_destroy, add="+")
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
  var_event_shop = tk.BooleanVar(value=bool(getattr(conf.scheduler, 'event_shop_enabled', True)))
  var_mission_rewards = tk.BooleanVar(value=bool(getattr(conf.scheduler, 'mission_rewards_enabled', True)))
  app.store.var_start_game = var_start_game
  app.store.var_single_live = var_single_live
  app.store.var_challenge_live = var_challenge_live
  app.store.var_activity_story = var_activity_story
  app.store.var_auto_cm = var_auto_cm
  app.store.var_gift = var_gift
  app.store.var_area_convos = var_area_convos
  app.store.var_event_shop = var_event_shop
  app.store.var_mission_rewards = var_mission_rewards

  def _save_scheduler() -> None:
    conf.scheduler.start_game_enabled = bool(var_start_game.get())
    conf.scheduler.solo_live_enabled = bool(var_single_live.get())
    conf.scheduler.challenge_live_enabled = bool(var_challenge_live.get())
    conf.scheduler.activity_story_enabled = bool(var_activity_story.get())
    conf.scheduler.cm_enabled = bool(var_auto_cm.get())
    conf.scheduler.gift_enabled = bool(var_gift.get())
    conf.scheduler.area_convos_enabled = bool(var_area_convos.get())
    conf.scheduler.event_shop_enabled = bool(var_event_shop.get())
    conf.scheduler.mission_rewards_enabled = bool(var_mission_rewards.get())
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
  cb_event_shop = tb.Checkbutton(lf_tasks, text="活动商店", variable=var_event_shop, command=_save_scheduler)
  cb_mission_rewards = tb.Checkbutton(lf_tasks, text="任务奖励", variable=var_mission_rewards, command=_save_scheduler)

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

  cb_event_shop.grid(row=1, column=4, sticky=tk.W, padx=20, pady=(8, 8))
  btn_run_event_shop = tb.Button(lf_tasks, text="▶", width=2, padding=0, bootstyle="secondary-toolbutton", command=lambda: _on_run("event_shop"))  # type: ignore[call-arg]
  btn_run_event_shop.grid(row=1, column=5, sticky=tk.W, padx=(4, 12), pady=(8, 8))

  cb_mission_rewards.grid(row=1, column=6, sticky=tk.W, padx=20, pady=(8, 8))
  btn_run_mission_rewards = tb.Button(lf_tasks, text="▶", width=2, padding=0, bootstyle="secondary-toolbutton", command=lambda: _on_run("mission_rewards"))  # type: ignore[call-arg]
  btn_run_mission_rewards.grid(row=1, column=7, sticky=tk.W, padx=(4, 12), pady=(8, 8))

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
    auto_set_unit_var = tk.BooleanVar(value=bool(conf.live.auto_set_unit))
    ap_multiplier_var = tk.StringVar(
      value=("保持现状" if conf.live.ap_multiplier is None else str(conf.live.ap_multiplier))
    )
    song_name_var = tk.StringVar(value=(conf.live.song_name or SONG_KEEP_UNCHANGED))
    last_single_song_name = {"value": song_name_var.get()}

    # 内置预设定义
    BUILTIN_PRESETS: dict[str, AutoLivePreset] = {
      "clear": AutoLivePreset(
        name="CLEAR 10 首歌",
        plan=ListLoopPlan(
          loop_count=10,
          play_mode='game_auto',
          ap_multiplier=1,
        )
      ),
      "fc": AutoLivePreset(
        name="FC 10 次",
        plan=SingleLoopPlan(
          loop_count=10,
          play_mode='script_auto',
          ap_multiplier=0,
        )
      ),
      "leader": AutoLivePreset(
        name="队长次数",
        plan=SingleLoopPlan(
          loop_count=30,
          play_mode='script_auto',
          ap_multiplier=0,
        )
      ),
    }

    def apply_preset(preset: AutoLivePreset) -> None:
      """统一的预设应用函数"""
      plan = preset.plan
      
      # 应用次数
      if plan.loop_count is None:
        count_mode_var.set("all")
        count_var.set("10")
      else:
        count_mode_var.set("specify")
        count_var.set(str(plan.loop_count))
      
      # 应用循环模式
      if isinstance(plan, SingleLoopPlan):
        loop_mode_var.set("single")
        # 应用歌曲选择
        if plan.song_select_mode == 'specified' and plan.song_name:
          song_name_var.set(plan.song_name)
        else:
          song_name_var.set(SONG_KEEP_UNCHANGED)
      elif isinstance(plan, ListLoopPlan):
        if plan.loop_song_mode == 'random':
          loop_mode_var.set("random")
        else:
          loop_mode_var.set("list")
        song_name_var.set("")
      
      # 应用其他设置
      auto_mode_var.set(plan.play_mode)
      debug_enabled_var.set(plan.debug_enabled)
      auto_set_unit_var.set(plan.auto_set_unit)
      
      if plan.ap_multiplier is None:
        ap_multiplier_var.set("保持现状")
      else:
        ap_multiplier_var.set(str(plan.ap_multiplier))
      
      _sync_count_state()
      _sync_loop_mode_state()

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

    def _apply_last_preset() -> None:
      manager = LivePresetManager()
      preset = manager.load_last_auto()
      if preset is None:
        messagebox.showinfo("提示", "没有找到上次设定", parent=win)
        return
      apply_preset(preset)

    row_preset = tb.Frame(body)
    row_preset.grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
    tb.Label(row_preset, text="预设：", width=8, anchor=tk.W).pack(side=tk.LEFT)
    tb.Button(row_preset, text="上次设定", command=_apply_last_preset).pack(side=tk.LEFT, padx=(8, 8))
    tb.Button(row_preset, text="CLEAR 10 首歌", command=lambda: apply_preset(BUILTIN_PRESETS["clear"])).pack(side=tk.LEFT, padx=(0, 8))
    tb.Button(row_preset, text="FC 10 次", command=lambda: apply_preset(BUILTIN_PRESETS["fc"])).pack(side=tk.LEFT, padx=(0, 8))
    tb.Button(row_preset, text="队长次数", command=lambda: apply_preset(BUILTIN_PRESETS["leader"])).pack(side=tk.LEFT)

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
    tb.Radiobutton(row_loop, text="列表顺序", value="list", variable=loop_mode_var).pack(side=tk.LEFT, padx=(0, 12))
    tb.Radiobutton(row_loop, text="列表随机", value="random", variable=loop_mode_var).pack(side=tk.LEFT)

    row_auto = tb.Frame(body)
    row_auto.grid(row=4, column=0, sticky=tk.W, pady=(0, 10))
    tb.Label(row_auto, text="自动模式：", width=8, anchor=tk.W).pack(side=tk.LEFT)
    tb.Radiobutton(row_auto, text="游戏自动", value="game_auto", variable=auto_mode_var).pack(side=tk.LEFT, padx=(8, 12))
    tb.Radiobutton(row_auto, text="脚本自动", value="script_auto", variable=auto_mode_var).pack(side=tk.LEFT)

    row_ap = tb.Frame(body)
    row_ap.grid(row=5, column=0, sticky=tk.W, pady=(0, 10))
    tb.Label(row_ap, text="AP 倍率：", width=8, anchor=tk.W).pack(side=tk.LEFT)
    cmb_ap_multiplier = tb.Combobox(
      row_ap,
      state="readonly",
      textvariable=ap_multiplier_var,
      values=["保持现状", *[str(i) for i in range(0, 11)]],
      width=24,
    )
    cmb_ap_multiplier.pack(side=tk.LEFT, padx=(8, 0))

    row_song = tb.Frame(body)
    row_song.grid(row=6, column=0, sticky=tk.W, pady=(0, 12))
    tb.Label(row_song, text="歌曲名称：", width=8, anchor=tk.W).pack(side=tk.LEFT)
    cmb_song_name = tb.Combobox(
      row_song,
      textvariable=song_name_var,
      values=SONG_NAME_OPTIONS,
      width=24,
    )
    cmb_song_name.pack(side=tk.LEFT, padx=(8, 0))

    row_debug = tb.Frame(body)
    row_debug.grid(row=7, column=0, sticky=tk.W, pady=(0, 12))
    tb.Checkbutton(row_debug, text="调试显示（脚本自动）", variable=debug_enabled_var).pack(side=tk.LEFT)

    row_auto_set_unit = tb.Frame(body)
    row_auto_set_unit.grid(row=8, column=0, sticky=tk.W, pady=(0, 12))
    tb.Checkbutton(row_auto_set_unit, text="自动编队", variable=auto_set_unit_var).pack(side=tk.LEFT)

    btn_bar = tb.Frame(body)
    btn_bar.grid(row=9, column=0, sticky=tk.E)

    def _sync_count_state() -> None:
      if count_mode_var.get() == "specify":
        ent_count.configure(state=tk.NORMAL)
      else:
        ent_count.configure(state=tk.DISABLED)

    def _sync_loop_mode_state(*_args) -> None:
      if loop_mode_var.get() in ("list", "random"):
        current_song_name = song_name_var.get().strip()
        if current_song_name:
          last_single_song_name["value"] = current_song_name
        song_name_var.set("")
        cmb_song_name.configure(state="disabled")
      else:
        if not song_name_var.get().strip():
          song_name_var.set(last_single_song_name["value"] or SONG_KEEP_UNCHANGED)
        cmb_song_name.configure(state="normal")

    last_auto_mode = auto_mode_var.get()

    def _on_auto_mode_change(*_args) -> None:
      nonlocal last_auto_mode
      current = auto_mode_var.get()
      if current == "script_auto" and last_auto_mode != "script_auto":
        messagebox.showwarning(
          "提示",
          "使用“脚本自动”时必须满足：\n1.当前选中演出歌曲为 EASY 难度\n2. 流速为 1，特效为轻量\n3.使用 MuMu 模拟器且控制方法选择「nemu_ipc」，或其他模拟器选择「scrcpy」\n4.分辨率为 16:9，支持 1280x720 及其等比例缩放（如 1600x900、1920x1080）\n5. 使用脚本自动演出带来的一切风险与后果由使用者自行承担",
          parent=win,
        )
      if current == "script_auto":
        ap_multiplier_var.set("0")
        cmb_ap_multiplier.configure(state="disabled")
      else:
        cmb_ap_multiplier.configure(state="readonly")
      last_auto_mode = current

    auto_mode_var.trace_add("write", _on_auto_mode_change)
    loop_mode_var.trace_add("write", _sync_loop_mode_state)

    def _on_start() -> None:
      count: int | None = None
      if count_mode_var.get() == "specify":
        value = count_var.get().strip()
        if not value.isdigit() or int(value) <= 0:
          messagebox.showerror("参数错误", "指定次数必须为正整数。", parent=win)
          return
        count = int(value)
      
      # 解析 AP 倍率
      ap_mult_str = ap_multiplier_var.get()
      ap_mult: int | None = None if ap_mult_str == "保持现状" else int(ap_mult_str)
      
      # 解析歌曲名称
      song_name = normalize_song_name_input(song_name_var.get())
      
      # 构建 Plan 对象
      loop_mode = loop_mode_var.get()
      play_mode = "script_auto" if auto_mode_var.get() == "script_auto" else "game_auto"
      
      if loop_mode == "single":
        plan = SingleLoopPlan(
          loop_count=count,
          song_select_mode='specified' if song_name else 'current',
          song_name=song_name,
          play_mode=play_mode,
          debug_enabled=bool(debug_enabled_var.get()),
          ap_multiplier=ap_mult,
          auto_set_unit=bool(auto_set_unit_var.get()),
        )
      else:  # list or random
        plan = ListLoopPlan(
          loop_count=count,
          loop_song_mode='random' if loop_mode == "random" else 'list_next',
          play_mode=play_mode,
          debug_enabled=bool(debug_enabled_var.get()),
          ap_multiplier=ap_mult,
          auto_set_unit=bool(auto_set_unit_var.get()),
        )
      
      # 保存为上次设定
      preset = AutoLivePreset(name="上次设定", plan=plan)
      manager = LivePresetManager()
      manager.save_last_auto(preset)
      
      win.destroy()
      sch.run_single("auto_live", run_in_thread=True, kwargs={"plan": plan})
      _refresh_power_button()

    tb.Button(btn_bar, text="开始", bootstyle="primary", command=_on_start).pack(side=tk.LEFT, padx=(0, 8))  # type: ignore[call-arg]
    tb.Button(btn_bar, text="取消", command=win.destroy).pack(side=tk.LEFT)

    _sync_count_state()
    _sync_loop_mode_state()
    _on_auto_mode_change()
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
