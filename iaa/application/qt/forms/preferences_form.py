from __future__ import annotations

from ..dsl import Checkbox, FormPage, Group, PreferencesContext, ref
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

    return page.spec, page.hooks
