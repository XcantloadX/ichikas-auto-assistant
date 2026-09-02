# 冲突报告：合并 `feat/en-server` 到 `release/26.07`

## 1. 概览

| 项 | 值 |
| --- | --- |
| 目标分支（被合并方 HEAD） | `release/26.07` @ `f418b3e` |
| 源分支（合入方 HEAD） | `feat/en-server` @ `1beef9e` |
| 合并基点（merge-base） | `288a5e7` |
| 提交差距 | release 领先基点 80 个提交；feat 领先基点 17 个提交 |
| 合并方式 | `git merge --no-commit --no-ff feat/en-server` |
| 冲突文件总数 | **39 个**（另有 1 个“目录重命名拆分”提示、1 个“文件位置”冲突） |

> 说明：本次合并仅为**分析用的一次性尝试**，测出冲突后已执行 `git merge --abort` 回滚，
> 工作区当前是干净的，未产生任何提交。本报告基于实测冲突结果编写。

---

## 2. 冲突分类总览

| 类别 | 数量 | 代表冲突类型 |
| --- | --- | --- |
| A. modify/delete（我方删除、对方修改） | 13 | `DU` |
| B. 目录重命名 / 文件位置（DSL 相关） | 1 组（`i18n.py` UA + rename split） | `UA`、`R` |
| C. 内容冲突（双方都改了同一个文件） | 25 | `UU` |
| **合计** | **39 个路径** | |

---

## 3. 冲突根因

两条分支在合并基点 `288a5e7` 之后**走向了两个相反方向的 UI 重构**，这是本轮冲突
数量庞大的根本原因：

- **`feat/en-server`**（看广告/闲聊等任务的 EN 国际服适配）：
  - 在旧的 **DSL 表单框架**上继续开发，未跟随 release 的 UI 重构；
  - 为适配国际服（提升包名、`en` 服务器、EN 广告恢复流程、EN 资源模板）；
  - 加入 **GUI 国际化**（`TStr` / `tstr()` / `iaa/i18n.py`、`i18n_controller`、
    `HelpService` 语言缓存、`preferences.language` 配置项）。
- **`release/26.07`**（中文服发布分支）：
  - `042d651 refactor(ui): 移除 DSL，改用直接 QML` —— **删除了整套 DSL 框架**，
    并把表单改成直接 QML 控件；
  - `2569793 refactor(ui): 提取 FormController 公共类`；
  - `3ed31f7 feat(core): 内嵌 scrcpy 画面到 Tab 内部` —— **删除了独立 scrcpy 窗口**；
  - `79a00eb feat(ui): 移除自动修改分辨率` —— 移除了 `auto` 分辨率选项；
  - 同时把大量硬编码中文文案直接写进 QML / Python 字符串。

因此绝大多数冲突本质上是“**release 的重构（删除 DSL、删除 scrcpy 窗口、删除 forms、
## 4. 逐类冲突分析

### 类别 A：modify/delete —— DSL / 旧表单 / scrcpy 窗口 / main.py 被 release 删除

release 删除了以下文件，feat 仍在修改/沿用它们，git 无法自动判定去留。

#### A-1. DSL 框架文件（core 争议点，13 个中的 7 个）

| 文件 | 说明 |
| --- | --- |
| `iaa/application/framework/dsl/__init__.py` | DSL 包入口 |
| `iaa/application/framework/dsl/runtime.py` | DSL 运行时 |
| `iaa/application/framework/dsl/specs.py` | DSL 规格定义 |
| `iaa/application/framework/dsl/qml/FieldRenderer.qml` | DSL 字段渲染 |
| `iaa/application/framework/dsl/qml/controls/DslMumuPicker.qml` | 模拟器选择控件 |
| `iaa/application/framework/dsl/qml/controls/DslSelectField.qml` | 下拉字段 |
| `iaa/application/framework/dsl/qml/controls/DslTransferList.qml` | 转移列表控件 |

- **冲突原因**：release `042d651` 移除 DSL；feat 在 DSL 上叠加了
  `Translatable` 协议、`TStr`（见 `iaa/application/qt/i18n.py`）等国际化改造。
- **解析建议**：**采纳 release 的重构（执行 `git rm`，即保留删除）**。
  DSL 已不存在于目标代码库，任何 feat 的 DSL 改动都应被放弃。feat 的
  GUI 国际化如果想保留，需要基于 release 的新直接-QML 表单重新实现，不能复用 DSL。
- **风险**：这是整轮合并唯一“需要人决策”的点——是否要保留 feat 的 EN GUI 国际化。
  若保留，需把 DSL 层的 i18n 移植到新 QML（工作量大）；若舍弃，则 `preferences.language`
  与 `iaa/i18n.py` 的相关联动也要一起收敛。

#### A-2. 目录重命名拆分：`iaa/application/framework/dsl/qml/components`

- **冲突原因**：release 把 `dsl/qml/components` 里的控件删除/重命名到了不同目录
  （如 `qt/qml/components`、`qt/qml/controls`、`qt/qml/components/form`），没有单一目的
  目录获得多数文件，git 无法自动重命名。
- **解析建议**：随 A-1 一并删除 DSL 目录即可；此提示是派生问题。

#### A-3. 独立 scrcpy 窗口被 release 移除

| 文件 | 说明 |
| --- | --- |
| `iaa/application/qt/controllers/scrcpy_controller.py` | scrcpy 控制器 |
| `iaa/application/qt/qml/windows/ScrcpyWindow.qml` | scrcpy 独立窗口 |

- **冲突原因**：release `3ed31f7` 把 scrcpy 画面**内嵌到 Tab 内部**，删除独立窗口与其
  控制器；feat 沿用并修改了它们（含 i18n）。
- **解析建议**：**保留 release 的删除**。feat 若还依赖 `scrcpyController`
  （在 `index.py` 冲突里用 `controller.scrcpyController`），需要检查目标版
  内嵌 Tab 的实现是否仍暴露相同能力，必要时改为引用新实现。

#### A-4. 旧 DSL 表单与自动分辨率控件被 release 移除

| 文件 | 说明 |
| --- | --- |
| `iaa/application/qt/forms/preferences_form.py` | 旧设置表单（DSL） |
| `iaa/application/qt/forms/settings_form.py` | 旧设备表单（DSL） |
| `iaa/application/qt/qml/controls/DslResolutionSelect.qml` | 旧分辨率控件 |

- **冲突原因**：release `042d651` / `2569793` 移除 DSL 表单、`79a00eb` 移除
  `auto` 分辨率选项；feat 仍引用这些旧形式。
- **解析建议**：**保留 release 的删除**；目标版用 `qt/qml/components/form` / `controls`
  下的新 QML 实现替代。

#### A-5. `iaa/main.py`

- **冲突原因**：release 把入口逻辑迁移走、删除了该文件；feat 仍把它作为入口并为其加了
  i18n（`translate` / `translate_error`）。
- **解析建议**：**保留 release 的删除**，确认新入口已覆盖 i18n 相关逻辑；
  若 feat 的启动期翻译（如“配置校验提示”）需要保留，搬入新入口。

---

### 类别 B：文件位置 / add-vs-rename —— `iaa/application/qt/i18n.py`

- **冲突类型**：`UA`（feat 新增文件位于被重命名目录内）+ “file location” 提示。
- **内容**：feat 在此定义 DSL 用到的 `Translatable` 协议、`TStr` 等。
- **解析建议**：与 A-1 同源。若 DSL 全删，该文件应一并弃用；feat 的 i18n 核心是在
  `iaa/i18n.py`（新增、无冲突，见第 5 节），不会被这类冲突波及。

---
删除 auto 分辨率）**”与“**feat 的 EN/i18n 修改**”在同一批文件上的叠加。

---