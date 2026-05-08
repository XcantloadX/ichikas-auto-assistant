import subprocess
import time

from kotonebot import logging
from kotonebot.client.host.adb_common import AdbRecipes, CommonAdbCreateDeviceMixin
from kotonebot.client.host.protocol import AdbHostConfig, Instance
from kotonebot.client import Device
from kotonebot.util import Countdown, Interval

logger = logging.getLogger(__name__)


class CustomEmulatorInstance(CommonAdbCreateDeviceMixin, Instance[AdbHostConfig]):
    def __init__(
        self,
        adb_ip: str,
        adb_port: int | None,
        device_serial: str | None,
        run_adb_connect: bool,
        wait_start_command: bool,
        start_command: str,
        stop_command: str,
        running_command: str,
    ) -> None:
        super().__init__(
            id='custom',
            name='Custom',
            adb_ip=adb_ip,
            adb_port=adb_port,
            adb_name=None,
            adb_serial=device_serial,
        )
        self._start_command = start_command
        self._stop_command = stop_command
        self._running_command = running_command
        self._run_adb_connect = run_adb_connect
        self._wait_start_command = wait_start_command
        self.started_by_us = False
        self.process: subprocess.Popen | None = None

    def refresh(self) -> None:
        pass

    def start(self) -> None:
        if not self._start_command.strip():
            raise ValueError('Custom emulator start_command is required.')
        logger.info('Starting custom emulator using command: %s', self._start_command)
        self.process = subprocess.Popen(self._start_command, shell=True)
        if self._wait_start_command:
            self.process.wait()
            self.process = None
        self.started_by_us = True

    def stop(self) -> None:
        if self._stop_command.strip():
            logger.info('Stopping custom emulator using command: %s', self._stop_command)
            subprocess.run(self._stop_command, shell=True)
            return
        if not self.process:
            logger.warning('Process is not running.')
            return
        logger.info('Stopping process "%s"...', self.process.pid)
        self.process.terminate()
        self.process.wait()
        self.process = None

    def running(self) -> bool:
        if self._running_command.strip():
            try:
                result = subprocess.run(
                    self._running_command,
                    shell=True,
                    capture_output=True,
                    text=True,
                )
                return result.returncode == 0
            except Exception as exc:  # noqa: BLE001
                logger.warning('Running command failed, fallback to default logic: %s', exc)
        if self.process is not None:
            return True
        return False

    def create_device(self, impl: AdbRecipes, host_config: AdbHostConfig) -> Device:
        return super().create_device(
            impl,
            host_config,
            connect=self._run_adb_connect,
            disconnect=self._run_adb_connect,
        )

    def wait_available(self, timeout: float = 180) -> None:
        from adbutils import adb, AdbTimeout, AdbError
        from adbutils._device import AdbDevice

        port = self.adb_port
        adb_ip = self.adb_ip
        serial = self.adb_serial
        if port is None and not serial:
            raise ValueError('Neither adb_port nor device_serial is set.')

        addr = f'{adb_ip}:{port}' if port is not None else None
        if addr:
            serial = addr

        logger.info('Starting to wait for emulator %s (%s) to be available...', self.name, serial)
        state = 1 if port is not None else 2
        cd = Countdown(timeout)
        it = Interval(1)
        d: AdbDevice | None = None

        while True:
            if cd.expired():
                raise TimeoutError(f'Emulator "{self.name}" is not available.')
            it.wait()
            try:
                match state:
                    case 1:
                        if not self._run_adb_connect:
                            logger.debug('Skip adb connect for %s(%s).', self.name, addr)
                            state = 2
                            continue
                        logger.debug('Connecting to emulator %s(%s)...', self.name, addr)
                        if addr and adb.connect(addr, timeout=0.5):
                            logger.debug('Connect to emulator %s(%s) success.', self.name, addr)
                            state = 2
                    case 2:
                        logger.debug('Getting device list...')
                        if devices := adb.device_list():
                            logger.debug('Get device list success. devices=%s', devices)
                            d = next((d for d in devices if d.serial == serial), None)
                            if d:
                                logger.debug('Get target device success. d=%s', d)
                                state = 3
                    case 3:
                        if not d:
                            logger.warning('Device is None.')
                            state = 2
                            continue
                        logger.debug('Waiting for device state...')
                        if d.get_state() == 'device':
                            logger.debug('Device state ready. state=%s', d.get_state())
                            state = 4
                    case 4:
                        if not d:
                            logger.warning('Device is None.')
                            state = 2
                            continue
                        logger.debug('Waiting for device boot completed...')
                        ret = d.shell('getprop sys.boot_completed')
                        if isinstance(ret, str) and ret.strip() == '1':
                            logger.debug('Device boot completed. ret=%s', ret)
                            state = 5
                    case 5:
                        if not d:
                            logger.warning('Device is None.')
                            state = 2
                            continue
                        app = d.app_current()
                        logger.debug('Waiting for launcher... (current=%s)', app)
                        if app and 'launcher' in app.package:
                            logger.info('Emulator %s(%s) now is available.', self.name, serial)
                            state = 6
                    case 6:
                        break
            except (AdbError, AdbTimeout):
                state = 1 if port is not None else 2
                continue

        time.sleep(1)
        logger.info('Emulator %s(%s) now is available.', self.name, serial)
