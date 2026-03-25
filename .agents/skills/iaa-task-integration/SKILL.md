---
name: iaa-task-integration
description: Add or update an Ichika Auto Assistant task by wiring everything around the task implementation itself. Use when Codex needs to create a new task placeholder, register a task, add scheduler enable switches, extend config models and default JSON files, expose task settings in the desktop GUI, or verify that a new task is reachable from CLI and GUI without implementing the business logic yet.
---

# Iaa Task Integration

## Overview

Use this skill to integrate a new task into the IAA project after or before the task logic exists.
Focus on task registration, config schema changes, default config migration, desktop GUI wiring, and minimal validation.

## Decide Task Type

Choose the task type before editing files.

Use a regular task when it should participate in the main scheduler run.
Use a manual task when it should only be launched explicitly from GUI or CLI.

In this repo:

- `iaa/tasks/registry.py`
  Put scheduled tasks in `REGULAR_TASKS`.
  Put explicit-run tasks in `MANUAL_TASKS`.
- `iaa/config/schemas.py`
  Add `scheduler.<task>_enabled` only for regular tasks.
- `iaa/application/desktop/tab_main.py`
  Regular tasks usually get a checkbox plus `▶`.
  Manual tasks usually get only a launch entry or custom dialog.

## Workflow

1. Create or confirm the task module.
2. Register the task and display name in `iaa/tasks/registry.py`.
3. Add config model fields in `iaa/config/schemas.py` and `iaa/config/base.py`.
4. Ensure new config files created by `iaa/config/manager.py` include the new section.
5. Update existing JSON files under `conf/` so current users can load the new model.
6. Wire scheduler toggles for regular tasks.
7. Wire desktop GUI entry points and task-specific settings.
8. Run a minimal validation pass.

## Edit Points

### 1. Task Module

If the user only wants a placeholder, implement the smallest safe stub:

- use the normal `@task(...)` decorator
- use the final display name the GUI should show
- keep the body side-effect free unless explicitly requested
- if useful, read config and log/report that the task is not implemented yet

Example pattern:

```python
from kotonebot import task, logging
from iaa.context import conf as get_conf, task_reporter

logger = logging.getLogger(__name__)

@task('活动商店', screenshot_mode='manual')
def event_shop() -> None:
    rep = task_reporter()
    items = list(get_conf().event_shop.purchase_items)
    rep.message('活动商店功能暂未实现')
    logger.info('Placeholder invoked. purchase_items=%s', items)
```

### 2. Registry

Always update all three places in `iaa/tasks/registry.py`:

- import the task
- add it to `REGULAR_TASKS` or `MANUAL_TASKS`
- add entries to `name_from_id()` and `TASK_INFOS`

If one of these is missed, the task often becomes runnable in one surface but invisible or mislabeled in another.

### 3. Config Schema

Split config into two concepts:

- scheduler enable flag
  Example: `event_shop_enabled: bool = True`
- task-specific config section
  Example: `event_shop: EventStoreConfig = EventStoreConfig()`

Typical files:

- `iaa/config/schemas.py`
  Add the new `BaseModel` for task-specific settings.
  Add scheduler enable flags for regular tasks.
  Update `SchedulerConfig.is_enabled()`.
- `iaa/config/base.py`
  Add the new task config field to `IaaConfig`.
- `iaa/config/manager.py`
  Make sure newly created config files contain the new section.

### 4. Existing Config JSON

Update every existing config file under `conf/`.

This repo validates with Pydantic defaults at runtime, so some missing fields may appear to work, but leaving old JSON files stale causes confusion:

- GUI may show different defaults than new config creation
- users cannot discover the new setting in saved config
- future stricter validation or export logic may break unexpectedly

For placeholder list settings, prefer a few meaningful sample values instead of an empty list so the GUI demonstrates the intended format.

### 5. Desktop GUI

There are usually two GUI surfaces to wire.

- `iaa/application/desktop/tab_main.py`
  Add the task enable checkbox and manual run button if needed.
  Save the scheduler bool back to config.
  Add any new `BooleanVar` to `app.store` if other UI code reads selected tasks.
- `iaa/application/desktop/tab_conf.py`
  Add task-specific settings UI.
  Keep placeholder settings simple.
  For `list[str]`, use a multiline `Text` widget and serialize one item per line.
- `iaa/application/desktop/index.py`
  If the selected-task summary/store tracks that task, add the new variable there too.

### 6. CLI And Scheduler Expectations

Usually no separate CLI parser change is needed because `iaa/main.py` builds task validation from `REGULAR_TASKS` and `MANUAL_TASKS`.

Still verify the behavior:

- regular task
  appears in `run`
  appears in task list
  can be invoked manually
- manual task
  appears in task list
  can be invoked manually
  does not silently join the scheduled run

## Minimal Validation

Run the cheapest checks first.

```powershell
python -m compileall iaa
python launch_desktop.py
```

If test tooling exists, run focused tests next.

Suggested spot checks:

1. Open the GUI and confirm the new task label, checkbox, and button render correctly.
2. Save config once and verify the new fields are persisted to JSON.
3. Launch the placeholder task from GUI or CLI and confirm it is reachable.
4. For a regular task, confirm toggling the checkbox changes scheduler behavior.

## Common Mistakes

- Forgetting `name_from_id()` or `TASK_INFOS`, which makes labels inconsistent.
- Adding a scheduler flag but not updating `is_enabled()`, so the task never runs.
- Updating schemas but not existing `conf/*.json`, so saved configs lag behind code.
- Adding the checkbox in `tab_main.py` but forgetting to persist it in `_save_scheduler()`.
- Adding task settings UI but never reading them back on save.
- Creating a placeholder task that accidentally performs real navigation or clicks.
- Forgetting that manual and regular tasks have different wiring paths.

## Practical Heuristics

- Keep placeholder tasks honest.
  Say "not implemented" in progress/logs instead of faking success.
- Prefer one config section per task when the settings are task-owned.
  Avoid stuffing unrelated fields into existing models just because they are nearby.
- Make the GUI teach the config format.
  For `list[str]`, one line per item is clearer than JSON-in-a-textbox.
- Treat existing config files as part of the public interface.
  Schema-only changes are incomplete until current JSON files are updated.
- Compile before deeper testing.
  It catches most integration mistakes quickly.

## Example Trigger Requests

- "新增一个任务占位，把配置和 GUI 接好。"
- "给 IAA 加一个常规任务，不写逻辑，只把注册和设置项补全。"
- "新增活动商店任务，包含开关和购买物品列表配置。"
- "帮我把一个新任务接到 registry、scheduler 和桌面端。"
