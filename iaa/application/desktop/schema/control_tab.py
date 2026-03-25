from __future__ import annotations

import os
import queue
import shutil
import tkinter as tk
from dataclasses import dataclass
from tkinter import filedialog, messagebox

import ttkbootstrap as tb

from iaa.context import hub as progress_hub
from iaa.progress import TaskProgressEvent
from iaa.tasks.registry import list_task_infos

from .settings_tab import SONG_KEEP_UNCHANGED, SONG_NAME_OPTIONS, _normalize_song_name_input


@dataclass(frozen=True, slots=True)
class ToggleTaskMeta:
    """Metadata for toggle-able home tasks."""

    task_id: str
    label: str
    scheduler_flag: str


TOGGLE_TASKS: tuple[ToggleTaskMeta, ...] = (
    ToggleTaskMeta('start_game', '启动游戏', 'start_game_enabled'),
    ToggleTaskMeta('solo_live', '单人演出', 'solo_live_enabled'),
    ToggleTaskMeta('challenge_live', '挑战演出', 'challenge_live_enabled'),
    ToggleTaskMeta('activity_story', '活动剧情', 'activity_story_enabled'),
    ToggleTaskMeta('cm', '自动 CM', 'cm_enabled'),
    ToggleTaskMeta('gift', '领取礼物', 'gift_enabled'),
    ToggleTaskMeta('area_convos', '区域对话', 'area_convos_enabled'),
    ToggleTaskMeta('event_shop', '活动商店', 'event_shop_enabled'),
    ToggleTaskMeta('mission_rewards', '任务奖励', 'mission_rewards_enabled'),
)


def build_control_tab(app, parent: tk.Misc) -> None:
    """Build control tab using task metadata."""

    lf_power = tb.Labelframe(parent, text='启停')
    lf_power.pack(fill=tk.X, padx=8, pady=(8, 12))

    btn_toggle = tb.Button(lf_power, text='启动', bootstyle='success', width=10)  # type: ignore[call-arg]
    run_buttons: list[tb.Button] = []

    def _on_export_report() -> None:
        try:
            tmp_zip = app.service.export_report_zip()
        except Exception as error:  # noqa: BLE001
            messagebox.showerror('导出失败', f'生成报告失败：{error}', parent=app.root)
            return
        try:
            initial_name = os.path.basename(tmp_zip)
            save_path = filedialog.asksaveasfilename(
                title='保存报告',
                defaultextension='.zip',
                initialfile=initial_name,
                filetypes=[('Zip 文件', '*.zip')],
                parent=app.root,
            )
            if not save_path:
                return
            shutil.copyfile(tmp_zip, save_path)
            messagebox.showinfo('导出成功', '报告已保存。', parent=app.root)
        except Exception as error:  # noqa: BLE001
            messagebox.showerror('保存失败', f'保存报告失败：{error}', parent=app.root)

    btn_export = tb.Button(lf_power, text='导出报告', bootstyle='secondary', command=_on_export_report)  # type: ignore[call-arg]

    progress_text_var = tk.StringVar(value='就绪')
    progress_percent_var = tk.IntVar(value=0)
    status_state = {'stop_requested': False, 'stopped': False, 'error_text': None}

    progress_row = tb.Frame(lf_power)
    progress_row.pack(side=tk.BOTTOM, fill=tk.X, padx=12, pady=(0, 10))
    tb.Label(progress_row, textvariable=progress_text_var).pack(anchor=tk.W)
    progress_bar = tb.Progressbar(progress_row, maximum=100, variable=progress_percent_var, mode='determinate')
    progress_bar.pack(fill=tk.X, pady=(4, 2))
    progress_bar_state = {'indeterminate': False}

    def _refresh_power_button() -> None:
        sch = app.service.scheduler
        is_transition = sch.is_starting or sch.is_stopping
        btn_toggle.configure(state=(tk.DISABLED if is_transition else tk.NORMAL))

        if sch.is_stopping:
            status_state['stop_requested'] = True

        if sch.is_starting:
            btn_toggle.configure(text='启动中', bootstyle='secondary')  # type: ignore[call-arg]
            progress_text_var.set('初始化脚本中...')
        elif sch.is_stopping:
            btn_toggle.configure(text='停止中', bootstyle='secondary')  # type: ignore[call-arg]
            progress_text_var.set('正在尝试停止...')
        elif sch.running:
            btn_toggle.configure(text='停止', bootstyle='danger')  # type: ignore[call-arg]
        else:
            btn_toggle.configure(text='启动', bootstyle='success')  # type: ignore[call-arg]
            if status_state['stop_requested'] or status_state['stopped']:
                progress_text_var.set('已停止')
                status_state['stop_requested'] = False
                status_state['stopped'] = False
            elif status_state['error_text']:
                progress_text_var.set(str(status_state['error_text']))
            else:
                progress_text_var.set('就绪')

        if is_transition and not progress_bar_state['indeterminate']:
            progress_bar.configure(mode='indeterminate')
            progress_bar.start(10)
            progress_bar_state['indeterminate'] = True
        elif (not is_transition) and progress_bar_state['indeterminate']:
            progress_bar.stop()
            progress_bar.configure(mode='determinate')
            progress_bar_state['indeterminate'] = False

        is_run_disabled = is_transition or sch.running
        for button in run_buttons:
            button.configure(state=(tk.DISABLED if is_run_disabled else tk.NORMAL))

    def _on_toggle() -> None:
        sch = app.service.scheduler
        if sch.is_starting or sch.is_stopping:
            return
        if sch.running:
            app.on_stop()
        else:
            app.on_start()
        _refresh_power_button()

    btn_toggle.configure(command=_on_toggle)
    btn_toggle.pack(side=tk.LEFT, padx=(12, 8), pady=10)
    btn_export.pack(side=tk.RIGHT, padx=(12, 12), pady=10)

    progress_event_queue: queue.Queue[TaskProgressEvent] = queue.Queue()
    unsubscribe_progress = progress_hub().subscribe(lambda event: progress_event_queue.put(event))

    def _to_int(value: object) -> int | None:
        try:
            return int(value)  # type: ignore[arg-type]
        except Exception:
            return None

    def _render_progress_event(event: TaskProgressEvent) -> None:
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
            progress_percent_var.set(max(0, min(100, percent)))

        message = payload.get('message')
        if not isinstance(message, str):
            message = ''

        phase_path = payload.get('phase_path')
        phase_parts: list[str] = []
        if isinstance(phase_path, list):
            phase_parts = [str(part) for part in phase_path if isinstance(part, str) and part]

        if event.type == 'task_failed':
            err = payload.get('error')
            err_msg = str(err) if err is not None else ''
            if err_msg.lower() == 'keyboardinterrupt':
                status_state['stopped'] = True
                status_state['error_text'] = None
                progress_text_var.set('已停止')
            else:
                error_text = f'执行「{event.task_name}」时出错：{err_msg or "未知错误"}'
                status_state['error_text'] = error_text
                status_state['stopped'] = False
                progress_text_var.set(error_text)
            return

        if event.type == 'task_started':
            status_state['error_text'] = None
            status_state['stopped'] = False

        parts: list[str] = [event.task_name]
        parts.extend(phase_parts)
        if message:
            parts.append(message)

        display_text = ' > '.join([part for part in parts if part])
        if current is not None:
            display_text = f'{display_text} ({current}/{total})' if total is not None else f'{display_text} ({current})'

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
            if parent.winfo_exists():
                parent.after(300, _schedule_refresh_loop)
        except tk.TclError:
            pass

    progress_unsubscribed = False

    def _on_parent_destroy(event: tk.Event) -> None:
        nonlocal progress_unsubscribed
        if progress_unsubscribed:
            return
        if event.widget is parent:
            unsubscribe_progress()
            progress_unsubscribed = True

    parent.bind('<Destroy>', _on_parent_destroy, add='+')
    _schedule_refresh_loop()

    lf_tasks = tb.Labelframe(parent, text='任务')
    lf_tasks.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

    conf = app.service.config.conf
    scheduler_conf = conf.scheduler
    task_vars: dict[str, tk.BooleanVar] = {}

    for meta in TOGGLE_TASKS:
        if hasattr(scheduler_conf, meta.scheduler_flag):
            task_vars[meta.task_id] = tk.BooleanVar(value=bool(getattr(scheduler_conf, meta.scheduler_flag)))

    def _save_scheduler() -> None:
        for meta in TOGGLE_TASKS:
            if meta.task_id not in task_vars:
                continue
            setattr(scheduler_conf, meta.scheduler_flag, bool(task_vars[meta.task_id].get()))
        app.service.config.save()

    def _on_run(task_id: str) -> None:
        sch = app.service.scheduler
        if sch.is_starting or sch.is_stopping or sch.running:
            return
        sch.run_single(task_id, run_in_thread=True)
        _refresh_power_button()

    ordered_toggles = [meta for meta in TOGGLE_TASKS if meta.task_id in task_vars]
    for index, meta in enumerate(ordered_toggles):
        row = index // 5
        col = (index % 5) * 2
        cb = tb.Checkbutton(lf_tasks, text=meta.label, variable=task_vars[meta.task_id], command=_save_scheduler)
        cb.grid(row=row, column=col, sticky=tk.W, padx=20, pady=(16 if row == 0 else 8, 8))
        run_btn = tb.Button(
            lf_tasks,
            text='▶',
            width=2,
            padding=0,
            bootstyle='secondary-toolbutton',
            command=lambda task_id=meta.task_id: _on_run(task_id),
        )  # type: ignore[call-arg]
        run_btn.grid(row=row, column=col + 1, sticky=tk.W, padx=(4, 12), pady=(16 if row == 0 else 8, 8))
        run_buttons.append(run_btn)

    sep = tb.Separator(lf_tasks, orient=tk.HORIZONTAL)
    sep.grid(row=2, column=0, columnspan=13, sticky=tk.EW, padx=20, pady=(8, 0))

    def _open_auto_live_dialog() -> None:
        sch = app.service.scheduler
        if sch.is_starting or sch.is_stopping or sch.running:
            return

        win = tk.Toplevel(app.root)
        win.title('自动演出')
        win.transient(app.root)
        win.grab_set()
        win.resizable(False, False)

        body = tb.Frame(win, padding=16)
        body.pack(fill=tk.BOTH, expand=True)
        body.grid_columnconfigure(0, weight=1)

        count_mode_var = tk.StringVar(value='specify')
        count_var = tk.StringVar(value='10')
        loop_mode_var = tk.StringVar(value='list')
        auto_mode_var = tk.StringVar(value='game_auto')
        debug_enabled_var = tk.BooleanVar(value=False)
        ap_multiplier_var = tk.StringVar(value=('保持现状' if conf.live.ap_multiplier is None else str(conf.live.ap_multiplier)))
        song_name_var = tk.StringVar(value=(conf.live.song_name or SONG_KEEP_UNCHANGED))
        last_single_song_name = {'value': song_name_var.get()}

        def _center_window() -> None:
            win.update_idletasks()
            width = win.winfo_width()
            height = win.winfo_height()
            root_x = app.root.winfo_rootx()
            root_y = app.root.winfo_rooty()
            root_w = app.root.winfo_width()
            root_h = app.root.winfo_height()
            if root_w > 1 and root_h > 1:
                x = root_x + (root_w - width) // 2
                y = root_y + (root_h - height) // 2
            else:
                x = (win.winfo_screenwidth() - width) // 2
                y = (win.winfo_screenheight() - height) // 2
            win.geometry(f'+{max(0, x)}+{max(0, y)}')

        def _sync_count_state() -> None:
            ent_count.configure(state=(tk.NORMAL if count_mode_var.get() == 'specify' else tk.DISABLED))

        def _sync_loop_mode_state(*_args: object) -> None:
            if loop_mode_var.get() in ('list', 'random'):
                current_song_name = song_name_var.get().strip()
                if current_song_name:
                    last_single_song_name['value'] = current_song_name
                song_name_var.set('')
                cmb_song_name.configure(state='disabled')
            else:
                if not song_name_var.get().strip():
                    song_name_var.set(last_single_song_name['value'] or SONG_KEEP_UNCHANGED)
                cmb_song_name.configure(state='normal')

        last_auto_mode = auto_mode_var.get()

        def _on_auto_mode_change(*_args: object) -> None:
            nonlocal last_auto_mode
            current = auto_mode_var.get()
            if current == 'script_auto' and last_auto_mode != 'script_auto':
                messagebox.showwarning(
                    '提示',
                    '使用“脚本自动”时必须满足：\n1.当前选中演出歌曲为 EASY 难度\n2. 流速为 1，特效为轻量\n3.使用 MuMu 模拟器且控制方法选择「nemu_ipc」\n4.分辨率为 16:9，支持 1280x720 及其等比例缩放（如 1600x900、1920x1080）\n5. 使用脚本自动演出带来的一切风险与后果由使用者自行承担',
                    parent=win,
                )
            if current == 'script_auto':
                ap_multiplier_var.set('0')
                cmb_ap_multiplier.configure(state='disabled')
            else:
                cmb_ap_multiplier.configure(state='readonly')
            last_auto_mode = current

        row_preset = tb.Frame(body)
        row_preset.grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
        tb.Label(row_preset, text='预设：', width=8, anchor=tk.W).pack(side=tk.LEFT)

        def _apply_preset_clear() -> None:
            count_mode_var.set('specify')
            count_var.set('10')
            loop_mode_var.set('list')
            auto_mode_var.set('game_auto')
            ap_multiplier_var.set('1')
            _sync_count_state()

        def _apply_preset_fc() -> None:
            count_mode_var.set('specify')
            count_var.set('10')
            loop_mode_var.set('single')
            auto_mode_var.set('script_auto')
            ap_multiplier_var.set('0')
            _sync_count_state()

        def _apply_preset_leader() -> None:
            count_mode_var.set('specify')
            count_var.set('30')
            loop_mode_var.set('single')
            auto_mode_var.set('script_auto')
            ap_multiplier_var.set('0')
            _sync_count_state()

        tb.Button(row_preset, text='CLEAR 10 首歌', command=_apply_preset_clear).pack(side=tk.LEFT, padx=(8, 8))
        tb.Button(row_preset, text='FC 10 次', command=_apply_preset_fc).pack(side=tk.LEFT, padx=(0, 8))
        tb.Button(row_preset, text='队长次数', command=_apply_preset_leader).pack(side=tk.LEFT)

        tb.Separator(body, orient=tk.HORIZONTAL).grid(row=1, column=0, sticky=tk.EW, pady=(0, 10))

        row_count = tb.Frame(body)
        row_count.grid(row=2, column=0, sticky=tk.W, pady=(0, 10))
        tb.Label(row_count, text='演出次数：', width=8, anchor=tk.W).pack(side=tk.LEFT)
        tb.Radiobutton(row_count, text='指定次数', value='specify', variable=count_mode_var, command=_sync_count_state).pack(side=tk.LEFT, padx=(8, 6))
        ent_count = tb.Entry(row_count, textvariable=count_var, width=8)
        ent_count.pack(side=tk.LEFT, padx=(0, 10))
        tb.Radiobutton(row_count, text='直到 AP 耗尽', value='all', variable=count_mode_var, command=_sync_count_state).pack(side=tk.LEFT)

        row_loop = tb.Frame(body)
        row_loop.grid(row=3, column=0, sticky=tk.W, pady=(0, 10))
        tb.Label(row_loop, text='循环模式：', width=8, anchor=tk.W).pack(side=tk.LEFT)
        tb.Radiobutton(row_loop, text='单曲循环', value='single', variable=loop_mode_var).pack(side=tk.LEFT, padx=(8, 12))
        tb.Radiobutton(row_loop, text='列表顺序', value='list', variable=loop_mode_var).pack(side=tk.LEFT, padx=(0, 12))
        tb.Radiobutton(row_loop, text='列表随机', value='random', variable=loop_mode_var).pack(side=tk.LEFT)

        row_auto = tb.Frame(body)
        row_auto.grid(row=4, column=0, sticky=tk.W, pady=(0, 10))
        tb.Label(row_auto, text='自动模式：', width=8, anchor=tk.W).pack(side=tk.LEFT)
        tb.Radiobutton(row_auto, text='游戏自动', value='game_auto', variable=auto_mode_var).pack(side=tk.LEFT, padx=(8, 12))
        tb.Radiobutton(row_auto, text='脚本自动', value='script_auto', variable=auto_mode_var).pack(side=tk.LEFT)

        row_ap = tb.Frame(body)
        row_ap.grid(row=5, column=0, sticky=tk.W, pady=(0, 10))
        tb.Label(row_ap, text='AP 倍率：', width=8, anchor=tk.W).pack(side=tk.LEFT)
        cmb_ap_multiplier = tb.Combobox(row_ap, state='readonly', textvariable=ap_multiplier_var, values=['保持现状', *[str(i) for i in range(0, 11)]], width=24)
        cmb_ap_multiplier.pack(side=tk.LEFT, padx=(8, 0))

        row_song = tb.Frame(body)
        row_song.grid(row=6, column=0, sticky=tk.W, pady=(0, 12))
        tb.Label(row_song, text='歌曲名称：', width=8, anchor=tk.W).pack(side=tk.LEFT)
        cmb_song_name = tb.Combobox(row_song, textvariable=song_name_var, values=SONG_NAME_OPTIONS, width=24)
        cmb_song_name.pack(side=tk.LEFT, padx=(8, 0))

        row_debug = tb.Frame(body)
        row_debug.grid(row=7, column=0, sticky=tk.W, pady=(0, 12))
        tb.Checkbutton(row_debug, text='调试显示（脚本自动）', variable=debug_enabled_var).pack(side=tk.LEFT)

        btn_bar = tb.Frame(body)
        btn_bar.grid(row=8, column=0, sticky=tk.E)

        def _on_start_auto_live() -> None:
            run_count = None
            if count_mode_var.get() == 'specify':
                value = count_var.get().strip()
                if not value.isdigit() or int(value) <= 0:
                    messagebox.showerror('参数错误', '指定次数必须为正整数。', parent=win)
                    return
                run_count = int(value)

            kwargs = {
                'run_count': run_count,
                'cycle_mode': loop_mode_var.get(),
                'play_mode': ('script_auto' if auto_mode_var.get() == 'script_auto' else 'game_auto'),
                'debug_enabled': bool(debug_enabled_var.get()),
                'ap_multiplier': (None if ap_multiplier_var.get() == '保持现状' else int(ap_multiplier_var.get())),
                'song_name': _normalize_song_name_input(song_name_var.get()),
            }
            win.destroy()
            app.service.scheduler.run_single('auto_live', run_in_thread=True, kwargs=kwargs)
            _refresh_power_button()

        tb.Button(btn_bar, text='开始', bootstyle='primary', command=_on_start_auto_live).pack(side=tk.LEFT, padx=(0, 8))  # type: ignore[call-arg]
        tb.Button(btn_bar, text='取消', command=win.destroy).pack(side=tk.LEFT)

        auto_mode_var.trace_add('write', _on_auto_mode_change)
        loop_mode_var.trace_add('write', _sync_loop_mode_state)
        _sync_count_state()
        _sync_loop_mode_state()
        _on_auto_mode_change()
        _center_window()

    def _run_main_story() -> None:
        sch = app.service.scheduler
        if sch.is_starting or sch.is_stopping:
            return
        confirm = messagebox.askyesno(
            '确认开始',
            '即将开始刷往期剧情，脚本会无限执行（即使所有剧情都已完成），需要手动停止。是否继续？',
            parent=app.root,
        )
        if not confirm:
            return
        sch.run_single('main_story', run_in_thread=True)
        _refresh_power_button()

    manual_actions = [
        ('自动演出', _open_auto_live_dialog),
        ('刷往期剧情', _run_main_story),
    ]

    base_row = (len(ordered_toggles) - 1) // 5 + 1
    for index, (label, callback) in enumerate(manual_actions):
        row_index = base_row + index
        lbl = tb.Label(lf_tasks, text=label)
        lbl.grid(row=row_index, column=0, sticky=tk.W, padx=20, pady=(8 if index == 0 else 0, 16))
        btn = tb.Button(lf_tasks, text='▶', width=2, padding=0, bootstyle='secondary-toolbutton', command=callback)  # type: ignore[call-arg]
        btn.grid(row=row_index, column=1, sticky=tk.W, padx=(4, 12), pady=(8 if index == 0 else 0, 16))
        run_buttons.append(btn)

    lf_tasks.grid_columnconfigure(12, weight=1)

    # Keep this access to maintain compatibility with existing app store readers.
    for meta in TOGGLE_TASKS:
        var = task_vars.get(meta.task_id)
        if var is not None:
            setattr(app.store, f'var_{meta.task_id}', var)

    # Publish available task infos for debugging or future UI actions.
    app.store.task_infos = [info for info in list_task_infos() if info.task_id != '_dump_item']
