from __future__ import annotations

from typing import Any

from iaa.config.live_presets import AutoLivePreset
from iaa.tasks.live.live import ListLoopPlan, SingleLoopPlan

SONG_KEEP_UNCHANGED = '保持不变'
SONG_NAME_OPTIONS = [
    SONG_KEEP_UNCHANGED,
    'メルト',
    '独りんぼエンヴィー',
]


def normalize_song_name_input(value: str) -> str | None:
    normalized = (value or '').strip()
    if not normalized or normalized == SONG_KEEP_UNCHANGED:
        return None
    return normalized


def auto_live_payload_to_plan(payload: dict[str, Any]) -> SingleLoopPlan | ListLoopPlan:
    count_mode = str(payload.get('countMode') or 'specify')
    loop_mode = str(payload.get('loopMode') or 'list')
    auto_mode = str(payload.get('playMode') or 'game_auto')
    ap_multiplier_raw = payload.get('apMultiplier', '保持现状')
    debug_enabled = bool(payload.get('debugEnabled'))
    auto_set_unit = bool(payload.get('autoSetUnit'))
    song_name = normalize_song_name_input(str(payload.get('songName') or ''))

    count: int | None = None
    if count_mode == 'specify':
        raw_count = str(payload.get('count') or '').strip()
        if not raw_count.isdigit() or int(raw_count) <= 0:
            raise ValueError('指定次数必须为正整数。')
        count = int(raw_count)
    elif count_mode != 'all':
        raise ValueError(f'未知的次数模式：{count_mode}')

    if ap_multiplier_raw in (None, '', '保持现状'):
        ap_multiplier: int | None = None
    else:
        ap_multiplier = int(ap_multiplier_raw)
        if not (0 <= ap_multiplier <= 10):
            raise ValueError('AP 倍率必须在 0 到 10 之间。')

    if loop_mode == 'single':
        return SingleLoopPlan(
            loop_count=count,
            song_select_mode='specified' if song_name else 'current',
            song_name=song_name,
            play_mode='script_auto' if auto_mode == 'script_auto' else 'game_auto',
            debug_enabled=debug_enabled,
            ap_multiplier=ap_multiplier,
            auto_set_unit=auto_set_unit,
        )
    if loop_mode in ('list', 'random'):
        return ListLoopPlan(
            loop_count=count,
            loop_song_mode='random' if loop_mode == 'random' else 'list_next',
            play_mode='script_auto' if auto_mode == 'script_auto' else 'game_auto',
            debug_enabled=debug_enabled,
            ap_multiplier=ap_multiplier,
            auto_set_unit=auto_set_unit,
        )
    raise ValueError(f'未知的循环模式：{loop_mode}')


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
            name='CLEAR 10 首歌',
            plan=ListLoopPlan(loop_count=10, play_mode='game_auto', ap_multiplier=1),
        ),
        AutoLivePreset(
            name='FC 10 次',
            plan=SingleLoopPlan(loop_count=10, play_mode='script_auto', ap_multiplier=0),
        ),
        AutoLivePreset(
            name='队长次数',
            plan=SingleLoopPlan(loop_count=30, play_mode='script_auto', ap_multiplier=0),
        ),
    ]
    return [preset_to_payload(preset) for preset in presets]
