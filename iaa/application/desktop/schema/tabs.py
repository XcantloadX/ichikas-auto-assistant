from __future__ import annotations

import tkinter as tk

from .about_tab import build_about_tab as _build_about_tab
from .control_tab import build_control_tab as _build_control_tab
from .renderer import RenderContext
from .settings_tab import build_settings_tab as _build_settings_tab


def build_control_tab(app, parent: tk.Misc) -> None:
    """Build schema-driven control tab."""
    _build_control_tab(app, parent)


def build_settings_tab(app, parent: tk.Misc) -> None:
    """Build schema-driven settings tab."""
    _build_settings_tab(parent, context=RenderContext(app=app, state=None))


def build_about_tab(app, parent: tk.Misc) -> None:
    """Build schema-driven about tab."""
    _build_about_tab(parent, context=RenderContext(app=app, state=None))
