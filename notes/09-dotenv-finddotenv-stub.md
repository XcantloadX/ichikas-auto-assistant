# dotenv.find_dotenv 栈回溯崩溃（p4a .pyc 帧 co_filename 指向不存在的构建机路径）

日期：2026-08-14
分支：`feat/p4a-android`
构建：31795031244（push 87cc2c4 触发）

## 一、现象

android 包桩（见 08）修复后，run 31792096948 的 APK 上机，启动 logcat 报：

```
Traceback (most recent call last):
  File ".../main.py", line 21
  File ".../iaa/application/qt/__init__.py", line 1
  File ".../iaa/application/qt/index.py", line 3
  File ".../iaa/application/qt/controllers/__init__.py", line 1
  File ".../iaa/application/qt/controllers/app_controller.py", line 12
  File ".../iaa/application/service/iaa_service.py", line 11
  File ".../iaa/application/service/config_service.py", line 3
  File ".../kotonebot/__init__.py", line 37
  File ".../kotonebot/ui/user.py", line 19
  File ".../kotonebot/ui/pushkit/__init__.py", line 2
  File ".../kotonebot/ui/pushkit/wxpusher.py", line 5
  File ".../kotonebot/ui/pushkit/image_host.py", line 11
  File ".../dotenv/main.py", line 419, in load_dotenv
  File ".../dotenv/main.py", line 364, in find_dotenv
AttributeError: 'NoneType' object has no attribute 'f_code'
```

即：上一轮的 android 包桩有效、`ctypes.util` 那关过了，import 链推进到
`kotonebot.ui.pushkit`（模块级 `load_dotenv()`），在 `find_dotenv` 处崩。

## 二、根因

- `kotonebot/ui/pushkit/image_host.py` **模块级**调用 `load_dotenv()`（无参），
  `python-dotenv` 的 `find_dotenv()` 会：
  1. `frame = sys._getframe()` 取当前帧；
  2. 沿 `f_back` 一路向上，找 `co_filename` **真实存在于磁盘**的调用者帧，
     以推导出调用者的工作目录来定位 `.env`。
- p4a 打包的是**预编译 `.pyc`**：每个帧的 `co_filename` 都是**构建机路径**
  （`/home/runner/work/_temp/iaa-app/...`），在设备上**不存在**。
- 于是 while 循环永远满足"该文件不存在"，一路走到栈顶（`__main__` 帧），
  其 `f_back is None`；循环继续 `frame = frame.f_back` 得到 `None`，
  再访问 `frame.f_code` → `AttributeError: 'NoneType' object has no attribute
  'f_code'`。

本地桌面不崩：桌面有真实 `.py` 文件，`co_filename` 存在，栈回溯能停下。

## 三、方案：android_stubs 替换 find_dotenv 为 Android 安全实现

- `iaa/platform/android_stubs.py` 新增 `install_dotenv_find_stub()`：把
  `dotenv.main.find_dotenv` 替换为一个恒返回 `''` 的实现（不遍历调用栈）。
- 为什么 `''` 安全：`load_dotenv()` 拿到空路径后，`DotEnv._get_stream` 里
  `if self.dotenv_path and os.path.isfile(...)` 直接跳过文件读取，等价于
  "找不到 .env"，不会抛错。Android 上没有 `.env` 需要加载（pushkit 仅桌面
  推送用）。
- 桌面不替换：桌面有真实文件系统与 `.env`，保留原始语义。
- `install_android_stubs()` 现依次装：cv2.typing 桩 + android 包桩 +
  dotenv.find_dotenv 桩。`main.py` 仍在任何 kotonebot/iaa import 之前调用。

## 四、验证

- 本地单测：`tests/test_android_imports.py` 新增 `DotenvFindStubTests`，
  验证 `is_android=True` 时 `find_dotenv()` 返回 `''` 且 `load_dotenv()`
  不抛错。
- `tests/test_android_imports.py` = **8 passed**。
- 待重新构建 APK 上机验证（构建 31795031244）。

## 五、经验

- p4a 打包的 **`.pyc` 帧 `co_filename` 指向构建机路径**，是比"缺包"更隐蔽
  的一类问题：任何"沿调用栈做文件存在性判断"的第三方库（python-dotenv 的
  `find_dotenv` 是典型）都会在 Android 上异常。排查标志：报错里的源码路径
  是 `/home/runner/...` 等 CI 构建机路径。
- 这类问题的通用兜底：在入口（`main.py` → `android_stubs`）把该库的对应
  函数替换为 Android 安全实现；库的真实语义在 Android 上不成立时直接给
  一个"什么都不做"的版本即可。
- 逐层剥洋葱：本轮的 import 链修复轨迹为
  Qt JNI → cv2.typing → mouse/ctypes.util(android 包) → dotenv.find_dotenv，
  每一层都需要重新构建 APK（~25min）上机验证。
