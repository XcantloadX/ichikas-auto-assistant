from __future__ import annotations

from typing import Any

from .specs import FieldSpec, FormSpec


class RuntimeEngine:
    def __init__(self, spec: FormSpec) -> None:
        self.spec = spec

    def build_runtime(self, state: Any) -> dict[str, Any]:
        groups: list[dict[str, Any]] = []
        field_map: dict[str, Any] = {}

        for group in self.spec.groups:
            group_visible = group.visible(state) if callable(group.visible) else group.visible
            if not group_visible:
                continue
            field_ids: list[str] = []
            for field in group.fields:
                runtime = self._build_field_runtime(field, state)
                if runtime['visible']:
                    field_ids.append(field.key)
                    field_map[field.key] = runtime
            groups.append({'title': group.title, 'fieldIds': field_ids})

        return {'title': self.spec.title, 'groups': groups, 'fieldMap': field_map}

    def find_field(self, field_id: str) -> FieldSpec | None:
        for group in self.spec.groups:
            for field in group.fields:
                if field.key == field_id:
                    return field
        return None

    def _build_field_runtime(self, field: FieldSpec, state: Any) -> dict[str, Any]:
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
        }
