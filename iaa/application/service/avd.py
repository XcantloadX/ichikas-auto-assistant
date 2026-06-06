"""AVD（Android 官方模拟器）host 支持。

结构：
  AvdHost     — 宿主（静态发现、installed 判断，持有 SDK 路径）
  AvdInstance — 单个 AVD 实例（生命周期管理、创建设备连接）
"""

import os
import re
import shutil
import subprocess
import time

from kotonebot import logging
from kotonebot.client.host.adb_common import AdbRecipes, CommonAdbCreateDeviceMixin
from kotonebot.client.host.protocol import AdbHostConfig, Instance
from kotonebot.client import Device
from kotonebot.errors import EmulatorNotFoundError
from kotonebot.util import Countdown, Interval

logger = logging.getLogger(__name__)


# ── emulator 可执行文件查找 ──────────────────────────────────────────────────────

def find_emulator_exe(sdk_path: str | None = None) -> str | None:
    """查找 Android emulator 可执行文件。

    查找顺序（sdk_path 非空时跳过自动查找，直接在该路径下定位）：
    1. 参数 sdk_path（用户在配置中手动指定）
    2. 环境变量 ANDROID_HOME / ANDROID_SDK_ROOT
    3. Windows 默认路径：%LOCALAPPDATA%\\Android\\Sdk
    4. macOS 默认路径：~/Library/Android/sdk
    5. Linux 默认路径：~/Android/Sdk
    6. PATH（shutil.which）
    """
    if sdk_path:
        exe = os.path.join(sdk_path, 'emulator', 'emulator')
        exe_win = exe + '.exe'
        if os.path.isfile(exe_win):
            return exe_win
        if os.path.isfile(exe):
            return exe
        logger.warning('sdk_path 指定为 "%s"，但未找到 emulator 可执行文件', sdk_path)
        return None

    candidates: list[str] = []

    for env_var in ('ANDROID_HOME', 'ANDROID_SDK_ROOT'):
        root = os.environ.get(env_var, '').strip()
        if root:
            candidates.append(os.path.join(root, 'emulator', 'emulator.exe'))
            candidates.append(os.path.join(root, 'emulator', 'emulator'))

    local_app_data = os.environ.get('LOCALAPPDATA', '').strip()
    if local_app_data:
        candidates.append(
            os.path.join(local_app_data, 'Android', 'Sdk', 'emulator', 'emulator.exe')
        )

    home = os.path.expanduser('~')
    candidates.append(os.path.join(home, 'Library', 'Android', 'sdk', 'emulator', 'emulator'))
    candidates.append(os.path.join(home, 'Android', 'Sdk', 'emulator', 'emulator'))

    for path in candidates:
        if os.path.isfile(path):
            return path

    return shutil.which('emulator')


# ── 私有工具函数 ───────────────────────────────────────────────────────────────

def _list_avd_names(emulator_exe: str) -> list[str]:
    """通过 `emulator -list-avds` 获取所有已创建的 AVD 名称。"""
    try:
        result = subprocess.run(
            [emulator_exe, '-list-avds'],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]
    except Exception as exc:  # noqa: BLE001
        logger.warning('Failed to list AVDs via emulator -list-avds: %s', exc)
        return []


def _list_running_serials() -> list[str]:
    """通过 `adb devices` 获取正在运行的 AVD serial（格式：emulator-XXXX）。"""
    try:
        from adbutils import adb
        return [d.serial for d in adb.device_list() if d.serial and d.serial.startswith('emulator-')]
    except Exception as exc:  # noqa: BLE001
        logger.warning('Failed to list running AVD serials: %s', exc)
        return []


def _fetch_avd_name(serial: str) -> str | None:
    match = re.match(r'^emulator-(\d+)$', serial)
    if not match:
        return None
    port = int(match.group(1))
    try:
        import socket
        with socket.create_connection(('127.0.0.1', port), timeout=2) as sock:
            sock.recv(1024) # 读欢迎消息
            sock.sendall(b'avd name\n')
            time.sleep(0.2)
            data = sock.recv(1024).decode('utf-8', errors='ignore')
        lines = [
            line.strip()
            for line in data.splitlines()
            if line.strip() and line.strip() != 'OK'
        ]
        if lines:
            return lines[0]
    except Exception:  # noqa: BLE001
        pass
    return None


# ── AvdInstance ───────────────────────────────────────────────────────────────

class AvdInstance(CommonAdbCreateDeviceMixin, Instance[AdbHostConfig]):
    """代表一个 AVD（Android Virtual Device）实例。

    由 AvdHost 创建，使用 ADB serial（emulator-XXXX）标识设备，无需 adb connect。
    启动时强制使用 cold boot（-no-snapshot-load），避免快照状态污染自动化流程。
    """

    def __init__(
        self,
        avd_name: str,
        emulator_exe: str,
        serial: str | None = None,
        extra_args: str = '',
    ) -> None:
        super().__init__(
            id=avd_name,
            name=avd_name,
            adb_ip='127.0.0.1',
            # adb_port 保持 None：让 CommonAdbCreateDeviceMixin 走 AdbTargetUsb 路径
            adb_port=None,
            adb_name=avd_name,
            adb_serial=serial,   # e.g. "emulator-5554"，未启动时为 None
        )
        self._avd_name = avd_name
        self._emulator_exe = emulator_exe
        self._extra_args: list[str] = extra_args.split() if extra_args.strip() else []
        self._process: subprocess.Popen | None = None
        self.started_by_us: bool = False

    def refresh(self) -> None:
        """重新扫描运行状态，更新 adb_serial。"""
        running_serials = _list_running_serials()
        # 已有 serial 且仍在运行：无需更新
        if self.adb_serial and self.adb_serial in running_serials:
            logger.debug('Refresh AVD "%s": serial %s still running.', self._avd_name, self.adb_serial)
            return
        # serial 失效或尚未获取：重新按名称匹配
        found = None
        for serial in running_serials:
            if _fetch_avd_name(serial) == self._avd_name:
                found = serial
                break
        if found:
            logger.debug('Refresh AVD "%s": updated serial %s -> %s.', self._avd_name, self.adb_serial, found)
        else:
            logger.debug('Refresh AVD "%s": not running, clearing serial.', self._avd_name)
        self.adb_serial = found

    def running(self) -> bool:
        """判断该 AVD 是否正在运行。"""
        self.refresh()
        return self.adb_serial is not None

    def start(self) -> None:
        """以 cold boot 方式启动 AVD（-no-snapshot-load），并追加用户自定义参数。"""
        cmd = [self._emulator_exe, '-avd', self._avd_name, '-no-snapshot-load', *self._extra_args]
        logger.info('Starting AVD (cold boot): %s', ' '.join(cmd))
        self._process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.started_by_us = True

    def stop(self) -> None:
        """停止 AVD。"""
        if self.adb_serial:
            try:
                from adbutils import adb
                adb.device(self.adb_serial).shell('reboot -p')
                logger.info('Sent power-off to %s', self.adb_serial)
                return
            except Exception as exc:  # noqa: BLE001
                logger.warning('Power-off failed, falling back to process termination: %s', exc)
        if self._process is not None:
            logger.info('Terminating AVD process (pid=%s): %s', self._process.pid, self._avd_name)
            self._process.terminate()
            try:
                self._process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._process.kill()
            self._process = None

    def create_device(self, impl: AdbRecipes, host_config: AdbHostConfig) -> Device:
        """创建设备连接。AVD 自动注册到 ADB，无需 adb connect。"""
        if self.adb_serial is None:
            raise RuntimeError(
                f'AVD "{self._avd_name}" 尚未运行或尚未发现 ADB serial，'
                '请先启动 AVD 并调用 wait_available()。'
            )
        return super().create_device(impl, host_config, connect=False, disconnect=False)

    def wait_available(self, timeout: float = 180) -> None:
        """等待 AVD 完全启动并可用。

        步骤：
        1. 轮询 adb devices，通过 AVD 名称匹配 serial（emulator-XXXX）
        2. 等待设备 state == 'device'
        3. 等待 sys.boot_completed == 1
        """
        from adbutils import adb, AdbError, AdbTimeout

        logger.info('Waiting for AVD "%s" to be available...', self._avd_name)
        cd = Countdown(timeout)
        it = Interval(2)

        # ── 阶段 1：发现 serial ────────────────────────────────────────────────
        if not self.adb_serial:
            logger.debug('Phase 1: discovering serial for AVD "%s"...', self._avd_name)
            while True:
                if cd.expired():
                    raise TimeoutError(
                        f'AVD "{self._avd_name}" 超时未发现 ADB serial（{timeout}s）。'
                    )
                it.wait()
                for serial in _list_running_serials():
                    if _fetch_avd_name(serial) == self._avd_name:
                        self.adb_serial = serial
                        logger.info('Discovered serial for AVD "%s": %s', self._avd_name, serial)
                        break
                if self.adb_serial:
                    break

        # ── 阶段 2：等待设备 state == 'device' ───────────────────────────────
        logger.debug('Phase 2: waiting for device state (serial=%s)...', self.adb_serial)
        d = None
        while True:
            if cd.expired():
                raise TimeoutError(
                    f'AVD "{self._avd_name}" 超时未进入 device 状态（{timeout}s）。'
                )
            it.wait()
            try:
                d = adb.device(self.adb_serial)
                if d.get_state() == 'device':
                    logger.debug('Device state ready: %s', self.adb_serial)
                    break
            except (AdbError, AdbTimeout):
                continue

        # ── 阶段 3：等待系统启动完成 ───────────────────────────────────────────
        logger.debug('Phase 3: waiting for boot_completed (serial=%s)...', self.adb_serial)
        while True:
            if cd.expired():
                raise TimeoutError(
                    f'AVD "{self._avd_name}" 超时未完成启动（{timeout}s）。'
                )
            it.wait()
            try:
                ret = d.shell('getprop sys.boot_completed')
                if isinstance(ret, str) and ret.strip() == '1':
                    logger.debug('Boot completed: %s', self.adb_serial)
                    break
            except (AdbError, AdbTimeout):
                continue

        time.sleep(1)
        logger.info('AVD "%s" (%s) is now available.', self._avd_name, self.adb_serial)


# ── AvdHost ───────────────────────────────────────────────────────────────────

class AvdHost:
    """AVD 宿主，封装 Android SDK emulator 工具。

    持有用户配置的 SDK 路径（可为空，空时自动查找），
    提供 installed / list / query 等发现接口，与 kotonebot 内置 host 结构一致。
    """

    def __init__(self, sdk_path: str | None = None) -> None:
        self._sdk_path = sdk_path
        self._emulator_exe: str | None = find_emulator_exe(sdk_path)

    def installed(self) -> bool:
        """返回 emulator 可执行文件是否可用。"""
        return self._emulator_exe is not None

    def list(self) -> list[AvdInstance]:
        """列出所有已创建的 AVD，并标注运行状态（adb_serial）。"""
        if not self.installed():
            raise EmulatorNotFoundError('Android SDK emulator')
        assert self._emulator_exe is not None, 'This cannot happen'  # for type checker
        avd_names = _list_avd_names(self._emulator_exe)
        running_serials = _list_running_serials()

        name_to_serial: dict[str, str] = {}
        for serial in running_serials:
            name = _fetch_avd_name(serial)
            if name:
                name_to_serial[name] = serial

        return [
            AvdInstance(
                avd_name=name,
                emulator_exe=self._emulator_exe,
                serial=name_to_serial.get(name),
            )
            for name in avd_names
        ]

    def query(self, name: str) -> AvdInstance | None:
        """按 AVD 名称查找实例，找不到时返回 None。"""
        for inst in self.list():
            if inst._avd_name == name:
                return inst
        return None
