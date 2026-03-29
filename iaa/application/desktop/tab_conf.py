import tkinter as tk

import ttkbootstrap as tb

from .index import DesktopApp
from typing import Literal, Optional
from iaa.config.schemas import (
  LinkAccountOptions,
  EmulatorOptions,
  GameCharacter,
  ChallengeLiveAward,
  CustomEmulatorData,
  MuMuEmulatorData,
  PhysicalAndroidData,
)
from .toast import show_toast
from .advance_select import AdvanceSelect
from iaa.config.base import IaaConfig
from iaa.config.schemas import ShopItem
from .widgets.shuttle import Shuttle

# 显示与值映射
EMULATOR_DISPLAY_MAP: dict[EmulatorOptions, str] = {
  'mumu': 'MuMu',
  'mumu_v5': 'MuMu v5.x',
  'custom': '自定义',
  'physical_android': '物理设备(USB)',
}
EMULATOR_VALUE_MAP: dict[str, EmulatorOptions] = {v: k for k, v in EMULATOR_DISPLAY_MAP.items()}

SERVER_DISPLAY_MAP: dict[Literal['jp', 'tw'], str] = {
  'jp': '日服',
  'tw': '台服',
}
SERVER_VALUE_MAP: dict[str, Literal['jp', 'tw']] = {v: k for k, v in SERVER_DISPLAY_MAP.items()}

LINK_DISPLAY_MAP: dict[LinkAccountOptions, str] = {
  'no': '不引继账号',
  'google': 'Google 账号',
  'google_play': 'Google Play',
}
LINK_VALUE_MAP: dict[str, LinkAccountOptions] = {v: k for k, v in LINK_DISPLAY_MAP.items()}

CONTROL_IMPL_DISPLAY_MAP: dict[Literal['nemu_ipc', 'adb', 'uiautomator'], str] = {
  'nemu_ipc': 'Nemu IPC',
  'adb': 'ADB',
  'uiautomator': 'UIAutomator2',
}
CONTROL_IMPL_VALUE_MAP: dict[str, Literal['nemu_ipc', 'adb', 'uiautomator']] = {v: k for k, v in CONTROL_IMPL_DISPLAY_MAP.items()}
DEFAULT_MUMU_INSTANCE_LABEL = '默认'


def get_selected_mumu_instance_id(store: 'ConfStore') -> str | None:
  if store.mumu_instance_var.get() == DEFAULT_MUMU_INSTANCE_LABEL:
    return None
  return store.mumu_instance_display_to_id.get(store.mumu_instance_var.get())


class ConfStore:
  def __init__(self):
    # 游戏设置
    self.emulator_var = tk.StringVar()
    self.server_var = tk.StringVar()
    self.link_var = tk.StringVar()
    self.control_impl_var = tk.StringVar()
    self.check_emulator_var = tk.BooleanVar()
    self.mumu_instance_var = tk.StringVar()
    self.mumu_instance_status_var = tk.StringVar()
    # 自定义模拟器设置
    self.custom_adb_ip_var = tk.StringVar()
    self.custom_adb_port_var = tk.StringVar()
    self.custom_emulator_path_var = tk.StringVar()
    self.custom_emulator_args_var = tk.StringVar()
    self.mumu_instance_display_to_id: dict[str, str] = {}
    self.mumu_instance_id_to_display: dict[str, str] = {}
    self.mumu_instance_row: Optional[tb.Frame] = None
    self.mumu_instance_combo: Optional[tb.Combobox] = None
    # 自定义行占位（在 UI 构建中会赋值 Frame）
    self.custom_ip_row: Optional[tb.Frame] = None
    self.custom_port_row: Optional[tb.Frame] = None
    self.custom_emulator_path_row: Optional[tb.Frame] = None
    self.custom_emulator_args_row: Optional[tb.Frame] = None
    # 物理设备设置
    self.physical_android_serial_var = tk.StringVar()
    self.physical_android_serial_row: Optional[tb.Frame] = None
    # 演出设置
    self.song_var = tk.StringVar()
    self.auto_set_unit_var = tk.BooleanVar()
    self.ap_multiplier_var = tk.StringVar()
    self.append_fc_var = tk.BooleanVar()
    self.append_random_var = tk.BooleanVar()
    # 挑战演出设置
    self.challenge_char_vars: dict[GameCharacter, tk.BooleanVar] = {}
    self.challenge_award_var = tk.StringVar()
    # 分组多选组件实例
    self.challenge_select: Optional[AdvanceSelect[GameCharacter]] = None
    # 奖励显示到值映射
    self.challenge_award_display_to_value: dict[str, ChallengeLiveAward] = {}
    # CM 设置
    self.cm_watch_ad_wait_sec_var = tk.StringVar()
    # 活动商店设置
    self.event_shop_purchase_items_text: Optional[tk.Text] = None
    self.event_shop_available_listbox: Optional[tk.Listbox] = None
    self.event_shop_selected_listbox: Optional[tk.Listbox] = None


def build_event_shop_config_group(parent: tk.Misc, conf: IaaConfig, store: ConfStore) -> None:
  frame = tb.Labelframe(parent, text="活动商店设置")
  frame.pack(fill=tk.X, padx=16, pady=8)

  row = tb.Frame(frame)
  row.pack(fill=tk.BOTH, padx=8, pady=8)
  tb.Label(row, text="购买物品", width=16, anchor=tk.NW).pack(side=tk.LEFT, pady=(4, 0))

  box_row = tb.Frame(row)
  box_row.pack(side=tk.LEFT, fill=tk.X, expand=True)

  # 使用可复用的 Shuttle 组件来承载穿梭框逻辑
  shuttle = Shuttle(box_row)
  shuttle.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

  # 填充初始数据：左侧为 conf 中已有项，右侧为未选的枚举项
  selected_ids: list[str] = list(conf.event_shop.purchase_items)
  selected_display: list[str] = []
  known_selected_values = set()
  for item_id in selected_ids:
    try:
      si = ShopItem(item_id)
      selected_display.append(si.display('cn'))
      known_selected_values.add(si.value)
    except Exception:
      selected_display.append(item_id)

  shuttle.set_selected(selected_display)

  avail = [si.display('cn') for si in ShopItem if si.value not in known_selected_values]
  shuttle.set_available(avail)

  # 保持向后兼容：暴露原来的 Listbox 引用
  store.event_shop_available_listbox = shuttle.available_lb
  store.event_shop_selected_listbox = shuttle.selected_lb


SONG_KEEP_UNCHANGED = '保持不变'
SONG_NAME_OPTIONS = [
  SONG_KEEP_UNCHANGED,
  'メルト',
  '独りんぼエンヴィー',
]


def normalize_song_name_input(value: str) -> str | None:
  normalized = (value or '').strip()
  if not normalized or normalized == SONG_KEEP_UNCHANGED:
    return None
  return normalized


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
  store.check_emulator_var.set(bool(conf.game.check_emulator))
  emulator_data = conf.game.emulator_data
  initial_mumu_instance_id = None
  if emulator_key in {'mumu', 'mumu_v5'} and isinstance(emulator_data, MuMuEmulatorData):
    initial_mumu_instance_id = emulator_data.instance_id
  store.mumu_instance_var.set(DEFAULT_MUMU_INSTANCE_LABEL)
  store.mumu_instance_status_var.set('点击刷新以载入实例列表')
  # 初始化自定义 ADB 设置
  if emulator_key in {'mumu', 'mumu_v5'} and isinstance(emulator_data, MuMuEmulatorData) and emulator_data.instance_id:
    store.mumu_instance_status_var.set(f"当前配置实例 ID: {emulator_data.instance_id}")

  custom_data = emulator_data if isinstance(emulator_data, CustomEmulatorData) else None
  if emulator_key == 'custom' and custom_data is not None:
    store.custom_adb_ip_var.set(custom_data.adb_ip or '127.0.0.1')
    store.custom_adb_port_var.set(str(custom_data.adb_port or 5555))
    store.custom_emulator_path_var.set(custom_data.emulator_path or '')
    store.custom_emulator_args_var.set(custom_data.emulator_args or '')
  else:
    store.custom_adb_ip_var.set('127.0.0.1')
    store.custom_adb_port_var.set('5555')
    store.custom_emulator_path_var.set('')
    store.custom_emulator_args_var.set('')
  if emulator_key == 'physical_android' and isinstance(emulator_data, PhysicalAndroidData):
    store.physical_android_serial_var.set((emulator_data.adb_serial or '').strip())
  else:
    store.physical_android_serial_var.set('')

  # 模拟器类型
  row = tb.Frame(frame)
  row.pack(fill=tk.X, padx=8, pady=8)
  tb.Label(row, text="模拟器类型", width=16, anchor=tk.W).pack(side=tk.LEFT)
  tb.Combobox(row, state="readonly", textvariable=store.emulator_var, values=list(EMULATOR_VALUE_MAP.keys()), width=28).pack(side=tk.LEFT)

  # 物理设备 ADB 序列号（仅在选择"物理设备(USB)"时显示）
  physical_android_serial_row = tb.Frame(frame)
  store.physical_android_serial_row = physical_android_serial_row
  tb.Label(physical_android_serial_row, text="ADB 序列号", width=16, anchor=tk.W).pack(side=tk.LEFT)
  tb.Entry(physical_android_serial_row, textvariable=store.physical_android_serial_var, width=30).pack(side=tk.LEFT)

  mumu_instance_row = tb.Frame(frame)
  store.mumu_instance_row = mumu_instance_row
  tb.Label(mumu_instance_row, text="多开实例", width=16, anchor=tk.W).pack(side=tk.LEFT)
  initial_mumu_values = [DEFAULT_MUMU_INSTANCE_LABEL]
  if initial_mumu_instance_id is not None:
    initial_label = f'[{initial_mumu_instance_id}] 实例 {initial_mumu_instance_id} (点击刷新查看名称)'
    store.mumu_instance_display_to_id[initial_label] = initial_mumu_instance_id
    store.mumu_instance_id_to_display[initial_mumu_instance_id] = initial_label
    store.mumu_instance_var.set(initial_label)
    initial_mumu_values.append(initial_label)

  mumu_instance_combo = tb.Combobox(
    mumu_instance_row,
    state="readonly",
    textvariable=store.mumu_instance_var,
    values=initial_mumu_values,
    width=28,
  )
  mumu_instance_combo.pack(side=tk.LEFT)
  store.mumu_instance_combo = mumu_instance_combo

  def _selected_mumu_instance_id() -> str | None:
    return get_selected_mumu_instance_id(store)

  def _set_mumu_choices(instance_pairs: list[tuple[str, str]], selected_id: str | None) -> None:
    displays = [f'[{instance_id}] {name}' for instance_id, name in instance_pairs]
    store.mumu_instance_display_to_id = {display: instance_id for display, (instance_id, _) in zip(displays, instance_pairs)}
    store.mumu_instance_id_to_display = {instance_id: display for display, instance_id in store.mumu_instance_display_to_id.items()}
    if store.mumu_instance_combo:
      store.mumu_instance_combo.configure(values=[DEFAULT_MUMU_INSTANCE_LABEL, *displays])

    if selected_id is None:
      store.mumu_instance_var.set(DEFAULT_MUMU_INSTANCE_LABEL)
      return

    if selected_id is not None and selected_id in store.mumu_instance_id_to_display:
      store.mumu_instance_var.set(store.mumu_instance_id_to_display[selected_id])
      return

    store.mumu_instance_var.set(DEFAULT_MUMU_INSTANCE_LABEL)

  def _refresh_mumu_instances() -> None:
    emu_val = EMULATOR_VALUE_MAP.get(store.emulator_var.get(), 'mumu')
    if emu_val not in {'mumu', 'mumu_v5'}:
      store.mumu_instance_status_var.set('当前模拟器无需选择实例')
      _set_mumu_choices([], None)
      return

    try:
      from kotonebot.client.host import Mumu12Host, Mumu12V5Host

      host_cls = Mumu12Host if emu_val == 'mumu' else Mumu12V5Host
      instances = host_cls.list()
      instance_pairs = [(str(instance.id), instance.name) for instance in instances]
      saved_id = None
      if conf.game.emulator == emu_val and isinstance(conf.game.emulator_data, MuMuEmulatorData):
        saved_id = conf.game.emulator_data.instance_id
      selected_id = _selected_mumu_instance_id() or saved_id
      _set_mumu_choices(instance_pairs, selected_id)
      if instance_pairs:
        current_id = _selected_mumu_instance_id()
        if current_id is None:
          store.mumu_instance_status_var.set('已载入实例列表')
        else:
          store.mumu_instance_status_var.set(f'已载入 {len(instance_pairs)} 个实例，当前选择 ID: {current_id}')
      else:
        store.mumu_instance_status_var.set('未找到可用实例')
    except Exception as e:
      _set_mumu_choices([], None)
      store.mumu_instance_status_var.set(f'刷新失败：{e}')

  tb.Button(mumu_instance_row, text="刷新", command=_refresh_mumu_instances).pack(side=tk.LEFT, padx=(8, 0))
  tb.Label(mumu_instance_row, textvariable=store.mumu_instance_status_var, anchor=tk.W).pack(side=tk.LEFT, padx=(8, 0))

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

  # 自定义模拟器路径（仅在选择“自定义”时显示）
  custom_emulator_path_row = tb.Frame(frame)
  store.custom_emulator_path_row = custom_emulator_path_row
  tb.Label(custom_emulator_path_row, text="模拟器路径", width=16, anchor=tk.W).pack(side=tk.LEFT)
  tb.Entry(custom_emulator_path_row, textvariable=store.custom_emulator_path_var, width=30).pack(side=tk.LEFT)

  # 自定义模拟器启动参数（仅在选择“自定义”时显示）
  custom_emulator_args_row = tb.Frame(frame)
  store.custom_emulator_args_row = custom_emulator_args_row
  tb.Label(custom_emulator_args_row, text="启动参数", width=16, anchor=tk.W).pack(side=tk.LEFT)
  tb.Entry(custom_emulator_args_row, textvariable=store.custom_emulator_args_var, width=30).pack(side=tk.LEFT)

  def _update_emulator_rows(*_args) -> None:
    emu_val = EMULATOR_VALUE_MAP.get(store.emulator_var.get(), 'mumu')
    if emu_val in {'mumu', 'mumu_v5'}:
      if store.mumu_instance_row:
        store.mumu_instance_row.pack(fill=tk.X, padx=8, pady=8)
    else:
      if store.mumu_instance_row:
        store.mumu_instance_row.pack_forget()

    if emu_val == 'physical_android':
      if store.physical_android_serial_row:
        store.physical_android_serial_row.pack(fill=tk.X, padx=8, pady=8)
    else:
      if store.physical_android_serial_row:
        store.physical_android_serial_row.pack_forget()

    if emu_val == 'custom':
      if store.custom_ip_row:
        store.custom_ip_row.pack(fill=tk.X, padx=8, pady=8)
      if store.custom_port_row:
        store.custom_port_row.pack(fill=tk.X, padx=8, pady=8)
      if store.custom_emulator_path_row:
        store.custom_emulator_path_row.pack(fill=tk.X, padx=8, pady=8)
      if store.custom_emulator_args_row:
        store.custom_emulator_args_row.pack(fill=tk.X, padx=8, pady=8)
    else:
      if store.custom_ip_row:
        store.custom_ip_row.pack_forget()
      if store.custom_port_row:
        store.custom_port_row.pack_forget()
      if store.custom_emulator_path_row:
        store.custom_emulator_path_row.pack_forget()
      if store.custom_emulator_args_row:
        store.custom_emulator_args_row.pack_forget()

  # 监听选择变化并初始化显示
  try:
    store.emulator_var.trace_add('write', lambda *_: _update_emulator_rows())
  except Exception:
    pass
  _update_emulator_rows()

  # 服务器
  row = tb.Frame(frame)
  row.pack(fill=tk.X, padx=8, pady=8)
  tb.Label(row, text="服务器", width=16, anchor=tk.W).pack(side=tk.LEFT)
  tb.Combobox(row, state="readonly", textvariable=store.server_var, values=list(SERVER_VALUE_MAP.keys()), width=28).pack(side=tk.LEFT)

  # 引继账号
  row = tb.Frame(frame)
  row.pack(fill=tk.X, padx=8, pady=8)
  tb.Label(row, text="引继账号", width=16, anchor=tk.W).pack(side=tk.LEFT)
  link_combobox = tb.Combobox(row, state="readonly", textvariable=store.link_var, values=list(LINK_VALUE_MAP.keys()), width=28)
  link_combobox.pack(side=tk.LEFT)

  def _update_link_account_state(*_args) -> None:
    server_val = SERVER_VALUE_MAP.get(store.server_var.get(), 'jp')
    if server_val == 'tw':
      store.link_var.set(LINK_DISPLAY_MAP['no'])
      link_combobox.configure(state="disabled")
    else:
      link_combobox.configure(state="readonly")

  store.server_var.trace_add('write', lambda *_: _update_link_account_state())
  _update_link_account_state()

  # 控制方式
  row = tb.Frame(frame)
  row.pack(fill=tk.X, padx=8, pady=8)
  tb.Label(row, text="控制方式", width=16, anchor=tk.W).pack(side=tk.LEFT)
  tb.Combobox(row, state="readonly", textvariable=store.control_impl_var, values=list(CONTROL_IMPL_DISPLAY_MAP.values()), width=28).pack(side=tk.LEFT)

  # 启动模拟器
  row = tb.Frame(frame)
  row.pack(fill=tk.X, padx=8, pady=8)
  tb.Checkbutton(row, text="检查并启动模拟器", variable=store.check_emulator_var).pack(side=tk.LEFT)


def build_live_config_group(parent: tk.Misc, conf: IaaConfig, store: ConfStore) -> None:
  frame = tb.Labelframe(parent, text="演出设置")
  frame.pack(fill=tk.X, padx=16, pady=8)

  store.song_var.set(conf.live.song_name or SONG_KEEP_UNCHANGED)
  store.auto_set_unit_var.set(bool(conf.live.auto_set_unit))
  store.ap_multiplier_var.set('保持现状' if conf.live.ap_multiplier is None else str(conf.live.ap_multiplier))
  store.append_fc_var.set(bool(conf.live.append_fc))
  store.append_random_var.set(bool(conf.live.prepend_random))

  # 歌曲名称
  row = tb.Frame(frame)
  row.pack(fill=tk.X, padx=8, pady=8)
  tb.Label(row, text="歌曲名称", width=16, anchor=tk.W).pack(side=tk.LEFT)
  tb.Combobox(row, textvariable=store.song_var, values=SONG_NAME_OPTIONS, width=28).pack(side=tk.LEFT)

  row = tb.Frame(frame)
  row.pack(fill=tk.X, padx=8, pady=8)
  tb.Label(row, text="AP 倍率", width=16, anchor=tk.W).pack(side=tk.LEFT)
  tb.Combobox(
    row,
    state="readonly",
    textvariable=store.ap_multiplier_var,
    values=['保持现状', *[str(i) for i in range(0, 11)]],
    width=28,
  ).pack(side=tk.LEFT)

  # 自动编队
  row = tb.Frame(frame)
  row.pack(fill=tk.X, padx=8, pady=8)
  tb.Checkbutton(row, text="自动编队", variable=store.auto_set_unit_var).pack(side=tk.LEFT)

  row = tb.Frame(frame)
  row.pack(fill=tk.X, padx=8, pady=8)
  tb.Checkbutton(row, text="追加一次 FullCombo 演出", variable=store.append_fc_var).pack(side=tk.LEFT)

  row = tb.Frame(frame)
  row.pack(fill=tk.X, padx=8, pady=8)
  tb.Checkbutton(row, text="追加一首随机歌曲", variable=store.append_random_var).pack(side=tk.LEFT)


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


def build_cm_config_group(parent: tk.Misc, conf: IaaConfig, store: ConfStore) -> None:
  frame = tb.Labelframe(parent, text="CM 设置")
  frame.pack(fill=tk.X, padx=16, pady=8)

  store.cm_watch_ad_wait_sec_var.set(str(int(conf.cm.watch_ad_wait_sec)))

  row = tb.Frame(frame)
  row.pack(fill=tk.X, padx=8, pady=8)
  tb.Label(row, text="广告等待秒数", width=16, anchor=tk.W).pack(side=tk.LEFT)
  tb.Entry(row, textvariable=store.cm_watch_ad_wait_sec_var, width=30).pack(side=tk.LEFT)


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
  build_cm_config_group(inner, conf, store)
  build_event_shop_config_group(inner, conf, store)

  def on_save() -> None:
    try:
      # 游戏设置
      emulator_val = EMULATOR_VALUE_MAP[store.emulator_var.get()]
      server_val = SERVER_VALUE_MAP[store.server_var.get()]
      link_val = 'no' if server_val == 'tw' else LINK_VALUE_MAP[store.link_var.get()]
      control_impl_val = CONTROL_IMPL_VALUE_MAP[store.control_impl_var.get()]
      conf.game.emulator = emulator_val
      conf.game.server = server_val
      conf.game.link_account = link_val
      conf.game.control_impl = control_impl_val
      conf.game.check_emulator = bool(store.check_emulator_var.get())
      # 模拟器附加数据
      if emulator_val in {'mumu', 'mumu_v5'}:
        conf.game.emulator_data = MuMuEmulatorData(
          instance_id=get_selected_mumu_instance_id(store),
        )
      elif emulator_val == 'custom':
        ip = (store.custom_adb_ip_var.get() or '').strip() or '127.0.0.1'
        try:
          port = int((store.custom_adb_port_var.get() or '').strip() or '5555')
        except Exception:
          port = 5555
        emulator_path = (store.custom_emulator_path_var.get() or '').strip()
        emulator_args = (store.custom_emulator_args_var.get() or '').strip()
        conf.game.emulator_data = CustomEmulatorData(
          adb_ip=ip,
          adb_port=port,
          emulator_path=emulator_path,
          emulator_args=emulator_args,
        )
      elif emulator_val == 'physical_android':
        serial = (store.physical_android_serial_var.get() or '').strip()
        if not serial:
          raise ValueError("物理设备模式下必须填写 ADB 序列号")
        conf.game.emulator_data = PhysicalAndroidData(adb_serial=serial)
      else:
        conf.game.emulator_data = None

      # 演出设置
      conf.live.song_name = normalize_song_name_input(store.song_var.get())
      conf.live.auto_set_unit = bool(store.auto_set_unit_var.get())
      ap_multiplier_display = store.ap_multiplier_var.get()
      conf.live.ap_multiplier = None if ap_multiplier_display == '保持现状' else int(ap_multiplier_display)
      conf.live.append_fc = bool(store.append_fc_var.get())
      conf.live.prepend_random = bool(store.append_random_var.get())

      # 挑战演出设置
      selected_chars: list[GameCharacter] = store.challenge_select.get() if store.challenge_select else []
      conf.challenge_live.characters = selected_chars
      award_display = store.challenge_award_var.get()
      conf.challenge_live.award = store.challenge_award_display_to_value.get(award_display, ChallengeLiveAward.Crystal)
      
      # CM 设置
      raw_wait_sec = (store.cm_watch_ad_wait_sec_var.get() or '').strip()
      if not raw_wait_sec:
        raise ValueError("CM 广告等待秒数不能为空")
      wait_sec = int(raw_wait_sec)
      if wait_sec <= 0:
        raise ValueError("CM 广告等待秒数必须大于 0")
      conf.cm.watch_ad_wait_sec = wait_sec

      # 活动商店设置（从已选列表读取；回退到文本框如果存在）
      ids: list[ShopItem] = []

      def add_shop_item(text: str) -> None:
        if any(text == e.value for e in ShopItem):
          ids.append(ShopItem(text))
          return
        member = ShopItem.from_display('cn', text)
        if member is not None:
          ids.append(member)
          return

      if store.event_shop_selected_listbox is not None:
        lb = store.event_shop_selected_listbox
        for i in range(lb.size()):
          disp = lb.get(i)
          add_shop_item(disp)
      else:
        purchase_items_text = store.event_shop_purchase_items_text.get("1.0", tk.END) if store.event_shop_purchase_items_text else ""
        for line in purchase_items_text.splitlines():
          s = line.strip()
          if not s:
            continue
          add_shop_item(s)
      conf.event_shop.purchase_items = ids

      app.service.config.save()
      show_toast(app.root, "保存成功", kind="success")
    except Exception as e:
      show_toast(app.root, f"保存失败：{e}", kind="danger")

  tb.Button(actions, text="保存", command=on_save).pack(anchor=tk.W)
