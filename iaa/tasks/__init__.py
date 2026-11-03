"""任务包。

导入即把 :mod:`iaa.unity_ui.uimap` 中已映射的 prefab 安装到 R 模块
（UI 树驱动），未映射的名字继续走模板匹配。
设环境变量 ``IAA_UI_TREE=0`` 可整体禁用（回退全模板匹配）。
"""
from __future__ import annotations

import os

from . import R

if os.environ.get('IAA_UI_TREE', '1') != '0':
    from ..unity_ui import uimap

    uimap.install(R)
