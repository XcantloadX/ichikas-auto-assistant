from typing import Literal

from kotonebot import task

from iaa.tasks.common import go_home
from iaa.context import conf, task_reporter
from .live import ListLoopPlan, SingleLoopPlan, solo_live as do_solo_live


@task('自动演出')
def auto_live(
    run_count: int | None = 10,
    cycle_mode: Literal['single', 'list'] = 'list',
    play_mode: Literal['game_auto', 'script_auto'] = 'game_auto',
    debug_enabled: bool = False,
    ap_multiplier: int | None = None,
    song_name: str | None = None,
) -> None:
    reporter = task_reporter()
    reporter.message('准备自动演出参数')
    if ap_multiplier is not None and not (0 <= ap_multiplier <= 10):
        raise ValueError('ap_multiplier 必须在 0 到 10 之间。')
    if run_count is not None and run_count <= 0:
        raise ValueError('run_count 必须为正整数或 None。')
    if cycle_mode == 'list' and song_name:
        raise ValueError('list cycle mode does not support song_name.')

    if cycle_mode == 'single':
        plan = SingleLoopPlan(
            loop_count=run_count,
            play_mode=play_mode,
            debug_enabled=debug_enabled,
            ap_multiplier=ap_multiplier,
            song_name=song_name,
            auto_set_unit=conf().live.auto_set_unit,
            song_select_mode='specified' if song_name else 'current',
        )
    else:
        plan = ListLoopPlan(
            loop_count=run_count,
            play_mode=play_mode,
            debug_enabled=debug_enabled,
            ap_multiplier=ap_multiplier,
            auto_set_unit=conf().live.auto_set_unit,
        )

    reporter.message('返回首页准备进入演出')
    go_home()
    reporter.message('进入自动演出流程')
    do_solo_live(plan)
