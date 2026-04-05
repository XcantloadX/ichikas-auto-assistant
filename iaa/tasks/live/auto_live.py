from kotonebot import task

from iaa.tasks.common import go_home
from iaa.context import task_reporter
from .live import ListLoopPlan, SingleLoopPlan, solo_live as do_solo_live


@task('自动演出')
def auto_live(plan: SingleLoopPlan | ListLoopPlan) -> None:
    reporter = task_reporter()
    reporter.message('准备自动演出参数')
    
    if plan.loop_count is not None and plan.loop_count <= 0:
        raise ValueError('loop_count 必须为正整数或 None。')
    if isinstance(plan, SingleLoopPlan) and plan.song_select_mode == 'specified' and not plan.song_name:
        raise ValueError('song_name is required when song_select_mode is specified.')

    reporter.message('返回首页准备进入演出')
    go_home()
    reporter.message('进入自动演出流程')
    do_solo_live(plan)
