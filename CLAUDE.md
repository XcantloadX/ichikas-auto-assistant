# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dev dependencies and build template resources
just setup

# Start the desktop GUI
uv run launch_desktop.py

# Run CLI directly
uv run launch_cli.py run              # run all configured regular tasks
uv run launch_cli.py invoke <task_id> # run a specific task
uv run launch_cli.py list tasks       # list available tasks
uv run launch_cli.py list configs     # list available configs

# Rebuild template resources (after adding/changing images in resources/)
just res

# Lint
uv run ruff check iaa/
uv run ruff format iaa/

# Run tests
uv run pytest tests/

# Package executables
just build
```

## Framework extraction

iaa 内部包含一套完整的游戏自动化框架（GUI、DSL、表单、配置管理、任务注册、调度等），计划以 **git subtree 源码形式**提取为独立公共框架，下游项目通过 `pip install -e` 接入。

设计原则（引入或重构框架层代码时必须遵守）：

- **开箱即用优先。** 下游开发者拉入后应能直接使用，不需要大量配置。
- **不要过度预留扩展 API。** 基本场景用预留 API，高级定制允许直接改源码。
- **模块独立，低耦合。** 避免框架各模块之间过度依赖，方便下游按需裁剪。
- **减少下游 merge 冲突。** 源码目录布局要稳定，功能聚合，避免频繁改动公共文件。
- **注释说明定制点。** 凡是下游可能需要自定义的地方，用注释标明「可在此处通过 XX 方式自定义 YY」。

## Architecture

**iaa** is a Python automation framework for *Project Sekai: Colorful Stage* that automates daily tasks using computer vision (OpenCV + ONNX Runtime) over ADB. The stack is:

- **kotonebot** — underlying automation framework providing device control, screenshot capture, and vision primitives
- **iaa** — game-specific tasks, configuration, GUI, and CLI built on top of kotonebot
- **PySide6** — desktop GUI (Qt6 via FluentWinUI3 controls)

### Package layout

```
iaa/
  application/
    service/         # IaaService (root), ConfigService, AssetsService, SchedulerService, HelpService
    qt/              # PySide6 GUI: windows, dialogs, models, QML files
    framework/       # Custom DSL and QML controls (incl. Select.qml)
  config/            # Pydantic config schemas and manager
  definitions/       # Game-specific constants and error types
  game_ui/           # UI element prefabs (kotonebot editor integration)
  tasks/             # Task implementations + registry.py
    R.py             # Auto-generated resource loader (do not hand-edit)
  telemetry.py       # Sentry integration
resources/           # Source image templates (.png + .png.json metadata)
tools/
  make_resources.py  # Generates iaa/tasks/R.py from resources/
```

### Task system

Tasks are registered in `iaa/tasks/registry.py` in two categories:

- **Regular tasks** — run automatically in sequence during a normal session (`start_game`, `cm`, `solo_live`, `challenge_live`, `activity_story`, `gift`, `area_convos`, `event_shop`)
- **Manual tasks** — user-triggered explicitly (`main_story`, `auto_live`, `mission_rewards`)

`auto_live` is the only task with `supports_kwargs=True`; it accepts a `plan` kwarg built from CLI flags or the GUI dialog.

To add a new task: implement the function, register it in `registry.py`, add scheduler enable switches, extend `iaa/config/schemas.py` and `iaa/config/base.py`, update existing `conf/*.json` files, and expose settings in the GUI. Use the `iaa-task-integration` skill.

### Template resource flow

Image templates follow a strict pipeline:

1. Place source images under `resources/` with accompanying `.png.json` metadata
2. Run `just res` (→ `tools/make_resources.py`) to regenerate `iaa/tasks/R.py`
3. Reference templates via `R.*` — never load image files with ad-hoc paths in task code

To add a template, use the `iaa-template-resource-integration` skill.

### Configuration

Configs live in `conf/` as JSON files validated by Pydantic models in `iaa/config/`. Multi-server support uses variants (`tw`, `cn`) on a `jp` base, controlled by `[tool.kotonebot.variant]` in `pyproject.toml`.

### Logging

`IaaService.__configure_logging()` sets up dual output: console (DEBUG) and `logs/YYYY-MM-DD-HH-MM-SS.log`. The root directory is auto-detected (packaged exe vs. source run).

## Code Style

- **Do not over-split functions.** If a helper is called only once, keep the logic inline unless the extracted function is genuinely complex or materially improves readability.
- **QML dropdowns:** use `Select` (`iaa/application/framework/dsl/qml/controls/Select.qml`) for all non-editable dropdowns, not `ComboBox`. Use `ComboBox` only when `editable: true` is needed. Import path from `iaa/application/qt/qml/**/`: `import "../../../framework/dsl/qml/controls"`.
- **QML icon glyphs:** always write Segoe Fluent Icons / Segoe MDL2 Assets glyphs as `\uXXXX` escape sequences (e.g. `text: "\uE713"`), never as literal Unicode characters. Literal PUA characters are silently dropped by file-writing tools, leaving empty strings at runtime.
- Always use the repo `.venv` (via `uv run`) for Python scripts, probes, and generators.

## Skills

This repo defines four local skills. Pick the one that matches the problem type:

| Skill | Use when |
|---|---|
| `kotonebot-emulator-debug` | Live emulator interaction — connect to MuMu, capture screenshots, click/swipe/scroll, reproduce a failure on the real UI |
| `kotonebot-vision-debug` | Recognition analysis — tune ROI / HSV thresholds, inspect masks and contours, compare detection strategies on a saved frame |
| `iaa-task-integration` | New-task wiring — registry, scheduler, config schema, existing `conf/*.json`, desktop GUI settings |
| `iaa-template-resource-integration` | Template resource flow — add/edit `resources/**/*.png.json`, run `tools/make_resources.py`, switch code to `R.*` |

If you don't yet have the failing frame, start with `kotonebot-emulator-debug`. Once you have it, switch to `kotonebot-vision-debug`. If the analysis ends with a reusable image template, finish with `iaa-template-resource-integration`.
