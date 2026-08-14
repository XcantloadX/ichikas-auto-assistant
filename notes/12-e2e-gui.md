# 非脚本 E2E 验证（GUI 页面 / config 读写 / 日志 / 设备 placeholder）

日期：2026-08-14
分支：`feat/p4a-android`
构建：31799130972 的 APK（369MB），模拟器 127.0.0.1:5557（SM-S9110 x86_64 API35）

## 一、验证方式

人工确认 GUI 正常 + adb 驱动自动化验证：
- `adb shell input tap <x> <y>` 导航/点击；
- `adb shell uiautomator dump` 导出 Qt 可访问性树（QML 控件会映射成
  android.view 节点，`content-desc` 即控件文本）判断页面内容与坐标；
- `run-as org.iaa.iaa cat files/app/conf/*.json`、`logs/*.log` 验证落盘。

## 二、E2E 结果

| 项 | 结果 | 证据 |
|---|---|---|
| 启动 & GUI 点亮 | ✅ | 进程稳定存活；QtQuick Controls 插件加载；人工确认截图 |
| 总览（控制页） | ✅ | 启停分组 + 任务列表（启动游戏/自动CM/单人演出/挑战演出/活动剧情/领取礼物/区域对话/活动商店/任务奖励/刷主线剧情/自动演出，开关齐全） |
| 画面页 | ✅ | 渲染正常（启动按钮 + scrcpy 提示） |
| 配置页 | ✅ | 游戏设置/设备设置/控制方式/演出设置/挑战演出/CM/活动商店/调度/开发者 全部分组与控件渲染 |
| 日志页 | ✅ | 自动换行/清空按钮 + 输出区渲染 |
| 关于页 | ✅ | 应用名 + 版本显示 |
| config 读写回环 | ✅ | GUI 把服务器切到"台服"→ 保存 → `123.json` 的 `game.server` 变为 `tw` |
| 日志落盘/显示 | ✅ | `logs/2026-08-14-20-50-49.log` 记录 `Telemetry initialized`、`Save config: 123` |
| 设备 placeholder | ✅ | 控制页点"启动" → scheduler 走 `create_device_for_current_config` → `SelfAndroidDevice`，任务跑到 OCR 才失败；失败经 UI 弹窗提示、可关闭，进程不崩 |
| 稳定性 | ✅ | 连续交互 ~30min 无崩溃/ANR |

## 三、设备 placeholder 路径细节

控制页"启动"按钮 → `run_controller.startRegular` → `scheduler.start_regular` →
`DeviceFactory.create_device_for_current_config`（Android 分支创建
`SelfAndroidDevice`，见 `iaa/platform/device_android/device.py`）→ scheduler
准备上下文并开始跑任务。

任务真正执行到 OCR（`kotonebot.backend.ocr.jp()`）时因
**`rapidocr_onnxruntime` 未打包**（文档化的后续项）抛
`ModuleNotFoundError`。该错误被 scheduler 捕获 → 停止 → 通过 GUI 弹窗
（"脚本运行失败" + 异常信息 + 取消/确认）呈现给用户，可正常关闭，进程不崩。
这验证了"设备 placeholder 不崩（含错误路径）"。

## 四、结论

非脚本 E2E 全部通过。本移植已达到：
**APK 编译 ✅ → 安装 ✅ → 启动 ✅ → GUI 各页面 ✅ → config/日志读写 ✅ →
设备 placeholder + scheduler 错误路径 ✅**

仅剩的已知缺口（均文档化为后续阶段）：
- `rapidocr_onnxruntime` / `onnxruntime` 未打包 → 实际跑任务（需 OCR）会失败
  （GUI 与错误处理正常，属预期）；
- `aarch64` 架构未构建；
- APK 体积（369MB）未瘦身；
- release 签名未做。

## 五、经验

- **Qt QML 控件在 uiautomator 里是可寻址的**（`content-desc` = 控件文本，
  bounds = 坐标），`uiautomator dump` 是 Android 上做 GUI E2E 的可行手段。
- GUI 的 config 读写回环可以直接用"点击 GUI → 检查 json 文件"验证，无需
  脚本级测试框架。
- 启动链错误路径（如缺 OCR）已被 scheduler 优雅处理，GUI 弹窗 + 进程存活；
  这是"placeholder 设备"设计能成立的底线。
