# ruff: noqa: E701
from typing import Annotated, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field
from iaa.definitions.enums import (
    LinkAccountOptions,
    GameCharacter,
    ChallengeLiveAward,
    ShopItem,
)


# ── 设备生命周期 ──────────────────────────────────────────────────────────────

class MuMuDevice(BaseModel):
    type: Literal['mumu_v5', 'mumu']
    instance_id: str | None = None
    check_and_start: bool = False

class CustomDevice(BaseModel):
    type: Literal['custom']
    check_and_start: bool = False
    start_command: str = ''
    wait_start_command: bool = False
    stop_command: str = ''
    running_command: str = ''

class NoDevice(BaseModel):
    type: Literal['none']

class PlayCoverDevice(BaseModel):
    type: Literal['playcover']
    check_and_start: bool = False

DeviceLifecycle = Annotated[
    MuMuDevice | CustomDevice | NoDevice | PlayCoverDevice,
    Field(discriminator='type')
]


# ── ADB 连接 ──────────────────────────────────────────────────────────────────

class AutoConnection(BaseModel):
    """MuMu 专用，连接信息由程序从 MuMu SDK 自动获取。"""
    type: Literal['auto']

class UsbConnection(BaseModel):
    type: Literal['usb']
    device_serial: str = ''        # 留空自动选第一个 USB 设备

class TcpConnection(BaseModel):
    type: Literal['tcp']
    ip: str = '127.0.0.1'
    port: int | None = None
    run_adb_connect: bool = True
    device_serial: str = ''        # 留空则默认 ip:port

DeviceConnection = Annotated[
    AutoConnection | UsbConnection | TcpConnection,
    Field(discriminator='type')
]


# ── 设备总配置 ────────────────────────────────────────────────────────────────

class DeviceConfig(BaseModel):
    lifecycle: DeviceLifecycle = Field(default_factory=lambda: MuMuDevice(type='mumu_v5'))
    connection: DeviceConnection = Field(default_factory=lambda: AutoConnection(type='auto'))
    control_impl: Literal['nemu_ipc', 'adb', 'uiautomator', 'scrcpy'] = 'nemu_ipc'
    scrcpy_virtual_display: bool = False
    resolution_method: Literal['auto', 'keep', 'wm_size'] = 'auto'


# ── 游戏配置（仅游戏层面） ────────────────────────────────────────────────────

class GameConfig(BaseModel):
    server: Literal['jp', 'tw', 'cn'] = 'jp'
    link_account: LinkAccountOptions = 'no'
    """
    是否引继账号。

    * `"no"`： 不引继账号
    * `"google"`： 引继 Google 账号
    * `"google_play"`： 引继 Google Play 账号
    """


class LiveConfig(BaseModel):
    enabled: bool = False
    mode: Literal['auto'] = 'auto'
    song_name: str | None = None
    count_mode: Literal['once', 'all', 'specify'] = 'all'
    """
    演出次数模式。

    * `"once"`： 一次。
    * `"all"`： 直到 AP 不足。
    * `"specify"`： 指定次数。
    """
    count: int | None = None
    """
    指定次数。
    """
    auto_set_unit: bool = False
    """演出前是否自动编队"""
    ap_multiplier: int | None = 10
    """AP 倍率。None 表示保持现状。"""
    append_fc: bool = False
    """是否在常规演出后追加一次 Full Combo 演出。"""
    prepend_random: bool = False
    """是否在常规演出前追加一首随机歌曲。"""


class ChallengeLiveConfig(BaseModel):
    characters: list[GameCharacter] = [GameCharacter.Ichika]
    award: ChallengeLiveAward = ChallengeLiveAward.Crystal


class CmConfig(BaseModel):
    watch_ad_wait_sec: int = 70




class EventStoreConfig(BaseModel):
    purchase_items: list[ShopItem] = [
        ShopItem.ITEM_CRYSTAL,
        ShopItem.ITEM_3STAR_MEMBER,
    ]


class DeveloperConfig(BaseModel):
    sekai_dump_post_process: bool = False
    screen_recording_enabled: bool = False

class SchedulerConfig(BaseModel):
    start_game_enabled: bool = True
    solo_live_enabled: bool = True
    challenge_live_enabled: bool = True
    activity_story_enabled: bool = True
    cm_enabled: bool = True
    gift_enabled: bool = True
    area_convos_enabled: bool = True
    mission_rewards_enabled: bool = True
    event_shop_enabled: bool = True
    dump_sekai_home_enabled: bool = False

    def is_enabled(self, task_id: str) -> bool:
        """根据任务标识判断是否启用。

        任务标识应与 `iaa.tasks.registry.REGULAR_TASKS` 的键一致，例如：
        - "start_game"
        - "cm"
        - "solo_live"
        - "challenge_live"
        - "activity_story"
        - "gift"
        - "area_convos"
        - "mission_rewards"
        - "_dump_sekai_home"
        """
        if task_id == 'start_game':
            return bool(self.start_game_enabled)
        if task_id == 'cm':
            return bool(self.cm_enabled)
        if task_id == 'solo_live':
            return bool(self.solo_live_enabled)
        if task_id == 'challenge_live':
            return bool(self.challenge_live_enabled)
        if task_id == 'activity_story':
            return bool(self.activity_story_enabled)
        if task_id == 'gift':
            return bool(self.gift_enabled)
        if task_id == 'area_convos':
            return bool(self.area_convos_enabled)
        if task_id == 'mission_rewards':
            return bool(self.mission_rewards_enabled)
        if task_id == 'event_shop':
            return bool(self.event_shop_enabled)
        if task_id == '_dump_sekai_home':
            return bool(self.dump_sekai_home_enabled)
        return False
