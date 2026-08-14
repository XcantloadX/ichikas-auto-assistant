# Android GUI 启动成功（里程碑）：构建链 + 启动链全部打通

日期：2026-08-14
分支：`feat/p4a-android`
构建：31799130972（push 06b696b 触发，23m16s success）
产物：`iaa-26.07b1-x86_64-debug.apk`（369MB，含资源后比上版 +4MB）

## 一、结果

**应用在模拟器（127.0.0.1:5557，SM-S9110 x86_64 API35）上成功启动，QML GUI 正常运行
（人工确认截图）。** 这是本移植项目的首个"能点亮 GUI"里程碑。

启动链路验证（logcat）：
- Python for Android 初始化成功；
- 应用进程稳定存活（pid 5833 从 20:37 到 20:45 无崩溃，被用户手动停止）；
- QML 引擎正常加载 QtQuick Controls 插件（Basic/Fusion/Layouts/Templates/Window）；
- 应用自动创建了 `files/app/conf/123.json`、`_shared.json` 与
  `files/app/logs/2026-08-14-20-44-26.log` —— `env.app_root()` 正确解析到
  `ANDROID_PRIVATE`（`/data/user/0/org.iaa.iaa/files/app`），config 读写与
  日志落盘均正常。

## 二、本轮（自 07 交接以来）修复的启动链问题

| # | 现象 | 根因 | 修复 | 笔记 |
|---|---|---|---|---|
| 1 | `No module named 'android'` @ ctypes/util.py | p4a 补丁让 stdlib ctypes.util 依赖 `android._ctypes_library_finder`（android recipe 需 pyjnius/sdl，qt bootstrap 不含） | `android_stubs` 加 `android` 包桩（纯文件系统 find_library） | 08 |
| 2 | `dotenv.find_dotenv` `'NoneType' has no 'f_code'` | p4a 打包 .pyc 帧 co_filename 是构建机路径、设备上不存在 → 栈回溯一路走到栈顶 f_back=None | `android_stubs` 把 `dotenv.main.find_dotenv` 换成 Android 安全空实现 | 09 |
| 3 | `ImportError: cannot import name 'R' from 'iaa.tasks'` | `R.py`/`iaa/res` 是 gitignored 生成物，CI 只搬 git checkout → 设备上没有 | workflow 增 "Generate iaa resources" 步骤，host 侧跑 `make_resources.py --production` | 10 |

## 三、新增/修改文件（自 07 交接）

- `iaa/platform/android_stubs.py`：+android 包桩、+dotenv.find_dotenv 桩。
- `tests/test_android_imports.py`：+AndroidPackageStubTests、+DotenvFindStubTests。
- `.github/workflows/android-build.yml`：+资源生成步骤（kotonebot --no-deps +
  pydantic/rich/opencv<5/numpy/dotenv/mouse/typing-extensions/psutil）。
- `notes/08/09/10`：三篇根因文档。

## 四、验证

- 本地：`tests/test_android_imports.py` = 8 passed；全套 android 相关 30 passed。
- 设备：APK 安装（uninstall 后 install，369MB 流式安装成功）→ 启动 → GUI 点亮
  → conf/logs 落盘正常。
- 桌面回归：android 相关测试全部通过（workflow 变更不影响桌面构建链）。

## 五、下一步（继续 E2E）

- [x] `env.app_root()` / logs / conf 落盘位置验证（本节已完成）
- [ ] 非脚本 E2E 深化：GUI 各页面（总览/设置/偏好）、config 读写回环、
      日志显示、设备 placeholder 不崩（task 列表页触发 registry，已验证不崩）。
- [ ] 后续规划：onnxruntime/rapidocr、aarch64、APK 瘦身、release 签名。
