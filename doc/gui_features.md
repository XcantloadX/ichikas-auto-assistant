## 现有 Tkinter GUI 功能梳理

### 控制页（tab_control）
- 显示调度器状态：正在运行与否、启动/停止过渡态、当前执行任务名称。
- 单一启动/停止按钮：调用 `scheduler.start_regular` / `scheduler.stop`，并根据状态禁用。
- 任务开关：
  - 启动游戏 (`start_game_enabled`)
  - 单人演出 (`solo_live_enabled`)
  - 挑战演出 (`challenge_live_enabled`)
  - 活动剧情 (`activity_story_enabled`)
  - 自动 CM (`cm_enabled`)
  切换后立即写入配置。
- 单任务立即执行按钮（禁用于运行/切换中）：
  - 启动游戏 `start_game`
  - 单人演出 `solo_live`
  - 挑战演出 `challenge_live`
  - 活动剧情 `activity_story`
  - 自动 CM `cm`
- “刷完成歌曲首数”按钮：确认后运行 `ten_songs` 手动任务。

### 配置页（tab_settings）
- 游戏设置：
  - 模拟器类型：MuMu / 自定义；自定义时显示 ADB IP 与端口。
  - 服务器：仅日服 (`jp`)。
  - 引继账号：不引继 / Google Play。
  - 控制方式：`nemu_ipc` / `adb` / `uiautomator`。
- 演出设置：
  - 歌曲选择：固定映射（保持不变 / 几首预设曲目），控件当前禁用但会保存值。
  - “完全清空体力”布尔开关。
- 挑战演出设置：
  - 角色单选（按分组展示，使用 AdvanceSelect）。
  - 奖励优先级选择：水晶、音乐卡、奇迹晶石、魔法之布、硬币、中级练习乐谱。
- 保存按钮：将上述配置写入默认配置文件。

### 关于页（tab_about）
- 显示 LOGO 与版本号。
- 友情链接：GitHub / Bilibili / 教程文档 / QQ 群（可点击打开浏览器）。
- LOGO 悬停提示文本。
