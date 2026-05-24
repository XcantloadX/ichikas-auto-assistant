from __future__ import annotations

from typing import Any, Generic, TypeVar

from .specs import FieldSpec, FormSpec

TCtx = TypeVar('TCtx')


class RuntimeEngine(Generic[TCtx]):
    def __init__(self, spec: FormSpec[TCtx]) -> None:
        self.spec = spec

    def build_runtime(self, state: TCtx) -> dict[str, Any]:
        # 不变式：所有 group 和 field 必须始终出现在输出中（即使 visible=False）。
        # 这样 fieldMap.keys() 在正常交互中保持稳定，_emit_updates 可以走增量路径
        # （fieldUpdated / groupUpdated），避免触发 runtimeChanged 全量重建。
        # 若违反此不变式，分段按钮等带动画的控件会因 Repeater 重建而被销毁，动画丢失。
        # 可见性控制由 QML 侧通过 fieldUpdated / groupUpdated 信号响应式处理。
        groups: list[dict[str, Any]] = []
        field_map: dict[str, Any] = {}

        for group in self.spec.groups:
            group_visible = group.visible(state) if callable(group.visible) else group.visible
            field_ids: list[str] = []
            for field in group.fields:
                runtime = self._build_field_runtime(field, state)
                field_ids.append(field.key)
                field_map[field.key] = runtime
            groups.append({'title': group.title, 'fieldIds': field_ids, 'visible': bool(group_visible)})

        return {'title': self.spec.title, 'groups': groups, 'fieldMap': field_map}

    def find_field(self, field_id: str) -> FieldSpec[TCtx] | None:
        for group in self.spec.groups:
            for field in group.fields:
                if field.key == field_id:
                    return field
        return None

    def _build_field_runtime(self, field: FieldSpec[TCtx], state: TCtx) -> dict[str, Any]:
        value = field.ref.get(state)
        visible = field.visible(state) if callable(field.visible) else field.visible
        enabled = field.enabled(state) if callable(field.enabled) else field.enabled

        if field.options is None:
            options: list[Any] = []
        elif callable(field.options):
            options = field.options(state)
        else:
            options = field.options

        error = ''
        for validator in field.validators:
            msg = validator(value, state)
            if msg:
                error = msg
                break

        return {
            'id': field.key,
            'kind': field.kind,
            'label': field.label,
            'helpText': field.help_text,
            'value': value,
            'visible': bool(visible),
            'enabled': bool(enabled),
            'options': options,
            'error': error,
            'loading': False,
            'props': field.props,
            'refreshable': 'refresh' in field.actions,
            'actions': list(field.actions.keys()),
        }
