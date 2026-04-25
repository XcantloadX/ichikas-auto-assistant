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

    return page.spec, page.hooks
