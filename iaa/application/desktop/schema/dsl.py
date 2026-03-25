from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

from .reactive import Signal


VisibleFn = Callable[[], bool]
EnabledFn = Callable[[], bool]


@dataclass(frozen=True, slots=True)
class FieldSpec:
    """Field definition in the settings DSL."""

    key: str
    label: str
    kind: str
    signal: Signal[Any]
    options: tuple[Any, ...] = ()
    formatter: Callable[[Any], str] | None = None
    parser: Callable[[str], Any] | None = None
    visible_if: VisibleFn | None = None
    enabled_if: EnabledFn | None = None
    depends_on: tuple[Signal[Any], ...] = ()
    help_text: str | None = None
    custom_renderer: Callable[..., None] | None = None


@dataclass(frozen=True, slots=True)
class SectionSpec:
    """Section definition in the settings DSL."""

    key: str
    title: str
    fields: tuple[FieldSpec, ...] = ()


@dataclass(frozen=True, slots=True)
class ScreenSpec:
    """Top-level screen definition."""

    key: str
    title: str
    sections: tuple[SectionSpec, ...] = ()


class SectionBuilder:
    """Builder used by section factory functions."""

    def __init__(self, key: str, title: str):
        self._key = key
        self._title = title
        self._fields: list[FieldSpec] = []

    def checkbox(
        self,
        key: str,
        label: str,
        *,
        bind: Signal[bool],
        enabled_if: EnabledFn | None = None,
        depends_on: Sequence[Signal[Any]] = (),
        help_text: str | None = None,
    ) -> None:
        self._fields.append(
            FieldSpec(
                key=key,
                label=label,
                kind='checkbox',
                signal=bind,
                enabled_if=enabled_if,
                depends_on=tuple(depends_on),
                help_text=help_text,
            )
        )

    def text_input(
        self,
        key: str,
        label: str,
        *,
        bind: Signal[Any],
        parser: Callable[[str], Any] | None = None,
        formatter: Callable[[Any], str] | None = None,
        visible_if: VisibleFn | None = None,
        enabled_if: EnabledFn | None = None,
        depends_on: Sequence[Signal[Any]] = (),
        help_text: str | None = None,
    ) -> None:
        self._fields.append(
            FieldSpec(
                key=key,
                label=label,
                kind='text',
                signal=bind,
                parser=parser,
                formatter=formatter,
                visible_if=visible_if,
                enabled_if=enabled_if,
                depends_on=tuple(depends_on),
                help_text=help_text,
            )
        )

    def select(
        self,
        key: str,
        label: str,
        *,
        bind: Signal[Any],
        options: Sequence[Any],
        formatter: Callable[[Any], str] | None = None,
        parser: Callable[[str], Any] | None = None,
        visible_if: VisibleFn | None = None,
        enabled_if: EnabledFn | None = None,
        depends_on: Sequence[Signal[Any]] = (),
        help_text: str | None = None,
    ) -> None:
        self._fields.append(
            FieldSpec(
                key=key,
                label=label,
                kind='select',
                signal=bind,
                options=tuple(options),
                formatter=formatter,
                parser=parser,
                visible_if=visible_if,
                enabled_if=enabled_if,
                depends_on=tuple(depends_on),
                help_text=help_text,
            )
        )

    def custom(
        self,
        key: str,
        label: str,
        *,
        bind: Signal[Any],
        renderer: Callable[..., None],
        visible_if: VisibleFn | None = None,
        enabled_if: EnabledFn | None = None,
        depends_on: Sequence[Signal[Any]] = (),
        help_text: str | None = None,
    ) -> None:
        self._fields.append(
            FieldSpec(
                key=key,
                label=label,
                kind='custom',
                signal=bind,
                visible_if=visible_if,
                enabled_if=enabled_if,
                depends_on=tuple(depends_on),
                help_text=help_text,
                custom_renderer=renderer,
            )
        )

    def build(self) -> SectionSpec:
        """Finalize and return immutable section spec."""
        return SectionSpec(key=self._key, title=self._title, fields=tuple(self._fields))


@dataclass
class SettingsRegistry:
    """Registry that collects section factory functions."""

    _factories: list[tuple[str, str, Callable[[SectionBuilder], None]]] = field(default_factory=list)

    def section(self, key: str, title: str) -> Callable[[Callable[[SectionBuilder], None]], Callable[[SectionBuilder], None]]:
        """Register a section factory.

        :param key: Stable section key.
        :param title: Section title.
        """

        def _decorate(fn: Callable[[SectionBuilder], None]) -> Callable[[SectionBuilder], None]:
            self._factories.append((key, title, fn))
            return fn

        return _decorate

    def build(self, *, screen_key: str, screen_title: str) -> ScreenSpec:
        """Build immutable screen spec from registered factories."""
        sections: list[SectionSpec] = []
        for key, title, factory in self._factories:
            builder = SectionBuilder(key, title)
            factory(builder)
            sections.append(builder.build())
        return ScreenSpec(key=screen_key, title=screen_title, sections=tuple(sections))
