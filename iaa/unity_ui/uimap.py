"""R.* → Unity UI 节点映射表。

把 ``iaa/tasks/R.py`` 中原本靠模板匹配的 prefab 逐个映射到 UI 树定位条件。
:meth:`install` 后，已映射的名字走 UI 树，未映射的继续走模板匹配（渐进迁移）。

映射规范：
- ``path_re`` 用 ``$`` 锚定结尾，锚到稳定祖先（如 ``/MainMenu/Base/``），
  避免 ``(Clone)`` / 重建实例带来的路径抖动
- 名字全局唯一的节点才允许只用 ``name``
- 可点击元素配 ``interactable=True`` 以跳过隐藏/禁用态
"""
from __future__ import annotations

from typing import Any

from .prefab import UIPrefab


def make_prefab(cls_name: str, spec: dict[str, Any]) -> type[UIPrefab]:
    """由映射条目动态生成 UIPrefab 子类。

    :param cls_name: 类名（用于日志/异常信息）
    :param spec: 定位条件（``path``/``path_re``/``name``/``text``/``interactable``）
    :return: UIPrefab 子类
    """
    attrs: dict[str, Any] = {'display_name': cls_name}
    for k, v in spec.items():
        attrs[f'ui_{k}'] = v
    return type(cls_name, (UIPrefab,), attrs)


#: R 路径（如 ``Hud.ButtonLive``）→ 定位条件
MAP: dict[str, dict[str, Any]] = {
    # ---- 首页 HUD（底栏菜单，ScreenLayerHome）----
    'Hud.ButtonLive': dict(path_re=r'/ScreenLayerHome/ComponentRoot/BottomRight/MainMenu/Base/Live$'),
    'Hud.ButtonMySekai': dict(path_re=r'/ScreenLayerHome/ComponentRoot/BottomRight/MainMenu/Base/Mysekai$'),
    'Hud.ButtonStory': dict(path_re=r'/ScreenLayerHome/ComponentRoot/BottomRight/MainMenu/Base/Story$'),
    'Hud.ButtonGacha': dict(path_re=r'/ScreenLayerHome/ComponentRoot/BottomRight/MainMenu/Base/Gacha$'),
    'Hud.ButtonMember': dict(path_re=r'/ScreenLayerHome/ComponentRoot/BottomRight/MainMenu/Base/Member$'),
    # ---- 一括受取按钮（礼物页/任务页 footer）----
    'Hud.ButtonClaimAll': dict(path_re=r'/(ScreenLayerPresent|ScreenLayerMission)/.*(Fotters|ListViewRoot)/UIPartsCommonButton$'),
    # ---- LIVE 选歌决定按钮（3D 手机 UI 主按钮，各 live 模式同构）----
    'Live.ButtonDecide': dict(path_re=r'/MainButtonContent/PositiveButton$'),
    # ---- 启动时的新闻弹窗（お知らせ）关闭按钮 ----
    'Login.IconNotification': dict(path_re=r'/NewsDialog\(Clone\)/.*/UIPartsCloseButton$'),
    # ---- 通用返回按钮（各页面 Layer_Header 左上角）----
    # 剧情播放期间底层 layer 仍 active，需否定 ScreenLayerScenario 保持
    # "被覆盖即不可见"语义（否则 skip_stories 结束条件会假阳性）
    'Hud.ButtonGoBack': dict(path_re=r'/UIPartsBackButton$', not_exists_re=r'/ScreenLayerScenario/'),
    # ---- 首页右上角入口（TopRight）----
    'Daily.ButtonGift': dict(path_re=r'/ScreenLayerHome/ComponentRoot/TopRight/Present$'),
    'Daily.ButtonMission': dict(path_re=r'/ScreenLayerHome/ComponentRoot/TopRight/Mission$'),
    # ---- 剧情分类页（ScreenLayerStoryCategorySelect）----
    # メイン/イベントストーリー 横幅入口
    'Story.ImageMainStory': dict(path_re=r'/ScreenLayerStoryCategorySelect/ComponentRoot/MainAndEventStory$'),
    # ---- 剧情列表页（ScreenLayerArchiveEventSelect）----
    'Story.StoryList.ButtonFilter': dict(path_re=r'/ScreenLayerArchiveEventSelect/ComponentRoot/ContentArea/RightTop/UIPartsFilterButton$'),
    # 決定按钮（选中章节后进入分集列表）
    'Story.StoryList.ButtonEnter': dict(path_re=r'/ScreenLayerArchiveEventSelect/ComponentRoot/ContentArea/RightBottom/ReadButton$'),
    # 左侧「ユニット すべて」展开 tab
    'Story.StoryList.ButtonExpandUnit': dict(path_re=r'/UnitLogoTabSubWindowDialog\(Clone\)/UnitLogoTabSubWindowDialog/Window/ContentRoot/Info$'),
    # ---- 分集列表页（ScreenLayerStorySelect）----
    'Story.ButtonBookmark': dict(path_re=r'/ScreenLayerStorySelect/ComponentRoot/Front/Top/UIPartsBookMarkButton$',
                                 not_exists_re=r'/ScreenLayerScenario/'),
    'Story.ButtonGoBack': dict(path_re=r'/UIPartsBackButton$', not_exists_re=r'/ScreenLayerScenario/'),
    # ---- 剧情播放（ScreenLayerScenario）----
    # 右上「…」菜单按钮：剧情画面标志物；菜单隐藏时 ScenarioMenu 内按钮
    # 依旧可点（CanvasGroup alpha=0 但 raycast 生效，实测 Skip 直点可弹确认）
    'Story.ButtonStoryMenu': dict(path_re=r'/ScreenLayerScenario/ComponentRoot/UILayer/RightTop/UIPartsMenuButton$'),
    'Story.ButtonIconSkip': dict(path_re=r'/ScenarioMenu/Base/Content/Skip$'),
    'Story.ButtonIconFastforward': dict(path_re=r'/ScenarioMenu/Base/Content/Fast$'),
    # 剧情开始确认弹窗（StoryReadConfirmDialog）：无语音播放按钮。
    # 按钮为同名 UIPartsCommonButton+序号后缀，按子孙文本区分。
    'Story.ButtonWithoutVoice': dict(path_re=r'/StoryReadConfirmDialog\(Clone\)/WindowRoot/FooterButtons/UIPartsCommonButton( \(1\))?$', has_text_re=r'ボイスなし'),
    # 跳过确认弹窗（ScenarioAllSkipConfirmDialog）的 スキップ 按钮
    'Story.ButtonSkipStory': dict(path_re=r'/ScenarioAllSkipConfirmDialog\(Clone\)/WindowRoot/FooterButtons/UIPartsCommonButton$', has_text=r'スキップ'),
    # MV 暂停弹窗（MusicVideoPoseDialog，游戏内拼写如此）——主线剧情 MV 暂停后跳过
    'Story.TextMvPausedDialog': dict(name='MessageBody', path_re=r'/MusicVideoPoseDialog\(Clone\)/'),
    'Story.ButtonSkipMv': dict(path_re=r'/MusicVideoPoseDialog\(Clone\)/WindowRoot/FooterButtons/UIPartsCommonButton$', has_text=r'スキップ'),
    # ---- 网络错误弹窗（Common1/2ButtonDialog，globals.handle_network_error）----
    # 「タイトルへ戻ります」1 按钮弹窗
    'NetworkError.DialogReturningToTitle.Text': dict(name='MessageBody', path_re=r'/Common1ButtonDialog\(Clone\)/'),
    'NetworkError.DialogReturningToTitle.ButtonOk': dict(path_re=r'/Common1ButtonDialog\(Clone\)/WindowRoot/FooterButtons/UIPartsCommonButton$', interactable=True),
    # 「通信エラー」重试弹窗（Common2ButtonDialog；结构按 1 按钮版类比，未实测）
    'NetworkError.DialogConnectionError.Text': dict(name='MessageBody', path_re=r'/Common2ButtonDialog\(Clone\)/'),
    'NetworkError.DialogConnectionError.ButtonRetry': dict(path_re=r'/Common2ButtonDialog\(Clone\)/WindowRoot/FooterButtons/UIPartsCommonButton$', has_text_re=r'リトライ'),
    # ---- LIVE 详情确认页（ScreenLayerFreeLiveFinalConfirmation，各 live 模式同构）----
    # 头部 LiveBoost 设置按钮（打开 AP 倍率弹窗）
    'Live.ButtonApMultiplierSettings': dict(path_re=r'/ScreenLayerHeader/ComponentRoot/MenuLayout/PlayerInfo/LiveBoost/UIPartsSettingButton$'),
    # AP 倍率弹窗（BoostRecoveryDialog，含 ライブボーナス消費 内容）
    'Live.ApMultiplierDialog.TextTip': dict(path_re=r'/BoostRecoveryDialog\(Clone\)$'),
    'Live.ApMultiplierDialog.ButtonPlus': dict(path_re=r'/BoostRecoveryDialog\(Clone\)/.*UIPartsIncrementButton$'),
    'Live.ApMultiplierDialog.ButtonMinus': dict(path_re=r'/BoostRecoveryDialog\(Clone\)/.*UIPartsDecrementButton$'),
    'Live.ApMultiplierDialog.ButtonConfirm': dict(path_re=r'/BoostRecoveryDialog\(Clone\)/WindowRoot/FooterButtons/UIPartsCommonButton$', has_text=r'決定'),
    # 当前倍率数字（NumText，如 '0'）——替代 BoxApNumber+OCR（新增叶子名）
    'Live.ApMultiplierDialog.TextApNumber': dict(path_re=r'/BoostRecoveryDialog\(Clone\)/.*NumText$'),
    # 自動編成弹窗（RecommendedDeckOrganizationDialog）
    'Live.ButtonSetRecommendUnit': dict(path_re=r'/ScreenLayerFreeLiveFinalConfirmation/ComponentRoot/ContentArea/DeckListView/DeckView/AutoEditButton$'),
    'Live.AutoSetDialog.TextUnitRecommend': dict(path_re=r'/RecommendedDeckOrganizationDialog\(Clone\)$'),
    'Live.AutoSetDialog.TextRecommend': dict(path_re=r'/RecommendedDeckOrganizationDialog\(Clone\)/.*UIPartsGroupFiterUnitRadio/Recommend$'),
    'Live.AutoSetDialog.TextEventMember': dict(path_re=r'/RecommendedDeckOrganizationDialog\(Clone\)/.*UIPartsGroupFiterUnitRadio/[^/]+$', has_text_re=r'イベント'),
    'Live.AutoSetDialog.ButtonConfirm': dict(path_re=r'/RecommendedDeckOrganizationDialog\(Clone\)/WindowRoot/FooterButtons/UIPartsCommonButton$', has_text=r'決定'),
    # 开始演出（3D 手机 UI 的 PlayButton）
    'Live.ButtonStartLive': dict(path_re=r'/SoloLiveFinalConfirmButton/PlayButton$'),
    # AUTO 演出开关（UIPartsToggle 的 Off/On 子节点存在性即状态；仅激活节点被 dump）
    'Live.SwitchAutoLiveOn': dict(path_re=r'/AutoLiveToggle/ToggleRoot/UIPartsToggle/On$'),
    'Live.SwitchAutoLiveOff': dict(path_re=r'/AutoLiveToggle/ToggleRoot/UIPartsToggle/Off$'),
    'Live.ButtonAutoLiveSettings': dict(path_re=r'/AutoLiveToggle/ConsecutiveAutoLiveRoot/ConsecutiveAutoLiveSetting/Button$'),
    # ---- 活动商店（ScreenLayerEventExchange）----
    # 「2026/11/18 20:59まで」结束时间文本：位于活动商店的标志
    'Shop.TextEndTimeUntil': dict(name='EndAtText'),
}


def install(r_module: object) -> int:
    """把映射表安装到 R 模块：已映射的名字替换为 UIPrefab 子类。

    允许叶子名在 R 中不存在（如替代 OCR 的 ``TextApNumber``）——此时在
    父级上新建属性；中间层级仍必须存在，防映射名拼错。

    :param r_module: ``iaa.tasks.R`` 模块对象
    :return: 安装的映射数
    :raises AttributeError: 映射的中间层级不存在时（映射名拼错）
    """
    n = 0
    for dotted, spec in MAP.items():
        parts = dotted.split('.')
        parent = r_module
        for p in parts[:-1]:
            parent = getattr(parent, p)
        cls = make_prefab(parts[-1], spec)
        setattr(parent, parts[-1], cls)
        n += 1
    return n
