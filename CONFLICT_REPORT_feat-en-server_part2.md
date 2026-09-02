# 冲突报告补充：类别 C 内容冲突与合并策略

> 本文是对 `CONFLICT_REPORT_feat-en-server.md` 的补充，覆盖“类别 C 内容冲突、
> 非冲突新增、合并策略与风险提示”。（前文覆盖概览、分类、根因、类别 A/B。）

---

### 类别 C：内容冲突（25 个 `UU`）

根因基本都可归为三类：
1. **任务实现**：release 重构任务注册（`TASK_INFOS`/`get_enabled`）VS feat 继续用 `REGULAR_TASKS`。
2. **UI/文案**：release 硬编码中文 VS feat 用 `App.Globals.t(...)` / `tstr(...)` 国际化。
3. **资源/配置**：release 加 `startup_page`、feat 加 `language`、EN 资源目录等。

| 文件 | 冲突点 | 最小化解析 |
| --- | --- | --- |
| `iaa/config/shared.py` | `InterfaceConfig`：release 加 `startup_page`，feat 加 `language` | **两个字段都保留**（相互独立，是简单叠加） |
| `iaa/application/service/scheduler.py` | `_get_enabled_tasks`：release 用 `TASK_INFOS`+`get_enabled`；feat 用 `REGULAR_TASKS`（已被删除的注册表） | 采用 release 的 `TASK_INFOS` 方案；删除对已不存在 `REGULAR_TASKS` 的引用 |
| `iaa/tasks/cm.py` | ①`get_conf().tasks.cm` VS `get_conf().cm`（配置路径迁移）；②Skip 阈值 `0.7` + `current_server != 'en'`（EN 特判）与纯 JP 逻辑冲突 | 保留 release 的配置路径结构；把 feat 的 EN 分支（provider 恢复、EN 广告）合并进新结构；阈值以 feat 的 EN 特判为准 |
| `iaa/application/qt/index.py` | engine 初始化：release 用 `ProfileStoreBackend(controller.tabManager, controller)`；feat 集中注册 controller/engine 属性 + i18n | 以 feat 的 engine 构造为主，保留 release 的 controller 装配；按目标版把 `i18nController` 接上 |
| `iaa/application/qt/controllers/app_controller.py` | ①`ConfigValidationError` 导入；②`windowTitleChanged` / `pathWarningRequired` 信号名；③窗口标题（`_tr` vs 中文判断）；④迁移弹窗文案（i18n） | 保留 feat 的 i18n 文案与信号；将 release 的启动流程（导入校验、`apply_runtime_preferences`）融合进来 |
| `iaa/application/qt/controllers/help_controller.py` | feat 的 `HelpService` 带 `iaa_service` + `get_language` 语言感知；release 是无参服务 | 以 feat 语言感知版为主，接好构造参数 |
| `iaa/application/qt/controllers/preferences_controller.py` | `runtimeChanged`/`interfaceChanged`（feat）VS `configChanged`（release）；language 联动 | 保留 feat 的 signal 拆分 + language 联动，融合 release 的偏好应用逻辑 |
| `iaa/application/qt/controllers/progress_bridge.py` / `run_controller.py` / `settings_controller.py` | 控制器构造/属性与 i18n 有关联改动 | 与 `index.py` 的 engine 装配一并还原 |
| `iaa/application/qt/models/__init__.py` | feat 从 `auto_live_constants` 导出常量（`AP_KEEP_UNCHANGED` 等）；release 无这些 | 保留 feat 导出（新模块无冲突，见第 5 节） |
| `iaa/application/qt/models/auto_live.py` | feat 引入 `auto_live_constants`、`normalize_song_name_input`、`_normalize_ap_multiplier_raw`、预设名常量；release 是内联字面量 | 以 feat 的常量化版本为主，逐个核对预设语义（含 release `ce011f1` 的预设优化、`464d03f` 的 AP 0 提示） |
| `iaa/application/qt/models/mappings.py` | 显示映射：release 硬编码中文 `str`；feat 用 `TStr` + 新增 `en` 服务器 + 新增 `auto` 分辨率 | 以 feat 的 `TStr`/i18n 版为主，确认 release 除 `en` 外的选项都被覆盖 |
| `iaa/application/qt/qml/MainWindow.qml` / `SideNavigationBar.qml` | 硬编码文案 VS `App.Globals.t(...)`（版本号、导航） | 保留 feat 的 i18n 调用 |
| `iaa/application/qt/qml/components/form/HotkeyField.qml` | feat 版依赖 `field`/`formController`（来自 DSL 的 form 体系），release 版是无 DSL 的 `value`/`root.userCommitted` | **需重点核对**：release 已移除 DSL，`formController.setValue` 可能不存在于新 QML，需按 release 的新表单数据流改写 |
| `iaa/application/qt/qml/dialogs/AutoLiveDialog.qml` / `ConfigManagerDialog.qml` | feat 用 `formData`/常量/`App.Globals.t`；release 改过的控件（`FormSegmentedButton` 等） | 保留 feat 逻辑，转用 release 存活的控件（`controls/SegmentedButton.qml`/`Select.qml`） |
| `iaa/application/qt/qml/pages/AboutPage.qml` / `ControlPage.qml` / `PreferencesPage.qml` | feat 用 `App.Globals.t(...)`、`runController`/`preferencesController` 属性 + 导出条数；release 用 `root.ctrl_*`、硬编码中文、`runCtrl` | 采用 feat 的 i18n 与 controller 引用；`ControlPage` 任务开关走 `setRegularTaskEnabled(modelData.id,...)`，与 scheduler 方案统一 |
| `iaa/application/service/config_service.py` | ①`tstr` 导入；②`self.iaa.scheduler.running`（feat）VS `self._is_running()`（release）守卫 | 保留 feat 的 i18n 报错 + release 的运行守卫逻辑 |
| `iaa/application/service/help_service.py` | 无参构造 VS `IaaService`+`_detect_system_language`+缓存 | 保留 feat 语言感知版 |
| `resources/jp/shop/screenshot_event_shop.png.json` | 同一识别资源里 `cn` VS `en` 字段（feat 改 `cn`->`en`） | 以 feat 的 `en` 为准（这是 EN 资源模板的正常归属）；JP 应仍为 `cn`/日文 |
| `tests/test_qt_auto_live.py` | 测试 import：`auto_live_payload_to_plan` 位置（`tasks.live.live` VS `qt.models.auto_live`）+ `auto_live_constants` | 跟随 feat 的实现位置修正 import；确认 `ListLoopPlan`/`SingleLoopPlan` 仍在 |

---

## 5. 合并后可干净合入（非冲突）的关键新增

以下属于 feat 的新增，无冲突、应完整保留（这是 feat 的价值所在）：

- **国际服资源**：`resources/en/...`（cm / common_dialog / daily / live / login / map / story / shop 等整批截图与识别模板）—— 新增 `A`。
- **i18n 基础设施**：`iaa/i18n.py`（`TStr`/`tstr`/`_detect_system_language`）、`iaa/application/qt/controllers/i18n_controller.py`、`App.Globals.t`。
- **auto_live 常量化**：`iaa/tasks/live/auto_live_constants.py`。
- **测试**：`tests/test_qt_i18n.py`、`tests/test_global_en_config.py`、`tests/test_live_auto_loop.py`。
- **文档/帮助页**：`README.en.md`、`assets/help/en_US/...`、`assets/help/zh_CN/...`。
- **JP 识别资源批量微改**：`resources/jp/**/*.png.json` 大量 `M`（feat 为适配识别差异做的批量调整），除 event_shop 外均自动合并成功，无需处理。

---

## 6. 推荐合并策略与顺序

1. **先做结构性决策**（决定全部 modify/delete 的去留）：
   - 采纳 release：`git rm` 掉 DSL / 旧 forms / scrcpy 独立窗口 / `main.py` / `qt/i18n.py`。
   - 明确是否保留 feat 的 **EN GUI 国际化**。若保留，需在 release 的新直接-QML UI 上把 i18n 移植回来（主要落在 `AutoLiveDialog`、`PreferencesPage`、`SettingsPage`、`HotkeyField` 等）。
2. **再加全部新增资源**：`git add` 第 5 节的新文件（已自动 ok）。
3. **逐一解决 `UU` 内容冲突**，遵循“**任务逻辑以 release 的新注册表为准、文案以 feat 的 i18n 为准**”的原则。
4. **跑测试**：`tests/test_qt_auto_live.py`（含新的 `test_qt_i18n.py`、`test_live_auto_loop.py`）、`test_cli.py`、`test_config_service.py`，并启动 UI 验证 engine 装配、控制页任务列表、CM 广告流程（EN 分支）。

---

## 7. 关键风险提示

- **DSL 与 i18n 的耦合**：feat 的 GUI 国际化建立在已删除的 DSL 之上，真正需要人决策的只有一个点——**对新 QML 界面要不要做 EN 文案翻译**。全部冲突量都从这里扩散。
- **`get_conf().cm` vs `get_conf().tasks.cm`**：配置路径被 release 迁移（`tasks.cm`），若保留 feat 的 `cm` 路径会访问不存在路径，必须用 release 的路径。
- **`REGULAR_TASKS` 已不存在**：feat 中仍引用的旧任务注册表在 release 中已改为 `TASK_INFOS`，相关冲突不可“两全其一”，只能以 release 为准并保留 EN 分支。

---