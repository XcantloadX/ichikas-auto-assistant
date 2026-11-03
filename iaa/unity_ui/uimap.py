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
    # ---- 启动时的新闻弹窗（お知らせ）关闭按钮 ----
    'Login.IconNotification': dict(path_re=r'/NewsDialog\(Clone\)/.*/UIPartsCloseButton$'),
    # ---- 通用返回按钮（各页面 Layer_Header 左上角）----
    'Hud.ButtonGoBack': dict(path_re=r'/UIPartsBackButton$'),
    # ---- 首页右上角入口（TopRight）----
    'Daily.ButtonGift': dict(path_re=r'/ScreenLayerHome/ComponentRoot/TopRight/Present$'),
    'Daily.ButtonMission': dict(path_re=r'/ScreenLayerHome/ComponentRoot/TopRight/Mission$'),
}


def install(r_module: object) -> int:
    """把映射表安装到 R 模块：已映射的名字替换为 UIPrefab 子类。

    :param r_module: ``iaa.tasks.R`` 模块对象
    :return: 安装的映射数
    :raises AttributeError: R 路径不存在时（映射名拼错）
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
