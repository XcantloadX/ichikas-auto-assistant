from kotonebot import task

from .live import SingleLoopPlan, solo_live as do_solo_live
from iaa.tasks.common import go_home
from iaa.context import conf


@task('单人演出')
def solo_live():
    go_home()
    plan = SingleLoopPlan(
        play_mode='game_auto',
        ap_multiplier=conf().live.ap_multiplier,
        song_name=conf().live.song_name,
        auto_set_unit=conf().live.auto_set_unit,
        song_select_mode='specified' if conf().live.song_name else 'current',
    )
    do_solo_live(plan)
    # if not do_solo_live('single-loop'):
    #     return
    # if conf().live.fully_deplete:
    #     go_home()
    #     do_solo_live()
