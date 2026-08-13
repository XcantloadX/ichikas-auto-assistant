# Android 构建链调研与落地（p4a + Qt 官方 deploy 路线）

日期：2026-08-13
分支：`feat/p4a-android`
本文档记录首个 Android APK（x86_64 模拟器）构建链的调研结论、选型、依赖可行性、
CI 设计，以及明确的下一步 action 清单。

## 1. 选型结论

| 项 | 结论 |
|---|---|
| 打包路线 | **官方 `pyside6-android-deploy`**（Qt for Python 6.11）+ buildozer 1.5.0 + p4a `qt` bootstrap。Qt 官方工具本质就是「动态生成 p4a recipe + 驱动 buildozer」，全功能、成功率高，且是唯一官方支持路径。裸 buildozer 自写 spec 只作兜底排查用。 |
| 宿主 OS | GitHub Actions `ubuntu-24.04`（p4a 仅 Linux/macOS）。Windows 无法原生跑。 |
| 宿主 Python | **3.11**（工具硬性要求 ≤3.11；`sys.version_info >= (3,12)` 直接抛错）。 |
| 目标 Python | **3.11.9**（Qt android wheel 只有 cp311/cp310；`p4a` python3 recipe 默认 3.14.2，**必须 pin**）。 |
| 架构 | **x86_64**（目标模拟器 Android 15 / API 35）。`qt` bootstrap 单架构；官方 wheel 仅 aarch64 + x86_64。 |
| 入口 | 根目录 `main.py`（已建），委托 `iaa.application.qt.index.android_main()`。 |
| SDK/NDK | NDK **r27c**（Qt 官方工具 `ANDROID_NDK_VERSION=27c`）；SDK 手动预装（cmdline-tools + platform 35 + build-tools 35）。JDK 17。 |
| 输出 | `buildozer.spec` 由官方工具生成，CI 补丁合并本项目需求（两次 deploy 模式）。 |

### pyside6-android-deploy 工作流（关键事实，来自 pyside-setup 6.11.1 源码）

- 入口要求：cwd 下有 `main.py`；`-c pysidedeploy.spec`（默认 `./pysidedeploy.spec`，不存在则自动生成）。
- 自动安装 `[python] android_packages`（默认 `buildozer==1.5.0,cython==0.29.33`）。
- 生成 p4a 动态 recipe 到 **`<project>/deployment/recipes`**（`generated_files_path = project/deployment`），
  并将 `p4a.local_recipes` 指向它。
- 生成 `buildozer.spec`（`Buildozer.initialize`）：
  - **若 buildozer.spec 已存在 → 原样使用、不再写入任何键**（这就是「全手动模式」的入口）。
  - 若不存在 → `buildozer init` 后注入：
    `app.requirements = python3,shiboken6,PySide6`、`android.archs`、`p4a.bootstrap=qt`、
    `p4a.branch=develop`、`p4a.local_recipes=<deployment>/recipes`、
    `p4a.extra_args=--qt-libs=… --load-local-libs=… --init-classes=…`、
    `android.permissions`（由 wheel 内 xml 扫描）、`android.add_jars`、`buildozer.bin_dir`。
  - 结论：**工具生成的 `requirements` 会被其写死**，本项目额外依赖必须“先生成、再补丁”注入。
- `p4a.extra_args` 里 `--qt-libs` 对应 `[qt] modules`：留空则由工具扫描 PySide6 import +
  QML `import Qt…` 自动推断（本应用 QML 用到 QtQuick.Controls/Effects/Layouts/Window/QtQml.Models）。
- NDK/SDK 查找：工具缓存 `~/.pyside6_android_deploy/`；未找到 NDK 会自行下载 r27c，
  SDK 未找到则交给 buildozer 下载（需要 `android.accept_sdk_license=True`）。
- `--keep-deployment-files` 保留生成文件（否则结束时清理）。

## 2. 依赖可行性结论（重点）

本地验证命令（Windows 也能跑，只下载不安装）：

```
py -3.11 -m pip download pydantic-core --platform android_21 --python-version 311 --only-binary=:all: --no-deps -d tmp
```

### 高风险依赖 1：pydantic-core

- **PyPI 无任何 android wheel**。实测 `--platform android_21` 只下到
  `pydantic_core-0.0.1-py3-none-any.whl` —— 那是 **0.0.1 蹭名占位包**，不是真构建；
  `pydantic-core==2.33.2`（桌面锁定版本）直接报“No matching distribution”。
- 逐一核对 PyPI JSON：`2.20.1 / 2.30.0 / 2.33.2 / 2.48.0` 均 **NONE**（任何版本都没有 android 轮子）。
- **p4a 现成 recipe（好消息）**：`pythonforandroid/recipes/pydantic-core`（v2026.05.09 发布版即含），
  基于 `RustCompiledComponentsRecipe`（rustup + NDK clang 交叉编译），**版本固定 2.41.4**。
  - 配套：`pydantic==2.12.3` 正好 require `pydantic-core==2.41.4` —— 与 recipe 完全对齐；
    桌面锁的是 pydantic 2.11.7/core 2.33.2，**Android 与桌面解耦、互不影响**。
  - 前提：**宿主必须装 rustup**（recipe `check_host_deps` 强制）。
- 替代方案（不推荐首版用）：
  - 社区 `Eutalix/android-pydantic-core`：Termux 用预编译 wheel（`linux_<arch>` 平台标签 +
    Termux RPATH），与 p4a 打包 ABI/路径不对应，只能参考其 NDK+maturin 思路。
  - OpenEmbedded meta-python 有 recipe（cargo/maturin），非 p4a 生态。

### 高风险依赖 2：onnxruntime

- **PyPI 无 android python wheel**；官方 Android 产物是 **Maven AAR / Java+C 接口**，非 Python。
- p4a 主仓库**无 onnxruntime recipe**；社区有 cmake 自编译 recipe：
  `daslearning-org/vision-ai` `onnx/p4a_local_recipes/onnxruntime`（version 1.22.1，
  依赖 pybind11/protobuf，NDK 25b；可复制到 `p4a.local_recipes` 使用，工作量大、风险高）。
- **本项目现状：启动链不 import onnxruntime**。kotonebot 的 `backend/ocr.py` 只在
  `if TYPE_CHECKING:` 下引用 `rapidocr_onnxruntime`；`iaa` 侧也没有模块级 import。
- **结论：首版 APK 不带 onnxruntime / rapidocr_onnxruntime / thefuzz(+rapidfuzz)**，
  待后续 OCR 能力需求再走社区 recipe 或替换方案。

### 各依赖 p4a 支持矩阵（v2026.05.09 发布版 recipe 列表实测）

| 依赖 | p4a 状态 | 首版 | 备注 |
|---|---|---|---|
| PySide6 6.11.1 / shiboken6 | qt bootstrap + 官方动态 recipe | ✅ | android_x86_64 wheel（cp311）官方下载站 |
| python3 | recipe（默认 3.14.2） | ✅ | **pin `python3==3.11.9, hostpython3==3.11.9`**（hostpython 有同版本 guard） |
| pydantic-core | **recipe 2.41.4**（Rust） | ✅ | PyPI 无 wheel；需 rustup |
| pydantic | 纯 Python | ✅ | pin `==2.12.3` 对齐 recipe；pip `--no-deps` 需显式列出 |
| opencv | recipe 4.12.0（NDKRecipe，`depends=[numpy]`） | ✅ | 体积大、编译慢 |
| numpy | recipe **v2.3.0**（Meson，无 BLAS） | ✅ | 桌面 `numpy<2.0` 仅是桌面约束；Android 用 recipe 默认 2.3.0（运行期 API 兼容需回归验证） |
| grpcio | recipe 1.64.0 | 后续 | 启动链不 import；recipe 编译较久 |
| av | recipe 13.1.0（依赖 ffmpeg） | 后续 | 只被 kotonebot scrcpy 视频流使用，首版不装 |
| onnxruntime | 无官方 recipe（社区有） | 后续 | 官方 Android 用 AAR；Python 侧需自编译 recipe |
| rapidocr-onnxruntime | 无 | 后续 | 与 onnxruntime 同进退 |
| thefuzz | 纯 Python，但依赖 rapidfuzz(C++) | 后续 | rapidfuzz 无 recipe/无 android wheel |
| pynput | 无 recipe | **排除** | iaa 已门控为 noop（`global_hotkey_controller.py`） |
| psutil | 无 recipe | **排除** | iaa 未 import（仅桌面打包用） |
| requests / click / sentry-sdk / plyer | 纯 Python | ✅ | 需把传递依赖（charset-normalizer/idna/urllib3/certifi）显式列出 |
| typing-extensions / annotated-types / typing-inspection / python-dotenv / ksaa-res | 纯 Python | ✅ | pydantic/kotonebot 运行时依赖 |

### 关键机制（影响 requirements 写法的 p4a 行为）

1. **p4a 对无 recipe 的纯 Python 依赖用 `pip install --target … --no-deps`**（v2026.05.09
   `run_pymodules_install`）→ **传递依赖不会自动装，必须把运行期要 import 的顶层包全部显式列出**。
2. p4a 的自动依赖解析（`process_python_modules` 的 pip `--dry-run --only-binary=:all:`）
   一旦遇到“有编译依赖但无 android wheel 的包”（如 kotonebot→onnxruntime、pydantic→pydantic-core）
   会整体失败并退回只装显式列表 → 行为等同第 1 点。
3. **buildozer 默认传 `--ignore-setup-py`** → 仓库 `pyproject.toml`
   （`requires-python="~=3.10.0"`、桌面依赖、win_amd64 wheel URL）**不会**被 p4a 以 pip 安装，
   避免 3.11 解释器与桌面依赖污染。app 源码由 p4a `--private` 整目录拷贝进包。
4. 版本 pin 机制：`requirements` 里 `recipe==version` 会设置 `VERSION_<recipe>` 环境变量
   （`toolchain.py`），`Recipe.version` 优先读它。

## 3. 交付文件与用法

| 文件 | 作用 |
|---|---|
| `main.py` | p4a 入口，委托 `android_main()`。 |
| `pysidedeploy.spec` | 官方工具配置（`[app]/[qt]/[android]/[buildozer]`）；CI 与本地一致。 |
| `buildozer.spec` | **骨架/参考**（标注 `[自动生成]` / `[硬编码]`）。CI 会先把它挪为 `.sample`，让官方工具生成完整 spec 后再补丁合并本仓库的依赖与参数。 |
| `requirements/p4a.txt` | Android 侧“额外”依赖清单（与补丁逻辑同源）。 |
| `.github/workflows/android-build.yml` | ubuntu-24.04 手动触发 workflow，产物 APK + 日志上传。 |

## 4. CI 流程描述（android-build.yml）

1. checkout；apt 安装 JDK17 / build-essential / ccache / autoconf automake libtool /
   zlib1g-dev libffi-dev libssl-dev / pkg-config / ninja / wget unzip zip curl。
2. rustup（pydantic-core recipe 需要）；setup-python 3.11；pip 装 `PySide6==6.11.1`
   （自带 `pyside6-android-deploy`）+ `buildozer==1.5.0` + `cython==0.29.33`。
3. 从 `download.qt.io` 下载 `pyside6-6.11.1-…-cp311-cp311-android_x86_64.whl` 与
   `shiboken6-…-android_x86_64.whl`（URL 已实测 200）。
4. 预装并缓存 NDK r27c 到 `~/.pyside6_android_deploy/android-ndk/android-ndk-r27c`
   （与 Qt 工具缓存路径一致）+ SDK（cmdline-tools + platform 35 + build-tools 35.0.0）。
5. rsync 仓库到 `$RUNNER_TEMP/iaa-app`（排除 .git/.venv/缓存）；把仓库 `buildozer.spec`
   挪为 `.sample`。
6. **Pass 1**：`pyside6-android-deploy --keep-deployment-files …` → 生成完整 buildozer.spec
   + 动态 recipes + deployment/（失败也继续，`|| true`）。
7. **补丁**（内联 python/configparser）：把 `requirements` 替换为
   `python3==3.11.9,hostpython3==3.11.9,shiboken6,PySide6` + `requirements/p4a.txt` 全量，
   并写死 `android.accept_sdk_license/wakelock/api=35/minapi=24/ndk_api=24/permissions`。
8. **Pass 2**：恢复 `.buildozer` 后再次 `pyside6-android-deploy` → 工具发现 buildozer.spec
   已存在 → 原样使用补丁后的配置 → 完整构建（numpy/opencv/pydantic-core recipe + 纯 Python）。
9. 上传 `*.apk`（artifact `iaa-android-x86_64`）+ `buildozer.spec` + buildozer 日志。

## 5. 预计坑（首次运行高概率失败点）

1. **SDK/NDK 首次下载体积与耗时**：NDK r27c 约 1GB、SDK 数百 MB；已用 actions/cache 缓存，
   但首次无命中。CI 预算首次 60–120min 可接受。
2. **python 版本**：不 pin 时 p4a 用 python3.14 构建，与 Qt cp311 wheel 生态、hostpython guard 冲突 →
   **必须 pin 3.11.9**。这是 Pass1 生成 spec 后补丁步骤的核心修正点。
3. **pydantic-core Rust 编译**：recipe 只认 rustup 环境；`cargo` 首次编译约 5–15min；
   若 NDK 版本与 recipe 不兼容（建议 r25b–r27c）会报 clang/链接错误。
4. **numpy 2.3.0（recipe 默认）与桌面 numpy<2 的 API 差异**：iaa/kotonebot 运行期兼容性需在
   模拟器上回归（如 `np.bool8`/`np.float_` 移除类 API）。
5. **QML 模块不全**：`[qt] modules` 留空依赖工具推断；若缺 QuickEffects/QuickControls2 会
   “module not found”，届时在 pysidedeploy.spec 显式列出。
6. **venv 误进 QML 扫描**：官方工具会扫描项目内 Python 源码，`.venv` 在项目里会触发
   “You are including a lot of QML files from a local venv” → CI 用独立目录 + rsync 排除。
7. **charset_normalizer 等传递依赖**：因 `--no-deps`，忘列就运行时 `ModuleNotFoundError`；
   已在 p4a.txt 显式列全。
8. **`p4a.branch=develop`**：Qt 工具强制 develop（含 qt bootstrap 动态 recipe 支持）；
   与 buildozer 1.5.0 的 p4a 安装逻辑耦合，升级 buildozer 需回归。

## 6. 下一步 action 清单

首版 APK（GUI 点亮）之后，按优先级迭代：

- [ ] **验证产物**：`adb install` 到 127.0.0.1:5557（x86_64/API35）→ `adb logcat` 观察启动崩溃；
      用 `iaa.platform.env.app_root()`（ANDROID_PRIVATE）核对路径。
- [ ] **补全启动链依赖**：跑通后按崩溃堆栈补齐缺包（如 `ksaa-res` 数据、`mouse` 若被 kotonebot 实际引用）。
- [ ] **onnxruntime / rapidocr**：OCR 能力需要时，评估复制 `daslearning-org/vision-ai` 社区 recipe
      到 `p4a.local_recipes`，或改走 onnxruntime-android AAR + JNI。
- [ ] **grpcio、av(+ffmpeg)**：控制/视频流能力需要时加入（有 recipe，编译时间长）。
- [ ] **多架构 aarch64**：真机支持；qt bootstrap 单架构，需并行两个 job。
- [ ] **APK 瘦身**：PySide6 全量偏大；用 `[qt] modules` 裁剪、QML 插件排除、R8/proguard。
- [ ] **签名与 release(.aab)**：正式发布用 `mode=release` + keystore。
- [ ] **缓存优化**：p4a 构建目录（`.buildozer`）与 cargo 目标目录入 actions/cache，缩短迭代。
- [ ] **依赖收敛**：若 numpy 2.x 在设备上有 API 兼容问题，评估 p4a recipe 覆盖到 numpy 1.26。
