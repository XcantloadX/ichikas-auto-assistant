from typing import Callable, Literal, TypeVar
from typing_extensions import assert_never
from pydantic import BaseModel, ConfigDict

from kotonebot import logging
from kotonebot.core import AnyOf, Prefab
from kotonebot import device, Loop, action, sleep, color, ocr

from .. import R
from ..common import at_home, go_home
from iaa.context import conf, server, task_reporter, keyboard
from ._select_song import next_song
from ._scene import at_song_select
from .auto_live_core import RhythmGameAnalyzer
from iaa.config.schemas import ChallengeLiveAward, GameCharacter

logger = logging.getLogger(__name__)
LiveMode = Literal['all'] | Literal['once'] | Literal['script'] | int | None
SoloPlayMode = Literal['game_auto', 'script_auto']
SongChoiceMode = Literal['current', 'specified', 'random']
LoopSongMode = Literal['list_next', 'random']
PrefabClass = TypeVar('PrefabClass', bound=Prefab)
ChallengeCharacterPrefab = tuple[PrefabClass, PrefabClass | None]


class LivePlan(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    play_mode: SoloPlayMode = 'game_auto'
    debug_enabled: bool = False
    ap_multiplier: int | None = None
    auto_set_unit: bool = False


class OncePlan(LivePlan):
    song_select_mode: SongChoiceMode = 'current'
    song_name: str | None = None


class SingleLoopPlan(LivePlan):
    loop_count: int | None = None
    song_select_mode: SongChoiceMode = 'current'
    song_name: str | None = None


class ListLoopPlan(LivePlan):
    loop_count: int | None = None
    loop_song_mode: LoopSongMode = 'list_next'


CHARACTER_PREFABS: dict[GameCharacter, ChallengeCharacterPrefab] = {
    GameCharacter.Miku: (R.Live.ChallengeLive.CharaMiku, R.Live.ChallengeLive.GroupVirtualSinger),
    GameCharacter.Rin: (R.Live.ChallengeLive.CharaRin, R.Live.ChallengeLive.GroupVirtualSinger),
    GameCharacter.Len: (R.Live.ChallengeLive.CharaLen, R.Live.ChallengeLive.GroupVirtualSinger),
    GameCharacter.Luka: (R.Live.ChallengeLive.CharaLuka, R.Live.ChallengeLive.GroupVirtualSinger),
    GameCharacter.Meiko: (R.Live.ChallengeLive.CharaMeiko, R.Live.ChallengeLive.GroupVirtualSinger),
    GameCharacter.Kaito: (R.Live.ChallengeLive.CharaKaito, R.Live.ChallengeLive.GroupVirtualSinger),
    GameCharacter.Ichika: (R.Live.ChallengeLive.CharaIchika, R.Live.ChallengeLive.GroupLeoneed),
    GameCharacter.Saki: (R.Live.ChallengeLive.CharaSaki, R.Live.ChallengeLive.GroupLeoneed),
    GameCharacter.Honami: (R.Live.ChallengeLive.CharaHonami, R.Live.ChallengeLive.GroupLeoneed),
    GameCharacter.Shiho: (R.Live.ChallengeLive.CharaShiho, R.Live.ChallengeLive.GroupLeoneed),
    GameCharacter.Minori: (R.Live.ChallengeLive.CharaMinori, R.Live.ChallengeLive.GroupMoreMoreJump),
    GameCharacter.Haruka: (R.Live.ChallengeLive.CharaHaruka, R.Live.ChallengeLive.GroupMoreMoreJump),
    GameCharacter.Airi: (R.Live.ChallengeLive.CharaAiri, R.Live.ChallengeLive.GroupMoreMoreJump),
    GameCharacter.Shizuku: (R.Live.ChallengeLive.CharaShizuku, R.Live.ChallengeLive.GroupMoreMoreJump),
    GameCharacter.Kohane: (R.Live.ChallengeLive.CharaKohane, R.Live.ChallengeLive.GroupVividBadSquad),
    GameCharacter.An: (R.Live.ChallengeLive.CharaAn, R.Live.ChallengeLive.GroupVividBadSquad),
    GameCharacter.Akito: (R.Live.ChallengeLive.CharaAkito, R.Live.ChallengeLive.GroupVividBadSquad),
    GameCharacter.Toya: (R.Live.ChallengeLive.CharaToya, R.Live.ChallengeLive.GroupVividBadSquad),
    GameCharacter.Tsukasa: (R.Live.ChallengeLive.CharaTsukasa, R.Live.ChallengeLive.GroupWonderlandsShowtime),
    GameCharacter.Emu: (R.Live.ChallengeLive.CharaEmu, R.Live.ChallengeLive.GroupWonderlandsShowtime),
    GameCharacter.Nene: (R.Live.ChallengeLive.CharaNene, R.Live.ChallengeLive.GroupWonderlandsShowtime),
    GameCharacter.Rui: (R.Live.ChallengeLive.CharaRui, R.Live.ChallengeLive.GroupWonderlandsShowtime),
    GameCharacter.Kanade: (R.Live.ChallengeLive.CharaKanade, R.Live.ChallengeLive.Group25AtNightcord),
    GameCharacter.Mafuyu: (R.Live.ChallengeLive.CharaMafuyu, R.Live.ChallengeLive.Group25AtNightcord),
    GameCharacter.Ena: (R.Live.ChallengeLive.CharaEna, R.Live.ChallengeLive.Group25AtNightcord),
    GameCharacter.Mizuki: (R.Live.ChallengeLive.CharaMizuki, R.Live.ChallengeLive.Group25AtNightcord),
}

CHALLENGE_AWARD_PREFABS: dict[ChallengeLiveAward, PrefabClass] = {
    ChallengeLiveAward.Crystal: R.Live.ChallengeLive.Award.Crystal,
    ChallengeLiveAward.MusicCard: R.Live.ChallengeLive.Award.MusicCard,
    ChallengeLiveAward.MiracleGem: R.Live.ChallengeLive.Award.MiracleGem,
    ChallengeLiveAward.MagicCloth: R.Live.ChallengeLive.Award.MagicCloth,
    ChallengeLiveAward.Coin: R.Live.ChallengeLive.Award.Coin,
    ChallengeLiveAward.IntermediatePracticeScore: R.Live.ChallengeLive.Award.IntermediatePracticeScore,
}

def _skip():
    if server() == 'jp':
        device.click(1, 1)
    elif server() == 'tw' or server() == 'cn':
        # 台服要点侧边，点左上角没用
        device.click(6, 346)
    else:
        raise NotImplementedError(f'Unsupported server: {server()}')


def select_song(song_name: str):
    kbd = keyboard()
    for _ in Loop():
        if kbd.can_input():
            sleep(0.5)
            break
        elif R.Live.SongSelect.IconSearch.try_click():
            sleep(0.5)
        elif R.Live.SongSelect.ButtonClearSearch.try_click():
            sleep(0.5)
    with kbd:
        kbd.send(song_name)
        sleep(0.2)
        kbd.enter()
    sleep(0.5)

def _configure_ap_multiplier(ap_multiplier: int) -> None:
    rep = task_reporter()
    logger.info(f'Setting AP multiplier to {ap_multiplier}.')
    rep.message('设置 AP 倍率')
    # 打开 AP 倍率设置
    for _ in Loop():
        if R.Live.ApMultiplierDialog.TextTip.find():
            logger.debug('AP multiplier dialog opened.')
            sleep(1)
            break
        elif R.Live.ButtonApMultiplierSettings.try_click():
            logger.debug('Clicked AP multiplier settings button.')
    # 执行
    retry_count = 0
    def _set(ap_multiplier: int) -> bool:
        # 设置 AP 倍率
        current_multiplier = ocr.ocr(R.Live.ApMultiplierDialog.BoxApNumber).squash().numbers()
        if not current_multiplier:
            raise RuntimeError('Failed to read current AP multiplier.')
        current_multiplier = int(current_multiplier[0])
        logger.debug(f'Current AP multiplier: {current_multiplier}, target: {ap_multiplier}')
        # 计算点击方向与次数
        if current_multiplier < ap_multiplier:
            button = R.Live.ApMultiplierDialog.PointPlus
            times = ap_multiplier - current_multiplier
        elif current_multiplier > ap_multiplier:
            button = R.Live.ApMultiplierDialog.PointMinus
            times = current_multiplier - ap_multiplier
        else:
            logger.debug('Current AP multiplier already at target.')
            return True
        # 执行
        for i in range(times):
            device.click(button)
            logger.debug(
                f'Clicked AP multiplier {"plus" if button == R.Live.ApMultiplierDialog.PointPlus else "minus"} button. ({i + 1}/{times})'
            )
            sleep(0.3)
        return False
    while True:
        device.screenshot()
        try:
            if _set(ap_multiplier):
                break
        except Exception:
            logger.exception('Error setting AP multiplier')
        sleep(0.5)
        retry_count += 1
        if retry_count >= 5:
            raise RuntimeError('Failed to set AP multiplier after 5 attempts.')
    # 然后关闭弹窗
    R.Live.ApMultiplierDialog.ButtonConfirm.wait().click()
    sleep(0.5)


def _configure_auto_live(live_mode: LiveMode) -> bool:
    rep = task_reporter()
    check = AnyOf[
        R.Live.SwitchAutoLiveOff,
        R.Live.SwitchAutoLiveOn
    ].wait()

    def _turn_off_auto():
        if check.prefab == R.Live.SwitchAutoLiveOn:
            check.click()
            logger.debug('Clicked auto live switch to turn off.')
            sleep(0.3)

    # 设置自动演出设置
    # 消耗全部 AP
    if live_mode == 'all':
        chose = False
        # 要先关掉自动，然后再走打开的逻辑
        _turn_off_auto()
        for _ in Loop(interval=0.6):
            if R.Live.SwitchAutoLiveOn.find():
                logger.debug('Auto live switch checked on.')
                break
            elif R.Live.TextAtLeastOneAp.find():
                logger.info('No AP left to enable auto live. Exiting.')
                rep.message('AP 不足，正在退出')
                return False
            elif R.Live.ButtonAutoLiveSettings.try_click():
                logger.debug('Clicked auto live settings button.')
            elif not chose and R.Live.TextAutoLiveUntilInsufficient.find():
                device.click()
                logger.debug('Chose auto live until insufficient AP.')
                sleep(0.3)
                chose = True
            elif R.Live.ButtonDecideAutoLive.try_click():
                logger.debug('Clicked decide auto live button.')
                sleep(0.3)
        return True
    # 进行一次 AUTO
    elif live_mode == 'once':
        for _ in Loop(interval=0.6):
            if R.Live.SwitchAutoLiveOn.find():
                logger.debug('Auto live switch checked on.')
                break
            elif R.Live.TextAtLeastOneAp.find():
                logger.info('No AP left to enable auto live. Exiting.')
                return False
            elif R.Live.SwitchAutoLiveOff.try_click():
                logger.debug('Clicked auto live switch.')
                sleep(0.3)
        return True
    # 脚本自动演出
    elif live_mode == 'script':
        # 先关掉游戏 AUTO
        _turn_off_auto()
    return True


def _configure_unit() -> None:
    rep = task_reporter()
    logger.info('Auto setting unit.')
    rep.message('自动编队中')
    # 首先打开自动编队
    for _ in Loop():
        if R.Live.AutoSetDialog.TextUnitRecommend.find():
            logger.debug('Auto set unit dialog opened.')
            sleep(0.3)
            break
        elif R.Live.ButtonSetRecommendUnit.try_click():
            logger.debug('Clicked auto set unit button.')
    # 然后编队
    R.Live.AutoSetDialog.TextRecommend.wait().click()
    sleep(0.3)
    logger.debug('Clicking イベントメンバー button.')
    for _ in Loop():
        btn = (
            R.Live.AutoSetDialog.TextEventMember.find() or
            R.Live.AutoSetDialog.TextUnitRecommend.find()
        )
        if btn:
            btn.click()
            break
    sleep(0.3)
    logger.debug('Clicked あすすめ button.')
    R.Live.AutoSetDialog.ButtonConfirm.wait().click()
    sleep(0.3)
    logger.debug('Closed auto set unit dialog.')


def _run_live(live_mode: LiveMode, debug_enabled: bool) -> None:
    # 开始演出
    logger.debug('Clicking start live button.')
    R.Live.ButtonStartLive.wait().click()
    if live_mode == 'script':
        analyzer = RhythmGameAnalyzer(
            device,
            R.Live.TextLife.template.pixels,
            debug=debug_enabled,
            stop_check=R.Live.TextScoreRank.exists
        )
        analyzer.run()
    else:
        sleep(74.8 + 5)  # 孑然妒火（最短曲） + 5s 缓冲


def _wait_live_end(live_mode: LiveMode) -> None:
    rep = task_reporter()
    is_mutiple_auto = (live_mode == 'all' or isinstance(live_mode, int))
    for _ in Loop():
        # 结束条件
        if is_mutiple_auto:
            # 指定演出次数或直到 AP 不足
            # 结束条件是「已完成指定次数的演出」提示
            if R.Live.TextAutoLiveCompleted.exists():
                _skip()
                rep.message('AP 不足，正在退出')
                logger.info('Auto lives all completed.')
                sleep(0.3)
                break
        else:
            # 单次演出
            # 结束条件是「SCORERANK」提示
            if R.Live.TextScoreRank.exists():
                logger.debug('Waiting for SCORERANK')
                sleep(1) # 等待 SCORERANK 动画完成
                device.click_center()
                break


def _settle_to_home() -> bool:
    if at_home():
        return True
    # 台服要点 OK 才行
    if server() == 'tw' and R.Live.ButtonLiveCompletedOk.try_click():
        logger.debug('Clicked live completed ok button.')
    _skip()
    sleep(0.6)
    return False


def _settle_to_select() -> bool:
    # 返回选歌界面要点“返回歌曲选择”按钮
    if R.Live.ButtonLiveCompletedNext.try_click():
        logger.debug('Clicked live completed ok button.')
    elif R.Live.ButtonGoSongSelect.try_click():
        logger.debug('Clicked select song button.')
    elif at_song_select():
        logger.debug('Now at song select.')
        return True
    # 处理歌曲 RANK 奖励
    elif R.Live.TextScoreRankReward.exists():
        if R.Live.ButtonCloseScoreRankReward.try_click():
            logger.debug('Clicked claim score rank reward button.')
    # 处理 RANK UP 升级
    elif R.Live.TextLevelUpBouns.exists():
        _skip()
        logger.debug('Skip RANK UP bonus screen finished.')
    # RANK UP 升级后的奖励获得提示
    elif R.Cm.TextAwardClaimed.exists():
        _skip()
        logger.debug('Skip RANK UP bonus reward claimed screen finished.')
    else:
        logger.debug('Waiting for reward screen finished.')
    return False


def _finish_live(
    return_to: Literal['home'] | Literal['select'] | None,
    finish_pre_check: Callable[[], tuple[bool, bool]] | None,
) -> bool:
    rep = task_reporter()
    if return_to is None:
        return True
    # 返回
    rep.message('结算中')
    for _ in Loop(interval=0.5):
        if finish_pre_check:
            should_skip, should_break = finish_pre_check()
            if should_break:
                break
            if should_skip:
                continue
        # 返回主页只要一直点就可以了
        if return_to == 'home':
            if _settle_to_home():
                break
        elif return_to == 'select':
            if _settle_to_select():
                break
    return True


def _enter_song_select() -> None:
    reporter = task_reporter()
    reporter.message('进入单人演出')
    # 进入单人演出
    for _ in Loop(interval=0.6):
        if R.Hud.ButtonLive.q(threshold=0.55).find():
            device.click()
            logger.debug('Clicked home LIVE button.')
            sleep(1)
        elif R.Live.ButtonSoloLive.try_click():
            logger.debug('Clicked SoloLive button.')
        elif at_song_select():
            logger.debug('Now at song select.')
            break


def _prepare_solo_live(song_select_mode: SongChoiceMode | Literal['list_next'], song_name: str | None) -> None:
    _enter_song_select()
    if song_select_mode == 'specified':
        if not song_name:
            raise ValueError('song_name is required when song_select_mode is specified.')
        select_song(song_name)
    elif song_select_mode == 'random':
        # 点一下随机按钮
        R.Live.SongSelect.ButtonRandom.wait().click()
        sleep(1)
        # 然后等歌曲稳定
        R.Live.SongSelect.TextVo.wait()
    elif song_select_mode == 'list_next':
        next_song()
    enter_unit_select()


def _start_single_live_run(
    live_mode: LiveMode,
    auto_set_unit: bool,
    ap_multiplier: int | None,
    song_select_mode: SongChoiceMode,
    song_name: str | None,
    debug_enabled: bool = False,
) -> bool:
    _prepare_solo_live(song_select_mode, song_name)
    return start_auto_live(
        live_mode,
        return_to='home',
        debug_enabled=debug_enabled,
        auto_set_unit=auto_set_unit,
        ap_multiplier=ap_multiplier,
    )

@action('演出', screenshot_mode='manual')
def start_auto_live(
    live_mode: LiveMode = 'all',
    *,
    return_to: Literal['home'] | Literal['select'] | None = 'home',
    finish_pre_check: Callable[[], tuple[bool, bool]] | None = None,
    debug_enabled: bool = False,
    auto_set_unit: bool = False,
    ap_multiplier: int | None = None,
) -> bool:
    """
    前置：位于编队界面\n
    结束：首页、选歌界面或 LIVE CLEAR 画面

    :param live_mode: 自动演出设置。\n
        * `"all"`: 自动演出直到 AP 不足
        * 任意整数: 自动演出指定次数
        * `"once"`: 自动演出一次
        * `"script"`: 脚本自动演出一次
        * `None`: 不自动演出
    :param return_to: 返回位置。\n
        * `"home"`: 返回首页
        * `"select"`: 返回选歌界面（已弃用，仅保留兼容）
        * `None`: 不返回，直接在 LIVE CLEAR 或「已完成指定次数的演出」画面结束
    :param finish_pre_check:
        结束演出时的额外处理，在检查循环的开始处调用。返回 `(should_skip, should_break)`。
        * `should_skip`: 如果 True，则跳过当前循环。
        * `should_break`: 如果 True，则结束循环。
        如果 `should_skip` 为 True，则 `should_break` 会被忽略。
    :param debug_enabled: 是否启用调试模式，启用后会在自动演出时显示更多日志，并在脚本自动演出时显示节奏游戏分析器的调试信息。
    :param auto_set_unit: 是否在演出前自动编队
    :param ap_multiplier: AP 倍率，范围 [0, 10]。若为数字，表示演出前自动设置倍率为对应值；若为 None，表示保持现状。
    :raises NotImplementedError: 如果未实现的功能被调用。
    :return: 若为 False，表示因为 AP 不足没有进行演出。
    """
    if live_mode is None or isinstance(live_mode, int):
        raise NotImplementedError('Not implemented yet.')
    rep = task_reporter()
    rep.message('准备开始演出')
    if return_to == 'select':
        logger.warning(
            "return_to='select' is deprecated; prefer return_to='home' and re-enter song select manually."
        )
    # 等待编队界面
    AnyOf[
        R.Live.SwitchAutoLiveOff,
        R.Live.SwitchAutoLiveOn
    ].wait()
    # 设置 AP 倍率
    if ap_multiplier is not None:
        _configure_ap_multiplier(ap_multiplier)
    # 配置 AUTO 设置
    if not _configure_auto_live(live_mode):
        return False
    # 自动编队
    if auto_set_unit:
        _configure_unit()
    logger.info('Auto live setting finished.')
    # 演出
    rep.message('演出中')
    _run_live(live_mode, debug_enabled)
    _wait_live_end(live_mode)
    return _finish_live(return_to, finish_pre_check)

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
def solo_live(plan: OncePlan | SingleLoopPlan | ListLoopPlan):
    """
    :param plan: 单人演出执行计划。
    """
    if isinstance(plan, (SingleLoopPlan, ListLoopPlan)) and plan.loop_count is not None and plan.loop_count <= 0:
        raise ValueError('loop_count must be positive.')
    if plan.ap_multiplier is not None and not (0 <= plan.ap_multiplier <= 10):
        raise ValueError('ap_multiplier must be between 0 and 10.')
    if isinstance(plan, (OncePlan, SingleLoopPlan)) and plan.song_select_mode == 'specified' and not plan.song_name:
        raise ValueError('song_name is required when song_select_mode is specified.')
    reporter = task_reporter()
    auto_set_unit = plan.auto_set_unit
    count = 0
    if isinstance(plan, OncePlan):
        _prepare_solo_live(plan.song_select_mode, plan.song_name)
        start_auto_live('once', return_to='home', auto_set_unit=auto_set_unit, ap_multiplier=plan.ap_multiplier)
        return
    if isinstance(plan, SingleLoopPlan):
        # 单曲循环
        max_count = plan.loop_count or float('inf')
        # 游戏内 AUTO
        if plan.play_mode == 'game_auto':
            reporter.message('开始单曲循环（游戏自动）')
            _prepare_solo_live(plan.song_select_mode, plan.song_name)
            start_auto_live('all', return_to='home', auto_set_unit=auto_set_unit, ap_multiplier=plan.ap_multiplier)
            reporter.message('单曲循环完成，返回首页')
        # 脚本自动
        else:
            total = (int(max_count) if max_count != float('inf') else None)
            reporter.message('开始单曲循环（脚本自动）')
            with reporter.phase('单曲循环', total=total) as phase:
                while True:
                    if not _start_single_live_run(
                        'script',
                        auto_set_unit=auto_set_unit,
                        ap_multiplier=plan.ap_multiplier,
                        song_select_mode=plan.song_select_mode,
                        song_name=plan.song_name,
                        debug_enabled=plan.debug_enabled,
                    ):
                        break
                    count += 1
                    phase.step(f'已完成 {count} 次单曲循环')
                    if count >= max_count:
                        logger.info(f'Completed {count} loops.')
                        break
            reporter.message('单曲循环完成，返回首页')
        return
    if isinstance(plan, ListLoopPlan):
        # 列表循环
        max_count = plan.loop_count or float('inf')
        total = (int(max_count) if max_count != float('inf') else None)
        reporter.message('开始列表循环')
        with reporter.phase('列表循环', total=total) as phase:
            for _ in Loop():
                _prepare_solo_live(plan.loop_song_mode, None)
                start_auto_live(
                    'once' if plan.play_mode == 'game_auto' else 'script',
                    return_to='home',
                    debug_enabled=plan.debug_enabled,
                    auto_set_unit=auto_set_unit,
                    ap_multiplier=plan.ap_multiplier,
                )
                count += 1
                logger.info(f'Song looped. {count}/{max_count}')
                phase.step(f'已完成 {count} 次列表循环')
                if count >= max_count:
                    break
        reporter.message('列表循环完成')
        return
    assert_never(plan)

@action('挑战演出', screenshot_mode='manual')
def challenge_live(
    character: GameCharacter
):
    rep = task_reporter()
    rep.message('进入挑战演出')
    # 进入挑战演出
    for _ in Loop(interval=0.6):
        if R.Hud.ButtonLive.q(threshold=0.55).try_click():
            logger.debug('Clicked home LIVE button.')
            sleep(1)
        elif btn := R.Live.ButtonChallengeLive.find():
            if not color.find('#ff5589', rect=R.Live.BoxChallengeLiveRedDot):
                logger.info("Today's challenge live already cleared.")
                return
            device.click(btn)
            logger.debug('Clicked ChallengeLive button.')
        elif R.Live.ChallengeLive.TextSelectCharacter.find():
            logger.debug('Now at character select.')
            break
        elif R.Live.ChallengeLive.GroupVirtualSinger.try_click():
            # 为了防止误触某个角色，导致次数不够提示弹出来，挡住 TextSelectCharacter
            # 文本，结果一直卡在 TextSelectCharacter 识别上。
            # 加上这个点击用于取消次数不足提示。
            logger.debug('Clicked group virtual singer.')

    # 选择角色
    rep.message(f'选择角色：{character.value}')
    logger.info(f'Selecting character: {character.value}')
    char, group = CHARACTER_PREFABS[character]
    for _ in Loop(interval=0.6):
        if char.try_click():
            logger.debug('Clicked character.')
        elif group and group.try_click():
            logger.debug('Clicked group for character.')
        elif at_song_select():
            logger.debug('Now at song select.')
            break
    enter_unit_select()
    # 处理奖励
    def claim_reward():
        # 选择奖励
        if R.Live.ChallengeLive.TextWeeklyAward.find():
            if CHALLENGE_AWARD_PREFABS[conf().challenge_live.award].try_click():
                logger.debug('Clicked award.')
                sleep(0.3)
                return True, False
        # 确认领取提示
        elif R.Live.ChallengeLive.TextAwardClaimConfirm.find():
            if R.Live.ChallengeLive.ButtonConfirm.try_click():
                logger.debug('Clicked confirm award claim.')
                sleep(0.3)
                return True, False
        return False, False
    rep.message('开始挑战演出')
    start_auto_live('once', finish_pre_check=claim_reward, auto_set_unit=False, ap_multiplier=None)
    rep.message('挑战演出完成，返回首页')
    go_home()
