# ruff: noqa: E701
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict
from iaa.definitions.enums import (
    LinkAccountOptions,
    EmulatorOptions,
    GameCharacter,
    ChallengeLiveAward,
    ShopItem,
)


class MuMuEmulatorData(BaseModel):
    model_config = ConfigDict(extra='forbid')

    instance_id: str | None = None


class CustomEmulatorData(BaseModel):
    model_config = ConfigDict(extra='forbid')

    adb_ip: str = '127.0.0.1'
    adb_port: int = 5555
    emulator_path: str = ''
    emulator_args: str = ''


class PhysicalAndroidData(BaseModel):
    adb_serial: str = ''


class GameConfig(BaseModel):
    server: Literal['jp', 'tw', 'cn'] = 'jp'
    link_account: LinkAccountOptions = 'no'
    emulator: EmulatorOptions = 'mumu_v5'
    control_impl: Literal['nemu_ipc', 'adb', 'uiautomator', 'scrcpy'] = 'nemu_ipc'
    check_emulator: bool = False
    scrcpy_virtual_display: bool = False
    resolution_method: Literal['auto', 'keep', 'wm_size'] = 'auto'
    emulator_data: MuMuEmulatorData | CustomEmulatorData | PhysicalAndroidData | None = None
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
    characters: list[GameCharacter] = []
    award: ChallengeLiveAward = ChallengeLiveAward.Crystal


class CmConfig(BaseModel):
    watch_ad_wait_sec: int = 70




class EventStoreConfig(BaseModel):
    purchase_items: list[ShopItem] = [
        ShopItem.ITEM_CRYSTAL,
        ShopItem.ITEM_3STAR_MEMBER,
    ]

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
        return False
