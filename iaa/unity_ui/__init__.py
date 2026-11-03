"""Unity UI-Tree 自动化框架。

注入 arm64 guest agent 到 Unity(il2cpp) 游戏进程（frida Java → System.load），
agent 在宿内经 dlsym 调用 il2cpp C API，通过 TCP 服务 dump 场景/UI 树；
Python 侧提供 Playwright 风格的元素定位与查询，用于替代模板匹配与 OCR
识别层（交互仍走模拟点击）。

模块划分
========
- :mod:`injector`     frida 注入（加载 guest agent .so，幂等）
- :mod:`guest_agent`  agent TCP 行协议客户端
- :mod:`client`       生命周期编排（注入/bootstrap/dump 重试）
- :mod:`tree`         UI 树数据模型（parent 指针建树 + 坐标换算）
- :mod:`locator`      Playwright 风格定位器
- :mod:`element`      可操作元素（click 走 kotonebot device）
"""
