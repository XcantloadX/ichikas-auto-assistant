from __future__ import annotations

from typing import Literal

from iaa.definitions.enums import (
    ChallengeLiveAward,
    EmulatorOptions,
    GameCharacter,
    LinkAccountOptions,
)

EMULATOR_DISPLAY_MAP: dict[EmulatorOptions, str] = {
    'mumu': 'MuMu',
    'mumu_v5': 'MuMu v5.x',
    'custom': '自定义',
    'physical_android': '物理设备(USB)',
}
EMULATOR_VALUE_MAP: dict[str, EmulatorOptions] = {value: key for key, value in EMULATOR_DISPLAY_MAP.items()}

SERVER_DISPLAY_MAP: dict[Literal['jp', 'tw', 'cn'], str] = {
    'jp': '日服',
    'tw': '台服',
    'cn': '国服',
}
SERVER_VALUE_MAP: dict[str, Literal['jp', 'tw', 'cn']] = {value: key for key, value in SERVER_DISPLAY_MAP.items()}

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


def challenge_character_groups_for_ui() -> list[dict[str, object]]:
    return [
        {
            'group': group_name,
            'options': [
                {'value': character.value, 'label': f'{character.last_name_cn}{character.first_name_cn}'}
                for character in characters
            ],
        }
        for group_name, characters in CHALLENGE_CHARACTER_GROUPS
    ]


def challenge_characters_for_ui() -> list[dict[str, str]]:
    all_characters = []
    for _, characters in CHALLENGE_CHARACTER_GROUPS:
        for character in characters:
            all_characters.append({
                'value': character.value,
                'label': f'{character.last_name_cn}{character.first_name_cn}'
            })
    return all_characters


def challenge_awards_for_ui() -> list[dict[str, str]]:
    return [
        {'value': award.value, 'label': label}
        for award, label in ChallengeLiveAward.display_map_cn().items()
    ]
