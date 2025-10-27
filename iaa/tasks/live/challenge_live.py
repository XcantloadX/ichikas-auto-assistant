from kotonebot import task

from iaa.context import conf
from iaa.tasks.common import go_home
from .live import challenge_live as do_challenge_live

@task('挑战演出')
def challenge_live():
    go_home()
    do_challenge_live(conf().challenge_live.characters[0])