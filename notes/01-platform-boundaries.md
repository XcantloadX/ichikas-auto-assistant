# 平台边界盘点（探索 agent 输出转存）

来源：对 `feat/p4a-android`（基于 release/26.07）的代码库快速盘点，2026-08-13。

## 核心矛盾

iaa 当前是"PC 上的控制方"（SchedulerService → DeviceFactory → kotonebot AndroidDevice 遥控真机/模拟器）。
移植 Android 后 iaa 是"被自动化的一方"（自己跑在游戏同一设备上），
`DeviceFactory`/`host`/`implements` 链路在设备上不可用，需要一个新的"自身设备"（Self Device）placeholder。

## 各层问题汇总

### 1. sys.platform 分支（大多安全）
- `launch_desktop.py:7-8` os.name=='nt' pause —— 桌面入口，Android 不用。
- `qt/index.py:28-35` win32 模块级条件导入 —— 安全。
- `qt/index.py:116-119` `hwnd = int(window.winId())` + NativeEventFilter —— 需 Android 门控。
- `app_controller.py:58-65` `_get_window_title` 三分支 —— 需加 Android。
- `screen_recorder.py`: platform.system() != 'Windows' 提前返回 —— 设备上禁录屏。
- `global_hotkey_controller.py:5` **无门控 `from pynput import keyboard`** —— import 即崩溃，必须处理。

### 2. Windows 专用依赖
- **pynput**（模块级 import）→ Android 硬失败点。AppController 依赖链必然带上它（controllers/__init__.py:10）。
- platform_win32.py（DWM 无边框样式）整文件只在 win32 引入 —— 可保留。
- plyer 通知有 android 后端，可反向利用。
- opencv/numpy/av 的 win_amd64 wheel 对 Android 不可用，p4a 走各自 recipe。
- onnxruntime 1.14.0 需 p4a/android 对应版本。

### 3. adb/scrcpy/模拟器控制层（Android 上全部失效）
- `iaa/input.py` AdbKeyboardInput、`iaa/context.py:73-81` —— 输入层需 placeholder。
- `device_factory.py:127-177` create_device 六种 impl —— **最自然插入点**（加 `self_android` 分支）。
- `scheduler.py` `_setup_resolution`/`__prepare_context`、`virtual_device_session.py`（预览）、
  `tasks/start_game.py`、`game_ui/*`（编辑工具）—— 全部控制方视角。
- kotonebot `implements/__init__.py` 无设备内 backend，只有 adb/scrcpy/uiautomator2（遥控）。
- Kotonebot 的 `AndroidCommandable`/`Screenshotable`/`TouchDriver` protocol 接口可供"自身设备"实现。

### 4. 文件路径假设
- `iaa_service.py:84-90` `app_root()` 基于 sys.executable —— Android 上指向解释器目录，须重设计。
- `cli/index.py:23-26` 同逻辑。
- `telemetry.py:16-28` 用 sys.executable 判断 is_dev —— p4a 下可能误判为 dev。
- `config/manager.py:36` `config_path='./conf'` 模块级 cwd 相对路径（运行期被 config_service 覆盖为 app_root/conf）。
- `utils.py:39-42` asset_path 用 `./assets` cwd 相对 —— Android 直接失败。
- `utils.py:9-37` sprite_path 的 p4a 兜底是 `importlib.resources('iaa.res')`（靠谱）。
- `screen_recorder.py:103` `Path('dumps/screen_records')`、`_dump_sekai_home.py` 等（开发工具任务）。

### 5. QML 资源加载
- `qt/index.py:109-110`：`engine.load(QUrl.fromLocalFile(qml/MainWindow.qml))`，基于 `__file__` 绝对路径，**无 .qrc**。
- `qmldir` 声明 6 个 QML 单例；`import IaaApp 1.0` 由 Python `qmlRegisterSingletonType` 提供。
- 需把 `iaa/application/qt/qml/` 与 `iaa/application/framework/dsl/qml/` 打进 APK（相对 import 自动解析）。
- `MainWindow.qml:16-23` 用 `Qt.platform.os` 分支字体（Noto Sans CJK 兜底，Android 可取）。
- `QQuickStyle.setStyle("FluentWinUI3")` 需随包带 Style QML（Qt 6.8+ 支持全平台）。

### 6. 启动依赖链
launch_desktop → qt.index.main()；launch_cli → cli 链。qt/index 的 import 链：
LogBridge → PySide6 → iaa.config → IaaService → qt/controllers(→**pynput**) → tasks/registry(→iaa.tasks.R 资源断言)。
真正 import 即失败：①pynput ②QtWidgets(QApplication)。其余平台逻辑都能延迟到运行时。

### 7. Config manager 与存储
- JSON 文件，模块级可变 `config_path`，运行时被 ConfigService 覆盖为 app_root/conf。
- Android 方案：入口把 config_path 指向可写私有目录，业务层零改动。
- 含 ProfileV1..V4 / SharedV1..V2 迁移链。

### 8. 构建系统
- pyproject/uv.lock/justfile 桌面专用；`build.py`(PyInstaller)/tools/build 桌面专用。
- 需新增 p4a：`buildozer.spec` + `main.py` + 独立 workflow（ubuntu runner）。
- `requires-python = "~=3.10.0"` 需放宽到 3.11（p4a 主流实际是 3.11 recipe）。

### 9. kotonebot 对 Android
- extra "android" 指"被控对象是 Android"，不是"运行在 Android 上"（adbutils/uiautomator2/av）。
- `client/protocol.py` 提供 protocol 接口；`util.py` 只有 is_windows/is_linux/is_macos，无 is_android。
- kaa 含 AutoHotkey.exe（win）/OCR onnx 模型（可打包资源）。

### 10. 测试
- 可复用：config 迁移链、表单 DSL、图片 provider（纯逻辑）。控制层测试作废。

## 建议新增文件
```
iaa/platform/__init__.py
iaa/platform/env.py                 # app_root()/data_dir()/asset_path()/logs_dir()（桌面+android）
iaa/platform/qml_loader.py
iaa/platform/device_android/        # self_android placeholder（Screenshot/Touch/Command）
main.py                             # p4a 入口
buildozer.spec                      # p4a 配置
.github/workflows/android-build.yml
```