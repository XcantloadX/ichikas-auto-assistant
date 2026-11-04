
from kotonebot import task, logging, Loop, device, sleep

from . import R
from iaa.definitions.enums import ShopItem
from iaa.context import conf as get_conf, task_reporter, server
from iaa.i18n import TStr, tstr
from iaa.game_ui.side_tabbar import SideTabbar

logger = logging.getLogger(__name__)

def _ui_read_cells() -> list[dict]:
    """从 UI 树读取当前可见的商品 cell（文本身份）。

    EventExchangeCell 含 ItemName（商品名 TMP 文本）、Num（价格）、
    Remaining（剩余次数），可整体替代图标模板匹配。角色卡（ItemName 为
    角色名，不在 :class:`ShopItem` 名表内）按价格判星（15000=★3、5000=★2，
    与旧 Icon5000/15000EventCoin 图标逻辑等价）。

    :return: ``[{'name': 商品名, 'price': 价格文本, 'rem': 剩余次数文本,
        'center': (x, y) 屏幕坐标}, ...]``；UI 树不可用时返回空列表
    """
    import re as _re

    from iaa.unity_ui.prefab import get_default_client
    from iaa.unity_ui.tree import flat_nodes

    try:
        roots = get_default_client().snapshot()
    except Exception:  # noqa: BLE001 基础设施故障降级为"未找到"
        return []
    cells: list[dict] = []
    for n in flat_nodes(roots):
        if n.name != 'EventExchangeCell(Clone)' or n.screen_rect is None:
            continue
        info: dict = {'name': None, 'price': None, 'rem': None, 'center': None}
        stack = [n]
        while stack:
            x = stack.pop()
            t = x.text
            if x.name == 'ItemName' and t:
                info['name'] = t
            elif x.name == 'Remaining' and t:
                info['rem'] = _re.sub(r'<[^>]+>', '', t)
            elif x.name == 'Num' and t and not t.startswith('×') and info['price'] is None:
                info['price'] = t
            stack.extend(x.children)
        if info['name']:
            info['center'] = (int(n.screen_rect[0]), int(n.screen_rect[1]))
            cells.append(info)
    return cells


_JP_ITEM_NAMES: dict[str, ShopItem] | None = None


def _match_item_ui(cell: dict) -> ShopItem | None:
    """按 ItemName 文本匹配 :class:`ShopItem`（UI 树路径，替代图标模板）。

    :param cell: :func:`_ui_read_cells` 的条目
    :return: 匹配的商品；无法识别返回 None
    """
    global _JP_ITEM_NAMES
    if _JP_ITEM_NAMES is None:
        _JP_ITEM_NAMES = {i.display('jp'): i for i in ShopItem}
    name = cell['name'] or ''
    # ボーカルカード交換チケット 类商品名带单位前缀（'25時、…\nボーカルカード交換チケット'）
    for jp, item in _JP_ITEM_NAMES.items():
        if name == jp or name.endswith(jp):
            return item
    # 角色卡：名称不在名表内，按价格判星
    if cell.get('price') == '15000':
        return ShopItem.ITEM_3STAR_MEMBER
    if cell.get('price') == '5000':
        return ShopItem.ITEM_2STAR_MEMBER
    return None

def goto_event_shop() -> None:
    """导航到活动商店界面
    
    前置：无\n
    结束：成功进入活动商店界面
    """
    for _ in Loop(interval=1):
        if R.Shop.TextEndTimeUntil.exists():
            logger.info("Now at event shop")
            return
        elif R.Shop.ButtonExchange.try_click():
            logger.debug("Clicked on Exchange button")
        elif R.Shop.ButtonEventExchange.try_click():
            logger.debug("Clicked on Event Exchange button")
        elif R.Login.ButtonMenu.try_click():
            logger.debug("Clicked on Menu button")

def _purchase(center: tuple[int, int]) -> bool:
    """购买一个商品（UI 树 cell 中心点击打开数量弹窗，弹窗内走模板 fallback）。

    :param center: 商品 cell 中心屏幕坐标
    :return: 是否购买成功（跳过/失败返回 False）
    """
    # 首先打开购买对话框
    for _ in Loop():
        if R.Shop.AmountDialog.ButtonConfirm.exists():
            logger.info("Purchase dialog opened")
            break
        else:
            device.click(center)
            sleep(0.5)
    
    # 调整大小
    plus_btn = R.Shop.AmountDialog.ButtonPlus.find()
    if plus_btn is None and R.Shop.AmountDialog.ButtonConfirm.exists():
        # 说明是卡片，不需要调整数量
        pass
    else:
        # 否则调整到最大
        assert plus_btn is not None
        for _ in Loop(interval=0.5):
            if R.Shop.AmountDialog.ButtonPlus.q(enabled=True).find():
                logger.debug("Purchase amount +10")
                for _ in range(10):
                    plus_btn.click()
                    sleep(0.2)
            else:
                logger.info("Purchase amount maximized")
                break
        
    # 确认购买
    # R.Shop.AmountDialog.ButtonCancel.click()
    # sleep(1)
    btn = R.Shop.AmountDialog.ButtonConfirm.wait()
    if not btn.enabled:
        if not btn.enabled:
            logger.info("Event coin not enough for purchasing. Skipping...")
            R.Shop.AmountDialog.ButtonCancel.click()
            sleep(0.5)
            return False
        logger.info("Event coin not enough for purchasing. Skipping...")
        return False
    for _ in Loop():
        if btn := R.Shop.AmountDialog.ButtonConfirm.find():
            btn.click()
            logger.info("Clicked confirm button")
            sleep(1)
        elif R.Shop.TextExchangeDone.try_click():
            sleep(0.5)
            logger.info("Purchase successful")
            return True

def _do_single() -> None:
    rep = task_reporter()
    targets = list(get_conf().tasks.event_shop.purchase_items)

    view = R.Shop.EventShopListView.require()
    assert view.scrollable is not None
    view.scrollable.measure_bounds()

    # UI 树全量扫描：按文本匹配商品（替代图标模板）
    rep.message(TStr(zh_CN='扫描列表', en_US='Scanning list'))
    view.scrollable.to_top()
    available_targets: set[ShopItem] = set()
    cell_center: dict[ShopItem, tuple[int, int]] = {}
    for _progress in view.scrollable.walk_down(step=0.8):
        for cell in _ui_read_cells():
            matched = _match_item_ui(cell)
            if matched is None:
                logger.debug("UI cell %r does not match any target", cell['name'])
                continue
            logger.debug("Matched cell %s", matched.display(server()))
            available_targets.add(matched)
            cell_center[matched] = cell['center']

    purchasable_targets = [target for target in targets if target in available_targets]

    for target in targets:
        if target not in available_targets:
            logger.info("Target item %s not found in event shop. Skipping.", target.display(server()))

    if not purchasable_targets:
        logger.info("No configured target items found in event shop.")
        return

    with rep.phase(tstr('progress.phase.event'), total=len(purchasable_targets)) as phase:
        for target in purchasable_targets:
            phase.step(target.display(server()))
            # 购买后商品列表会变化且界面回顶，每轮重新滚动查找该商品
            view.scrollable.to_top()
            found: tuple[int, int] | None = None
            for _progress in view.scrollable.walk_down(step=0.8):
                for cell in _ui_read_cells():
                    if _match_item_ui(cell) == target:
                        found = cell['center']
                        break
                if found is not None:
                    break

            if found is None:
                logger.info("Target item %s disappeared after repurchase. Skipping.", target.display(server()))
                continue

            logger.info("Found target item %s", target.display(server()))
            if _purchase(found):
                # 购买后商品列表会变化，并且界面会自动回顶；
                # 与旧实现语义一致：每个目标每轮只购买一次，进入下一目标。
                view.scrollable.to_top()
                continue

            logger.info("Skipping target item %s because it cannot be purchased now", target.display(server()))

@task('活动商店', screenshot_mode='manual')
def event_shop():
    goto_event_shop()

    rep = task_reporter()
    sidebar = SideTabbar()
    tabs = sidebar.update().tabs
    if len(tabs) == 0:
        logger.warning("No tabs found in sidebar. Continuing without switching tabs.")
        
    with rep.phase(tstr('progress.phase.event'), total=len(tabs)):
        for tab in tabs:
            sidebar.switch_to(tab)
            _do_single()