import time
import logging
import threading
import os
import uuid
from typing import TYPE_CHECKING, Callable, Any

from kotonebot.client.device import Device, Size
from kotonebot.client.scaler import ProportionalScaler
from iaa.config.schemas import CustomEmulatorData, MuMuEmulatorData, PhysicalAndroidData
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
    emulator: str,
    resolution_method: str,
    package_name: str
) -> str | None:
    """
    设置设备分辨率。
    
    :param device: 设备实例
    :param emulator: 模拟器类型 ('mumu', 'mumu_v5', 'custom', 'physical_android')
    :param resolution_method: 分辨率设置方式 ('auto', 'keep', 'wm_size')
    :param package_name: 游戏包名，用于 kill 游戏
    :return: 原始物理分辨率，用于恢复；如果不需修改则返回 None
    """
    if resolution_method == 'keep':
        logger.debug('Resolution method is "keep", skip resolution setup.')
        return None
    
    if resolution_method == 'auto':
        if emulator != 'physical_android':
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
                    return
                self.__running = True
                # 启动阶段结束
                self.is_starting = False
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
                logger.exception("Scheduler runner crashed: %s", e)
                if self.on_error:
                    try:
                        self.on_error(e)
                    except Exception:
                        logger.exception("Error handler raised an exception")
            finally:
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
        from kotonebot.client.host.protocol import HostProtocol, Instance
        impl = self.iaa.config.conf.game.control_impl
        emulator = self.iaa.config.conf.game.emulator
        check_emulator = bool(self.iaa.config.conf.game.check_emulator)
        emulator_data = self.iaa.config.conf.game.emulator_data

        def _maybe_start(instance: Instance) -> None:
            if check_emulator and not instance.running():
                logger.info('Emulator is not running, starting: %s', instance)
                instance.start()
                instance.wait_available()

        def _resolve_mumu_instance(host_cls: type[HostProtocol], host_name: str) -> Instance:
            def _check(id: str):
                if host_cls is Mumu12V5Host and host_cls.check_app_keptlive(id):
                    raise RuntimeError(
                        '检测到当前模拟器 MuMu 12 已开启“应用保活”功能。\n'
                        '请前往 MuMu 模拟器设置 → 其他 → 后台挂机时保活运行 中关闭，然后重新尝试。'
                    ) 

            instance_id = emulator_data.instance_id if isinstance(emulator_data, MuMuEmulatorData) else None
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

        if emulator == 'mumu':
            host = _resolve_mumu_instance(Mumu12Host, 'MuMu')
            _maybe_start(host)
            if impl == 'nemu_ipc':
                from kotonebot.client.host.mumu12_host import MuMu12HostConfig
                device = host.create_device('nemu_ipc', MuMu12HostConfig())
            elif impl == 'adb':
                from kotonebot.client.host import AdbHostConfig
                device = host.create_device('adb', AdbHostConfig())
            elif impl == 'scrcpy':
                from kotonebot.client.host import AdbHostConfig
                use_vd = self.iaa.config.conf.game.scrcpy_virtual_display
                device = host.create_device('scrcpy', _build_scrcpy_config(AdbHostConfig().timeout, use_vd))
            elif impl == 'uiautomator':
                from kotonebot.client.host import AdbHostConfig
                device = host.create_device('uiautomator2', AdbHostConfig())
            else:
                raise ValueError(f"Unknown control implementation: {impl}")
        elif emulator == 'mumu_v5':
            host = _resolve_mumu_instance(Mumu12V5Host, 'MuMu v5')
            _maybe_start(host)
            if impl == 'nemu_ipc':
                from kotonebot.client.host.mumu12_host import MuMu12HostConfig
                device = host.create_device('nemu_ipc', MuMu12HostConfig())
            elif impl == 'adb':
                from kotonebot.client.host import AdbHostConfig
                device = host.create_device('adb', AdbHostConfig())
            elif impl == 'scrcpy':
                from kotonebot.client.host import AdbHostConfig
                use_vd = self.iaa.config.conf.game.scrcpy_virtual_display
                device = host.create_device('scrcpy', _build_scrcpy_config(AdbHostConfig().timeout, use_vd))
            elif impl == 'uiautomator':
                from kotonebot.client.host import AdbHostConfig
                device = host.create_device('uiautomator2', AdbHostConfig())
            else:
                raise ValueError(f"Unknown control implementation: {impl}")
        elif emulator == 'custom':
            from kotonebot.client.host import create_custom
            from kotonebot.client.host import AdbHostConfig
            data = emulator_data if isinstance(emulator_data, CustomEmulatorData) else None
            if data is None:
                raise RuntimeError('Custom emulator data is required when emulator is set to custom.')
            adb_ip = data.adb_ip or '127.0.0.1'
            adb_port = data.adb_port or 5555
            emulator_path = data.emulator_path or ''
            emulator_args = data.emulator_args or ''
            instance = create_custom(
                adb_ip=adb_ip,
                adb_port=adb_port,
                adb_name="",
                exe_path=emulator_path,
                emulator_args=emulator_args,
            )
            _maybe_start(instance)
            if impl == 'adb':
                device = instance.create_device('adb', AdbHostConfig())
            elif impl == 'scrcpy':
                use_vd = self.iaa.config.conf.game.scrcpy_virtual_display
                device = instance.create_device('scrcpy', _build_scrcpy_config(AdbHostConfig().timeout, use_vd))
            elif impl == 'uiautomator':
                device = instance.create_device('uiautomator2', AdbHostConfig())
            elif impl == 'nemu_ipc':
                raise ValueError("'nemu_ipc' 实现仅支持 MuMu12，不支持 custom 模拟器。")
            else:
                raise ValueError(f"Unknown control implementation: {impl}")
        elif emulator == 'physical_android':
            from kotonebot.client.host import PhysicalAndroidHost
            from kotonebot.client.host import AdbHostConfig
            data = self.iaa.config.conf.game.emulator_data
            if not isinstance(data, PhysicalAndroidData):
                raise ValueError('physical_android 模式下 emulator_data 必须是 PhysicalAndroidData。')
            adb_serial = (data.adb_serial or '').strip()
            if not adb_serial:
                devices = PhysicalAndroidHost.list()
                if not devices:
                    raise ValueError('未找到任何 USB 设备。请连接设备后重试。')
                usb_host = devices[0]
                logger.info('自动选择 USB 设备: %s', usb_host.id)
            else:
                usb_host = PhysicalAndroidHost.query(id=adb_serial)
                if usb_host is None:
                    raise ValueError(f'找不到 ADB USB 设备: {adb_serial}')
            if not usb_host.running():
                raise ValueError(f'ADB USB 设备不可用: {adb_serial}')
            if impl == 'adb':
                device = usb_host.create_device('adb', AdbHostConfig())
            elif impl == 'scrcpy':
                use_vd = self.iaa.config.conf.game.scrcpy_virtual_display
                device = usb_host.create_device('scrcpy', _build_scrcpy_config(AdbHostConfig().timeout, use_vd))
            elif impl == 'uiautomator':
                device = usb_host.create_device('uiautomator2', AdbHostConfig())
            elif impl == 'nemu_ipc':
                raise ValueError("'nemu_ipc' 实现仅支持 MuMu12，不支持 physical_android。")
            else:
                raise ValueError(f"Unknown control implementation: {impl}")
        else:
            raise ValueError(f"Unknown emulator: {emulator}")
        
        return device

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
        emulator = self.iaa.config.conf.game.emulator
        
        device = self.__create_device()
        device.orientation = 'landscape'
        
        # 设置分辨率
        resolution_method = self.iaa.config.conf.game.resolution_method
        package_name = package_by_server(self.iaa.config.conf.game.server)
        self._original_resolution = _setup_resolution(device, emulator, resolution_method, package_name)
        
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


