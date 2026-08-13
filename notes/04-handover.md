# Android 移植交接文档（checkpoint）

日期：2026-08-13
分支：`feat/p4a-android`（已推送 origin，工作树干净）
交接对象：下一位继续处理的 agent

## 一、当前总体状态

| 里程碑 | 状态 |
|---|---|
| 平台环境层 `iaa/platform/env.py`（app_root/数据目录/Android 检测） | ✅ 完成，桌面回归测试通过 |
| self placeholder 设备 + DeviceFactory 接入 | ✅ 完成，测试通过 |
| Qt GUI Android 适配（QGuiApplication/pynput 门控/QFileDialog） | ✅ 完成，测试通过 |
| p4a 构建链（main.py/pysidedeploy.spec/buildozer.spec/requirements/p4a.txt） | ✅ 完成 |
| GH Actions 编译（android-build.yml） | ✅ **APK 已成功产出并安装到模拟器** |
| 模拟器启动 | ❌ **启动即崩溃（Qt JNI null JavaVM）** |
| 非脚本 E2E | 未开始 |

## 二、已跑通的构建链（重要，不要重蹈覆辙）

最终能出 APK 的 CI 流程（`.github/workflows/android-build.yml`）关键点：

1. **runner 用 `ubuntu-22.04`**，不能用 24.04（libtool 2.4.7 移除 `LT_SYS_SYMBOL_USCORE` 宏，libffi autogen 失败）。
2. **pyside6-android-deploy 只跑一次**（pass1，`|| true` 容忍失败），它负责生成 `buildozer.spec` + `deployment/recipes` + `deployment/jar`；**随后用内联 python/configparser 补丁 spec**（并入 requirements、permissions、api、numeric_version、source.include_exts 加 ttf/txt）。
3. **pass2 用 `buildozer -v android debug` 直接构建**，**绝不能重跑 pyside6-android-deploy**（其 `cleanup()` 会 purge 掉补丁后的 spec）。
4. **sdkmanager legacy 软链**：buildozer 只认 `$SDK/tools/bin/sdkmanager`，cmdline-tools 装出来的是 `cmdline-tools/latest/bin`。软链要在 **pass2 前**才建，否则 pass1 内部的 buildozer 会真的去构建（浪费 20 分钟）。
5. **`android.numeric_version=2607`**：仓库版本号 `26.07b1` 非数值点分，p4a apk 打包必须显式 versionCode。
6. 系统依赖：openjdk-17 + rustup（pydantic-core recipe 用）+ ccache + autoconf automake libtool + zlib/ffi/ssl dev + ninja + meson。
7. PySide6 android wheel（`pyside6-6.11.1-...-cp311-cp311-android_x86_64.whl`）从 `download.qt.io` 下载，需缓存 + 重试（镜像偶发 SSL 断连）。
8. Python pin：`python3==3.11.9,hostpython3==3.11.9`（Qt android wheel 只有 cp311；p4a 默认 3.14 会冲突）。
9. **依赖取舍**（见 `requirements/p4a.txt`）：pydantic-core 用 p4a 内置 Rust recipe（pin 2.41.4 + pydantic==2.12.3）；opencv/numpy 用 recipe；onnxruntime/rapidocr/thefuzz 首版**不装**（启动链不 import，后续需要再走社区 recipe）；pynput/psutil 无 recipe 已排除。

产物：**`iaa-26.07b1-x86_64-debug.apk`（348MB）**，可从 GH Actions artifact `iaa-android-x86_64` 下载（最近一次成功 run：31661969780）。

## 三、当前阻塞问题：启动崩溃（下一步核心任务）

### 现象
- `adb install` 成功 → `am start -n org.iaa.iaa/org.kivy.android.PythonActivity` → 8 秒内 SIGSEGV。
- logcat crash buffer 关键栈：
  - `#00 libQt6Core_x86_64.so (QJniEnvironment::getJniEnv()+46)` → **null 指针解引用**（fault addr 0x0）
  - `#02 libQt6Quick_x86_64.so (JNI_OnLoad+67)`
  - `#23 org.qtproject.qt.android.QtLoader.loadLibraryHelper`
  - 线程名 `qtMainLoopThrea`（pid 3149/3251）
- 即：**Qt Java 侧在后台线程加载 libQt6Quick 时，JNI_OnLoad 里 QJniEnvironment() 拿到的 JavaVM 为空**。

### 已排查到的事实
1. p4a 的 `qt` bootstrap 的 `PythonActivity` 正确地 `extends org.qtproject.qt.android.bindings.QtActivity`（源码已确认：`pythonforandroid/bootstraps/qt/build/src/main/java/org/kivy/android/PythonActivity.java`）。
2. 工具生成的 spec 里 `p4a.extra_args = --qt-libs=... --load-local-libs=plugins_platforms_qtforandroid --init-classes=` —— **`--init-classes=` 是空的**。Qt 官方 deploy 的 `BuildozerConfig.__find_jars()` 会从 wheel 内 `*-android-dependencies.xml` 的 `<jar initClass="...">` 收集 init class，但我们这版似乎没收集到。
3. APK 内已含 `libQt6Core/Qml/Quick/...`、`libplugins_platforms_qtforandroid_x86_64.so`、`Qt6AndroidBindings.jar`（被打进 dex，deployment/jar 里有 5 个 Qt6Android jar）。
4. **下一步调研方向（未完成）**：
   - Qt 官方 `QtActivity`/`QtLoader` 在 onCreate 时如何 registerJavaVM；p4a qt bootstrap 是否依赖某个 **init class / AndroidManifest meta-data**（如 `android.app.lib_name`、`QtLoader` 启动类）。
   - 对比 EchterAlsFake/PySide6-to-Android 与官方 `pyside6-android-deploy` 产物的 AndroidManifest 差异（尤其 application android:name 是否是 `org.qtproject.qt.android.bindings.QtApplication`、activity 是否要换成 QtActivity）。
   - p4a `--init-classes` 的正确取值（Qt 官方工具通常写 `org.qtproject.qt.android.bindings.QtActivity` 或 loader 类）。
   - 可能根因：Qt 6.11 的 QtLoader 需要应用级 `QtApplication` 或 `QtActivity.onCreate` 先调用 `QtNative.registerJavaVM()`；p4a bootstrap 可能少配了 application 类或 meta-data。

### 本地可用的调试手段
- 模拟器 adb：`adb -s 127.0.0.1:5557 shell ...`（设备 SM-S9110 x86_64 API35，`sys.boot_completed=1`）。
- 抓日志：`adb logcat -c` → `am start` → `adb logcat -d -b crash` / `-b main`。
- 产物 APK 已解包在 `%TEMP%\opencode\apk-unzip`（lib/ 内容已看）；wheel 未成功下载到本地（curl 写了空文件），但 CI 有缓存。
- 桌面回归验证：`& .venv\Scripts\python.exe -m pytest tests/test_env.py tests/test_self_android.py tests/test_android_imports.py -q`（24 passed）。

## 四、未开始/未完成的事项
- [ ] **修复 Qt 启动崩溃**（上述，当前最高优先级）。
- [ ] 启动成功后：验证 `env.app_root()`（ANDROID_PRIVATE 路径）、logs/conf 落盘位置。
- [ ] 非脚本 E2E：GUI 页面能打开（总览/设置/偏好）、config 读写、日志显示、设备 placeholder 不崩。
- [ ] 若 GUI 无法点亮（QML 模块不全、Fluent 样式、字体），按崩溃堆栈迭代。
- [ ] 后续：onnxruntime/rapidocr、grpcio/av、aarch64、APK 瘦身、release 签名。

## 五、其他备忘
- `notes/00-overview.md`（总览+调研结论）、`notes/01-platform-boundaries.md`（平台边界盘点）、`notes/03-build-infra.md`（构建链详细设计+坑清单）已就绪；`notes/02-*` 空位（原计划放构建过程的，可跳过或补充）。
- 桌面构建链（build.py/tools/build/）未受影响。
- 变更文件清单：`iaa/platform/**`（新）、`iaa/application/qt/**`（index/controllers/app_controller/run_controller/virtual_device_session）、`iaa/application/service/**`（iaa_service/config_service/assets_service/device_factory）、`iaa/input.py`、`iaa/utils.py`、`iaa/telemetry.py`、`iaa/application/cli/index.py`、`main.py`、`buildozer.spec`、`pysidedeploy.spec`、`requirements/p4a.txt`、`.github/workflows/android-build.yml`、`tests/test_env.py`、`tests/test_self_android.py`、`tests/test_android_imports.py`、`.gitignore`。
- CI 迭代技巧：改 workflow 后 push 到分支即自动触发（workflow_dispatch 在默认分支才可见，所以配了 push 触发）。
