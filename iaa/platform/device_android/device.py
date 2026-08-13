"""Android 自身设备（self_android）占位实现。

iaa 运行在游戏同一台设备上时，控制层（adb / scrcpy / uiautomator2）不适用，
但上层仍需要一个 device 对象：:func:`scheduler.__prepare_context` / GUI 路径会
调用 ``create_device_for_current_config`` 后把 device 注入 kotonebot
``init_context``。本模块提供最小占位实现，保证该链路不崩。

设计约束
========

- **不 import kotonebot**：刻意回避 ``kotonebot.client.protocol`` / 
  ``kotonebot.client.device`` 的协议类导入（Android wheel 上这些模块依赖较重，
  且 p4a 下导入顺序敏感）。本模块只依赖标准库，对外暴露 duck-typing 接口，
  由 kotonebot 的 ``ContextDevice`` 通过属性委托透传即可工作。

- **截图 / 触摸抛 ``NotImplementedError``**：本次不做真实 MediaProjection
  截图与无障碍事件注入，方法体直接抛异常并注明"placeholder，未实现"。

- **``commands`` 为 no-op 占位**：``adb_shell`` 返回空串，``launch_app`` /
  ``current_package`` / ``install_apk`` 返回 None，标记 TODO 指向真实实现
  （MediaProjection + AccessibilityService）。

- **``start()`` / ``stop()`` 直接通过**：p4a 下进程本身就是"设备"，
  没有可启动/停止的外部 driver，生命周期的语义退化为空操作。

.. NOTE::
    目前 ``device.of_android()``（kotonebot 全局转发）依赖 ``isinstance(
    self._device, AndroidDevice)``，而占位实现并非 ``AndroidDevice`` 子类，
    Android 上直接调用 ``of_android()``/``is_android`` 的任务会失败。
    这是已知取舍：E2E 只覆盖非脚本路径；待真实控制实现时再改为继承
    ``AndroidDevice``。不含 ``of_android()`` 调用的任务与全部 GUI 路径不受影响。
"""

from __future__ import annotations

from typing import Literal


# 统一占位说明。消息放在常量的 docstring 里，供异常/日志复用，避免散落。
_NOT_IMPLEMENTED_MSG = (
    'Android 自身设备控制为 placeholder，未实现'
    '（planned: MediaProjection 截图 + AccessibilityService 注入）'
)


class SelfAndroidCommands:
    """Android 自身设备的占位 commands（duck-typing ``AndroidCommandable``）。

    所有方法均为 no-op，供 scheduler 的 ``_setup_resolution``、任务里的
    ``adb_shell``/``launch_app`` 等调用路径安全通过。
    """

    def launch_app(self, package_name: str) -> None:
        """启动应用（占位 no-op）。

        TODO: 真实实现使用 ``Intent ACTION_MAIN`` 拉起游戏。

        :param package_name: 包名（占位阶段忽略）。
        :return: 恒为 ``None``。
        """
        # 占位阶段直接返回 None，不让上层感知"启动失败"。
        return None

    def current_package(self) -> str | None:
        """查询前台应用包名（占位 no-op）。

        TODO: 真实实现通过无障碍服务或 ActivityTaskManager 查询。

        :return: 占位阶段恒为 ``None``。
        """
        return None

    def adb_shell(self, cmd: str) -> str:
        """执行 adb shell 命令（占位 no-op）。

        Android 上不存在 adb server（自身设备），返回空串让调用方按
        "无输出"处理，避免因结果解析失败而崩溃。

        :param cmd: 命令（占位阶段忽略）。
        :return: 恒为空字符串。
        """
        return ''

    def install_apk(self, path: str) -> None:
        """安装 APK（占位 no-op）。

        自身设备无法也无须通过 adb 安装游戏，返回 ``None``。

        :param path: APK 路径（占位阶段忽略）。
        :return: 恒为 ``None``。
        """
        return None


class SelfAndroidDevice:
    """Android 自身设备（self_android）占位 ``Device`` 实现。

    通过 duck-typing 满足 kotonebot ``ContextDevice`` 的属性委托：
    ``scheduler`` 设置 ``orientation``、调用 ``start()``/``stop()``，
    kernel 通过 ``commands`` 调用 ``adb_shell``/``launch_app``。

    与真实 equipment 的差异：截图/触摸直接抛 ``NotImplementedError`` 并
    注明占位；不强制 ``screen_size``/``scaler`` 等视觉链路，避免误用。
    """

    def __init__(self) -> None:
        self.orientation: Literal['portrait', 'landscape'] = 'portrait'
        """当前方向（scheduler 会在任务前改为 ``'landscape'``）。"""

        self.commands = SelfAndroidCommands()
        """占位 commands，见 :class:`SelfAndroidCommands`。"""

        self._started: bool = False
        """占位生命周期状态：本设备即进程自身，start/stop 无实际动作。"""

    def start(self) -> None:
        """启动设备（占位直接通过）。

        p4a 下进程本身就是设备，无需连接 driver。只维护内部状态位。
        """
        self._started = True

    def stop(self) -> None:
        """停止设备（占位直接通过）。

        进程不随 iaa 的 stop 退出，仅复位内部状态位。
        """
        self._started = False

    def screenshot(self) -> object:
        """返回当前屏幕截图（占位未实现）。

        :raises NotImplementedError: 恒抛出，注明 placeholder。
        """
        raise NotImplementedError(_NOT_IMPLEMENTED_MSG)

    def screenshot_raw(self) -> object:
        """返回未过 Hook 的原始截图（占位未实现）。

        :raises NotImplementedError: 恒抛出，注明 placeholder。
        """
        raise NotImplementedError(_NOT_IMPLEMENTED_MSG)

    def detect_orientation(self) -> Literal['portrait', 'landscape'] | None:
        """检测屏幕方向（占位未实现）。

        :return: 占位阶段恒为 ``None``（无法检测）。
        """
        return None

    def click(self, x: int, y: int) -> None:
        """点击屏幕坐标（占位未实现）。

        :param x: 横坐标。
        :param y: 纵坐标。
        :raises NotImplementedError: 恒抛出，注明 placeholder。
        """
        raise NotImplementedError(_NOT_IMPLEMENTED_MSG)

    def swipe(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        duration: float | None = None,
    ) -> None:
        """滑动屏幕（占位未实现）。

        :param x1: 起点横坐标。
        :param y1: 起点纵坐标。
        :param x2: 终点横坐标。
        :param y2: 终点纵坐标。
        :param duration: 持续时长（秒），占位阶段忽略。
        :raises NotImplementedError: 恒抛出，注明 placeholder。
        """
        raise NotImplementedError(_NOT_IMPLEMENTED_MSG)

    def launch_app(self, package_name: str) -> None:
        """启动游戏（占位转发到 commands）。

        :param package_name: 应用包名。
        """
        self.commands.launch_app(package_name)

    def current_package(self) -> str | None:
        """当前前台包名（占位转发到 commands）。

        :return: 占位阶段恒为 ``None``。
        """
        return self.commands.current_package()