"""Frida 注入器：把 guest agent（arm64 .so）加载进游戏进程。

链条：frida attach → Java.perform → ``Runtime.load0(app.getClass(), path)``
→ ART/guest linker/houdini 正常加载我们的 .so → JNI_OnLoad 起 TCP 服务。

注入是幂等的：agent 已加载时 ``System.load`` 只是 dlopen 引用计数 +1，
不会重复执行初始化。

.. NOTE::
    反作弊（pcam/libchecker）会杀 spawn 模式的 frida，因此只能 attach
    运行中的进程；运行时外来 dlopen 不被拦截（已验证）。

.. NOTE::
    javaloader.js 由 ``javaloader.ts`` 经 ``npx frida-compile`` 生成
    （frida 17 移除了内置 Java bridge，需自带 frida-java-bridge）。
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import frida

#: guest agent .so 的仓库内路径
AGENT_SO_PATH = Path(__file__).parents[2] / 'guest_agent' / 'iaa_agent.so'
#: agent 在设备上的部署路径
AGENT_SO_DEVICE_PATH = '/data/local/tmp/iaa_agent.so'
#: frida Java bridge loader（frida-compile 产物）
JAVALOADER_JS_PATH = Path(__file__).parent / 'agent' / 'javaloader.js'

#: 模拟器 adb 地址
ADB_SERIAL = '127.0.0.1:5555'
#: frida-server 经 adb forward 暴露的地址
FRIDA_ADDRESS = '127.0.0.1:27042'
#: frida-server 端口
FRIDA_PORT = 27042


def adb_shell(cmd: str, serial: str = ADB_SERIAL) -> str:
    """执行一条 adb shell 命令并返回 stdout。

    :param cmd: shell 命令
    :param serial: adb 设备 serial
    :return: stdout 文本
    """
    return subprocess.run(
        ['adb', '-s', serial, 'shell', cmd],
        capture_output=True, text=True, timeout=30,
    ).stdout


def ensure_frida_forward(serial: str = ADB_SERIAL) -> None:
    """确保 frida-server 的 adb 端口转发存在。

    :param serial: adb 设备 serial
    :raises RuntimeError: adb 转发失败时
    """
    r = subprocess.run(
        ['adb', '-s', serial, 'forward', f'tcp:{FRIDA_PORT}', f'tcp:{FRIDA_PORT}'],
        capture_output=True, text=True, timeout=30,
    )
    if r.returncode != 0:
        raise RuntimeError(f'adb forward tcp:{FRIDA_PORT} failed: {r.stderr.strip()}')


def get_device(serial: str = ADB_SERIAL) -> frida.core.Device:
    """连接 frida-server 并返回 Device。

    :param serial: adb 设备 serial
    :return: frida Device 对象
    """
    ensure_frida_forward(serial)
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


def ensure_agent_so(serial: str = ADB_SERIAL) -> None:
    """确保最新编译的 agent .so 已部署到设备（按文件大小判断是否重推）。

    :param serial: adb 设备 serial
    """
    local_size = AGENT_SO_PATH.stat().st_size
    out = adb_shell(f'ls -l {AGENT_SO_DEVICE_PATH}', serial)
    if out.strip() and out.split()[3].isdigit() and int(out.split()[3]) == local_size:
        return
    subprocess.run(
        ['adb', '-s', serial, 'push', str(AGENT_SO_PATH), AGENT_SO_DEVICE_PATH],
        capture_output=True, text=True, timeout=60, check=True,
    )
    # 反作弊环境下 /data/local/tmp 需 root 可读性处理（已验证 644 即可）
    adb_shell(f'su -c "chmod 644 {AGENT_SO_DEVICE_PATH}"', serial)


def inject(serial: str = ADB_SERIAL, package: str = 'com.sega.pjsekai') -> int:
    """向运行中的游戏进程注入 guest agent（幂等）。

    :param serial: adb 设备 serial
    :param package: android 包名
    :return: 游戏进程 pid
    :raises RuntimeError: 进程未运行或注入失败时
    """
    device = get_device(serial)
    pid = find_pid(device, package)
    if pid is None:
        raise RuntimeError(f'process of {package} not running')

    session = device.attach(pid)
    try:
        script = session.create_script(JAVALOADER_JS_PATH.read_text(encoding='utf-8'))
        errors: list[str] = []

        def on_message(message, _data) -> None:
            if message['type'] == 'error':
                errors.append(message.get('stack') or message.get('description') or 'unknown')

        script.on('message', on_message)
        script.load()
        result = script.exports_sync.load(AGENT_SO_DEVICE_PATH)
        if result != 'ok':
            raise RuntimeError(f'Runtime.load0 failed: {result}')
        if errors:
            raise RuntimeError(f'javaloader script error: {errors[0]}')
    finally:
        try:
            session.detach()
        except Exception:  # noqa: BLE001 注入完成后即断开，失败不影响结果
            pass
    return pid
