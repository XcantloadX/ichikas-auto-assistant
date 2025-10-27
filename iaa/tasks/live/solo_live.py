from kotonebot import task

from .live import solo_live as do_solo_live
from iaa.tasks.common import go_home
from iaa.context import conf


@task('单人演出')
def solo_live():
    go_home()
    if not do_solo_live('single-loop'):
        return
    if conf().live.fully_deplete:
        go_home()
        do_solo_live()