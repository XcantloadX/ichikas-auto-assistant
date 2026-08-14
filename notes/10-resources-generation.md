# iaa/tasks/R.py 缺失导致 task 注册链 ImportError（CI 未生成 gitignored 资源）

日期：2026-08-14
分支：`feat/p4a-android`
构建：待跑（push d2b4cf5 触发）

## 一、现象

dotenv 桩（09）修复后，run 31795031244 的 APK 上机，启动 logcat 报：

```
Traceback (most recent call last):
  File ".../main.py", line 21
  File ".../iaa/application/qt/__init__.py", line 1
  File ".../iaa/application/qt/index.py", line 3
  File ".../iaa/application/qt/controllers/__init__.py", line 1
  File ".../iaa/application/qt/controllers/app_controller.py", line 12
  File ".../iaa/application/service/iaa_service.py", line 13
  File ".../iaa/application/service/scheduler.py", line 16
  File ".../iaa/tasks/registry.py", line 5
  File ".../iaa/tasks/cm.py", line 7
ImportError: cannot import name 'R' from 'iaa.tasks' (unknown location)
```

即：上一轮 dotenv 桩有效，import 链推进到 `iaa.tasks.registry`（被 scheduler 模块级
import），`cm.py` 里 `from . import R` 失败——`iaa/tasks/R.py` 不存在。

## 二、根因

- `iaa/tasks/R.py` 与 `iaa/res/` 是 **gitignored 的生成产物**：
  - `iaa/.gitignore` 里 `res` 与 `tasks/R.py`；
  - 由 `tools/make_resources.py` 从**已跟踪**的 `resources/`（295 个源图 + `*.png.json`）
    生成。
- 桌面/发布流程靠本地跑 `just res`（`uv run ./tools/make_resources.py`）先生成再构建；
  **Android CI 没有这一步骤**——rsync 只搬 git checkout（不含 gitignored 生成物），
  于是 APK 里既没有 `R.py` 也没有 `iaa/res`。
- `scheduler.py` 模块级 `from .registry import ...` → `registry` 模块级 import 各 task
  模块 → `cm.py` 模块级 `from . import R` → 崩溃。这是**启动必经链**，无法用惰性化绕过。

## 三、方案：CI 增加 make_resources.py 步骤（host 侧轻量生成）

- 在 `android-build.yml` 的 "Prepare app build directory" 之后新增
  "Generate iaa resources (make_resources.py)"：
  - `pip install --no-deps "kotonebot==0.19.1"` + `pydantic rich opencv-python numpy
    python-dotenv mouse typing-extensions`（实测 `make_resources.py` 的模块级 import
    只需这 7 个；rapidocr/onnxruntime 是惰性导入，host 生成资源用不到 → 不拉重依赖）。
  - `python3 tools/make_resources.py --production` → 生成 `iaa/tasks/R.py` 与 `iaa/res`。
  - `ls -la iaa/tasks/R.py && test -d iaa/res` 兜底断言。
- 生成的 `iaa/res` 随 buildozer 打进 APK：`sprite_path` 在 Android 上走
  `importlib.resources('iaa.res')`（见 `iaa/platform/env.py::sprite_root`），
  打包后即可取用。
- `--production` 与本地 `just res` 一致（无 docstring 更小）。

## 四、验证

- 本地 `make_resources.py --production` 跑通：Parsed files 92 / Resources 199，
  生成 `iaa/tasks/R.py`（约 300KB）+ `iaa/res`（630 图，约 6MB）。
- 待重新构建 APK 上机验证（构建由 d2b4cf5 触发）。

## 五、经验

- **gitignored 的生成产物在 CI 上不会自动存在**：只要业务代码 import 了它们，
  CI 必须"先生成再打包"。本案例 `R.py`/`iaa/res` 由 `resources/`（已跟踪）生成，
  在 workflow 里补一个生成步骤即可，不要改业务 import 去绕开。
- host 侧跑生成工具时用 `--no-deps` + 显式最小依赖，避免把 target 环境才需要的
  重依赖（onnxruntime/rapidocr）装进 host。
- 启动链修复轨迹追加为：
  Qt JNI → cv2.typing → mouse/ctypes.util(android 包) → dotenv.find_dotenv →
  iaa.tasks.R 生成缺失。
