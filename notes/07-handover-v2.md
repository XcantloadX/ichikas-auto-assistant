# Android 移植交接文档 v2（checkpoint）

日期：2026-08-13（第二次交接）
分支：`feat/p4a-android`（本地有三处未提交修改，见文末）
交接对象：下一位继续处理的 agent

## 一、当前总体状态

| 里程碑 | 状态 |
|---|---|
| 平台环境层 `iaa/platform/env.py` | ✅ 桌面回归测试通过 |
| self placeholder 设备 + DeviceFactory 接入 | ✅ 测试通过 |
| Qt GUI Android 适配（QGuiApplication/pynput 门控/QFileDialog） | ✅ 测试通过 |
| p4a 构建链（main.py/pysidedeploy.spec/buildozer.spec/requirements/p4a.txt） | ✅ 完成 |
| GH Actions 编译 | ✅ 可稳定产出 APK（每次 ~25-28min） |
| 模拟器启动 | 🔶 **已修两层启动崩溃，正在清第三层 Python import 链** |
| 非脚本 E2E | 未开始 |

### 启动崩溃的修复进度（从根因→当前）

已修复并**验证**（前两层已在模拟器实机验证）：

1. **Qt JNI SIGSEGV（g_javaVM 为空）** ✅ 已实机验证通过
   - 根因：`pyside6-android-deploy` 用 `list(set(...))` 生成 `--qt-libs` 顺序随机；
     APK 里 `Qt6Quick` 排在 `Qt6Core` 前，JVM 只对 System.load 的库调 JNI_OnLoad，
     Qt6Core 的 JNI_OnLoad（注册全局 JavaVM）尚未执行 → `getJniEnv()` 空指针崩溃。
   - 修复：workflow 补丁步骤强制 `Core` 排到 `--qt-libs` 首位。
   - 详见 `notes/05-root-cause-jni.md`。实机：QtCore `Start` 日志出现，不再 SIGSEGV。

2. **cv2.typing 缺失（`'cv2' is not a package`）** ✅ 已实机验证通过
   - 根因：p4a opencv recipe 只装单个 `cv2.so`（`OPENCV_SKIP_PYTHON_LOADER=ON`），
     无桌面 wheel 的纯 Python `cv2/typing` 子包；kotonebot/iaa 27+ 模块顶部
     `from cv2.typing import MatLike`（仅注解用）。
   - 修复：新增 `iaa/platform/android_stubs.py`，`main.py` 在任何 iaa import 前
     注册 `cv2.typing` 桩到 `sys.modules`。
   - 详见 `notes/06-cv2-typing-stub.md`。实机：import 链推进到 `mouse`。

3. **`mouse` 缺失 + 控制层 adbutils 链（当前进行中，未推送）**
   - 现象（run 31668320869 实机）：`kotonebot/interop/win/_mouse.py` → `import mouse`
     → `ModuleNotFoundError`。
   - 后续推演（本地 Android 模拟 import 验证）还会撞到：
     `device_factory` → `avd/custom_emulator` → `kotonebot.host.adb_common` → `adbutils`
     （`MissingDependencyError`），以及 `tasks/live/auto_live_core` → `mumu12_host` → `adbutils`。

## 二、当前未提交的修改（本 agent 的最后工作，需 push + 重新编译验证）

工作树有三处修改（`git status` 可见，**尚未 commit/push**）：

1. `requirements/p4a.txt`：新增 `mouse`（纯 Python，pip --no-deps 可装；其模块级
   只实例化 listener 不启动线程，Android import 安全）。
2. `iaa/application/service/device_factory.py`：桌面控制层（`avd`/`custom_emulator`
   → adbutils）改为模块级平台门控 `if not env.IS_ANDROID:` 导入；Android 分支用
   `_UnavailableOnAndroid` 兜底（误触达时抛明确错误）。桌面路径保持原行为。
3. `iaa/tasks/live/auto_live_core.py`：`mumu12_host` 导入改为方法内惰性导入
   （仅桌面联调脚本使用）。

**本地验证结果**：
- Android 模拟 import 全链通过（`ANDROID_PRIVATE` + 屏蔽 p4a 排除包后
  `import iaa.application.qt.index` 成功，含 cv2.typing 桩 + mouse stub）。
- 桌面回归：`tests/test_self_android.py test_device_factory.py test_android_imports.py
  test_qt_auto_live.py test_env.py` = **28 passed**。
- `tests/test_qt_settings.py` **收集期报错**（`MuMuEmulatorData` 导入失败）——
  **在 base commit 上同样报错，与本轮改动无关**，可忽略或另行修复。

**下一步（交接后第一件事）**：
1. `git add` + commit + push 上述三处修改 → 触发 GH Actions（run 预计 ~25min）。
2. `gh run watch` 等编译成功 → 下载 `iaa-android-x86_64` artifact。
3. 安装到模拟器：先 `adb uninstall org.iaa.iaa`（APK 365MB，直接 `-r` 会
   `INSTALL_FAILED_INSUFFICIENT_STORAGE`），再 `adb install`。
4. `adb logcat -c` → `am start -n org.iaa.iaa/org.kivy.android.PythonActivity` →
   观察是否还有下一个 `ModuleNotFoundError`。
5. 若还有新 import 缺失，按 `notes/06-cv2-typing-stub.md` 第五节的经验处理：
   - 纯 Python 包 → 加进 `requirements/p4a.txt`；
   - 纯 Python 子包/注解常量 → `android_stubs.py` 追加桩；
   - 桌面控制层死代码 → 参考 device_factory 的平台门控。

## 三、已跑通的构建链要点（不要重蹈覆辙）

1. **runner 用 `ubuntu-22.04`**（24.04 libtool 2.4.7 缺 `LT_SYS_SYMBOL_USCORE`）。
2. **pyside6-android-deploy 只跑一次**（pass1，`|| true`），生成 buildozer.spec +
   deployment/；随后内联 python/configparser 补丁 spec。
3. **pass2 用 `buildozer -v android debug` 直接构建**，绝不能重跑 deploy
   （其 cleanup() 会 purge 补丁后的 spec）。
4. sdkmanager legacy 软链在 **pass2 前**才建。
5. `android.numeric_version=2607` 必须显式（版本号 26.07b1 非数值点分）。
6. 系统依赖：openjdk-17 + rustup（pydantic-core recipe）+ ccache + autoconf automake
   libtool + zlib/ffi/ssl dev + ninja + meson。
7. PySide6 android wheel 从 download.qt.io 下载需缓存 + 重试。
8. Python pin：`python3==3.11.9,hostpython3==3.11.9`。
9. **`--qt-libs` 顺序修复已固化在 workflow 补丁步骤**（强制 Core 首位）。

产物：`iaa-26.07b1-x86_64-debug.apk`（365MB）。最近成功 run：31668320869。

## 四、未开始/未完成事项

- [ ] push 本轮三处修改并重新编译、实机验证启动。
- [ ] 启动成功后：验证 `env.app_root()`（ANDROID_PRIVATE 路径）、logs/conf 落盘位置。
- [ ] 非脚本 E2E：GUI 页面能打开（总览/设置/偏好）、config 读写、日志显示、
      设备 placeholder 不崩（task 列表页会触发 `iaa.tasks.registry` → 已做惰性化）。
- [ ] 若 GUI 无法点亮（QML 模块不全、Fluent 样式、字体），按崩溃堆栈迭代。
- [ ] 后续：onnxruntime/rapidocr、grpcio/av、aarch64、APK 瘦身、release 签名。

## 五、其他备忘

- notes/：`00-overview.md`（总览）、`01-platform-boundaries.md`（边界盘点）、
  `03-build-infra.md`（构建链）、`04-handover.md`（交接 v1）、
  `05-root-cause-jni.md`（Qt 崩溃根因+修复）、`06-cv2-typing-stub.md`（cv2.typing 桩）。
  本轮控制层门控经验建议补充到 06 或新建 07。
- 桌面构建链（build.py/tools/build/）未受影响。
- 本机调试手段：adb 127.0.0.1:5557（SM-S9110 x86_64 API35）；产物解包目录
  `%TEMP%\opencode\apk5-unzip`；已下载 wheel `%TEMP%\opencode\pyside6-6111-android.whl`、
  p4a 源码 `%TEMP%\opencode\p4a-src`、qtbase 源码 `%TEMP%\opencode\qtbase-src`。
- CI 迭代技巧：改 workflow 后 push 即自动触发。