# ruff: noqa: E701
from enum import Enum
from typing import Literal
from pydantic import BaseModel
from typing_extensions import assert_never

LinkAccountOptions = Literal['no', 'google', 'google_play']
EmulatorOptions = Literal['mumu', 'mumu_v5', 'custom']


class GameCharacter(str, Enum):
    # VIRTUAL SINGER
    Miku = 'miku'
    Rin = 'rin'
    Len = 'len'
    Luka = 'luka'
    Meiko = 'meiko'
    Kaito = 'kaito'

    # Leo/need
    Ichika = 'ichika'
    Saki = 'saki'
    Honami = 'honami'
    Shiho = 'shiho'

    # MORE MORE JUMP!
    Minori = 'minori'
    Haruka = 'haruka'
    Airi = 'airi'
    Shizuku = 'shizuku'

    # Vivid BAD SQUAD
    Kohane = 'kohane'
    An = 'an'
    Akito = 'akito'
    Toya = 'toya'

    # Wonderlands×Showtime
    Tsukasa = 'tsukasa'
    Emu = 'emu'
    Nene = 'nene'
    Rui = 'rui'

    # 25時、ナイトコードで。
    Kanade = 'kanade'
    Mafuyu = 'mafuyu'
    Ena = 'ena'
    Mizuki = 'mizuki'

    @property
    def last_name_jp(self) -> str:
        match self:
            # VIRTUAL SINGER
            case GameCharacter.Miku: return '初音'
            case GameCharacter.Rin: return '鏡音'
            case GameCharacter.Len: return '鏡音'
            case GameCharacter.Luka: return '巡音'
            case GameCharacter.Meiko: return 'MEIKO'
            case GameCharacter.Kaito: return 'KAITO'
            # Leo/need
            case GameCharacter.Ichika: return '星乃'
            case GameCharacter.Saki: return '天馬'
            case GameCharacter.Honami: return '望月'
            case GameCharacter.Shiho: return '日野森'
            # MORE MORE JUMP!
            case GameCharacter.Minori: return '花里'
            case GameCharacter.Haruka: return '桐谷'
            case GameCharacter.Airi: return '桃井'
            case GameCharacter.Shizuku: return '日野森'
            # Vivid BAD SQUAD
            case GameCharacter.Kohane: return '小豆沢'
            case GameCharacter.An: return '白石'
            case GameCharacter.Akito: return '東雲'
            case GameCharacter.Toya: return '青柳'
            # ワンダーランズ×ショウタイム
            case GameCharacter.Tsukasa: return '天馬'
            case GameCharacter.Emu: return '鳳'
            case GameCharacter.Nene: return '草薙'
            case GameCharacter.Rui: return '神代'
            # 25時、ナイトコードで。
            case GameCharacter.Kanade: return '宵崎'
            case GameCharacter.Mafuyu: return '朝比奈'
            case GameCharacter.Ena: return '東雲'
            case GameCharacter.Mizuki: return '暁山'
            case _:
                assert_never(self)

    @property
    def last_name_cn(self) -> str:
        match self:
            case GameCharacter.Miku: return '初音'
            case GameCharacter.Rin: return '镜音'
            case GameCharacter.Len: return '镜音'
            case GameCharacter.Luka: return '巡音'
            case GameCharacter.Meiko: return ''
            case GameCharacter.Kaito: return ''
            case GameCharacter.Ichika: return '星乃'
            case GameCharacter.Saki: return '天马'
            case GameCharacter.Honami: return '望月'
            case GameCharacter.Shiho: return '日野森'
            case GameCharacter.Minori: return '花里'
            case GameCharacter.Haruka: return '桐谷'
            case GameCharacter.Airi: return '桃井'
            case GameCharacter.Shizuku: return '日野森'
            case GameCharacter.Kohane: return '小豆泽'
            case GameCharacter.An: return '白石'
            case GameCharacter.Akito: return '东云'
            case GameCharacter.Toya: return '青柳'
            case GameCharacter.Tsukasa: return '天马'
            case GameCharacter.Emu: return '凤'
            case GameCharacter.Nene: return '草薙'
            case GameCharacter.Rui: return '神代'
            case GameCharacter.Kanade: return '宵崎'
            case GameCharacter.Mafuyu: return '朝比奈'
            case GameCharacter.Ena: return '东云'
            case GameCharacter.Mizuki: return '晓山'
            case _:
                assert_never(self)

    @property
    def last_name_en(self) -> str:
        match self:
            case GameCharacter.Miku: return 'Hatsune'
            case GameCharacter.Rin: return 'Kagamine'
            case GameCharacter.Len: return 'Kagamine'
            case GameCharacter.Luka: return 'Megurine'
            case GameCharacter.Meiko: return ''
            case GameCharacter.Kaito: return ''
            case GameCharacter.Ichika: return 'Hoshino'
            case GameCharacter.Saki: return 'Tenma'
            case GameCharacter.Honami: return 'Mochizuki'
            case GameCharacter.Shiho: return 'Hinomori'
            case GameCharacter.Minori: return 'Hanasato'
            case GameCharacter.Haruka: return 'Kiritani'
            case GameCharacter.Airi: return 'Momoi'
            case GameCharacter.Shizuku: return 'Hinomori'
            case GameCharacter.Kohane: return 'Azusawa'
            case GameCharacter.An: return 'Shiraishi'
            case GameCharacter.Akito: return 'Shinonome'
            case GameCharacter.Toya: return 'Aoyagi'
            case GameCharacter.Tsukasa: return 'Tenma'
            case GameCharacter.Emu: return 'Otori'
            case GameCharacter.Nene: return 'Kusanagi'
            case GameCharacter.Rui: return 'Kamishiro'
            case GameCharacter.Kanade: return 'Yoisaki'
            case GameCharacter.Mafuyu: return 'Asahina'
            case GameCharacter.Ena: return 'Shinonome'
            case GameCharacter.Mizuki: return 'Akiyama'
            case _:
                assert_never(self)

    @property
    def first_name_jp(self) -> str:
        match self:
            case GameCharacter.Miku: return 'ミク'
            case GameCharacter.Rin: return 'リン'
            case GameCharacter.Len: return 'レン'
            case GameCharacter.Luka: return 'ルカ'
            case GameCharacter.Meiko: return ''
            case GameCharacter.Kaito: return ''
            case GameCharacter.Ichika: return '一歌'
            case GameCharacter.Saki: return '咲希'
            case GameCharacter.Honami: return '穂波'
            case GameCharacter.Shiho: return '志歩'
            case GameCharacter.Minori: return 'みのり'
            case GameCharacter.Haruka: return '遥'
            case GameCharacter.Airi: return '愛莉'
            case GameCharacter.Shizuku: return '雫'
            case GameCharacter.Kohane: return 'こはね'
            case GameCharacter.An: return '杏'
            case GameCharacter.Akito: return '彰人'
            case GameCharacter.Toya: return '冬弥'
            case GameCharacter.Tsukasa: return '司'
            case GameCharacter.Emu: return 'えむ'
            case GameCharacter.Nene: return '寧々'
            case GameCharacter.Rui: return '類'
            case GameCharacter.Kanade: return '奏'
            case GameCharacter.Mafuyu: return 'まふゆ'
            case GameCharacter.Ena: return '絵名'
            case GameCharacter.Mizuki: return '瑞希'
            case _:
                assert_never(self)

    @property
    def first_name_cn(self) -> str:
        match self:
            case GameCharacter.Miku: return '未来'
            case GameCharacter.Rin: return '铃'
            case GameCharacter.Len: return '连'
            case GameCharacter.Luka: return '流歌'
            case GameCharacter.Meiko: return 'MEIKO'
            case GameCharacter.Kaito: return 'KAITO'
            case GameCharacter.Ichika: return '一歌'
            case GameCharacter.Saki: return '咲希'
            case GameCharacter.Honami: return '穗波'
            case GameCharacter.Shiho: return '志步'
            case GameCharacter.Minori: return '实乃里'
            case GameCharacter.Haruka: return '遥'
            case GameCharacter.Airi: return '爱莉'
            case GameCharacter.Shizuku: return '雫'
            case GameCharacter.Kohane: return '心羽音'
            case GameCharacter.An: return '杏'
            case GameCharacter.Akito: return '彰人'
            case GameCharacter.Toya: return '冬弥'
            case GameCharacter.Tsukasa: return '司'
            case GameCharacter.Emu: return '笑梦'
            case GameCharacter.Nene: return '宁宁'
            case GameCharacter.Rui: return '类'
            case GameCharacter.Kanade: return '奏'
            case GameCharacter.Mafuyu: return '真冬'
            case GameCharacter.Ena: return '绘名'
            case GameCharacter.Mizuki: return '瑞希'
            case _:
                assert_never(self)

    @property
    def first_name_en(self) -> str:
        match self:
            case GameCharacter.Miku: return 'Miku'
            case GameCharacter.Rin: return 'Rin'
            case GameCharacter.Len: return 'Len'
            case GameCharacter.Luka: return 'Luka'
            case GameCharacter.Meiko: return 'MEIKO'
            case GameCharacter.Kaito: return 'KAITO'
            case GameCharacter.Ichika: return 'Ichika'
            case GameCharacter.Saki: return 'Saki'
            case GameCharacter.Honami: return 'Honami'
            case GameCharacter.Shiho: return 'Shiho'
            case GameCharacter.Minori: return 'Minori'
            case GameCharacter.Haruka: return 'Haruka'
            case GameCharacter.Airi: return 'Airi'
            case GameCharacter.Shizuku: return 'Shizuku'
            case GameCharacter.Kohane: return 'Kohane'
            case GameCharacter.An: return 'An'
            case GameCharacter.Akito: return 'Akito'
            case GameCharacter.Toya: return 'Toya'
            case GameCharacter.Tsukasa: return 'Tsukasa'
            case GameCharacter.Emu: return 'Emu'
            case GameCharacter.Nene: return 'Nene'
            case GameCharacter.Rui: return 'Rui'
            case GameCharacter.Kanade: return 'Kanade'
            case GameCharacter.Mafuyu: return 'Mafuyu'
            case GameCharacter.Ena: return 'Ena'
            case GameCharacter.Mizuki: return 'Mizuki'
            case _:
                assert_never(self)


class ChallengeLiveAward(str, Enum):
    Crystal = 'crystal'
    """水晶"""
    MusicCard = 'music_card'
    """音乐卡"""
    MiracleGem = 'miracle_gem'
    """奇迹晶石"""
    MagicCloth = 'magic_cloth'
    """魔法之布"""
    Coin = 'coin'
    """硬币"""
    IntermediatePracticeScore = 'intermediate_practice_score'
    """中级练习乐谱"""

    @staticmethod
    def display_map_cn() -> dict['ChallengeLiveAward', str]:
        return {
            ChallengeLiveAward.Crystal: "水晶",
            ChallengeLiveAward.MusicCard: "音乐卡",
            ChallengeLiveAward.MiracleGem: "奇迹晶石",
            ChallengeLiveAward.MagicCloth: "魔法之布",
            ChallengeLiveAward.Coin: "硬币",
            ChallengeLiveAward.IntermediatePracticeScore: "中级练习乐谱",
        }


class CustomEmulatorData(BaseModel):
    adb_ip: str = '127.0.0.1'
    adb_port: int = 5555
    emulator_path: str = ''
    emulator_args: str = ''


class GameConfig(BaseModel):
    server: Literal['jp', 'tw'] = 'jp'
    link_account: LinkAccountOptions = 'no'
    emulator: EmulatorOptions = 'mumu_v5'
    control_impl: Literal['nemu_ipc', 'adb', 'uiautomator'] = 'nemu_ipc'
    check_emulator: bool = False
    emulator_data: CustomEmulatorData | None = None
    """
    是否引继账号。
    
    * `"no"`： 不引继账号
    * `"google"`： 引继 Google 账号
    * `"google_play"`： 引继 Google Play 账号
    """


class LiveConfig(BaseModel):
    enabled: bool = False
    mode: Literal['auto'] = 'auto'
    song_id: int = -1
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
    fully_deplete: bool = False


class ChallengeLiveConfig(BaseModel):
    characters: list[GameCharacter] = []
    award: ChallengeLiveAward = ChallengeLiveAward.Crystal


class CmConfig(BaseModel):
    watch_ad_wait_sec: int = 70


class SchedulerConfig(BaseModel):
    start_game_enabled: bool = True
    solo_live_enabled: bool = True
    challenge_live_enabled: bool = True
    activity_story_enabled: bool = True
    cm_enabled: bool = True
    gift_enabled: bool = True
    area_convos_enabled: bool = True

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
        return False
