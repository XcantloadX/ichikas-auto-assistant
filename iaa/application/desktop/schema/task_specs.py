from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True, slots=True)
class TaskRowSpec:
    """UI metadata for one home-page task row.

    :param task_id: Scheduler task id.
    :param label: Display label.
    :param is_toggle: Whether task participates in regular schedule toggles.
    :param get_enabled: Read enabled state from config scheduler.
    :param set_enabled: Write enabled state to config scheduler.
    """

    task_id: str
    label: str
    is_toggle: bool
    get_enabled: Callable[[object], bool] | None = None
    set_enabled: Callable[[object, bool], None] | None = None
