import time
import logging
import threading
import os
import uuid
from typing import TYPE_CHECKING, Callable, Any

from kotonebot.client.device import Device, Size
from kotonebot.client.scaler import ProportionalScaler
from iaa.config.schemas import MuMuDevice, CustomDevice, NoDevice, PlayCoverDevice, TcpConnection, UsbConnection
from iaa.application.service.custom_emulator import CustomEmulatorInstance
from iaa.definitions.consts import package_by_server
from iaa.utils import asset_path

if TYPE_CHECKING:
    from .iaa_service import IaaService
from iaa.tasks.registry import REGULAR_TASKS, name_from_id
from iaa.tasks.registry import MANUAL_TASKS
from iaa.context import init as init_config_context
from iaa.context import set_task_reporter, reset_task_reporter, hub as progress_hub
from iaa.progress import TaskProgressEvent, TaskReporter

logger = logging.getLogger(__name__)
SCRCPY_BUNDLED_VERSION = '3.3.1'
TARGET_RESOLUTION = '1280x720'


def _parse_wm_size_output(output: str) -> str | None:
    """
    解析 `wm size` 命令输出，返回原始物理分辨率。
    
    输出格式示例：
    - "Physical size: 1080x1920"
    - "Physical size: 1080x1920\\nOverride size: 1280x720"
    """
    import re
    match = re.search(r'Physical size:\s*(\d+x\d+)', output)
    if match:
        return match.group(1)
    return None


def _setup_resolution(
    device: 'Device',
    is_physical_device: bool,
    resolution_method: str,
    package_name: str
) -> str | None:
    """
    设置设备分辨率。

    :param device: 设备实例
    :param is_physical_device: 是否为物理设备（NoDevice lifecycle）
    :param resolution_method: 分辨率设置方式 ('auto', 'keep', 'wm_size')
    :param package_name: 游戏包名，用于 kill 游戏
    :return: 原始物理分辨率，用于恢复；如果不需修改则返回 None
    """
    if resolution_method == 'keep':
        logger.debug('Resolution method is "keep", skip resolution setup.')
        return None

    if resolution_method == 'auto':
        if not is_physical_device:
            logger.debug('Resolution method is "auto" but not physical device, skip resolution setup.')
            return None
    
    result = device.commands.adb_shell('wm size')
    original = _parse_wm_size_output(result)
    
    if original is None:
        logger.warning('Failed to parse wm size output: %s', result)
        return None
    
    if original == TARGET_RESOLUTION:
        logger.debug('Current resolution is already %s, skip.', TARGET_RESOLUTION)
        return None
    
    # device.commands.adb_shell(f'am force-stop {package_name}')
    # logger.info('Killed game package: %s', package_name)
    # time.sleep(1)

    device.commands.adb_shell(f'wm size {TARGET_RESOLUTION}')
    logger.info('Set resolution from %s to %s', original, TARGET_RESOLUTION)
    time.sleep(0.5)

    # 然后再启动
    device.commands.launch_app(package_name)
    

    return original


def _restore_resolution(device: 'Device', original_resolution: str) -> None:
    """
    恢复设备分辨率。
    
    :param device: 设备实例
    :param original_resolution: 原始分辨率
    """
    try:
        device.commands.adb_shell('wm size reset')
        logger.info('Reset resolution to original.')
    except Exception as e:
        logger.warning('Failed to reset resolution: %s', e)


class SchedulerService:
    def __init__(self, iaa_service: 'IaaService'):
        self.iaa = iaa_service
        self._thread: threading.Thread | None = None
        self.__running: bool = False
        self.__stop_requested: bool = False
        self.is_starting: bool = False
        """是否正在启动"""
        self.is_stopping: bool = False
        """是否正在停止"""
        self.on_error: Callable[[Exception], None] | None = None
        """
        任务发生错误时执行的回调函数。注意，调用可能来自其他线程。
        
        仅在异步执行任务时有效。同步执行任务可自行 try-except。
        """
        self.current_task_id: str | None = None
        """当前正在执行的任务 ID"""
        self.current_task_name: str | None = None
        """当前正在执行的任务名称"""
        self.device: Device | None = None
        """当前正在执行的任务的设备"""
        self._device_started: bool = False
        """设备生命周期是否已启动"""
        self._original_resolution: str | None = None
        """原始分辨率，用于恢复"""
        self._connect_thread: threading.Thread | None = None
        """设备连接线程"""

    @property
    def running(self) -> bool:
        """调度器是否正在运行。"""
        return self.__running

    # -------------------- Shared runner --------------------
    def __start_tasks(
        self,
        get_tasks: Callable[[], list[tuple[str, Callable[[], None]]]],
        *,
        thread_name: str,
        run_in_thread: bool = True,
    ) -> None:
        """执行指定任务"""
        # 已在运行则忽略
        if self._thread and self._thread.is_alive():
            logger.warning("Scheduler already running, skip start.")
            return

        self.is_starting = True

        def _runner() -> None:
            run_id = uuid.uuid4().hex
            completion_status: str = 'success'
            try:
                logger.info("Preparing context...")
                self.__prepare_context()
                if self.device is None:
                    raise RuntimeError("Device not initialized after context preparation.")
                self.device.start()
                self._device_started = True
                logger.info("Scheduler started.")
                tasks = get_tasks()
                if not tasks:
                    logger.info("No tasks to run. Exiting...")
                    completion_status = 'no_tasks'
                    return
                self.__running = True
                # 启动阶段结束
                self.is_starting = False
                if self.iaa.config.conf.developer.screen_recording_enabled:
                    try:
                        from iaa.application.service.screen_recorder import start_recording
                        start_recording()
                    except Exception as e:
                        logger.warning('Failed to start screen recording: %s', e)
                total_tasks = len(tasks)
                for index, (task_id, func) in enumerate(tasks):
                    self.current_task_id = task_id
                    self.current_task_name = name_from_id(task_id)
                    task_name = self.current_task_name
                    progress_hub().publish(
                        TaskProgressEvent(
                            run_id=run_id,
                            task_id=task_id,
                            task_name=task_name,
                            timestamp=time.time(),
                            type='task_started',
                            payload={
                                'message': '开始执行',
                                'run_total_tasks': total_tasks,
                                'run_completed_tasks': index,
                                'run_current_task_index': index + 1,
                            },
                        )
                    )
                    token = set_task_reporter(
                        TaskReporter(
                            hub=progress_hub(),
                            run_id=run_id,
                            task_id=task_id,
                            task_name=task_name,
                        )
                    )
                    try:
                        logger.info(f"Running task: {task_id} ({task_name})")
                        func()
                        logger.info(f"Task finished: {task_id} ({task_name})")
                        progress_hub().publish(
                            TaskProgressEvent(
                                run_id=run_id,
                                task_id=task_id,
                                task_name=task_name,
                                timestamp=time.time(),
                                type='task_finished',
                                payload={
                                    'message': '执行完成',
                                    'percent': 100,
                                    'run_total_tasks': total_tasks,
                                    'run_completed_tasks': index + 1,
                                    'run_current_task_index': index + 1,
                                },
                            )
                        )
                    except KeyboardInterrupt:
                        completion_status = 'interrupted'
                        progress_hub().publish(
                            TaskProgressEvent(
                                run_id=run_id,
                                task_id=task_id,
                                task_name=task_name,
                                timestamp=time.time(),
                                type='task_failed',
                                payload={
                                    'message': f'任务中断：{task_name}',
                                    'error': 'KeyboardInterrupt',
                                    'run_total_tasks': total_tasks,
                                    'run_completed_tasks': index,
                                    'run_current_task_index': index + 1,
                                },
                            )
                        )
                        logger.info("KeyboardInterrupt received. Stopping scheduler.")
                        break
                    except Exception as e:  # noqa: BLE001
                        completion_status = 'failed'
                        progress_hub().publish(
                            TaskProgressEvent(
                                run_id=run_id,
                                task_id=task_id,
                                task_name=task_name,
                                timestamp=time.time(),
                                type='task_failed',
                                payload={
                                    'message': f'执行失败：{task_name}',
                                    'error': str(e),
                                    'run_total_tasks': total_tasks,
                                    'run_completed_tasks': index,
                                    'run_current_task_index': index + 1,
                                },
                            )
                        )
                        logger.exception(f"Task '{task_id}' raised an exception: {e}")
                        if self.on_error:
                            try:
                                self.on_error(e)
                            except Exception:
                                logger.exception("Error handler raised an exception")
                        break
                    finally:
                        reset_task_reporter(token)
                        self.current_task_id = None
                        self.current_task_name = None
            except Exception as e:  # noqa: BLE001
                completion_status = 'crashed'
                logger.exception("Scheduler runner crashed: %s", e)
                if self.on_error:
                    try:
                        self.on_error(e)
                    except Exception:
                        logger.exception("Error handler raised an exception")
            finally:
                if self.iaa.config.conf.developer.screen_recording_enabled:
                    try:
                        from iaa.application.service.screen_recorder import stop_recording
                        stop_recording()
                    except Exception as e:
                        logger.warning('Failed to stop screen recording: %s', e)
                if self.device is not None and self._original_resolution is not None:
                    _restore_resolution(self.device, self._original_resolution)
                    self._original_resolution = None
                if self.device is not None and self._device_started:
                    try:
                        self.device.stop()
                    finally:
                        self._device_started = False
                self.device = None
                self._thread = None
                self.__running = False
                # 停止阶段结束
                if self.__stop_requested:
                    self.is_stopping = False
                    self.__stop_requested = False
                from kotonebot.backend.context import vars
                try:
                    vars.flow.clear_interrupt()
                except Exception:
                    logger.exception("Failed to clear flow interrupt state.")
                # 若在准备阶段失败，也需要复位启动标记
                self.is_starting = False
                logger.info("Scheduler stopped.")

                # 发送通知
                if completion_status != 'no_tasks':
                    from iaa.notify import send_notification
                    from iaa.config.manager import read_shared
                    shared_config = read_shared()
                    message_map = {
                        'success': '任务执行完成',
                        'interrupted': '任务已中断',
                        'failed': '任务执行失败',
                        'crashed': '调度器发生错误',
                    }
                    send_notification('iaa', message_map.get(completion_status, '任务结束'), shared_config.notify)

        if run_in_thread:
            self._thread = threading.Thread(target=_runner, name=thread_name, daemon=True)
            self._thread.start()
        else:
            _runner()

    def start_regular(self, run_in_thread: bool = True) -> None:
        """
        启动常规任务调度。
        """
        def _get() -> list[tuple[str, Callable[[], None]]]:
            return self._get_enabled_tasks()
        self.__start_tasks(_get, thread_name="IAA-Scheduler", run_in_thread=run_in_thread)
    
    def stop(self, block: bool = False) -> None:
        """
        请求停止任务执行并回收线程。

        :param block: 是否阻塞直至线程停止。
        """
        if not self.__running or self._thread is None:
            logger.warning("Scheduler not running, skip stop.")
            return
        from kotonebot.backend.context import vars
        self.__stop_requested = True
        self.is_stopping = True
        vars.flow.request_interrupt()
        if block:
            self._thread.join()
        # Note: device.stop() and resolution restore are handled in finally block of _runner

    def run_single(
        self,
        task_id: str,
        run_in_thread: bool = True,
        args: tuple[Any, ...] | None = None,
        kwargs: dict[str, Any] | None = None,
    ) -> None:
        """运行单个任务。"""
        tasks = MANUAL_TASKS.copy()
        tasks.update(REGULAR_TASKS)
        if task_id not in tasks:
            raise ValueError(f"Unknown manual task: {task_id}")
        task_func = tasks[task_id]
        call_args = args or ()
        call_kwargs = kwargs or {}

        def _call() -> None:
            task_func(*call_args, **call_kwargs)

        def _get() -> list[tuple[str, Callable[[], None]]]:
            return [(task_id, _call)]
        self.__start_tasks(_get, thread_name="IAA-Scheduler-Manual", run_in_thread=run_in_thread)

    def __create_device(self) -> 'Device':
        """
        创建设备实例。

        .. NOTE::
            需要和任务执行在同一个线程中调用。
        """
        from kotonebot.client.host import Mumu12Host, Mumu12V5Host
        from kotonebot.client.host import AdbHostConfig
        from kotonebot.client.host.protocol import HostProtocol, Instance

        device_conf = self.iaa.config.conf.device
        lifecycle = device_conf.lifecycle
        connection = device_conf.connection
        impl = device_conf.control_impl
        use_vd = device_conf.scrcpy_virtual_display

        def _maybe_start(instance: Instance) -> None:
            check = lifecycle.check_and_start if isinstance(lifecycle, (MuMuDevice, CustomDevice)) else False
            if check and not instance.running():
                logger.info('Device is not running, starting: %s', instance)
                instance.start()
                instance.wait_available()

        def _resolve_mumu_instance(host_cls: type[HostProtocol], host_name: str, instance_id: str | None) -> Instance:
            def _check(id: str):
                if host_cls is Mumu12V5Host and host_cls.check_app_keptlive(id):
                    raise RuntimeError(
                        '检测到当前模拟器 MuMu 12 已开启"应用保活"功能。\n'
                        '请前往 MuMu 模拟器设置 → 其他 → 后台挂机时保活运行 中关闭，然后重新尝试。'
                    )

            if instance_id is not None:
                instance = host_cls.query(id=instance_id)
                if instance is None:
                    raise RuntimeError(f'{host_name} instance not found: {instance_id}')
                _check(instance.id)
                return instance

            hosts = host_cls.list()
            if not hosts:
                raise RuntimeError(f'No {host_name} host found.')
            _check(hosts[0].id)
            return hosts[0]

        def _build_scrcpy_config(timeout: float, use_virtual_display: bool):
            from kotonebot.client.implements.scrcpy import ScrcpyConfig, VirtualDisplayConfig

            jar_path = asset_path('scrcpy.jar')
            if not os.path.isfile(jar_path):
                raise FileNotFoundError(f'Scrcpy jar not found: {jar_path}')

            virtual_display_config = None
            if use_virtual_display:
                virtual_display_config = VirtualDisplayConfig(
                    enabled=True,
                    reuse_existing=True,
                    launch_package=package_by_server(self.iaa.config.conf.game.server),
                    width=1280,
                    height=720,
                    system_decorations=False
                )

            return ScrcpyConfig(
                timeout=timeout,
                server_jar_path=jar_path,
                server_version=SCRCPY_BUNDLED_VERSION,
                virtual_display=virtual_display_config,
            )

        def _apply_impl(host) -> 'Device':
            if impl == 'nemu_ipc':
                from kotonebot.client.host.mumu12_host import MuMu12HostConfig
                return host.create_device('nemu_ipc', MuMu12HostConfig())
            elif impl == 'adb':
                return host.create_device('adb', AdbHostConfig())
            elif impl == 'scrcpy':
                return host.create_device('scrcpy', _build_scrcpy_config(AdbHostConfig().timeout, use_vd))
            elif impl == 'uiautomator':
                return host.create_device('uiautomator2', AdbHostConfig())
            else:
                raise ValueError(f"Unknown control implementation: {impl}")

        # ── Step 1：按 lifecycle 类型解析 host ────────────────────────────────

        if isinstance(lifecycle, MuMuDevice):
            host_cls = Mumu12Host if lifecycle.type == 'mumu' else Mumu12V5Host
            host_name = 'MuMu' if lifecycle.type == 'mumu' else 'MuMu v5'
            host = _resolve_mumu_instance(host_cls, host_name, lifecycle.instance_id)
            _maybe_start(host)
            if impl == 'nemu_ipc':
                pass  # nemu_ipc 支持 MuMu
            elif impl in ('adb', 'scrcpy', 'uiautomator'):
                pass
            else:
                raise ValueError(f"Unknown control implementation: {impl}")
            return _apply_impl(host)

        elif isinstance(lifecycle, CustomDevice):
            start_command = (lifecycle.start_command or '').strip()
            if not start_command:
                raise ValueError('自定义设备的启动命令不能为空。')

            if isinstance(connection, TcpConnection):
                if connection.run_adb_connect and connection.port is None:
                    raise ValueError('TCP 连接已启用 adb connect，但未填写端口。')
                adb_ip = connection.ip
                adb_port = connection.port if connection.run_adb_connect else None
                device_serial = (connection.device_serial or '').strip() or None
                run_adb_connect = connection.run_adb_connect
            elif isinstance(connection, UsbConnection):
                adb_ip = '127.0.0.1'
                adb_port = None
                device_serial = (connection.device_serial or '').strip() or None
                run_adb_connect = False
                if not device_serial:
                    raise ValueError('USB 连接模式下，自定义设备需要填写设备序列号。')
            else:
                raise ValueError('自定义设备不支持自动连接（auto）模式，请选择 USB 或 TCP。')

            custom_instance = CustomEmulatorInstance(
                adb_ip=adb_ip,
                adb_port=adb_port,
                device_serial=device_serial,
                run_adb_connect=run_adb_connect,
                wait_start_command=lifecycle.wait_start_command,
                start_command=start_command,
                stop_command=(lifecycle.stop_command or '').strip(),
                running_command=(lifecycle.running_command or '').strip(),
            )
            self._custom_emulator_instance = custom_instance
            _maybe_start(custom_instance)
            if impl == 'nemu_ipc':
                raise ValueError("'nemu_ipc' 仅支持 MuMu，不支持自定义设备。")
            return _apply_impl(custom_instance)

        elif isinstance(lifecycle, NoDevice):
            from kotonebot.client.host import PhysicalAndroidHost

            if isinstance(connection, UsbConnection):
                adb_serial = (connection.device_serial or '').strip()
                if not adb_serial:
                    devices = PhysicalAndroidHost.list()
                    if not devices:
                        raise ValueError('未找到任何 USB 设备，请连接设备后重试。')
                    host = devices[0]
                    logger.info('自动选择 USB 设备: %s', host.id)
                else:
                    host = PhysicalAndroidHost.query(id=adb_serial)
                    if host is None:
                        raise ValueError(f'找不到 ADB USB 设备: {adb_serial}')
                if not host.running():
                    raise ValueError(f'ADB USB 设备不可用: {host.id}')
                if impl == 'nemu_ipc':
                    raise ValueError("'nemu_ipc' 仅支持 MuMu，不支持物理设备。")
                return _apply_impl(host)

            elif isinstance(connection, TcpConnection):
                from iaa.application.service.custom_emulator import CustomEmulatorInstance
                if connection.port is None:
                    raise ValueError('TCP 连接需要填写端口。')
                tcp_instance = CustomEmulatorInstance(
                    adb_ip=connection.ip,
                    adb_port=connection.port,
                    device_serial=(connection.device_serial or '').strip() or None,
                    run_adb_connect=connection.run_adb_connect,
                    wait_start_command=False,
                    start_command='',
                    stop_command='',
                    running_command='',
                )
                if impl == 'nemu_ipc':
                    raise ValueError("'nemu_ipc' 仅支持 MuMu，不支持物理设备。")
                return _apply_impl(tcp_instance)

            else:
                raise ValueError('设备类型为"无"时，连接方式不能为自动，请选择 USB 或 TCP。')

        elif isinstance(lifecycle, PlayCoverDevice):
            from kotonebot.client.playcover import Playcover
            from iaa.definitions.consts import bundle_id_by_server

            bundle_id = bundle_id_by_server(self.iaa.config.conf.game.server)
            app = Playcover.find(bundle_id)
            if app is None:
                raise ValueError(f'未找到 PlayCover 应用：{bundle_id}')

            if lifecycle.check_and_start and not app.running():
                logger.info('PlayCover app not running, launching: %s', bundle_id)
                app.launch()
                app.wait_available(timeout=60)

            if not app.running():
                raise RuntimeError('游戏未在运行。请启动游戏，或在配置里启用「检查并启动」。')

            return app.create_device()

        else:
            raise ValueError(f"Unknown lifecycle type: {type(lifecycle)}")

    def connect_device(self, on_success: Callable[[], None] | None = None, on_error: Callable[[Exception], None] | None = None) -> None:
        """
        在后台线程中连接设备。

        :param on_success: 连接成功后的回调。
        :param on_error: 连接失败后的回调。
        """
        if self.device is not None:
            if on_success:
                on_success()
            return
        
        if self._connect_thread is not None and self._connect_thread.is_alive():
            return
        
        def _connect() -> None:
            try:
                logger.info("Connecting to device...")
                device = self.__create_device()
                device.orientation = 'landscape'
                device.start()
                self.device = device
                self._device_started = True
                logger.info("Device connected successfully.")
                if on_success:
                    on_success()
            except Exception as e:
                logger.exception("Failed to connect device: %s", e)
                if on_error:
                    on_error(e)
        
        self._connect_thread = threading.Thread(target=_connect, name="IAA-DeviceConnect", daemon=True)
        self._connect_thread.start()

    def capture_screenshot(self):
        """
        获取当前设备截图。

        优先复用调度器当前持有的设备；若当前未持有设备，则临时创建设备、
        启动、截图，并在完成后立即清理。
        """
        if self.device is not None:
            return self.device.screenshot()

        logger.info("No active scheduler device. Creating a temporary device for screenshot capture.")
        device = self.__create_device()
        device.orientation = 'landscape'
        started = False
        try:
            device.start()
            started = True
            return device.screenshot()
        finally:
            if started:
                try:
                    device.stop()
                except Exception:
                    logger.exception("Failed to stop temporary screenshot device.")

    def __prepare_context(self) -> None:
        """
        初始化配置上下文与设备上下文。

        .. NOTE::
            需要和任务执行在同一个线程中调用。
        """
        # 因为导入 kotonebot 开销较大，这里延迟导入
        from kotonebot.backend.context.context import init_context

        device = self.__create_device()
        device.orientation = 'landscape'

        # 设置分辨率（PlayCover 不走 ADB，直接跳过）
        device_conf = self.iaa.config.conf.device
        if not isinstance(device_conf.lifecycle, PlayCoverDevice):
            is_physical = isinstance(device_conf.lifecycle, NoDevice)
            package_name = package_by_server(self.iaa.config.conf.game.server)
            self._original_resolution = _setup_resolution(device, is_physical, device_conf.resolution_method, package_name)
        else:
            self._original_resolution = None
        
        init_context(target_device=device, force=True)
        self.device = device

        # 初始化框架全局配置
        from kotonebot.config import conf
        from iaa.tasks.globals import data_download
        conf().loop.loop_callbacks = [
            data_download,
        ]
        conf().device.default_logic_resolution = Size(1280, 720)
        conf().device.default_scaler_factory = ProportionalScaler

        # 初始 contextvars
        logger.debug("Initializing configuration context...")
        init_config_context(self.iaa.config.conf)
        server = self.iaa.config.conf.game.server
        logger.debug("Setting game server to %s", server)
        from iaa.tasks import R
        R.current_variant.set(server)

    def _get_enabled_tasks(self) -> list[tuple[str, Callable[[], None]]]:
        """根据配置返回启用的任务列表，顺序与 REGULAR_TASKS 保持一致。"""
        conf = self.iaa.config.conf
        tasks: list[tuple[str, Callable[[], None]]] = []
        for name, func in REGULAR_TASKS.items():
            if conf.scheduler.is_enabled(name):
                tasks.append((name, func))
        return tasks


