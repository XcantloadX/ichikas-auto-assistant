from kotonebot import task

from ..common import go_home
from iaa.context import conf
from .live import ListLoopPlan, solo_live

@task('完成不同歌曲')
def ten_songs():
    go_home()
    plan = ListLoopPlan(
        loop_count=10,
        auto_set_unit=conf().live.auto_set_unit,
    )
    solo_live(plan)
