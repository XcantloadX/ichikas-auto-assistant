from kotonebot import action

from .. import R

@action('是否位于选歌界面')
def at_song_select():
    """
    检测是否位于歌曲选择界面，返回找到的按钮结果。

    前置：位于选歌界面
    结束：-
    """
    return R.Live.ButtonDecide.find() 