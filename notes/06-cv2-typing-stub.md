# cv2.typing 缺失导致启动 import 失败（p4a opencv recipe 无 typing 子包）

日期：2026-08-13
分支：`feat/p4a-android`

## 一、现象

Qt JNI 崩溃修复（Core 首位）后的第二次设备启动，logcat：

```
ModuleNotFoundError: No module named 'cv2.typing'; 'cv2' is not a package
  File ".../main.py", line 10, in <module>
  File ".../iaa/application/qt/index.py", line 3
  ...
  File ".../iaa/application/service/config_service.py", line 3, in <module>
  File ".../kotonebot/__init__.py"
  File ".../kotonebot/backend/context/context.py", line 21
    from cv2.typing import MatLike
```

即：Qt 层已过，Python 侧业务 import 链在 `kotonebot` 处中断。

## 二、根因

- **桌面 opencv-python wheel**：`cv2` 是**包**（目录），含纯 Python 的
  `cv2/typing/__init__.py`（`MatLike = Union[Mat, NumPyArrayNumeric]`、
  `Rect = Sequence[int]` 等，仅类型注解用）。
- **p4a opencv recipe**（`pythonforandroid/recipes/opencv/__init__.py`）：
  `-DOPENCV_SKIP_PYTHON_LOADER=ON` → 只把 `cv2.so` 作为**单个扩展模块**
  装进 site-packages。`cv2` 不是包 → `cv2.typing` 无从谈起，import 即抛
  `'cv2' is not a package`。
- kotonebot 与 iaa 共 27+ 个模块顶部有 `from cv2.typing import MatLike`
  （另有 `from cv2.typing import MatLike, Rect as CvRect`）。全部只用于
  函数签名注解，运行期从不取值。

## 三、方案：sys.modules 桩（不动任何业务 import）

- 新增 `iaa/platform/android_stubs.py`：
  `install_cv2_typing_stub()` 把 `cv2.typing` 以 `types.ModuleType` 注册进
  `sys.modules`，提供 `MatLike = Any`、`Rect = Sequence[int]`。桌面（
  `env.IS_ANDROID` 为 False）直接跳过，不 shadow 真实包。
- `main.py` 在 `from iaa.application.qt.index import android_main` **之前**
  调用 `android_stubs.install_android_stubs()` —— 必须早于任何 kotonebot
  import，否则 import 链先触发查找失败。
- 为什么桩够用：`MatLike`/`Rect` 仅出现在注解里，注解求值只需名字存在；
  桩语义与桌面别名（`Union[np.ndarray,...]` / `Sequence[int]`）一致。

## 四、验证

- 本地单测：`tests/test_android_imports.py::Cv2TypingStubTests` 模拟 p4a
  布局（`sys.modules['cv2']` 为裸 module），注册桩后 `from cv2.typing import
  MatLike, Rect as CvRect` 成功；幂等。
- `tests/test_env.py tests/test_self_android.py tests/test_android_imports.py`
  = 21 passed。
- 需重新构建 APK 后上机验证（push 触发）。

## 五、经验

- p4a recipe 与桌面 wheel 的**包结构可能不等价**：opencv 是典型（recipe 产出
  单 .so，wheel 是包目录）。凡业务代码 `import <包>.<子模块>` 且子模块是
  纯 Python 注解/常量时，用 `sys.modules` 桩兜底比改业务 import 侵入更小、
  更集中。
- 后续若引入 onnxruntime/rapidocr（同为无 recipe 的 C 扩展），同样走
  `android_stubs.py` 追加桩或社区 recipe，入口保持唯一。
