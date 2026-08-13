"""Android 自身设备（self_android）占位实现。

当 iaa 以 python-for-android 构建、运行在**游戏同一台设备**上时，
传统控制层（adb / scrcpy / uiautomator2 / 模拟器发现）在该场景下均
不可用，但上层（SchedulerService / DeviceFactory / kotonebot
``init_context`` 以及常规 GUI 路径）依旧需要拿到一个 device 对象才能
跑通任务调度。本包提供一个最小占位实现，保证不崩、可被 kotonebot
上下文正常接管。
"""

from .device import SelfAndroidCommands, SelfAndroidDevice

__all__ = ['SelfAndroidCommands', 'SelfAndroidDevice']