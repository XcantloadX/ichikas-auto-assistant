import time
import logging
import threading
import uuid
from typing import TYPE_CHECKING, Callable, Any

from kotonebot.client.device import Device, Size
from kotonebot.client.scaler import ProportionalScaler
from kotonebot.errors import DeviceConnectionError
from iaa.config.schemas import NoDevice, PlayCoverDevice, AvdDevice
from iaa.application.service.device_factory import DeviceFactory, LifecyclePolicy
from iaa.definitions.consts import package_by_server

if TYPE_CHECKING:
    from .iaa_service import IaaService
from iaa.tasks.registry import TASK_INFOS, name_from_id
from iaa.context import init as init_config_context
from iaa.context import set_task_reporter, reset_task_reporter, hub as progress_hub
from iaa.progress import TaskProgressEvent, TaskReporter

logger = logging.getLogger(__name__)
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
    def __init__(self, iaa_service: 'IaaService', on_thread_start: 'Callable[[], None] | None' = None, on_prepare_context: 'Callable[[], None] | None' = None):
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
        self._flow_controller = None
        """当前运行线程的 FlowController 直接引用，用于跨线程安全中断。"""
        self._on_thread_start: 'Callable[[], None] | None' = on_thread_start
        """线程启动时的钩子，在任何日志输出之前调用（可在此处设置 ContextVar 等线程级初始化）。"""
        self._on_prepare_context: 'Callable[[], None] | None' = on_prepare_context
        """上下文准备完毕后的钩子（可在此处通过传入回调自定义 ContextVar 初始化逻辑）。"""
        self.device: Device | None = None
        """当前正在执行的任务的设备"""
        self._device_started: bool = False
        """设备生命周期是否已启动"""
        self._original_resolution: str | None = None
        """原始分辨率，用于恢复"""
        self._connect_thread: threading.Thread | None = None
        """设备连接线程"""
        self._stop_lifecycle: 'Callable[[], None] | None' = None
        """完成后关闭模拟器的回调，仅本次由 iaa 启动时设置"""
        # TODO: _ensure_device_started 放在这里看起来有点 hacky。需要讨论一个更好的设计？
        self._ensure_device_started: Callable[[], None] | None = None
        """scrcpy 虚拟屏模式下由 Tab 注入，任务启动前同步等待 UI 虚拟屏就绪。"""
        self._device_factory: DeviceFactory | None = DeviceFactory(iaa_service.config)
        """设备创建入口；GUI 下由 TabManager 按 tab 注入，与 config 绑定。"""

    def _require_device_factory(self) -> DeviceFactory:
        if self._device_factory is None:
            raise RuntimeError('DeviceFactory is not available.')
        return self._device_factory

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
            # 最先设置线程级 ContextVar（log bridge、tab name 等），确保启动阶段日志也能路由到 GUI
            if self._on_thread_start is not None:
                self._on_thread_start()
            run_id = uuid.uuid4().hex
            completion_status: str = 'success'
            try:
                logger.info("Preparing context...")
                self.__prepare_context()
                if self.device is None:
                    raise RuntimeError("Device not initialized after context preparation.")
                if not self._device_started:
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
                        if not self.iaa.config.conf.scheduler.continue_on_error:
                            break
                    finally:
                        reset_task_reporter(token)
                        self.current_task_id = None
                        self.current_task_name = None
            except Exception as e:  # noqa: BLE001
                completion_status = 'crashed'
                if isinstance(e, DeviceConnectionError):
                    logger.exception("Device connection failed: %s", e)
                else:
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
                if self._stop_lifecycle is not None and self.iaa.config.conf.device.stop_on_finish:
                    try:
                        logger.info('Stopping lifecycle instance.')
                        self._stop_lifecycle()
                    except Exception as e:
                        logger.warning('Failed to stop lifecycle instance: %s', e)
                self._stop_lifecycle = None
                self._flow_controller = None
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
        self.__stop_requested = True
        self.is_stopping = True
        if self._flow_controller is not None:
            self._flow_controller.request_interrupt()
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
        if task_id not in TASK_INFOS:
            raise ValueError(f"Unknown manual task: {task_id}")
        task_func = TASK_INFOS[task_id].func
        call_args = args or ()
        call_kwargs = kwargs or {}

        def _call() -> None:
            task_func(*call_args, **call_kwargs)

        def _get() -> list[tuple[str, Callable[[], None]]]:
            return [(task_id, _call)]
        self.__start_tasks(_get, thread_name="IAA-Scheduler-Manual", run_in_thread=run_in_thread)

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
                resolved, device = self._require_device_factory().create_device_for_current_config(
                    policy=LifecyclePolicy.CHECK_AND_START
                )
                self._stop_lifecycle = resolved.stop_callback
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
        resolved, device = self._require_device_factory().create_device_for_current_config(
            policy=LifecyclePolicy.CHECK_AND_START
        )
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
            # 若本次由 factory 启动了 lifecycle 实例，截图后一并回收。
            if resolved.stop_callback is not None:
                try:
                    resolved.stop_callback()
                except Exception:
                    logger.exception("Failed to stop temporary screenshot lifecycle.")

    def __prepare_context(self) -> None:
        """
        初始化配置上下文与设备上下文。

        .. NOTE::
            需要和任务执行在同一个线程中调用。
        """
        # 因为导入 kotonebot 开销较大，这里延迟导入
        from kotonebot.backend.context.context import init_context

        if self._ensure_device_started is not None:
            self._ensure_device_started()

        resolved, device = self._require_device_factory().create_device_for_current_config(
            policy=LifecyclePolicy.CHECK_AND_START
        )
        self._stop_lifecycle = resolved.stop_callback  # 原本在 _maybe_start 里设置
        device.orientation = 'landscape'

        # 设置分辨率（PlayCover 不走 ADB，直接跳过）
        device_conf = self.iaa.config.conf.device
        if not isinstance(device_conf.lifecycle, PlayCoverDevice):
            # AvdDevice 和 NoDevice 均需走 wm size 路径（_setup_resolution 内部判重跳过）
            is_physical = isinstance(device_conf.lifecycle, (NoDevice, AvdDevice))
            package_name = package_by_server(self.iaa.config.conf.game.server)
            self._original_resolution = _setup_resolution(device, is_physical, device_conf.resolution_method, package_name)
        else:
            self._original_resolution = None
        
        init_context(target_device=device, force=True)
        from kotonebot.backend.context.context import get_context
        _ctx = get_context()
        if _ctx is not None:
            self._flow_controller = _ctx.vars.flow
        if self._on_prepare_context is not None:
            self._on_prepare_context()
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
        return [
            (info.task_id, info.func)
            for info in TASK_INFOS.values()
            if info.kind == 'regular'
            and info.get_enabled is not None
            and info.get_enabled(conf)
        ]


