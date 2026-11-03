"""Frida 注入器：管理 agent 会话生命周期。

职责：
- 连接 frida-server（默认经 adb forward 127.0.0.1:27042）
- 按包名定位游戏进程并 attach
- 加载 agent.js 并提供 RPC 接口
- 进程死亡/会话失效时的重建
"""
from __future__ import annotations

import subprocess
import threading
import time
from pathlib import Path
from typing import Callable

import frida

AGENT_PATH = Path(__file__).parent / 'agent' / 'agent.js'

#: 模拟器 adb 地址
ADB_SERIAL = '127.0.0.1:5555'
#: frida-server 经 adb forward 暴露的地址
FRIDA_ADDRESS = '127.0.0.1:27042'


def adb_shell(cmd: str) -> str:
    """执行一条 adb shell 命令并返回 stdout。

    :param cmd: shell 命令
    :return: stdout 文本
    """
    return subprocess.run(
        ['adb', '-s', ADB_SERIAL, 'shell', cmd],
        capture_output=True, text=True,
    ).stdout


def ensure_forward() -> None:
    """确保 adb 端口转发存在。

    :raises RuntimeError: adb 转发失败时
    """
    r = subprocess.run(
        ['adb', '-s', ADB_SERIAL, 'forward', 'tcp:27042', 'tcp:27042'],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        raise RuntimeError(f'adb forward failed: {r.stderr.strip()}')


def get_device() -> frida.core.Device:
    """连接 frida-server 并返回 Device。

    :return: frida Device 对象
    """
    ensure_forward()
    return frida.get_device_manager().add_remote_device(FRIDA_ADDRESS)


def find_pid(device: frida.core.Device, package: str) -> int | None:
    """按包名查找游戏进程 pid。

    :param device: frida Device
    :param package: android 包名
    :return: pid；未运行返回 None
    """
    for app in device.enumerate_applications():
        if app.identifier == package and app.pid > 0:
            return app.pid
    return None


class AgentSession:
    """一条 frida 会话 + 已加载 agent 的封装。

    负责 agent 脚本生命周期、消息回调分发、RPC 调用与失效重建。
    """

    def __init__(self, package: str, on_message: Callable | None = None) -> None:
        """绑定到指定包名的运行中进程并加载 agent。

        :param package: android 包名
        :param on_message: agent send 消息回调（payload dict）
        :raises RuntimeError: 进程未运行或 attach 失败时
        """
        self.package = package
        self._on_message = on_message
        self._device = get_device()
        pid = find_pid(self._device, package)
        if pid is None:
            raise RuntimeError(f'process of {package} not running')
        self.pid = pid
        self._session = self._device.attach(pid)
        self._script = self._session.create_script(AGENT_PATH.read_text(encoding='utf-8'))
        self._script.on('message', self._dispatch)
        self._script.load()
        self._lock = threading.Lock()

    def _dispatch(self, message, data) -> None:
        """frida 消息分发。"""
        if message['type'] == 'send' and self._on_message:
            try:
                self._on_message(message['payload'])
            except Exception:  # noqa: BLE001 回调异常不影响 agent
                pass

    def call(self, method: str, *args, timeout: float = 30):
        """调用 agent 的 rpc.exports 方法。

        :param method: rpc 方法名
        :param args: 参数
        :param timeout: 超时秒数
        :return: agent 返回值
        :raises RuntimeError: 会话失效时
        """
        with self._lock:
            fn = getattr(self._script.exports_sync, method)
            return fn(*args)

    def alive(self) -> bool:
        """检查目标进程是否仍存活。"""
        out = adb_shell(f'ls /proc/{self.pid}/cmdline 2>/dev/null')
        return bool(out.strip()) and 'No such' not in out

    def detach(self) -> None:
        """卸载脚本并断开会话（进程仍运行）。"""
        try:
            self._script.unload()
        except Exception:  # noqa: BLE001
            pass
        try:
            self._session.detach()
        except Exception:  # noqa: BLE001
            pass
