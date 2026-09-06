from __future__ import annotations

from iaa.tasks.live.auto_live_constants import (
    AP_KEEP_UNCHANGED,
    PRESET_CLEAR_10,
    PRESET_FC_10,
    PRESET_SCRIPT_999,
    SONG_KEEP_UNCHANGED,
)
from iaa.config.live_presets import AutoLivePreset
from iaa.tasks.live.live import (
    ListLoopPlan,
    SingleLoopPlan,
    auto_live_payload_to_plan as auto_live_payload_to_plan,
    normalize_song_name_input as normalize_song_name_input,
)

SONG_NAME_OPTIONS = [
    SONG_KEEP_UNCHANGED,
    'メルト',
    '独りんぼエンヴィー',
]


def preset_to_payload(preset: AutoLivePreset) -> dict[str, object]:
    """把预设转换为 GUI 表单使用的 payload。

    :param preset: 演出预设。
    :return: 含 countMode/loopMode/playMode/apMultiplier/songName 等键的 payload。
    """
    plan = preset.plan
    payload: dict[str, object] = {
        'name': preset.name,
        'countMode': 'all' if plan.loop_count is None else 'specify',
        'count': '' if plan.loop_count is None else str(plan.loop_count),
        'playMode': plan.play_mode,
        'debugEnabled': plan.debug_enabled,
        'autoSetUnit': plan.auto_set_unit,
        'apMultiplier': AP_KEEP_UNCHANGED if plan.ap_multiplier is None else str(plan.ap_multiplier),
        'songName': '',
        'loopMode': 'list',
    }
    if isinstance(plan, SingleLoopPlan):
        payload['loopMode'] = 'single'
        payload['songName'] = plan.song_name or SONG_KEEP_UNCHANGED
    elif isinstance(plan, ListLoopPlan):
        payload['loopMode'] = 'random' if plan.loop_song_mode == 'random' else 'list'
    return payload


def builtin_auto_presets() -> list[dict[str, object]]:
    """内置演出预设列表（payload 形式，供 GUI 下拉/按钮展示）。

    :return: 内置预设的 payload 列表。
    """
    presets = [
        AutoLivePreset(
            name=PRESET_CLEAR_10,
            plan=ListLoopPlan(loop_count=10, play_mode='game_auto', ap_multiplier=1),
        ),
        AutoLivePreset(
            name=PRESET_FC_10,
            plan=SingleLoopPlan(loop_count=10, play_mode='script_auto', ap_multiplier=0),
        ),
        AutoLivePreset(
            name=PRESET_SCRIPT_999,
            plan=SingleLoopPlan(loop_count=999, play_mode='script_auto', ap_multiplier=0),
        ),
    ]
    return [preset_to_payload(preset) for preset in presets]
