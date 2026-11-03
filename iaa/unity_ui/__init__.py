"""Unity UI-Tree 自动化框架。

通过 Frida 注入 Unity(il2cpp) 游戏进程，经 houdini native-bridge trampoline
调用 il2cpp C API，dump 场景/UI 树并提供 Playwright 风格的元素定位与查询，
用于替代模板匹配与 OCR 识别层（交互仍走模拟点击）。

模块划分
========
- :mod:`injector`  frida 会话/agent 生命周期管理
- :mod:`client`    对 agent RPC 的 Python 封装（bootstrap/dump/窗口重试）
- :mod:`tree`      UI 树数据模型
- :mod:`locator`   Playwright 风格定位器
- :mod:`element`   可操作元素（click 走 kotonebot device）
"""
