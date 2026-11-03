"""guest agent 的 TCP 客户端。

agent（arm64，见 ``guest_agent/iaa_agent.c``）注入游戏进程后在本机
起 TCP 服务（默认 0.0.0.0:29170，经 adb forward 暴露给宿主）。
行协议：每连接一请求一响应，请求/响应均为单行 JSON，响应以 ``\\n`` 结尾。

命令::

    {"cmd":"ping"}               → {"ok":true,"agent":"iaa","il2cpp":true}
    {"cmd":"boot"}               → {"ok":true}   （幂等，可重复调用）
    {"cmd":"dbg"}                → 调试信息（前几个 Transform 名）
    {"cmd":"dump","max":6000}    → {"ok":true,"n":N,"nodes":[...]}
"""
from __future__ import annotations

import json
import socket
import subprocess

#: agent 在 guest 侧监听的端口
AGENT_PORT = 29170
#: 默认 adb serial（MuMu）
DEFAULT_SERIAL = '127.0.0.1:5555'


def adb_shell(serial: str, cmd: str) -> str:
    """执行一条 adb shell 命令并返回 stdout。

    :param serial: adb 设备 serial
    :param cmd: shell 命令
    :return: stdout 文本
    """
    return subprocess.run(
        ['adb', '-s', serial, 'shell', cmd],
        capture_output=True, text=True, timeout=30,
    ).stdout


class GuestAgentClient:
    """与 guest agent 的 TCP 通信客户端（无状态，每次请求新建连接）。

    用法::

        ga = GuestAgentClient()
        if ga.ping():
            ga.boot()
            nodes = ga.dump()
    """

    def __init__(self, serial: str = DEFAULT_SERIAL, port: int = AGENT_PORT) -> None:
        """创建客户端。

        :param serial: adb 设备 serial
        :param port: agent TCP 端口（guest 侧）
        """
        self.serial = serial
        """adb 设备 serial。"""

        self.port = port
        """agent TCP 端口。"""

    def ensure_forward(self) -> None:
        """确保 adb 端口转发存在。

        :raises RuntimeError: adb forward 失败时
        """
        r = subprocess.run(
            ['adb', '-s', self.serial, 'forward', f'tcp:{self.port}', f'tcp:{self.port}'],
            capture_output=True, text=True, timeout=30,
        )
        if r.returncode != 0:
            raise RuntimeError(f'adb forward tcp:{self.port} failed: {r.stderr.strip()}')

    def call(self, cmd: dict, timeout: float = 60) -> dict:
        """发送一条命令并等待单行 JSON 响应。

        :param cmd: 请求 dict（如 ``{"cmd":"dump","max":6000}``）
        :param timeout: 连接/读取超时秒数
        :return: 响应 dict
        :raises GuestAgentError: 连接失败、响应不完整或 JSON 解析失败时
        """
        payload = (json.dumps(cmd) + '\n').encode()
        buf = b''
        try:
            with socket.create_connection(('127.0.0.1', self.port), timeout=timeout) as s:
                s.settimeout(timeout)
                s.sendall(payload)
                while not buf.endswith(b'\n'):
                    d = s.recv(1 << 20)
                    if not d:
                        break
                    buf += d
        except OSError as e:
            raise GuestAgentError(f'agent tcp call failed: {cmd} ({e})') from e
        if not buf.endswith(b'\n'):
            raise GuestAgentError(f'agent connection closed mid-response: {cmd}')
        try:
            return json.loads(buf)
        except json.JSONDecodeError as e:
            raise GuestAgentError(f'agent bad json response: {buf[:200]!r}') from e

    def ping(self) -> bool:
        """探测 agent 是否存活且已加载。

        :return: agent 可响应且 il2cpp 已解析时 True
        """
        try:
            r = self.call({'cmd': 'ping'}, timeout=10)
        except GuestAgentError:
            return False
        return bool(r.get('ok')) and bool(r.get('il2cpp'))

    def boot(self) -> None:
        """执行 bootstrap（解析 il2cpp 类/方法句柄）。幂等。

        :raises GuestAgentError: bootstrap 失败时
        """
        r = self.call({'cmd': 'boot'}, timeout=60)
        if not r.get('ok'):
            raise GuestAgentError(f'boot failed: {r}')

    def dump(self, max_nodes: int = 8000, timeout: float = 120) -> dict:
        """dump 当前 UI 树。

        :param max_nodes: 节点数上限
        :param timeout: 超时秒数
        :return: 原始响应 dict（``{"ok":true,"n":N,"nodes":[...]}``，平铺 + parent 指针）
        :raises GuestAgentError: dump 失败时
        """
        r = self.call({'cmd': 'dump', 'max': max_nodes}, timeout=timeout)
        if not r.get('ok'):
            raise GuestAgentError(f'dump failed: {r.get("err", r)}')
        return r


class GuestAgentError(RuntimeError):
    """guest agent 通信/执行错误。"""
