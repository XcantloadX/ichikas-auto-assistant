"""Schema-driven desktop UI helpers."""

from .dsl import FieldSpec, ScreenSpec, SectionSpec, SettingsRegistry
from .reactive import Signal, of, signal, watch

__all__ = [
    'FieldSpec',
    'ScreenSpec',
    'SectionSpec',
    'SettingsRegistry',
    'Signal',
    'of',
    'signal',
    'watch',
]
