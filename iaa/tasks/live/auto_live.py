from typing import Literal

from kotonebot import task

from iaa.tasks.common import go_home
from iaa.context import task_reporter
from .live import solo_live as do_solo_live


@task('自动演出')
def auto_live(
    count_mode: Literal['specify', 'all'] = 'specify',
    count: int | None = 10,
    loop_mode: Literal['single', 'list'] = 'list',
    auto_mode: Literal['none', 'game_auto', 'script_auto'] = 'game_auto',
    debug_enabled: bool = False,
) -> None:
    reporter = task_reporter()
    reporter.message('准备自动演出参数')
    if count_mode == 'specify':
        if count is None or count <= 0:
            raise ValueError('count 必须为正整数。')
        loop_count = count
    else:
        loop_count = None

    songs_mode: Literal['single-loop', 'list-loop'] = 'single-loop' if loop_mode == 'single' else 'list-loop'
    # 目前任务层仅支持 game/script 两种自动模式；none 按 game_auto 处理。
    inner_auto_mode: Literal['game', 'script'] = 'script' if auto_mode == 'script_auto' else 'game'

    reporter.message('返回首页准备进入演出')
    go_home()
    reporter.message('进入自动演出流程')
    do_solo_live(
        songs=songs_mode,
        loop_count=loop_count,
        auto_mode=inner_auto_mode,
        debug_enabled=debug_enabled,
    )
