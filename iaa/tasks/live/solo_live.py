from kotonebot import task

from .live import OncePlan, SingleLoopPlan, solo_live as do_solo_live
from iaa.tasks.common import go_home
from iaa.context import conf


@task('单人演出')
def solo_live():    
    # 追加随机歌曲：为了完成 CLEAR 10 首不同歌曲的任务
    if conf().tasks.solo_live.prepend_random:
        go_home()
        do_solo_live(
            OncePlan(
                ap_multiplier=1,
                auto_set_unit=conf().tasks.solo_live.auto_set_unit,
                song_select_mode='random',
            )
        )

    # 清体力
    go_home()
    do_solo_live(SingleLoopPlan(
        play_mode='game_auto',
        ap_multiplier=conf().tasks.solo_live.ap_multiplier,
        song_name=conf().tasks.solo_live.song_name,
        auto_set_unit=conf().tasks.solo_live.auto_set_unit,
        song_select_mode='specified' if conf().tasks.solo_live.song_name else 'current',
    ))

    # 追加随机歌曲：为了完成 FC 10 次的任务
    if conf().tasks.solo_live.append_fc:
        go_home()
        do_solo_live(
            SingleLoopPlan(
                loop_count=1,
                play_mode='script_auto',
                debug_enabled=False,
                ap_multiplier=0,
                song_name=conf().tasks.solo_live.song_name,
                auto_set_unit=conf().tasks.solo_live.auto_set_unit,
                song_select_mode='specified' if conf().tasks.solo_live.song_name else 'current',
            )
        )
