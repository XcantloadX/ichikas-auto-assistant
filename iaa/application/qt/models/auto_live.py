from __future__ import annotations

from iaa.config.live_presets import AutoLivePreset
from iaa.tasks.live.live import ListLoopPlan, SingleLoopPlan, SONG_KEEP_UNCHANGED

SONG_NAME_OPTIONS = [
    SONG_KEEP_UNCHANGED,
    'メルト',
    '独りんぼエンヴィー',
]


def preset_to_payload(preset: AutoLivePreset) -> dict[str, object]:
    plan = preset.plan
    payload: dict[str, object] = {
        'name': preset.name,
        'countMode': 'all' if plan.loop_count is None else 'specify',
        'count': '' if plan.loop_count is None else str(plan.loop_count),
        'playMode': plan.play_mode,
        'debugEnabled': plan.debug_enabled,
        'autoSetUnit': plan.auto_set_unit,
        'apMultiplier': '保持现状' if plan.ap_multiplier is None else str(plan.ap_multiplier),
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
    presets = [
        AutoLivePreset(
            name='CLEARx10',
            plan=ListLoopPlan(loop_count=10, play_mode='game_auto', ap_multiplier=1),
        ),
        AutoLivePreset(
            name='APx10',
            plan=SingleLoopPlan(loop_count=10, play_mode='script_auto', ap_multiplier=0),
        ),
        AutoLivePreset(
            name='脚本x999',
            plan=SingleLoopPlan(loop_count=999, play_mode='script_auto', ap_multiplier=0),
        ),
    ]
    return [preset_to_payload(preset) for preset in presets]
