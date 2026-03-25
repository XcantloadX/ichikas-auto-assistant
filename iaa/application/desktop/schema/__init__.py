"""Schema-driven desktop UI helpers."""

from .dsl import FieldSpec, ScreenSpec, SectionSpec, SettingsRegistry
from .reactive import ReactiveObject, Signal, state_from_config, to_config

__all__ = [
    'FieldSpec',
    'ScreenSpec',
    'SectionSpec',
    'SettingsRegistry',
    'ReactiveObject',
    'Signal',
    'state_from_config',
    'to_config',
]
