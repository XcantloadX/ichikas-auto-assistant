from __future__ import annotations

from typing import Any, Literal

from iaa.i18n import TStr, tstr
from iaa.definitions.enums import (
    ChallengeLiveAward,
    GameCharacter,
    LinkAccountOptions,
    ShopItem,
)
from iaa.definitions.consts import ServerName

LIFECYCLE_TYPE_DISPLAY_MAP: dict[str, TStr] = {
    'mumu_v5': TStr(zh_CN='MuMu 12 (v5)', en_US='MuMu 12 (v5)'),
    'mumu': TStr(zh_CN='MuMu 12 (v4)', en_US='MuMu 12 (v4)'),
    'avd': TStr(zh_CN='AVD', en_US='AVD'),
    'custom': tstr('settings.option.lifecycle.custom'),
    'none': tstr('settings.option.lifecycle.none'),
    'playcover': TStr(zh_CN='PlayCover', en_US='PlayCover'),
}

CONNECTION_TYPE_DISPLAY_MAP: dict[str, TStr] = {
    'usb': TStr(zh_CN='USB', en_US='USB'),
    'tcp': tstr('settings.option.connection.tcp'),
}

SERVER_DISPLAY_MAP: dict[ServerName, TStr] = {
    'jp': tstr('settings.option.server.jp'),
    'tw': tstr('settings.option.server.tw'),
    'cn': tstr('settings.option.server.cn'),
    'en': tstr('settings.option.server.en'),
}

LINK_DISPLAY_MAP: dict[LinkAccountOptions, TStr] = {
    'no': tstr('settings.option.link.no'),
    'google': tstr('settings.option.link.google'),
    'google_play': TStr(zh_CN='Google Play', en_US='Google Play'),
}

CONTROL_IMPL_DISPLAY_MAP: dict[Literal['nemu_ipc', 'adb', 'uiautomator', 'scrcpy', 'qemu_grpc'], TStr] = {
    'nemu_ipc': TStr(zh_CN='Nemu IPC', en_US='Nemu IPC'),
    'adb': TStr(zh_CN='ADB', en_US='ADB'),
    'uiautomator': TStr(zh_CN='UIAutomator2', en_US='UIAutomator2'),
    'scrcpy': TStr(zh_CN='Scrcpy', en_US='Scrcpy'),
    'qemu_grpc': TStr(zh_CN='QEMU gRPC', en_US='QEMU gRPC'),
}

RESOLUTION_METHOD_DISPLAY_MAP: dict[Literal['keep', 'wm_size'], TStr] = {
    'keep': tstr('settings.option.resolution.keep'),
    'wm_size': tstr('settings.option.resolution.wm_size'),
}

DEFAULT_MUMU_INSTANCE_LABEL = '默认'

CHALLENGE_CHARACTER_GROUPS: list[tuple[str, list[GameCharacter]]] = [
    (
        'VIRTUAL SINGER',
        [
            GameCharacter.Miku,
            GameCharacter.Rin,
            GameCharacter.Len,
            GameCharacter.Luka,
            GameCharacter.Meiko,
            GameCharacter.Kaito,
        ],
    ),
    (
        'Leo/need',
        [GameCharacter.Ichika, GameCharacter.Saki, GameCharacter.Honami, GameCharacter.Shiho],
    ),
    (
        'MORE MORE JUMP!',
        [GameCharacter.Minori, GameCharacter.Haruka, GameCharacter.Airi, GameCharacter.Shizuku],
    ),
    (
        'Vivid BAD SQUAD',
        [GameCharacter.Kohane, GameCharacter.An, GameCharacter.Akito, GameCharacter.Toya],
    ),
    (
        'ワンダーランズ×ショウタイム',
        [GameCharacter.Tsukasa, GameCharacter.Emu, GameCharacter.Nene, GameCharacter.Rui],
    ),
    (
        '25時、ナイトコードで。',
        [GameCharacter.Kanade, GameCharacter.Mafuyu, GameCharacter.Ena, GameCharacter.Mizuki],
    ),
]


def _character_label(character: GameCharacter) -> TStr:
    return TStr(
        zh_CN=f'{character.last_name_cn}{character.first_name_cn}',
        en_US=f'{character.first_name_en} {character.last_name_en}'.strip(),
    )


def challenge_character_groups_for_ui() -> list[dict[str, object]]:
    return [
        {
            'group': group_name,
            'options': [
                {
                    'value': character.value,
                    'label': _character_label(character),
                    'image': f'chibi/{character.value}.png',
                }
                for character in characters
            ],
        }
        for group_name, characters in CHALLENGE_CHARACTER_GROUPS
    ]


def challenge_characters_for_ui() -> list[dict[str, Any]]:
    all_characters = []
    for _, characters in CHALLENGE_CHARACTER_GROUPS:
        for character in characters:
            all_characters.append({
                'value': character.value,
                'label': _character_label(character),
            })
    return all_characters


_CHALLENGE_AWARD_IMAGES: dict[ChallengeLiveAward, str] = {
    ChallengeLiveAward.Crystal: 'game_items/Jewel.png',
    ChallengeLiveAward.MusicCard: 'game_items/Song_card.png',
    ChallengeLiveAward.MiracleGem: 'game_items/Miracle_gem.png',
    ChallengeLiveAward.MagicCloth: 'game_items/Magic_cloth.png',
    ChallengeLiveAward.Coin: 'game_items/Coin.png',
    ChallengeLiveAward.IntermediatePracticeScore: 'game_items/Practice_score_(intermediate).png',
}


_CHALLENGE_AWARD_LABELS_CN: dict[ChallengeLiveAward, str] = {
    ChallengeLiveAward.Crystal: '水晶',
    ChallengeLiveAward.MusicCard: '音乐卡',
    ChallengeLiveAward.MiracleGem: '奇迹晶石',
    ChallengeLiveAward.MagicCloth: '魔法之布',
    ChallengeLiveAward.Coin: '硬币',
    ChallengeLiveAward.IntermediatePracticeScore: '中级练习乐谱',
}

_CHALLENGE_AWARD_LABELS_EN: dict[ChallengeLiveAward, str] = {
    ChallengeLiveAward.Crystal: 'Crystals',
    ChallengeLiveAward.MusicCard: 'Music Card',
    ChallengeLiveAward.MiracleGem: 'Miracle Gem',
    ChallengeLiveAward.MagicCloth: 'Magic Cloth',
    ChallengeLiveAward.Coin: 'Coins',
    ChallengeLiveAward.IntermediatePracticeScore: 'Practice Score (Intermediate)',
}


def challenge_awards_for_ui() -> list[dict[str, Any]]:
    return [
        {
            'value': award.value,
            'label': TStr(
                zh_CN=_CHALLENGE_AWARD_LABELS_CN.get(award, award.value),
                en_US=_CHALLENGE_AWARD_LABELS_EN.get(award, award.value),
            ),
            'image': _CHALLENGE_AWARD_IMAGES.get(award, ''),
        }
        for award in ChallengeLiveAward
    ]


# 商店道具的 UI 显示名（英文译名）。zh 侧直接复用 ShopItem 的简中名（item.cn），
# 枚举里的 jp/cn/tw 是游戏内名称（供 OCR 匹配），与界面显示语言无关。
_SHOP_ITEM_LABELS_EN: dict[str, str] = {
    '2star_event_card': '★2 Member Card',
    '3star_event_card': '★3 Member Card',
    'cover_card_voucher': 'Vocal Card Exchange Ticket',
    'crystal': 'Crystals',
    'wish_piece': 'Wish Fragments',
    'bonus_energy_drink_s': 'Live Bonus Drink (S)',
    'stamp_voucher': 'Stamp Exchange Ticket',
    'practice_score_intermediate': 'Practice Score (Intermediate)',
    'music_card': 'Music Card',
    'miracle_gem': 'Miracle Gem',
    'magic_cloth': 'Magic Cloth',
    'magic_thread': 'Magic Thread',
    'magical_seed': 'Magical Seed',
    'wish_drop': 'Wish Drops',
    'skill_up_score_intermediate': 'Skill Up Score (Intermediate)',
    'coin_100000': 'Coins ×100000',
    'coin_1': 'Coins ×1',
}


def shop_items_for_ui() -> list[dict[str, Any]]:
    """商店道具选项，label 为跟随界面语言的 TStr。"""
    return [
        {
            'value': item.value,
            'label': TStr(
                zh_CN=item.cn,
                en_US=_SHOP_ITEM_LABELS_EN.get(item.value, item.value),
            ),
        }
        for item in ShopItem
    ]
