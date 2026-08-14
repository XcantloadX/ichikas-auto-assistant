# 缺失 android 包导致 ctypes.util 导入失败（p4a 补丁后 stdlib 依赖 android recipe）

日期：2026-08-14
分支：`feat/p4a-android`
构建：31792096948（push a9a1b30 触发）

## 一、现象

run 31787887069 的 APK 上机（模拟器 127.0.0.1:5557，`adb uninstall` 后重装）启动，
logcat 报：

```
ModuleNotFoundError: No module named 'android'
  File ".../main.py", line 21, in <module>
  File ".../iaa/application/qt/__init__.py", line 1
  File ".../iaa/application/qt/index.py", line 3
  File ".../iaa/application/qt/controllers/__init__.py", line 1
  File ".../iaa/application/qt/controllers/app_controller.py", line 12
  File ".../iaa/application/service/iaa_service.py", line 11
  File ".../iaa/application/service/config_service.py", line 3
  File ".../kotonebot/__init__.py", line 35
  File ".../kotonebot/backend/bot.py", line 11
  File ".../kotonebot/client/host/__init__.py", line 3
  File ".../kotonebot/client/host/protocol.py", line 10
  File ".../kotonebot/interop/win/_mouse.py", line 5
  File ".../mouse/__init__.py", line 54
  File ".../mouse/_nixmouse.py", line 9
  File ".../python3/Lib/ctypes/util.py", line 11
```

即：上一轮补的 `mouse` 已随包打进去、import 链推进到 `ctypes.util`，在这里断。

## 二、根因

- p4a 会**打补丁改写 stdlib `ctypes/util.py`**（`python3/patches/cpython-311-ctypes-find-library.patch`），
  把 `find_library` 全部替换为：

  ```python
  from android._ctypes_library_finder import find_library as _find_lib
  def find_library(name):
      return _find_lib(name)
  ```

- `android` 包是 p4a 的**一个 recipe**（`pythonforandroid/recipes/android`），
  其 `_ctypes_library_finder` 用 pyjnius 查 Activity 的 nativeLibraryDir。
  该 recipe `depends = [('sdl3','sdl2','genericndkbuild'), 'pyjnius']`，
  需要 sdl/python 启动器环境 —— **qt bootstrap 构建默认不含它**。
- 因此只要是任何代码 `import ctypes.util`（本例是纯 Python `mouse` 包的
  `_nixmouse.py`），在 p4a Android 上都会触发 `import android` 失败，进而
  拖垮 `kotonebot.interop.win._mouse` 的整条导入链。

## 三、方案：android_stubs 追加 android 包桩

- `iaa/platform/android_stubs.py` 新增 `install_android_package_stub()`：
  注册 `android` 与 `android._ctypes_library_finder` 两个 `types.ModuleType`
  到 `sys.modules`，桩的 `find_library` 是**纯文件系统实现**
  （`_find_library`：扫 `/system/lib64`、`/system/lib`、`LD_LIBRARY_PATH`，
  按 `lib<name>.so` / `<name>.so(.n)` 形态匹配，找不到返回 `None`），
  不依赖 pyjnius / sdl。
- 为什么不引真实 android recipe：真实实现依赖 pyjnius，且 iaa 在 Android 上
  不做模拟点击/输入（该链路是 placeholder），不需要 pyjnius 的 JNI 能力；
  `env.py` 等平台层只用 `os.environ` / `importlib.resources`，不依赖
  `android` 包。桩语义足够且侵入最小，与 06 的 cv2.typing 桩一脉相承。
- `install_android_stubs()` 现在依次装 cv2.typing 桩 + android 包桩；
  `main.py` 仍在任何 kotonebot/iaa import 之前调用，保证早于
  `import ctypes.util` 的所有触发点。

## 四、验证

- 本地单测：`tests/test_android_imports.py` 新增 `AndroidPackageStubTests`，
  验证 `from android._ctypes_library_finder import find_library` 可导入、
  幂等、`_find_library` 对不存在的库返回 `None`。
- `tests/test_self_android.py test_device_factory.py test_android_imports.py
  test_qt_auto_live.py test_env.py` = **30 passed**（此前 28 + 新增 2）。
- 待重新构建 APK 上机验证（构建 31792096948）。

## 五、经验

- p4a 的补丁会改写 **stdlib** 模块（不止 recipe 缺包），如 `ctypes/util.py`。
  这类 stdlib 改动无法用"requirements 加包"补，只能：
  - 引对应 recipe（本案例 android recipe 依赖 pyjnius，重）；
  - 或 `sys.modules` 桩（本案例采用，零 JNI 依赖）。
- 判断桩是否够用的依据：目标包是否只在"可能根本不执行的死链路"里被 import
  （`mouse` 是 Windows 输入专用，Android 上仅是 `kotonebot.interop.win` 的
  注解/占位用途），以及 iaa 平台层是否真的用到该包的真实 API。
- 若未来引入 pyjnius/plyer 等真正要用 JNI 的场景，可再升级为真实 android
  recipe，桩与真实包可共存（先桩后真，`sys.modules` 以先到者为准）。
