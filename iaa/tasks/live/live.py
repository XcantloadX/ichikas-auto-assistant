from typing import Callable, Literal
from typing_extensions import assert_never

from kotonebot import logging
from kotonebot import device, image, Loop, action, sleep, color

from .. import R
from ..common import at_home
from iaa.context import conf
from ._select_song import next_song
from ._scene import at_song_select
from iaa.config.schemas import ChallengeLiveAward, GameCharacter

logger = logging.getLogger(__name__)

@action('演出', screenshot_mode='manual')
def start_auto_live(
    auto_setting: Literal['all'] | Literal['once'] | int | None = 'all',
    back_to: Literal['home'] | Literal['select'] | None = 'home',
    finish_pre_check: Callable[[], tuple[bool, bool]] | None = None,
) -> bool:
    """
    前置：位于编队界面\n
    结束：首页、选歌界面或 LIVE CLEAR 画面

    :param auto_setting: 自动演出设置。\n
        * `"all"`: 自动演出直到 AP 不足
        * 任意整数: 自动演出指定次数
        * `"once"`: 自动演出一次
        * `None`: 不自动演出
    :param back_to: 返回位置。\n
        * `"home"`: 返回首页
        * `"select"`: 返回选歌界面
        * `None`: 不返回，直接在 LIVE CLEAR 或「已完成指定次数的演出」画面结束
    :param finish_pre_check:
        结束演出时的额外处理，在检查循环的开始处调用。返回 `(should_skip, should_break)`。
        * `should_skip`: 如果 True，则跳过当前循环。
        * `should_break`: 如果 True，则结束循环。
        如果 `should_skip` 为 True，则 `should_break` 会被忽略。
    :raises NotImplementedError: 如果未实现的功能被调用。
    :return: 若为 False，表示因为 AP 不足没有进行演出。
    """
    if auto_setting is None or isinstance(auto_setting, int):
        raise NotImplementedError('Not implemented yet.')
    # 设置自动演出设置
    if auto_setting == 'all':
        chose = False
        for _ in Loop(interval=0.6):
            if image.find(R.Live.SwitchAutoLiveOn):
                logger.debug('Auto live switch checked on.')
                break
            elif image.find(R.Live.TextAtLeastOneAp):
                logger.info('No AP left to enable auto live. Exiting.')
                return False
            elif image.find(R.Live.ButtonAutoLiveSettings):
                device.click()
                logger.debug('Clicked auto live settings button.')
            elif not chose and image.find(R.Live.TextAutoLiveUntilInsufficient):
                device.click()
                logger.debug('Chose auto live until insufficient AP.')
                sleep(0.3)
                chose = True
            elif image.find(R.Live.ButtonDecideAutoLive):
                device.click()
                logger.debug('Clicked decide auto live button.')
                sleep(0.3)
    elif auto_setting == 'once':
        for _ in Loop(interval=0.6):
            if image.find(R.Live.SwitchAutoLiveOn):
                logger.debug('Auto live switch checked on.')
                break
            elif image.find(R.Live.TextAtLeastOneAp):
                logger.info('No AP left to enable auto live. Exiting.')
                return False
            elif image.find(R.Live.SwitchAutoLiveOff):
                device.click()
                logger.debug('Clicked auto live switch.')
                sleep(0.3)
    logger.info('Auto live setting finished.')

    # 开始并等待完成
    logger.debug('Clicking start live button.')
    device.click(image.expect_wait(R.Live.ButtonStartLive))
    sleep(74.8 + 5) # 孑然妒火（最短曲） + 5s 缓冲

    is_mutiple_auto = (auto_setting == 'all' or isinstance(auto_setting, int))
    for _ in Loop():
        # 结束条件
        if is_mutiple_auto:
            # 指定演出次数或直到 AP 不足
            # 结束条件是「已完成指定次数的演出」提示
            if image.find(R.Live.TextAutoLiveCompleted):
                device.click(1, 1)
                logger.info('Auto lives all completed.')
                sleep(0.3)
                break
        else:
            # 单次演出
            # 结束条件是「SCORERANK」提示
            if image.find(R.Live.TextScoreRank):
                logger.debug('Waiting for SCORERANK')
                sleep(1) # 等待 SCORERANK 动画完成
                device.click_center()
                break
    if back_to is None:
        return True
    # 返回
    for _ in Loop(interval=0.5):
        if finish_pre_check:
            should_skip, should_break = finish_pre_check()
            if should_break:
                break
            if should_skip:
                continue
        # 返回主页只要一直点就可以了
        if back_to == 'home':
            if at_home():
                break
            device.click(1, 1)
            sleep(0.6)
        # 返回选歌界面要点“返回歌曲选择”按钮
        elif back_to == 'select':
            if image.find(R.Live.ButtonLiveCompletedNext):
                device.click()
                logger.debug('Clicked live completed ok button.')
            elif image.find(R.Live.ButtonGoSongSelect):
                device.click()
                logger.debug('Clicked select song button.')
            elif at_song_select():
                logger.debug('Now at song select.')
                break
            else:
                logger.debug('Waiting for reward screen finished.')
    return True

@action('选歌', screenshot_mode='manual')
def enter_unit_select():
    """
    前置：位于选歌界面\n
    结束：位于编队界面
    """
    for _ in Loop(interval=0.6):
        if btn_start := at_song_select():
            device.click(btn_start)
            logger.debug('Clicked start live button.')
            break
    logger.info('Song select finished.')

@action('单人演出', screenshot_mode='manual')
def solo_live(
    songs: list[str] | Literal['single-loop'] | Literal['list-loop'] | None = None,
    loop_count: int | None = None,
):
    """
    
    :param songs: 演出歌曲列表。\n
    * `None`: 不指定歌曲
    * `"single-loop"`: 单曲循环演出
    * `"list-loop"`: 列表循环演出
    * `list[str]`: 指定要演出的歌曲列表
    :param loop_count: 列表循环演出次数。\n
        * `None`: 不限制次数
        * 任意整数: 演出指定次数
    """
    if loop_count is not None and loop_count <= 0:
        raise ValueError('loop_count must be positive.')
    # 进入单人演出
    for _ in Loop(interval=0.6):
        if image.find(R.Hud.ButtonLive, threshold=0.55):
            device.click()
            logger.debug('Clicked home LIVE button.')
            sleep(1)
        elif image.find(R.Live.ButtonSoloLive):
            device.click()
            logger.debug('Clicked SoloLive button.')
        elif at_song_select():
            logger.debug('Now at song select.')
            break
    
    count = 0
    max_count = loop_count or float('inf')
    match songs:
        case None:
            enter_unit_select()
            start_auto_live('once', back_to='home')
        case 'single-loop':
            enter_unit_select()
            start_auto_live('all', back_to='home')
        # 列表循环
        case 'list-loop':
            for _ in Loop():
                next_song()
                enter_unit_select()
                start_auto_live('once', back_to='select')
                logger.info(f'Song looped. {count}/{max_count}')
                count += 1
                if count >= max_count:
                    break
        case songs if isinstance(songs, list):
            raise NotImplementedError('Not implemented yet.')
        case _:
            assert_never(songs)

@action('挑战演出', screenshot_mode='manual')
def challenge_live(
    character: GameCharacter
):
    # 进入挑战演出
    for _ in Loop(interval=0.6):
        if image.find(R.Hud.ButtonLive, threshold=0.55):
            device.click()
            logger.debug('Clicked home LIVE button.')
            sleep(1)
        elif image.find(R.Live.ButtonChallengeLive):
            if not color.find('#ff5589', rect=R.Live.BoxChallengeLiveRedDot):
                logger.info("Today's challenge live already cleared.")
                return
            device.click()
            logger.debug('Clicked ChallengeLive button.')
        elif image.find(R.Live.ChallengeLive.TextSelectCharacter):
            logger.debug('Now at character select.')
            break
        elif image.find(R.Live.ChallengeLive.GroupVirtualSinger):
            # 为了防止误触某个角色，导致次数不够提示弹出来，挡住 TextSelectCharacter
            # 文本，结果一直卡在 TextSelectCharacter 识别上。
            # 加上这个点击用于取消次数不足提示。
            device.click()
            logger.debug('Clicked group virtual singer.')

    # 选择角色
    logger.info(f'Selecting character: {character.value}')
    def char_to_res(ch: GameCharacter):
        """返回 (角色贴图, 分组贴图或 None)。"""
        match ch:
            case GameCharacter.Miku:
                return (R.Live.ChallengeLive.CharaMiku, R.Live.ChallengeLive.GroupVirtualSinger)
            case GameCharacter.Rin:
                return (R.Live.ChallengeLive.CharaRin, R.Live.ChallengeLive.GroupVirtualSinger)
            case GameCharacter.Len:
                return (R.Live.ChallengeLive.CharaLen, R.Live.ChallengeLive.GroupVirtualSinger)
            case GameCharacter.Luka:
                return (R.Live.ChallengeLive.CharaLuka, R.Live.ChallengeLive.GroupVirtualSinger)
            case GameCharacter.Meiko:
                return (R.Live.ChallengeLive.CharaMeiko, R.Live.ChallengeLive.GroupVirtualSinger)
            case GameCharacter.Kaito:
                return (R.Live.ChallengeLive.CharaKaito, R.Live.ChallengeLive.GroupVirtualSinger)

            case GameCharacter.Ichika:
                return (R.Live.ChallengeLive.CharaIchika, R.Live.ChallengeLive.GroupLeoneed)
            case GameCharacter.Saki:
                return (R.Live.ChallengeLive.CharaSaki, R.Live.ChallengeLive.GroupLeoneed)
            case GameCharacter.Honami:
                return (R.Live.ChallengeLive.CharaHonami, R.Live.ChallengeLive.GroupLeoneed)
            case GameCharacter.Shiho:
                return (R.Live.ChallengeLive.CharaShiho, R.Live.ChallengeLive.GroupLeoneed)

            case GameCharacter.Minori:
                return (R.Live.ChallengeLive.CharaMinori, R.Live.ChallengeLive.GroupMoreMoreJump)
            case GameCharacter.Haruka:
                return (R.Live.ChallengeLive.CharaHaruka, R.Live.ChallengeLive.GroupMoreMoreJump)
            case GameCharacter.Airi:
                return (R.Live.ChallengeLive.CharaAiri, R.Live.ChallengeLive.GroupMoreMoreJump)
            case GameCharacter.Shizuku:
                return (R.Live.ChallengeLive.CharaShizuku, R.Live.ChallengeLive.GroupMoreMoreJump)

            case GameCharacter.Kohane:
                return (R.Live.ChallengeLive.CharaKohane, R.Live.ChallengeLive.GroupVividBadSquad)
            case GameCharacter.An:
                return (R.Live.ChallengeLive.CharaAn, R.Live.ChallengeLive.GroupVividBadSquad)
            case GameCharacter.Akito:
                return (R.Live.ChallengeLive.CharaAkito, R.Live.ChallengeLive.GroupVividBadSquad)
            case GameCharacter.Toya:
                return (R.Live.ChallengeLive.CharaToya, R.Live.ChallengeLive.GroupVividBadSquad)

            case GameCharacter.Tsukasa:
                return (R.Live.ChallengeLive.CharaTsukasa, R.Live.ChallengeLive.GroupWonderlandsShowtime)
            case GameCharacter.Emu:
                return (R.Live.ChallengeLive.CharaEmu, R.Live.ChallengeLive.GroupWonderlandsShowtime)
            case GameCharacter.Nene:
                return (R.Live.ChallengeLive.CharaNene, R.Live.ChallengeLive.GroupWonderlandsShowtime)
            case GameCharacter.Rui:
                return (R.Live.ChallengeLive.CharaRui, R.Live.ChallengeLive.GroupWonderlandsShowtime)

            case GameCharacter.Kanade:
                return (R.Live.ChallengeLive.CharaKanade, R.Live.ChallengeLive.Group25AtNightcord)
            case GameCharacter.Mafuyu:
                return (R.Live.ChallengeLive.CharaMafuyu, R.Live.ChallengeLive.Group25AtNightcord)
            case GameCharacter.Ena:
                return (R.Live.ChallengeLive.CharaEna, R.Live.ChallengeLive.Group25AtNightcord)
            case GameCharacter.Mizuki:
                return (R.Live.ChallengeLive.CharaMizuki, R.Live.ChallengeLive.Group25AtNightcord)
            case _ as impossible:
                assert_never(impossible)

    def award_to_res(award: ChallengeLiveAward):
        match award:
            case ChallengeLiveAward.Crystal:
                return R.Live.ChallengeLive.Award.Crystal
            case ChallengeLiveAward.MusicCard:
                return R.Live.ChallengeLive.Award.MusicCard
            case ChallengeLiveAward.MiracleGem:
                return R.Live.ChallengeLive.Award.MiracleGem
            case ChallengeLiveAward.MagicCloth:
                return R.Live.ChallengeLive.Award.MagicCloth
            case ChallengeLiveAward.Coin:
                return R.Live.ChallengeLive.Award.Coin
            case ChallengeLiveAward.IntermediatePracticeScore:
                return R.Live.ChallengeLive.Award.IntermediatePracticeScore
            case _ as impossible:
                assert_never(impossible)

    char_img, group_img = char_to_res(character)
    for _ in Loop(interval=0.6):
        if group_img and image.find(group_img):
            device.click()
            logger.debug('Clicked group for character.')
        elif image.find(char_img):
            device.click()
            logger.debug('Clicked character.')
        elif at_song_select():
            logger.debug('Now at song select.')
            break
    enter_unit_select()
    # 处理奖励
    def claim_reward():
        # 选择奖励
        if image.find(R.Live.ChallengeLive.TextWeeklyAward):
            if image.find(award_to_res(conf().challenge_live.award)):
                device.click()
                logger.debug('Clicked award.')
                sleep(0.3)
                return True, False
        # 确认领取提示
        elif image.find(R.Live.ChallengeLive.TextAwardClaimConfirm):
            if image.find(R.Live.ChallengeLive.ButtonConfirm):
                device.click()
                logger.debug('Clicked confirm award claim.')
                sleep(0.3)
                return True, False
        return False, False
    start_auto_live('once', finish_pre_check=claim_reward)