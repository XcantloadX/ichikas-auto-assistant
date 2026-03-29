# ruff: noqa: E701
from enum import Enum
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict
from typing_extensions import assert_never

LinkAccountOptions = Literal['no', 'google', 'google_play']
EmulatorOptions = Literal['mumu', 'mumu_v5', 'custom', 'physical_android']


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
    server: Literal['jp', 'tw'] = 'jp'
    link_account: LinkAccountOptions = 'no'
    emulator: EmulatorOptions = 'mumu_v5'
    control_impl: Literal['nemu_ipc', 'adb', 'uiautomator'] = 'nemu_ipc'
    check_emulator: bool = False
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


class ShopItem(str, Enum):
    jp: str
    cn: str
    tw: str

    ITEM_2STAR_MEMBER = ("2star_event_card", "★2メンバー", "★2成员", "★2成員")
    ITEM_3STAR_MEMBER = ("3star_event_card", "★3メンバー", "★3成员", "★3成員")
    ITEM_COVER_CARD_VOUCHER = ("cover_card_voucher", "ボーカルカード交換チケット", "歌手兑换卡", "歌手兌換券")
    ITEM_CRYSTAL = ("crystal", "クリスタル", "水晶", "水晶")
    ITEM_WISH_PIECE = ("wish_piece", "想いのカケラ", "心愿碎片", "心願碎片")
    ITEM_BONUS_ENERGY_DRINK_S = ("bonus_energy_drink_s", "ライブボーナスドリンク（小）", "演出能量饮料（小）", "LIVE BOUNS 飲料（小）")
    ITEM_STAMP_VOUCHER = ("stamp_voucher", "スタンプ交換券", "表情兑换券", "貼園交換券")
    ITEM_PRACTICE_SCORE_INTERMEDIATE = ("practice_score_intermediate", "練習用スコア（中級）", "练习乐谱（中级）", "練習譜（中級）")
    ITEM_MUSIC_CARD = ("music_card", "ミュージックカード", "音乐卡", "音樂卡")
    ITEM_MIRACLE_GEM = ("miracle_gem", "ミラクルジェム", "奇迹晶石", "奇蹟晶石")

    # ITEM_CUTE_GEM = ("cute_gem", "キュートジェム", "可爱晶石", "可愛晶石")
    # ITEM_COOL_GEM = ("cool_gem", "クールジェム", "冷酷晶石", "帥氣晶石")
    # ITEM_PURE_GEM = ("pure_gem", "ピュアジェム", "纯真晶石", "純真晶石")
    # ITEM_HAPPY_GEM = ("happy_gem", "ハッピージェム", "开心晶石", "開心晶石")
    # ITEM_MYSTERIOUS_GEM = ("mysterious_gem", "ミステリアスジェム", "神秘晶石", "神秘晶石")

    # ITEM_CUTE_CHARM = ("cute_charm", "キュートピース", "可爱碎片", "可愛碎片")
    # ITEM_COOL_CHARM = ("cool_charm", "クールピース", "冷酷碎片", "帥氣碎片")
    # ITEM_PURE_CHARM = ("pure_charm", "ピュアピース", "纯真碎片", "純真碎片")
    # ITEM_HAPPY_CHARM = ("happy_charm", "ハッピーピース", "开心碎片", "開心碎片")
    # ITEM_MYSTERIOUS_CHARM = ("mysterious_charm", "ミステリアスピース", "神秘碎片", "神秘碎片")

    ITEM_MAGIC_CLOTH = ("magic_cloth", "魔法の布", "魔法之布", "魔法布")
    ITEM_MAGIC_THREAD = ("magic_thread", "魔法の糸", "魔法之线", "魔法線")
    ITEM_MAGICAL_SEED = ("magical_seed", "ふしぎな種", "奇异种子", "不可思議的種子")
    ITEM_WISH_DROP = ("wish_drop", "願いの雫", "心愿之露", "祈願水滴")
    ITEM_SKILL_UP_SCORE_INTERMEDIATE = ("skill_up_score_intermediate", "スキルアップ用スコア（中級）", "技能升级乐谱（中级）", "技能升級譜（中級）")
    ITEM_COIN_100000 = ("coin_100000", "コイン×100000", "硬币x100000", "硬幣x100000")
    ITEM_COIN_1 = ("coin_1", "コインx1", "硬币x1", "硬幣x1")
    # ITEM_3STAR_VOUCHER = ("3star_voucher", "★3メンバーセレクト券", "★3成员自选券", "★3成員自選券")
    # ITEM_2STAR_VOUCHER = ("2star_voucher", "★2メンバー交換券", "★2成员自选券", "★2成員自選券")

    _display_maps: dict[str, dict[str, "ShopItem"]]

    def __new__(cls, value: str, jp: str, cn: str, tw: str):
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj.jp = jp
        obj.cn = cn
        obj.tw = tw
        return obj

    def display(self, server: Literal["jp", "cn", "tw"]) -> str:
        if server == "jp":
            return self.jp
        if server == "cn":
            return self.cn
        if server == "tw":
            return self.tw
        raise ValueError(f"Unsupported server: {server}")

    @classmethod
    def from_display(cls, server: Literal["jp", "cn", "tw"], text: str) -> Optional["ShopItem"]:
        try:
            return cls._display_maps[server].get(text)
        except KeyError as e:
            raise ValueError(f"Unsupported server: {server}") from e


ShopItem._display_maps = {
    "jp": {item.jp: item for item in ShopItem},
    "cn": {item.cn: item for item in ShopItem},
    "tw": {item.tw: item for item in ShopItem},
}

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
