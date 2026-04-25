from __future__ import annotations

from ..dsl import Checkbox, FormPage, Group, PreferencesContext, Select, ref
from ..dsl.refs import of

CTX = of(PreferencesContext)


def build_preferences_form() -> tuple:
    with FormPage('设置') as page:
        with Group('数据收集'):
            Checkbox(
                key='telemetry.sentry',
                label='自动发送匿名错误报告',
                ref=ref(CTX.shared.telemetry.sentry),
            )

        with Group('界面'):
            Select(
                key='interface.window_style',
                label='窗口背景样式',
                ref=ref(CTX.shared.interface.window_style),
                options=[
                    {'value': '', 'label': '自动'},
                    {'value': 'mica', 'label': 'Mica（仅 Win 11）'},
                    {'value': 'blur', 'label': '模糊背景'},
                    {'value': 'acrylic', 'label': '亚克力（Win 10 1803+）'},
                    {'value': 'solid', 'label': '纯色背景'},
                ],
            )
            Select(
                key='interface.color_scheme',
                label='色彩方案',
                ref=ref(CTX.shared.interface.color_scheme),
                options=[
                    {'value': 'auto', 'label': '跟随系统'},
                    {'value': 'light', 'label': '浅色'},
                    {'value': 'dark', 'label': '深色'},
                ],
            )
            Select(
                key='interface.theme_color',
                label='主题色',
                ref=ref(CTX.shared.interface.theme_color).map(
                    to_ui=lambda v: '' if v is None else str(v),
                    from_ui=lambda v: (str(v).strip() or None),
                ),
                options=[
                    {'value': '', 'label': '跟随系统'},
                    {'value': '#0078d4', 'label': '蓝色（#0078D4）'},
                    {'value': '#e81123', 'label': '红色（#E81123）'},
                    {'value': '#107c10', 'label': '绿色（#107C10）'},
                    {'value': '#ff8c00', 'label': '橙色（#FF8C00）'},
                    {'value': '#5c2d91', 'label': '紫色（#5C2D91）'},
                    {'value': '#00b7c3', 'label': '青色（#00B7C3）'},
                    {'value': '#6b69d6', 'label': '靛蓝（#6B69D6）'},
                    {'value': '#4a5459', 'label': '石墨灰（#4A5459）'},
                ],
            )

    return page.spec, page.hooks
