from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from typing import Any

import ttkbootstrap as tb

from .dsl import FieldSpec, FragmentSpec, ScreenSpec


@dataclass
class RenderContext:
    """Render context shared by custom renderers.

    :param app: Desktop app instance.
    :param state: Reactive state object.
    """

    app: Any
    state: Any


class TkSettingsRenderer:
    """Render a :class:`ScreenSpec` into Tk widgets."""

    def __init__(self, *, context: RenderContext):
        self._context = context

    def render(self, parent: tk.Misc, screen: ScreenSpec) -> None:
        """Render all sections under parent."""
        for section in screen.sections:
            frame = tb.Labelframe(parent, text=section.title)
            frame.pack(fill=tk.X, padx=16, pady=8)
            for item in section.items:
                self._render_item(frame, item)

    def _render_item(self, section_frame: tk.Misc, item: FieldSpec | FragmentSpec) -> None:
        if isinstance(item, FieldSpec):
            self._render_field(section_frame, item)
            return
        self._render_fragment(section_frame, item)

    def _render_field(self, section_frame: tk.Misc, field: FieldSpec) -> None:
        row = tb.Frame(section_frame)
        row.pack(fill=tk.X, padx=8, pady=8)

        tb.Label(row, text=field.label, width=16, anchor=tk.W).pack(side=tk.LEFT)

        def _apply_visibility(*_args: object) -> None:
            if field.visible_if is None or field.visible_if():
                row.pack(fill=tk.X, padx=8, pady=8)
            else:
                row.pack_forget()

        if field.kind == 'checkbox':
            self._render_checkbox(row, field)
        elif field.kind == 'text':
            self._render_text(row, field)
        elif field.kind == 'select':
            self._render_select(row, field)
        elif field.kind == 'custom':
            self._render_custom(row, field)
        else:
            raise ValueError(f'Unknown field kind: {field.kind}')

        _apply_visibility()
        for dep in field.depends_on:
            dep.subscribe(lambda _value, apply=_apply_visibility: apply())

    def _render_fragment(self, section_frame: tk.Misc, fragment: FragmentSpec) -> None:
        container = tb.Frame(section_frame)
        container.pack(fill=tk.X, padx=0, pady=0)
        for field in fragment.fields:
            self._render_field(container, field)

        def _apply_fragment_visibility(*_args: object) -> None:
            if fragment.visible_if is None or fragment.visible_if():
                container.pack(fill=tk.X, padx=0, pady=0)
            else:
                container.pack_forget()

        def _apply_fragment_enabled(*_args: object) -> None:
            enabled = True if fragment.enabled_if is None else bool(fragment.enabled_if())
            state = tk.NORMAL if enabled else tk.DISABLED
            self._set_child_widget_state(container, state)

        _apply_fragment_visibility()
        _apply_fragment_enabled()
        for dep in fragment.depends_on:
            dep.subscribe(lambda _value, apply=_apply_fragment_visibility: apply())
            dep.subscribe(lambda _value, apply=_apply_fragment_enabled: apply())

    def _set_child_widget_state(self, widget: tk.Misc, state: str) -> None:
        for child in widget.winfo_children():
            try:
                child.configure(state=state)
            except Exception:
                pass
            self._set_child_widget_state(child, state)

    def _apply_enabled_if(self, widget: tk.Misc, field: FieldSpec) -> None:
        def _refresh(*_args: object) -> None:
            enabled = True if field.enabled_if is None else bool(field.enabled_if())
            try:
                widget.configure(state=(tk.NORMAL if enabled else tk.DISABLED))
            except Exception:
                pass

        _refresh()
        for dep in field.depends_on:
            dep.subscribe(lambda _value, refresh=_refresh: refresh())

    def _render_checkbox(self, row: tk.Misc, field: FieldSpec) -> None:
        var = tk.BooleanVar(value=bool(field.signal.get()))
        check = tb.Checkbutton(row, variable=var, text='')
        check.pack(side=tk.LEFT)

        def _on_var_change(*_args: object) -> None:
            field.signal.set(bool(var.get()))

        var.trace_add('write', _on_var_change)
        field.signal.subscribe(lambda value: var.set(bool(value)))
        self._apply_enabled_if(check, field)

    def _render_text(self, row: tk.Misc, field: FieldSpec) -> None:
        formatter = field.formatter or (lambda value: '' if value is None else str(value))
        var = tk.StringVar(value=formatter(field.signal.get()))
        entry = tb.Entry(row, textvariable=var, width=30)
        entry.pack(side=tk.LEFT)

        def _on_var_change(*_args: object) -> None:
            text = var.get()
            if field.parser is not None:
                try:
                    parsed = field.parser(text)
                except Exception:
                    return
                field.signal.set(parsed)
            else:
                field.signal.set(text)

        var.trace_add('write', _on_var_change)
        field.signal.subscribe(lambda value: var.set(formatter(value)))
        self._apply_enabled_if(entry, field)

    def _render_select(self, row: tk.Misc, field: FieldSpec) -> None:
        formatter = field.formatter or (lambda value: '' if value is None else str(value))
        parser = field.parser

        display_values = [formatter(option) for option in field.options]
        display_to_value = {formatter(option): option for option in field.options}
        var = tk.StringVar(value=formatter(field.signal.get()))

        combo = tb.Combobox(row, state='readonly', textvariable=var, values=display_values, width=28)
        combo.pack(side=tk.LEFT)

        def _on_var_change(*_args: object) -> None:
            text = var.get()
            if parser is not None:
                try:
                    field.signal.set(parser(text))
                except Exception:
                    return
                return
            field.signal.set(display_to_value.get(text, text))

        var.trace_add('write', _on_var_change)
        field.signal.subscribe(lambda value: var.set(formatter(value)))
        self._apply_enabled_if(combo, field)

    def _render_custom(self, row: tk.Misc, field: FieldSpec) -> None:
        if field.custom_renderer is None:
            raise ValueError(f'custom field {field.key} has no renderer')
        field.custom_renderer(row=row, field=field, context=self._context)
