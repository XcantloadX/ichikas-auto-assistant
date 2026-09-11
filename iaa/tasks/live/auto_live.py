from kotonebot import task

from iaa.tasks.common import go_home
from iaa.context import task_reporter
from .live import ListLoopPlan, SingleLoopPlan, solo_live as do_solo_live
from iaa.i18n import TStr


@task('自动演出')
def auto_live(plan: SingleLoopPlan | ListLoopPlan) -> None:
    reporter = task_reporter()
    reporter.message(TStr(zh_CN='准备自动演出参数', en_US='Preparing auto live options'))
    
    if plan.loop_count is not None and plan.loop_count <= 0:
        raise ValueError('loop_count 必须为正整数或 None。')
    if isinstance(plan, SingleLoopPlan) and plan.song_select_mode == 'specified' and not plan.song_name:
        raise ValueError('song_name is required when song_select_mode is specified.')

    reporter.message(TStr(zh_CN='返回首页准备进入演出', en_US='Returning home before live'))
    go_home()
    reporter.message(TStr(zh_CN='进入自动演出流程', en_US='Starting auto live flow'))
    do_solo_live(plan)
