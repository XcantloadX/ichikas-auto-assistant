# iaa Android 移植总览

日期：2026-08-13
分支：`feat/p4a-android`

## 目标

将 iaa（PySide6 + QML 桌面游戏自动化助手）借助 python-for-android/ 完整移植到 Android。
模拟点击 / adb 等控制层本次**不做**，采用 placeholder。GUI（PySide6 QML）必须一并移植。

## 关键调研结论

### 技术路线：p4a `qt` bootstrap + `pyside6-android-deploy`

- p4a 主仓库**没有** `pyside6/pyqt5/pyqt6` 静态 recipe。
- 但自 Qt 6.6+，Qt 官方把 **p4a `qt` bootstrap** 并入了 python-for-android 主线，
  PySide6/shiboken6 的 recipe 由 `pyside6-android-deploy` 工具**动态生成**。
- 因此 **Qt 官方 Android 工具链本身就是 p4a + buildozer**，满足本项目强绑定 p4a 的要求：
  `pyside6-android-deploy` → 生成 `buildozer.spec` → buildozer → p4a `qt` bootstrap。
- 官方文档：
  - https://doc.qt.io/qtforpython-6/deployment/deployment-pyside6-android-deploy.html
  - https://python-for-android.readthedocs.io/en/latest/buildoptions.html
  - https://www.qt.io/blog/taking-qt-for-python-to-android

### 硬约束

| 约束 | 值 |
|---|---|
| 宿主 OS | 仅 Linux / macOS（Windows 不可原生跑）→ 用 GitHub Actions `ubuntu-latest` |
| 入口文件 | 必须叫 `main.py` |
| Python 版本 | 仅 3.10 / 3.11 |
| 架构 | 官方仅 aarch64 + x86_64（x86 需自编译） |
| 多架构 | `qt` bootstrap 不支持单次多架构 |
| Android wheel | PySide6 6.8+ 官方发布 android_aarch64 / android_x86_64 wheel（Qt 下载站 / qtpip） |
| 目标模拟器 | 127.0.0.1:5557，SM-S9110，API 35，**x86_64** → 构建 x86_64 |

### 当前设备状态

- 已连接 adb 设备：`127.0.0.1:5557`（SM-S9110, Android 15/API 35, x86_64）
- 本机是 Windows → 只能用 GH Actions 编译，产物下载回本机 adb install。

## 代码库关键事实（探索 agent 结论摘要）

1. **iaa 是"控制方"架构**：`SchedulerService → DeviceFactory → kotonebot(adb/scrcpy/uiautomator2)` 遥控游戏设备。
   Android 移植后 iaa 变成"被自动化的一方"，控制层整条链不可用 → 需自建设备 placeholder。
2. **import 即失败的硬点**（平台无关代码）：
   - `public/qa` `global_hotkey_controller.py:5` 无门控 `from pynput import keyboard` → Android 无 pynput。
   - QtWidgets `QApplication`/`QFileDialog`（Android Qt 无 widgets 模块）→ 应换 `QGuiApplication`。
3. **路径假设全坏**：
   - `IaaService.app_root()` 基于 `sys.executable`；
   - `utils.asset_path()` 用 cwd 相对 `./assets`；
   - `config.manager.config_path` 默认 `./conf`（运行时被覆盖为 `app_root()/conf`）；
   - Android 应改用 p4a 的 `ANDROID_APP_PATH` 等私有目录。
4. **QML 加载**：`QQmlApplicationEngine` + `__file__` 推导绝对路径加载 `MainWindow.qml`，相对 import 依赖 qml 目录原样进包
   （无 .qrc，需把 `iaa/application/qt/qml/`、`iaa/application/framework/dsl/qml/` 打进 APK）。
5. **C 扩展依赖**：onnxruntime(p4a 有 recipe)、opencv、numpy(有 recipe)、pydantic-core(纯 rust 预编译 wheel 需验证)。
   桌面 pyproject 里的 win_amd64 专用 wheel 对 Android 完全不可用。

## 移植决策

- 新增 `iaa/platform/env.py` 统一 app_root/data_dir/asset_path（桌面 + android 双实现）。
- `DeviceFactory.create_device` 加 `self_android` 分支（placeholder 设备）。
- 剥离 pynput：Android 上全局热键用空 stub。
- Qt 入口 Android 分支：`QGuiApplication` + 平台门控。
- 新增 `main.py`（p4a 入口）、`buildozer.spec`、GH Actions android workflow。
- 文本输入走系统 IME（Qt 在 Android 自动挂钩原生软键盘）。

## 遗留风险

- pydantic-core 在 Android 的可用性（需 p4a 构建时验证）。
- APK 体积（PySide6 全量偏大，需裁剪）。
- onnxruntime Android wheel 与 1.14.0 版本差异。