import tkinter as tk

import ttkbootstrap as tb

from .index import DesktopApp
from typing import cast, Literal, Optional
from iaa.config.schemas import LinkAccountOptions, EmulatorOptions, GameCharacter, ChallengeLiveAward, CustomEmulatorData
from .toast import show_toast
from .advance_select import AdvanceSelect
from iaa.config.base import IaaConfig

# 显示与值映射
EMULATOR_DISPLAY_MAP: dict[EmulatorOptions, str] = {
  'mumu': 'MuMu',
  'custom': '自定义',
}
EMULATOR_VALUE_MAP: dict[str, EmulatorOptions] = {v: k for k, v in EMULATOR_DISPLAY_MAP.items()}

SERVER_DISPLAY_MAP: dict[Literal['jp'], str] = {
  'jp': '日服',
}
SERVER_VALUE_MAP: dict[str, Literal['jp']] = {v: k for k, v in SERVER_DISPLAY_MAP.items()}

LINK_DISPLAY_MAP: dict[LinkAccountOptions, str] = {
  'no': '不引继账号',
  'google_play': 'Google Play',
}
LINK_VALUE_MAP: dict[str, LinkAccountOptions] = {v: k for k, v in LINK_DISPLAY_MAP.items()}

CONTROL_IMPL_DISPLAY_MAP: dict[Literal['nemu_ipc', 'adb', 'uiautomator'], str] = {
  'nemu_ipc': 'Nemu IPC',
  'adb': 'ADB',
  'uiautomator': 'UIAutomator2',
}
CONTROL_IMPL_VALUE_MAP: dict[str, Literal['nemu_ipc', 'adb', 'uiautomator']] = {v: k for k, v in CONTROL_IMPL_DISPLAY_MAP.items()}


class ConfStore:
  def __init__(self):
    # 游戏设置
    self.emulator_var = tk.StringVar()
    self.server_var = tk.StringVar()
    self.link_var = tk.StringVar()
    self.control_impl_var = tk.StringVar()
    # 自定义模拟器设置
    self.custom_adb_ip_var = tk.StringVar()
    self.custom_adb_port_var = tk.StringVar()
    self.custom_ip_row: Optional[tb.Frame] = None
    self.custom_port_row: Optional[tb.Frame] = None
    # 演出设置
    self.song_var = tk.StringVar()
    self.fully_deplete_var = tk.BooleanVar()
    # 挑战演出设置
    self.challenge_char_vars: dict[GameCharacter, tk.BooleanVar] = {}
    self.challenge_award_var = tk.StringVar()
    # 分组多选组件实例
    self.challenge_select: Optional[AdvanceSelect[GameCharacter]] = None
    # 映射表（仅用于歌曲选择）
    self.song_display_to_value: dict[str, int] = {}
    # 奖励显示到值映射
    self.challenge_award_display_to_value: dict[str, ChallengeLiveAward] = {}


def build_game_config_group(parent: tk.Misc, conf: IaaConfig, store: ConfStore) -> None:
  frame = tb.Labelframe(parent, text="游戏设置")
  frame.pack(fill=tk.X, padx=16, pady=8)

  # 初始化变量
  emulator_key = conf.game.emulator
  server_key = conf.game.server
  link_key = conf.game.link_account
  control_impl_key = conf.game.control_impl
  store.emulator_var.set(EMULATOR_DISPLAY_MAP.get(emulator_key, 'MuMu'))
  store.server_var.set(SERVER_DISPLAY_MAP.get(server_key, '日服'))
  store.link_var.set(LINK_DISPLAY_MAP.get(link_key, '不引继账号'))
  store.control_impl_var.set(CONTROL_IMPL_DISPLAY_MAP.get(control_impl_key, 'Nemu IPC'))
  # 初始化自定义 ADB 设置
  custom_data = conf.game.emulator_data
  if emulator_key == 'custom' and custom_data is not None:
    store.custom_adb_ip_var.set(custom_data.adb_ip or '127.0.0.1')
    store.custom_adb_port_var.set(str(custom_data.adb_port or 5555))
  else:
    store.custom_adb_ip_var.set('127.0.0.1')
    store.custom_adb_port_var.set('5555')

  # 模拟器类型
  row = tb.Frame(frame)
  row.pack(fill=tk.X, padx=8, pady=8)
  tb.Label(row, text="模拟器类型", width=16, anchor=tk.W).pack(side=tk.LEFT)
  tb.Combobox(row, state="readonly", textvariable=store.emulator_var, values=list(EMULATOR_VALUE_MAP.keys()), width=28).pack(side=tk.LEFT)

  # 自定义 ADB IP（仅在选择“自定义”时显示）
  custom_ip_row = tb.Frame(frame)
  store.custom_ip_row = custom_ip_row
  tb.Label(custom_ip_row, text="ADB IP", width=16, anchor=tk.W).pack(side=tk.LEFT)
  tb.Entry(custom_ip_row, textvariable=store.custom_adb_ip_var, width=30).pack(side=tk.LEFT)

  # 自定义 ADB 端口（仅在选择“自定义”时显示）
  custom_port_row = tb.Frame(frame)
  store.custom_port_row = custom_port_row
  tb.Label(custom_port_row, text="ADB 端口", width=16, anchor=tk.W).pack(side=tk.LEFT)
  tb.Entry(custom_port_row, textvariable=store.custom_adb_port_var, width=30).pack(side=tk.LEFT)

  def _update_custom_rows(*_args) -> None:
    emu_val = EMULATOR_VALUE_MAP.get(store.emulator_var.get(), 'mumu')
    if emu_val == 'custom':
      if store.custom_ip_row:
        store.custom_ip_row.pack(fill=tk.X, padx=8, pady=8)
      if store.custom_port_row:
        store.custom_port_row.pack(fill=tk.X, padx=8, pady=8)
    else:
      if store.custom_ip_row:
        store.custom_ip_row.pack_forget()
      if store.custom_port_row:
        store.custom_port_row.pack_forget()

  # 监听选择变化并初始化显示
  try:
    store.emulator_var.trace_add('write', lambda *_: _update_custom_rows())
  except Exception:
    pass
  _update_custom_rows()

  # 服务器
  row = tb.Frame(frame)
  row.pack(fill=tk.X, padx=8, pady=8)
  tb.Label(row, text="服务器", width=16, anchor=tk.W).pack(side=tk.LEFT)
  tb.Combobox(row, state="readonly", textvariable=store.server_var, values=list(SERVER_VALUE_MAP.keys()), width=28).pack(side=tk.LEFT)

  # 引继账号
  row = tb.Frame(frame)
  row.pack(fill=tk.X, padx=8, pady=8)
  tb.Label(row, text="引继账号", width=16, anchor=tk.W).pack(side=tk.LEFT)
  tb.Combobox(row, state="readonly", textvariable=store.link_var, values=list(LINK_VALUE_MAP.keys()), width=28).pack(side=tk.LEFT)

  # 控制方式
  row = tb.Frame(frame)
  row.pack(fill=tk.X, padx=8, pady=8)
  tb.Label(row, text="控制方式", width=16, anchor=tk.W).pack(side=tk.LEFT)
  tb.Combobox(row, state="readonly", textvariable=store.control_impl_var, values=list(CONTROL_IMPL_DISPLAY_MAP.values()), width=28).pack(side=tk.LEFT)


def build_live_config_group(parent: tk.Misc, conf: IaaConfig, store: ConfStore) -> None:
  frame = tb.Labelframe(parent, text="演出设置")
  frame.pack(fill=tk.X, padx=16, pady=8)

  # 歌曲映射
  song_value_to_display = {
    -1: '保持不变',
    1: 'Tell Your World｜Tell Your World',
    47: 'メルト｜Melt',
    74: '独りんぼエンヴィー｜孑然妒火',
  }
  store.song_display_to_value = {v: k for k, v in song_value_to_display.items()}

  song_id = conf.live.song_id
  current_song_display = song_value_to_display[song_id] if isinstance(song_id, int) and song_id in song_value_to_display else '保持不变'
  store.song_var.set(current_song_display)
  store.fully_deplete_var.set(bool(conf.live.fully_deplete))

  # 歌曲下拉
  row = tb.Frame(frame)
  row.pack(fill=tk.X, padx=8, pady=8)
  tb.Label(row, text="歌曲", width=16, anchor=tk.W).pack(side=tk.LEFT)
  tb.Combobox(row, state="disabled", textvariable=store.song_var, values=list(store.song_display_to_value.keys()), width=28).pack(side=tk.LEFT)

  # 完全清空体力
  row = tb.Frame(frame)
  row.pack(fill=tk.X, padx=8, pady=8)
  tb.Checkbutton(row, text="完全清空体力", variable=store.fully_deplete_var).pack(side=tk.LEFT)


def build_challenge_live_config_group(parent: tk.Misc, conf: IaaConfig, store: ConfStore) -> None:
  frame = tb.Labelframe(parent, text="挑战演出设置")
  frame.pack(fill=tk.X, padx=16, pady=8)

  # 分组到角色列表
  groups: list[tuple[str, list[GameCharacter]]] = [
    ("VIRTUAL SINGER", [
      GameCharacter.Miku, GameCharacter.Rin, GameCharacter.Len,
      GameCharacter.Luka, GameCharacter.Meiko, GameCharacter.Kaito,
    ]),
    ("Leo/need", [GameCharacter.Ichika, GameCharacter.Saki, GameCharacter.Honami, GameCharacter.Shiho]),
    ("MORE MORE JUMP!", [GameCharacter.Minori, GameCharacter.Haruka, GameCharacter.Airi, GameCharacter.Shizuku]),
    ("Vivid BAD SQUAD", [GameCharacter.Kohane, GameCharacter.An, GameCharacter.Akito, GameCharacter.Toya]),
    ("ワンダーランズ×ショウタイム", [GameCharacter.Tsukasa, GameCharacter.Emu, GameCharacter.Nene, GameCharacter.Rui]),
    ("25時、ナイトコードで。", [GameCharacter.Kanade, GameCharacter.Mafuyu, GameCharacter.Ena, GameCharacter.Mizuki]),
  ]

  selected: list[GameCharacter] = list(conf.challenge_live.characters)

  row = tb.Frame(frame)
  row.pack(fill=tk.X, padx=8, pady=8)
  tb.Label(row, text="角色", width=16, anchor=tk.W).pack(side=tk.LEFT)
  grouped_options: list[tuple[str, list[tuple[GameCharacter, str]]]] = [
    (name, [(ch, ch.last_name_cn + ch.first_name_cn) for ch in chars]) for name, chars in groups
  ]
  select = AdvanceSelect[GameCharacter](row, groups=grouped_options, selected=selected, mutiple=False, placeholder="请选择角色")
  select.pack(side=tk.LEFT, fill=tk.X, expand=True)
  store.challenge_select = select

  # 奖励优先设置
  award_display_map = ChallengeLiveAward.display_map_cn()
  store.challenge_award_display_to_value = {v: k for k, v in award_display_map.items()}
  current_award_display = award_display_map.get(conf.challenge_live.award, "水晶")

  row = tb.Frame(frame)
  row.pack(fill=tk.X, padx=8, pady=8)
  tb.Label(row, text="奖励", width=16, anchor=tk.W).pack(side=tk.LEFT)
  store.challenge_award_var.set(current_award_display)
  tb.Combobox(row, state="readonly", textvariable=store.challenge_award_var, values=list(store.challenge_award_display_to_value.keys()), width=28).pack(side=tk.LEFT)


def build_settings_tab(app: DesktopApp, parent: tk.Misc) -> None:  # noqa: ARG001
  # 可滚动容器
  container = tb.Frame(parent)
  container.pack(fill=tk.BOTH, expand=True)

  canvas = tk.Canvas(container, highlightthickness=0)
  vscroll = tb.Scrollbar(container, orient=tk.VERTICAL, command=canvas.yview)
  canvas.configure(yscrollcommand=vscroll.set)

  inner = tb.Frame(canvas)
  inner_id = canvas.create_window((0, 0), window=inner, anchor=tk.NW)

  def _on_inner_config(event: tk.Event) -> None:
    canvas.configure(scrollregion=canvas.bbox("all"))

  def _on_canvas_config(event: tk.Event) -> None:
    canvas.itemconfigure(inner_id, width=canvas.winfo_width())

  inner.bind("<Configure>", _on_inner_config)
  canvas.bind("<Configure>", _on_canvas_config)

  # 鼠标滚轮（限制顶部/底部不超出）
  def _on_mousewheel(event: tk.Event):
    first, last = canvas.yview()
    if event.delta > 0 and first <= 0:
      return "break"
    if event.delta < 0 and last >= 1:
      return "break"
    canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    return "break"

  # Linux 鼠标滚轮
  def _on_mousewheel_up(event: tk.Event):
    first, _ = canvas.yview()
    if first <= 0:
      return "break"
    canvas.yview_scroll(-1, "units")
    return "break"

  def _on_mousewheel_down(event: tk.Event):
    _, last = canvas.yview()
    if last >= 1:
      return "break"
    canvas.yview_scroll(1, "units")
    return "break"

  def _bind_mousewheel(event: tk.Event) -> None:
    canvas.bind_all("<MouseWheel>", _on_mousewheel)
    canvas.bind_all("<Button-4>", _on_mousewheel_up)
    canvas.bind_all("<Button-5>", _on_mousewheel_down)

  def _unbind_mousewheel(event: tk.Event) -> None:
    canvas.unbind_all("<MouseWheel>")
    canvas.unbind_all("<Button-4>")
    canvas.unbind_all("<Button-5>")

  canvas.bind("<Enter>", _bind_mousewheel)
  canvas.bind("<Leave>", _unbind_mousewheel)

  canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
  vscroll.pack(side=tk.RIGHT, fill=tk.Y)

  # 当前配置
  conf = app.service.config.conf

  # 顶部操作区：保存
  actions = tb.Frame(inner)
  actions.pack(fill=tk.X, padx=16, pady=(16, 8))

  # Store
  store = ConfStore()

  # 分组构建
  build_game_config_group(inner, conf, store)
  build_live_config_group(inner, conf, store)
  build_challenge_live_config_group(inner, conf, store)

  def on_save() -> None:
    try:
      # 游戏设置
      emulator_val = EMULATOR_VALUE_MAP[store.emulator_var.get()]
      server_val = SERVER_VALUE_MAP[store.server_var.get()]
      link_val = LINK_VALUE_MAP[store.link_var.get()]
      control_impl_val = CONTROL_IMPL_VALUE_MAP[store.control_impl_var.get()]
      conf.game.emulator = emulator_val
      conf.game.server = server_val
      conf.game.link_account = link_val
      conf.game.control_impl = control_impl_val
      # 自定义模拟器数据
      if emulator_val == 'custom':
        ip = (store.custom_adb_ip_var.get() or '').strip() or '127.0.0.1'
        try:
          port = int((store.custom_adb_port_var.get() or '').strip() or '5555')
        except Exception:
          port = 5555
        conf.game.emulator_data = CustomEmulatorData(adb_ip=ip, adb_port=port)
      else:
        conf.game.emulator_data = None

      # 演出设置
      song_display = store.song_var.get()
      conf.live.song_id = store.song_display_to_value.get(song_display, -1)
      conf.live.fully_deplete = bool(store.fully_deplete_var.get())

      # 挑战演出设置
      selected_chars: list[GameCharacter] = store.challenge_select.get() if store.challenge_select else []
      conf.challenge_live.characters = selected_chars
      award_display = store.challenge_award_var.get()
      conf.challenge_live.award = store.challenge_award_display_to_value.get(award_display, ChallengeLiveAward.Crystal)

      app.service.config.save()
      show_toast(app.root, "保存成功", kind="success")
    except Exception as e:
      show_toast(app.root, f"保存失败：{e}", kind="danger")

  tb.Button(actions, text="保存", command=on_save).pack(anchor=tk.W)