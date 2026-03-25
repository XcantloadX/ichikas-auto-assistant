from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from typing import Any

import ttkbootstrap as tb

from iaa.application.desktop.advance_select import AdvanceSelect
from iaa.application.desktop.toast import show_toast
from iaa.application.desktop.widgets.shuttle import Shuttle
from iaa.config.base import IaaConfig
from iaa.config.schemas import (
    ChallengeLiveAward,
    CustomEmulatorData,
    GameCharacter,
    MuMuEmulatorData,
    ShopItem,
)

from .dsl import SettingsRegistry
from .reactive import Signal, state_from_config, to_config
from .renderer import RenderContext, TkSettingsRenderer

DEFAULT_MUMU_INSTANCE_LABEL = '默认'
SONG_KEEP_UNCHANGED = '保持不变'
SONG_NAME_OPTIONS = [
    SONG_KEEP_UNCHANGED,
    'メルト',
    '独りんぼエンヴィー',
]


@dataclass
class _SettingsExtras:
    """Extra state not directly represented in ``IaaConfig`` tree."""

    mumu_instance_id: Signal[str | None]
    custom_adb_ip: Signal[str]
    custom_adb_port: Signal[int]
    custom_emulator_path: Signal[str]
    custom_emulator_args: Signal[str]


def _normalize_song_name_input(value: str) -> str | None:
    normalized = (value or '').strip()
    if not normalized or normalized == SONG_KEEP_UNCHANGED:
        return None
    return normalized


def _format_song_name(value: str | None) -> str:
    return SONG_KEEP_UNCHANGED if not value else value


def _display_ap_multiplier(value: int | None) -> str:
    return '保持现状' if value is None else str(value)


def _parse_ap_multiplier(text: str) -> int | None:
    return None if text == '保持现状' else int(text)


def _make_extras(conf: IaaConfig) -> _SettingsExtras:
    emulator_data = conf.game.emulator_data
    if isinstance(emulator_data, MuMuEmulatorData):
        mumu_instance_id = emulator_data.instance_id
    else:
        mumu_instance_id = None

    if isinstance(emulator_data, CustomEmulatorData):
        custom_ip = emulator_data.adb_ip
        custom_port = emulator_data.adb_port
        custom_path = emulator_data.emulator_path
        custom_args = emulator_data.emulator_args
    else:
        custom_ip = '127.0.0.1'
        custom_port = 5555
        custom_path = ''
        custom_args = ''

    return _SettingsExtras(
        mumu_instance_id=Signal(mumu_instance_id),
        custom_adb_ip=Signal(custom_ip),
        custom_adb_port=Signal(custom_port),
        custom_emulator_path=Signal(custom_path),
        custom_emulator_args=Signal(custom_args),
    )


def _bind_server_link_rule(state: Any) -> None:
    def _sync(server: str) -> None:
        if server == 'tw':
            state.game.link_account.set('no')

    state.game.server.subscribe(_sync)
    _sync(state.game.server.get())


def _render_mumu_instance_picker(*, row: tk.Misc, field: Any, context: RenderContext) -> None:
    status_var = tk.StringVar(value='点击刷新以载入实例列表')
    display_to_id: dict[str, str] = {}

    combo_var = tk.StringVar(value=DEFAULT_MUMU_INSTANCE_LABEL)
    combo = tb.Combobox(row, state='readonly', textvariable=combo_var, values=[DEFAULT_MUMU_INSTANCE_LABEL], width=28)
    combo.pack(side=tk.LEFT)

    def _set_selection(selected_id: str | None) -> None:
        if selected_id is None:
            combo_var.set(DEFAULT_MUMU_INSTANCE_LABEL)
            return
        for display, item_id in display_to_id.items():
            if item_id == selected_id:
                combo_var.set(display)
                return
        combo_var.set(DEFAULT_MUMU_INSTANCE_LABEL)

    def _on_combo_change(*_args: object) -> None:
        text = combo_var.get()
        field.signal.set(display_to_id.get(text))

    combo_var.trace_add('write', _on_combo_change)
    field.signal.subscribe(_set_selection)
    _set_selection(field.signal.get())

    def _refresh_instances() -> None:
        try:
            from kotonebot.client.host import Mumu12Host, Mumu12V5Host

            emulator = context.state.game.emulator.get()
            host_cls = Mumu12Host if emulator == 'mumu' else Mumu12V5Host
            instances = host_cls.list()
            pairs = [(str(instance.id), instance.name) for instance in instances]
            values = [DEFAULT_MUMU_INSTANCE_LABEL]
            display_to_id.clear()
            for item_id, name in pairs:
                display = f'[{item_id}] {name}'
                values.append(display)
                display_to_id[display] = item_id
            combo.configure(values=values)
            status_var.set('已载入实例列表' if pairs else '未找到可用实例')
            _set_selection(field.signal.get())
        except Exception as error:  # noqa: BLE001
            status_var.set(f'刷新失败：{error}')

    tb.Button(row, text='刷新', command=_refresh_instances).pack(side=tk.LEFT, padx=(8, 0))
    tb.Label(row, textvariable=status_var, anchor=tk.W).pack(side=tk.LEFT, padx=(8, 0))


def _render_challenge_characters(*, row: tk.Misc, field: Any, context: RenderContext) -> None:
    groups: list[tuple[str, list[GameCharacter]]] = [
        ('VIRTUAL SINGER', [
            GameCharacter.Miku, GameCharacter.Rin, GameCharacter.Len,
            GameCharacter.Luka, GameCharacter.Meiko, GameCharacter.Kaito,
        ]),
        ('Leo/need', [GameCharacter.Ichika, GameCharacter.Saki, GameCharacter.Honami, GameCharacter.Shiho]),
        ('MORE MORE JUMP!', [GameCharacter.Minori, GameCharacter.Haruka, GameCharacter.Airi, GameCharacter.Shizuku]),
        ('Vivid BAD SQUAD', [GameCharacter.Kohane, GameCharacter.An, GameCharacter.Akito, GameCharacter.Toya]),
        ('ワンダーランズ×ショウタイム', [GameCharacter.Tsukasa, GameCharacter.Emu, GameCharacter.Nene, GameCharacter.Rui]),
        ('25時、ナイトコードで。', [GameCharacter.Kanade, GameCharacter.Mafuyu, GameCharacter.Ena, GameCharacter.Mizuki]),
    ]

    grouped_options = [(name, [(ch, ch.last_name_cn + ch.first_name_cn) for ch in chars]) for name, chars in groups]
    select = AdvanceSelect[GameCharacter](
        row,
        groups=grouped_options,
        selected=list(field.signal.get()),
        mutiple=False,
        placeholder='请选择角色',
    )
    select.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _sync() -> None:
        field.signal.set(select.get())

    select.bind('<<ComboboxSelected>>', lambda _event: _sync())


def _render_event_shop_shuttle(*, row: tk.Misc, field: Any, context: RenderContext) -> None:
    shuttle = Shuttle(row)
    shuttle.pack(side=tk.LEFT, fill=tk.X, expand=True)

    selected_items = list(field.signal.get())
    selected_display = [item.display('cn') for item in selected_items]
    selected_values = {item.value for item in selected_items}

    shuttle.set_selected(selected_display)
    shuttle.set_available([item.display('cn') for item in ShopItem if item.value not in selected_values])

    def _sync(*_args: object) -> None:
        items: list[ShopItem] = []
        for index in range(shuttle.selected_lb.size()):
            display = shuttle.selected_lb.get(index)
            item = ShopItem.from_display('cn', display)
            if item is not None:
                items.append(item)
        field.signal.set(items)

    shuttle.selected_lb.bind('<<ListboxSelect>>', _sync)
    shuttle.available_lb.bind('<<ListboxSelect>>', _sync)


def _build_screen_spec(*, state: Any, extras: _SettingsExtras) -> Any:
    registry = SettingsRegistry()

    @registry.section('game', '游戏设置')
    def make_game(ui) -> None:
        ui.select('emulator', '模拟器类型', bind=state.game.emulator, options=['mumu', 'mumu_v5', 'custom'])
        ui.custom(
            'mumu_instance',
            '多开实例',
            bind=extras.mumu_instance_id,
            renderer=_render_mumu_instance_picker,
            visible_if=lambda: state.game.emulator.get() in {'mumu', 'mumu_v5'},
            depends_on=[state.game.emulator],
        )
        ui.text_input(
            'custom_adb_ip',
            'ADB IP',
            bind=extras.custom_adb_ip,
            visible_if=lambda: state.game.emulator.get() == 'custom',
            depends_on=[state.game.emulator],
        )
        ui.text_input(
            'custom_adb_port',
            'ADB 端口',
            bind=extras.custom_adb_port,
            parser=lambda text: int(text),
            formatter=lambda value: str(int(value)),
            visible_if=lambda: state.game.emulator.get() == 'custom',
            depends_on=[state.game.emulator],
        )
        ui.text_input(
            'custom_emulator_path',
            '模拟器路径',
            bind=extras.custom_emulator_path,
            visible_if=lambda: state.game.emulator.get() == 'custom',
            depends_on=[state.game.emulator],
        )
        ui.text_input(
            'custom_emulator_args',
            '启动参数',
            bind=extras.custom_emulator_args,
            visible_if=lambda: state.game.emulator.get() == 'custom',
            depends_on=[state.game.emulator],
        )
        ui.select('server', '服务器', bind=state.game.server, options=['jp', 'tw'])
        ui.select(
            'link_account',
            '引继账号',
            bind=state.game.link_account,
            options=['no', 'google', 'google_play'],
            enabled_if=lambda: state.game.server.get() != 'tw',
            depends_on=[state.game.server],
        )
        ui.select('control_impl', '控制方式', bind=state.game.control_impl, options=['nemu_ipc', 'adb', 'uiautomator'])
        ui.checkbox('check_emulator', '检查并启动模拟器', bind=state.game.check_emulator)

    @registry.section('live', '演出设置')
    def make_live(ui) -> None:
        ui.select(
            'song_name',
            '歌曲名称',
            bind=state.live.song_name,
            options=SONG_NAME_OPTIONS,
            formatter=_format_song_name,
            parser=_normalize_song_name_input,
        )
        ui.select(
            'ap_multiplier',
            'AP 倍率',
            bind=state.live.ap_multiplier,
            options=[None, *[i for i in range(0, 11)]],
            formatter=_display_ap_multiplier,
            parser=_parse_ap_multiplier,
        )
        ui.checkbox('auto_set_unit', '自动编队', bind=state.live.auto_set_unit)
        ui.checkbox('append_fc', '追加一次 FullCombo 演出', bind=state.live.append_fc)
        ui.checkbox('prepend_random', '追加一首随机歌曲', bind=state.live.prepend_random)

    @registry.section('challenge_live', '挑战演出设置')
    def make_challenge(ui) -> None:
        ui.custom('characters', '角色', bind=state.challenge_live.characters, renderer=_render_challenge_characters)
        award_options = list(ChallengeLiveAward)
        ui.select(
            'award',
            '奖励',
            bind=state.challenge_live.award,
            options=award_options,
            formatter=lambda value: ChallengeLiveAward.display_map_cn().get(value, str(value)),
            parser=lambda text: next(
                (k for k, v in ChallengeLiveAward.display_map_cn().items() if v == text),
                ChallengeLiveAward.Crystal,
            ),
        )

    @registry.section('cm', 'CM 设置')
    def make_cm(ui) -> None:
        ui.text_input(
            'watch_ad_wait_sec',
            '广告等待秒数',
            bind=state.cm.watch_ad_wait_sec,
            parser=lambda text: int(text),
            formatter=lambda value: str(int(value)),
        )

    @registry.section('event_shop', '活动商店设置')
    def make_event_shop(ui) -> None:
        ui.custom('purchase_items', '购买物品', bind=state.event_shop.purchase_items, renderer=_render_event_shop_shuttle)

    return registry.build(screen_key='settings', screen_title='配置')


def _apply_extras_to_config(*, conf: IaaConfig, state: Any, extras: _SettingsExtras) -> None:
    emulator = state.game.emulator.get()
    if emulator in {'mumu', 'mumu_v5'}:
        conf.game.emulator_data = MuMuEmulatorData(instance_id=extras.mumu_instance_id.get())
    elif emulator == 'custom':
        conf.game.emulator_data = CustomEmulatorData(
            adb_ip=(extras.custom_adb_ip.get() or '').strip() or '127.0.0.1',
            adb_port=int(extras.custom_adb_port.get()),
            emulator_path=(extras.custom_emulator_path.get() or '').strip(),
            emulator_args=(extras.custom_emulator_args.get() or '').strip(),
        )


def build_settings_tab(parent: tk.Misc, *, context: RenderContext) -> None:
    """Build settings tab using DSL + reactive state."""

    app = context.app

    container = tb.Frame(parent)
    container.pack(fill=tk.BOTH, expand=True)

    canvas = tk.Canvas(container, highlightthickness=0)
    vscroll = tb.Scrollbar(container, orient=tk.VERTICAL, command=canvas.yview)
    canvas.configure(yscrollcommand=vscroll.set)

    inner = tb.Frame(canvas)
    inner_id = canvas.create_window((0, 0), window=inner, anchor=tk.NW)

    def _on_inner_config(_event: tk.Event) -> None:
        canvas.configure(scrollregion=canvas.bbox('all'))

    def _on_canvas_config(_event: tk.Event) -> None:
        canvas.itemconfigure(inner_id, width=canvas.winfo_width())

    inner.bind('<Configure>', _on_inner_config)
    canvas.bind('<Configure>', _on_canvas_config)

    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    vscroll.pack(side=tk.RIGHT, fill=tk.Y)

    conf = app.service.config.conf
    state = state_from_config(conf)
    extras = _make_extras(conf)

    _bind_server_link_rule(state)

    actions = tb.Frame(inner)
    actions.pack(fill=tk.X, padx=16, pady=(16, 8))

    screen = _build_screen_spec(state=state, extras=extras)
    renderer = TkSettingsRenderer(context=RenderContext(app=app, state=state))
    renderer.render(inner, screen)

    def _on_save() -> None:
        try:
            new_conf = to_config(state, IaaConfig)
            if new_conf.game.server == 'tw':
                new_conf.game.link_account = 'no'
            _apply_extras_to_config(conf=new_conf, state=state, extras=extras)

            app.service.config.conf = new_conf
            app.service.config.save()
            show_toast(app.root, '保存成功', kind='success')
        except Exception as error:  # noqa: BLE001
            show_toast(app.root, f'保存失败：{error}', kind='danger')

    tb.Button(actions, text='保存', command=_on_save).pack(anchor=tk.W)
