# Qt 启动崩溃（SIGSEGV in JNI_OnLoad）根因分析与修复

日期：2026-08-13
分支：`feat/p4a-android`

## 一、现象

`am start -n org.iaa.iaa/org.kivy.android.PythonActivity` 后 8 秒内 SIGSEGV。

logcat crash buffer 关键栈：

```
#00 libQt6Core_x86_64.so (QJniEnvironment::getJniEnv()+46)   → null 解引用（fault addr 0x0）
#02 libQt6Quick_x86_64.so (JNI_OnLoad+67)
#23 org.qtproject.qt.android.QtLoader.loadLibraryHelper
线程名：qtMainLoopThrea
```

## 二、根因（已确认，非猜测）

### JNI 加载机制的三个事实

1. **JavaVM 全局指针只由 libQt6Core 注册**
   - `qtbase/src/corelib/kernel/qjnihelpers.cpp`：
     - `static JavaVM *g_javaVM = nullptr;`
     - `QtAndroidPrivate::initJNI(vm, env)` 中 `g_javaVM = vm;`（第 281 行）
     - `JNI_OnLoad`（第 482 行起）调用 `QtAndroidPrivate::initJNI(vm, env)`
   - `qjnienvironment.cpp:69`：`QJniEnvironment::getJniEnv()` 读 `QtAndroidPrivate::javaVM()` → `g_javaVM`，随后 `vm->GetEnv(...)`。

2. **JVM 只对“显式加载”的库调用 JNI_OnLoad**
   - `System.load(path)` / `System.loadLibrary(name)` 显式加载的库才会触发 `JNI_OnLoad`；
   - 库通过 dlopen 自动拉入的**依赖库不触发 JNI_OnLoad**（JNI 规范行为）。
   - 因此：`libQt6Quick` 被 `System.load` 时，JVM 只调 `libQt6Quick.JNI_OnLoad`，
     `libQt6Core`（作为依赖被 dlopen）的 `JNI_OnLoad` 不会执行 → `g_javaVM` 仍是 null。

3. **APK 内 qt_libs 加载顺序错误**
   - p4a qt bootstrap 模板 `bootstraps/qt/build/templates/libs.tmpl.xml` 把
     `qt_libs` 数组按 `p4a.extra_args --qt-libs` 原样写出（`common/build/build.py:690`）；
   - `QtLoader.loadQtLibraries()` 按数组顺序 `System.load`。
   - 实测 APK（`aapt dump --values resources`）里数组顺序：
     ```
     c++_shared, Qt6Quick, Qt6Core, Qt6QuickControls2, Qt6Network, Qt6Qml,
     Qt6Widgets, Qt6Gui, Qt6OpenGL
     ```
     → **Qt6Quick 排在 Qt6Core 之前**，先加载 → 其 JNI_OnLoad 里 `getJniEnv()` 读到空 `g_javaVM` → SIGSEGV。

### 顺序为什么会错

`pyside6-android-deploy`（Qt for Python 6.11.1）生成 `--qt-libs` 时：
`deploy_lib/android/android_config.py` 里 `self.modules = list(set(modls))` ——
**用 set 去重 → 顺序是 Python 集合的随机哈希序**。本次恰好 `Quick` 在 `Core` 前。

工具生成的 `buildozer.spec` 中：
```
p4a.extra_args = --qt-libs=Quick,Core,QuickControls2,Network,Qml,Widgets,Gui,OpenGL --load-local-libs=... --init-classes=
```

## 三、修复方案

**在 workflow 补丁步骤（Merge iaa requirements）里强制把 `Core` 排到 `--qt-libs` 首位。**

理由：
- `g_javaVM` 只需 `libQt6Core.JNI_OnLoad` 运行一次；
- 只要 `Core` 是第一个 `System.load` 的 Qt 库，其 JNI_OnLoad 先执行并注册 JavaVM，
  后续所有模块（都依赖 Core）的 JNI_OnLoad 里 `getJniEnv()` 就能拿到有效指针；
- 其余模块顺序无所谓（依赖由 dlopen 自动解析，且它们不负责注册 JavaVM）。

最小改动：patch 脚本中 `--qt-libs` 列表 `['Core'] + [非 Core 的其余模块]`。

## 四、验证手段

- 重新跑 GH Actions（push 即触发）。
- 产物 APK 用 `aapt dump --values resources` 核对 `array/qt_libs` 首项是否为 `Core`。
- 安装到 127.0.0.1:5557 后 `am start`，观察 logcat 是否还崩；
  若通过 QtCore 阶段，后续可能是 QML 模块/字体等新问题（按堆栈继续迭代）。

## 五、附：为什么 --init-classes 为空不是问题

- Qt 6.11.1 android wheel 内的 `*-android-dependencies.xml` 均无 `<jar initClass="...">` 属性
  （已核对 Qt6Core/Quick/Gui/Qml 等全部 24 个 xml）→ 工具收集不到 init class 是**正常**的。
- 本应用 Qt Java 侧启动不依赖 `--init-classes`（它是 p4a 用于"额外 Java 类静态初始化"的钩子），
  Application/Activity 类已在 manifest 里显式配置为 Qt 绑定类，JavaVM 注册走 libQt6Core 的 JNI_OnLoad。
