from __future__ import annotations

from typing import Any, Literal

from iaa.application.qt.i18n import TStr
from iaa.definitions.enums import (
    ChallengeLiveAward,
    GameCharacter,
    LinkAccountOptions,
)
from iaa.definitions.consts import ServerName

LIFECYCLE_TYPE_DISPLAY_MAP: dict[str, str] = {
    'mumu_v5': 'MuMu 12 (v5)',
    'mumu': 'MuMu 12 (v4)',
    'custom': '自定义模拟器',
    'none': '物理机 / 手动管理',
    'playcover': 'PlayCover',
}

CONNECTION_TYPE_DISPLAY_MAP: dict[str, str] = {
    'usb': 'USB',
    'tcp': 'TCP / 无线',
}

SERVER_DISPLAY_MAP: dict[ServerName, str] = {
    'jp': '日服',
    'tw': '台服',
    'cn': '国服',
    'en': '国际服',
}
SERVER_VALUE_MAP: dict[str, ServerName] = {value: key for key, value in SERVER_DISPLAY_MAP.items()}

LINK_DISPLAY_MAP: dict[LinkAccountOptions, str] = {
    'no': '不引继账号',
    'google': 'Google 账号',
    'google_play': 'Google Play',
}
LINK_VALUE_MAP: dict[str, LinkAccountOptions] = {value: key for key, value in LINK_DISPLAY_MAP.items()}

CONTROL_IMPL_DISPLAY_MAP: dict[Literal['nemu_ipc', 'adb', 'uiautomator', 'scrcpy'], str] = {
    'nemu_ipc': 'Nemu IPC',
    'adb': 'ADB',
    'uiautomator': 'UIAutomator2',
    'scrcpy': 'Scrcpy',
}
CONTROL_IMPL_VALUE_MAP: dict[str, Literal['nemu_ipc', 'adb', 'uiautomator', 'scrcpy']] = {
    value: key for key, value in CONTROL_IMPL_DISPLAY_MAP.items()
}

RESOLUTION_METHOD_DISPLAY_MAP: dict[Literal['auto', 'keep', 'wm_size'], str] = {
    'auto': '智能决定',
    'keep': '保持原始分辨率',
    'wm_size': '修改分辨率（wm size）',
}
RESOLUTION_METHOD_VALUE_MAP: dict[str, Literal['auto', 'keep', 'wm_size']] = {
    value: key for key, value in RESOLUTION_METHOD_DISPLAY_MAP.items()
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
