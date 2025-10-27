from kotonebot import task

from ..common import go_home
from .live import solo_live

@task('完成不同歌曲')
def ten_songs():
    go_home()
    solo_live('list-loop', loop_count=10)