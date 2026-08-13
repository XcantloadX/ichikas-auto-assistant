from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Literal, cast

from kotonebot.client.host.protocol import Instance
from kotonebot.client.playcover import PlaycoverApp
from kotonebot.errors import UserFriendlyError

from iaa.application.service.avd import AvdInstance
from iaa.application.service.custom_emulator import CustomEmulatorInstance
from iaa.config.schemas import (
    AvdDevice,
    CustomDevice,
    DeviceConfig,
    MuMuDevice,
    NoDevice,
    PlayCoverDevice,
    TcpConnection,
    UsbConnection,
)
from iaa.definitions.consts import package_by_server
from iaa.platform import env
from iaa.platform.device_android.device import SelfAndroidDevice
from iaa.utils import asset_path

_SCRCPY_BUNDLED_VERSION = '3.3.1'

if TYPE_CHECKING:
    from kotonebot.client.device import Device
    from kotonebot.client.host import AdbHostConfig
    from kotonebot.client.host.protocol import HostProtocol

ResolvedHostTarget = Instance[Any] | PlaycoverApp | SelfAndroidDevice

logger = logging.getLogger(__name__)


class LifecyclePolicy(Enum):
    """设备生命周期策略。"""

    REQUIRE_RUNNING = 'require_running'
    """必须已在运行，否则报错（画面预览用）。"""

    CHECK_AND_START = 'check_and_start'
    """按 lifecycle 的 ``check_and_start`` 决定是否自动启动（任务执行用）。"""


@dataclass
class ResolvedHost:
    """lifecycle 解析结果。只含 host/instance，不含 device driver。

    把 scheduler 原本散落在 _maybe_start / _stop_lifecycle 里的"是否由我启动"
    状态显式化，交还调用方决定何时 stop。
    """

    host: ResolvedHostTarget
    """已解析的可运行 host / instance 对象（非 HostProtocol 类本身）。"""

    started_by_us: bool
    """本次是否由 factory 启动 host。"""

    stop_callback: Callable[[], None] | None
    """``started_by_us`` 为真时的 ``host.stop`` 回调，否则为 ``None``。"""

    impl: str
    """透传 / 短路标记（如 ``'playcover'``），供 :meth:`DeviceFactory.create_device` 分发。"""


class DeviceFactory:
    """所有设备创建的单一入口。

    两条轴：
      resolve_host()  —— 轴 1：lifecycle 解析（MuMu / Custom / NoDevice / Avd / PlayCover）
      create_device() —— 轴 2：impl 选择（nemu_ipc / adb / scrcpy / uiautomator2 / qemu_grpc / playcover）
    """

    def __init__(self, config_service) -> None:
        """创建设备工厂。

        :param config_service: 配置服务，需提供 ``conf`` 属性以读取当前设备与游戏配置。
        """
        self._config = config_service

    def resolve_host(
        self,
        device_conf: DeviceConfig,
        *,
        policy: LifecyclePolicy,
        impl_hint: str,
    ) -> ResolvedHost:
        """按 lifecycle 类型解析出可运行的 host/instance。

        纯 lifecycle 轴，不做 impl 分发（AVD + qemu_grpc 的启动前准备为例外）。

        :param device_conf: 设备配置。
        :param policy: 生命周期策略，决定未运行时是报错还是尝试启动。
        :param impl_hint: 控制实现提示，用于校验 lifecycle 兼容性，以及 AVD qemu_grpc 启动参数门控。
        :return: 解析结果，含 host 与可选的 ``stop_callback``。
        :raises UserFriendlyError: 设备未运行、类型不兼容或配置无效时。
        :raises ValueError: lifecycle 类型未知或 impl 不支持当前 lifecycle 时。
        :raises RuntimeError: host 查询失败或 MuMu 应用保活冲突时。
        """
        lifecycle = device_conf.lifecycle
        connection = device_conf.connection

        if isinstance(lifecycle, MuMuDevice):
            return self._resolve_mumu(lifecycle, policy=policy, impl_hint=impl_hint)
        if isinstance(lifecycle, CustomDevice):
            return self._resolve_custom(
                lifecycle, connection, policy=policy, impl_hint=impl_hint
            )
        if isinstance(lifecycle, NoDevice):
            return self._resolve_no_device(
                connection, policy=policy, impl_hint=impl_hint
            )
        if isinstance(lifecycle, AvdDevice):
            return self._resolve_avd(
                lifecycle, device_conf, policy=policy, impl_hint=impl_hint
            )
        if isinstance(lifecycle, PlayCoverDevice):
            return self._resolve_playcover(lifecycle, policy=policy)

        raise ValueError(f'Unknown lifecycle type: {type(lifecycle)}')

    def create_device(
        self,
        resolved: ResolvedHost,
        *,
        impl: str,
        use_virtual_display: bool,
        game_server: Literal['jp', 'tw', 'cn'],
    ) -> Device:
        """在已就绪的 host 上创建指定 impl 的 device driver。

        假定 host 已 running（由 :meth:`resolve_host` 保证）。

        :param resolved: :meth:`resolve_host` 的返回结果。
        :param impl: 控制实现，如 ``'nemu_ipc'`` / ``'adb'`` / ``'scrcpy'`` / ``'uiautomator'`` / ``'qemu_grpc'`` / ``'playcover'`` / ``'self_android'``。
        :param use_virtual_display: 是否启用 scrcpy 虚拟屏。
        :param game_server: 游戏服务器标识，用于虚拟屏启动包名解析。
        :return: 已构造、尚未 ``start()`` 的设备实例。
        :raises ValueError: ``impl`` 未知时。
        :raises FileNotFoundError: scrcpy jar 资源缺失时。
        """
        if impl == 'self_android':
            if not isinstance(resolved.host, SelfAndroidDevice):
                raise RuntimeError('self_android requires a SelfAndroidDevice host.')
            return resolved.host

        if impl == 'playcover':
            if not isinstance(resolved.host, PlaycoverApp):
                raise RuntimeError('PlayCover lifecycle resolved to a non-PlaycoverApp host.')
            return resolved.host.create_device()

        if impl == 'qemu_grpc':
            from iaa.application.service.qemu_grpc import create_qemu_grpc_device

            if not isinstance(resolved.host, AvdInstance):
                raise RuntimeError('qemu_grpc requires an AvdInstance host.')
            return create_qemu_grpc_device(resolved.host)

        from kotonebot.client.host import AdbHostConfig
        from kotonebot.client.host.mumu12_host import MuMu12HostConfig

        host = cast(Instance[Any], resolved.host)
        if impl == 'nemu_ipc':
            return host.create_device('nemu_ipc', MuMu12HostConfig())
        if impl == 'adb':
            return host.create_device('adb', AdbHostConfig())
        if impl == 'scrcpy':
            return host.create_device(
                'scrcpy',
                self._build_scrcpy_config(
                    AdbHostConfig(), use_virtual_display, game_server
                ),
            )
        if impl == 'uiautomator':
            return host.create_device('uiautomator2', AdbHostConfig())

        raise ValueError(f'Unknown control implementation: {impl}')

    def create_scrcpy_preview_device(
        self, device_conf: DeviceConfig, game_server: Literal['jp', 'tw', 'cn']
    ) -> Device:
        """为画面页创建 scrcpy 虚拟屏预览设备（不自动启动模拟器）。

        :param device_conf: 设备配置。
        :param game_server: 游戏服务器标识，用于虚拟屏启动包名解析。
        :return: 已构造、尚未 ``start()`` 的 scrcpy 设备实例。
        :raises UserFriendlyError: PlayCover 或设备未运行时。
        """
        if isinstance(device_conf.lifecycle, PlayCoverDevice):
            raise UserFriendlyError('画面预览不支持 PlayCover。')

        resolved = self.resolve_host(
            device_conf,
            policy=LifecyclePolicy.REQUIRE_RUNNING,
            impl_hint='scrcpy',
        )
        return self.create_device(
            resolved,
            impl='scrcpy',
            use_virtual_display=device_conf.scrcpy_virtual_display,
            game_server=game_server,
        )

    def create_device_for_current_config(
        self, *, policy: LifecyclePolicy, impl: str | None = None
    ) -> tuple[ResolvedHost, Device]:
        """scheduler 便捷入口：从当前 config 读取并创建。

        .. NOTE::
            需要和任务执行在同一个线程中调用。

        .. NOTE::
            当运行在 Android（:data:`iaa.platform.env.IS_ANDROID` 为真）时，
            本设备即游戏所在设备，不存在模拟器 / adb 发现，直接短路返回
            ``self_android`` 占位设备，不再走 :meth:`resolve_host`。

        :param policy: 生命周期策略。
        :param impl: 控制实现；默认取 ``config.device.control_impl``。
        :return: ``(resolved, device)`` 元组，其中 ``resolved.stop_callback`` 供调用方写入 ``_stop_lifecycle``。
        :raises UserFriendlyError: 设备未运行、类型不兼容或配置无效时。
        :raises ValueError: lifecycle 类型未知或 impl 不支持当前 lifecycle 时。
        :raises RuntimeError: host 查询失败或 MuMu 应用保活冲突时。
        """
        if env.IS_ANDROID:
            return self._create_self_android()

        conf = self._config.conf
        impl = impl or conf.device.control_impl
        resolved = self.resolve_host(
            conf.device, policy=policy, impl_hint=impl
        )
        device = self.create_device(
            resolved,
            impl=impl,
            use_virtual_display=conf.device.scrcpy_virtual_display,
            game_server=conf.game.server,
        )
        return resolved, device

    def _create_self_android(self) -> tuple[ResolvedHost, Device]:
        """在 Android 自身设备上创建占位 host + device。

        Android 上没有模拟器发现这一环节：把占位 host 与占位设备直接拼好，
        返回与桌面一致的 ``(resolved, device)`` 元组，让 scheduler 的
        ``__prepare_context`` 能照常 ``init_context`` 拿到 self device。

        .. NOTE::
            host 即占位设备对象本身（``impl='self_android'``），
            ``create_device`` 分发时直接返回该 host，不再新建实例。

        :return: ``(resolved, device)``，其中 ``impl`` 为 ``'self_android'``。
        """
        device = SelfAndroidDevice()
        resolved = ResolvedHost(
            host=device,
            started_by_us=False,
            stop_callback=None,
            impl='self_android',
        )
        return resolved, device

    def _not_running_message(
        self,
        *,
        host_name: str,
        policy: LifecyclePolicy,
        instance_id: str | None = None,
    ) -> str:
        label = host_name
        if instance_id is not None:
            label = f'{host_name}（实例 {instance_id}）'
        if policy is LifecyclePolicy.CHECK_AND_START:
            return (
                f'模拟器 {label} 未运行。'
                '请手动启动模拟器，或在设备设置中勾选「检测并自动启动」。'
            )
        return (
            f'模拟器 {label} 未运行。'
            '请先运行任务（将自动启动模拟器），或手动启动模拟器后再启动设备。'
        )

    def _maybe_start(
        self,
        instance: Instance,
        *,
        check_and_start: bool,
        policy: LifecyclePolicy,
    ) -> tuple[bool, Callable[[], None] | None]:
        """启动实例（若需要）。返回 (started_by_us, stop_callback)。"""
        if policy is LifecyclePolicy.REQUIRE_RUNNING:
            return False, None
        if check_and_start and not instance.running():
            logger.info('Device is not running, starting: %s', instance)
            instance.start()
            instance.wait_available()
            return True, instance.stop
        return False, None

    def _require_running(
        self,
        instance: Instance,
        *,
        host_name: str,
        policy: LifecyclePolicy,
        instance_id: str | None = None,
    ) -> None:
        if not instance.running():
            raise UserFriendlyError(
                self._not_running_message(
                    host_name=host_name,
                    policy=policy,
                    instance_id=instance_id,
                )
            )

    def _resolve_mumu_instance(
        self,
        host_cls: type[HostProtocol],
        host_name: str,
        instance_id: str | None,
    ) -> Instance:
        from kotonebot.client.host import Mumu12V5Host

        def _check_keptlive(id: str) -> None:
            if host_cls is Mumu12V5Host and host_cls.check_app_keptlive(id):
                raise RuntimeError(
                    '检测到当前模拟器 MuMu 12 已开启"应用保活"功能。\n'
                    '请前往 MuMu 模拟器设置 → 其他 → 后台挂机时保活运行 中关闭，然后重新尝试。'
                )

        if instance_id is not None:
            instance = host_cls.query(id=instance_id)
            if instance is None:
                raise RuntimeError(f'{host_name} instance not found: {instance_id}')
            _check_keptlive(instance.id)
            return instance

        hosts = host_cls.list()
        if not hosts:
            raise RuntimeError(f'No {host_name} host found.')
        _check_keptlive(hosts[0].id)
        return hosts[0]

    def _resolve_mumu(
        self,
        lifecycle: MuMuDevice,
        *,
        policy: LifecyclePolicy,
        impl_hint: str,
    ) -> ResolvedHost:
        from kotonebot.client.host import Mumu12Host, Mumu12V5Host

        host_cls = Mumu12Host if lifecycle.type == 'mumu' else Mumu12V5Host
        host_name = 'MuMu' if lifecycle.type == 'mumu' else 'MuMu v5'
        host = self._resolve_mumu_instance(host_cls, host_name, lifecycle.instance_id)

        started_by_us, stop_callback = self._maybe_start(
            host,
            check_and_start=lifecycle.check_and_start,
            policy=policy,
        )
        if not started_by_us:
            self._require_running(
                host,
                host_name=host_name,
                policy=policy,
                instance_id=lifecycle.instance_id,
            )

        if impl_hint == 'nemu_ipc':
            pass  # nemu_ipc 支持 MuMu
        elif impl_hint in ('adb', 'scrcpy', 'uiautomator'):
            pass
        else:
            raise ValueError(f'Unknown control implementation: {impl_hint}')

        return ResolvedHost(
            host=host,
            started_by_us=started_by_us,
            stop_callback=stop_callback,
            impl=impl_hint,
        )

    def _resolve_custom(
        self,
        lifecycle: CustomDevice,
        connection,
        *,
        policy: LifecyclePolicy,
        impl_hint: str,
    ) -> ResolvedHost:
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

        started_by_us, stop_callback = self._maybe_start(
            custom_instance,
            check_and_start=lifecycle.check_and_start,
            policy=policy,
        )
        if not started_by_us and policy is LifecyclePolicy.REQUIRE_RUNNING:
            self._require_running(custom_instance, host_name='模拟器', policy=policy)

        if impl_hint == 'nemu_ipc':
            raise UserFriendlyError(
                "'nemu_ipc' 控制方式仅支持 MuMu 模拟器，不支持自定义设备。请在设备设置中更换控制方式。"
            )

        return ResolvedHost(
            host=custom_instance,
            started_by_us=started_by_us,
            stop_callback=stop_callback,
            impl=impl_hint,
        )

    def _resolve_no_device(
        self,
        connection,
        *,
        policy: LifecyclePolicy,
        impl_hint: str,
    ) -> ResolvedHost:
        from kotonebot.client.host import PhysicalAndroidHost

        if isinstance(connection, UsbConnection):
            adb_serial = (connection.device_serial or '').strip()
            if not adb_serial:
                devices = PhysicalAndroidHost.list()
                if not devices:
                    raise UserFriendlyError('未找到任何 USB 设备，请连接设备后重试。')
                host = devices[0]
                logger.info('自动选择 USB 设备: %s', host.id)
            else:
                host = PhysicalAndroidHost.query(id=adb_serial)
                if host is None:
                    raise UserFriendlyError(
                        f'找不到 ADB USB 设备：{adb_serial}。请确认设备已连接并授权 ADB 调试。'
                    )
            if not host.running():
                raise UserFriendlyError(f'ADB USB 设备不可用: {host.id}')
            if impl_hint == 'nemu_ipc':
                raise UserFriendlyError(
                    "'nemu_ipc' 控制方式仅支持 MuMu 模拟器，不支持物理设备。请在设备设置中更换控制方式。"
                )
            return ResolvedHost(
                host=host,
                started_by_us=False,
                stop_callback=None,
                impl=impl_hint,
            )

        if isinstance(connection, TcpConnection):
            if connection.port is None:
                raise UserFriendlyError('TCP 连接需要填写端口。')
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
            if impl_hint == 'nemu_ipc':
                raise UserFriendlyError(
                    "'nemu_ipc' 控制方式仅支持 MuMu 模拟器，不支持物理设备。请在设备设置中更换控制方式。"
                )
            return ResolvedHost(
                host=tcp_instance,
                started_by_us=False,
                stop_callback=None,
                impl=impl_hint,
            )

        raise UserFriendlyError('设备类型为"无"时，连接方式不能为自动，请选择 USB 或 TCP。')

    def _resolve_avd(
        self,
        lifecycle: AvdDevice,
        device_conf: DeviceConfig,
        *,
        policy: LifecyclePolicy,
        impl_hint: str,
    ) -> ResolvedHost:
        from iaa.application.service.avd import AvdHost

        avd_host = AvdHost(sdk_path=lifecycle.sdk_path)
        if lifecycle.avd_name:
            avd_instance = avd_host.query(lifecycle.avd_name)
            if avd_instance is None:
                raise RuntimeError(f'未找到 AVD："{lifecycle.avd_name}"')
        else:
            instances = avd_host.list()
            if not instances:
                raise RuntimeError('未找到任何 AVD，请先通过 Android Studio 创建 AVD。')
            avd_instance = instances[0]

        # AVD + qemu_grpc：impl 信息泄漏进 lifecycle 解析的唯一例外。
        avd_instance._extra_args = (
            lifecycle.extra_args.split() if lifecycle.extra_args.strip() else []
        )

        # qemu_grpc 直接读取硬件帧缓冲，wm size 无法改变实际分辨率。
        if impl_hint == 'qemu_grpc' and device_conf.resolution_method != 'keep':
            raise UserFriendlyError(
                'QEMU gRPC 模式不支持自动修改分辨率，请在「分辨率设置」中选择「保持原始分辨率」，'
                '并在 AVD Manager 中预先将 LCD 分辨率配置为 1280x720。'
            )

        # qemu_grpc 需要 AVD 以 -grpc <port> 启动；若用户未在 extra_args 中指定则注入默认端口。
        if impl_hint == 'qemu_grpc' and '-grpc' not in avd_instance._extra_args:
            avd_instance._extra_args += ['-grpc', '8554']
        # emulator 的 gRPC 服务默认拒绝所有未鉴权请求（streamScreenshot/sendTouch
        # 均在 allowlist 的 protected 列表中），需要显式启用 -grpc-use-token，
        # 配合 qemu_grpc.py 从 discovery 文件读取明文 token 并附加到每次调用。
        # 若用户已自行配置了 -grpc-use-token/-grpc-use-jwt 则尊重其选择。
        if impl_hint == 'qemu_grpc' and not any(
            a.startswith('-grpc-use-') for a in avd_instance._extra_args
        ):
            avd_instance._extra_args += ['-grpc-use-token']

        started_by_us, stop_callback = self._maybe_start(
            avd_instance,
            check_and_start=lifecycle.check_and_start,
            policy=policy,
        )
        if not started_by_us and policy is LifecyclePolicy.REQUIRE_RUNNING:
            self._require_running(avd_instance, host_name='模拟器', policy=policy)

        if impl_hint == 'nemu_ipc':
            raise UserFriendlyError(
                "'nemu_ipc' 控制方式仅支持 MuMu 模拟器，不支持 AVD。请在设备设置中更换控制方式。"
            )

        return ResolvedHost(
            host=avd_instance,
            started_by_us=started_by_us,
            stop_callback=stop_callback,
            impl=impl_hint,
        )

    def _resolve_playcover(
        self,
        lifecycle: PlayCoverDevice,
        *,
        policy: LifecyclePolicy,
    ) -> ResolvedHost:
        from kotonebot.client.playcover import Playcover
        from iaa.definitions.consts import bundle_id_by_server

        bundle_id = bundle_id_by_server(self._config.conf.game.server)
        app = Playcover.find(bundle_id)
        if app is None:
            raise ValueError(f'未找到 PlayCover 应用：{bundle_id}')

        started_by_us = False
        stop_callback = None
        if policy is LifecyclePolicy.CHECK_AND_START:
            if lifecycle.check_and_start and not app.running():
                logger.info('PlayCover app not running, launching: %s', bundle_id)
                app.launch()
                app.wait_available(timeout=60)
                started_by_us = True
                stop_callback = app.terminate

        if not app.running():
            if policy is LifecyclePolicy.CHECK_AND_START:
                raise RuntimeError('游戏未在运行。请启动游戏，或在配置里启用「检查并启动」。')
            raise UserFriendlyError(
                '游戏未在运行。请先运行任务（将自动启动模拟器），或手动启动游戏后再启动设备。'
            )

        return ResolvedHost(
            host=app,
            started_by_us=started_by_us,
            stop_callback=stop_callback,
            impl='playcover',
        )

    @staticmethod
    def _build_scrcpy_config(
        adb_config: 'AdbHostConfig',
        use_virtual_display: bool,
        game_server: Literal['jp', 'tw', 'cn'],
    ):
        from kotonebot.client.implements.scrcpy import ScrcpyConfig, VirtualDisplayConfig

        jar_path = asset_path('scrcpy.jar')
        if not os.path.isfile(jar_path):
            raise FileNotFoundError(f'Scrcpy jar not found: {jar_path}')

        virtual_display_config = None
        if use_virtual_display:
            virtual_display_config = VirtualDisplayConfig(
                enabled=True,
                reuse_existing=True,
                launch_package=package_by_server(game_server),
                width=1280,
                height=720,
                system_decorations=False,
            )

        return ScrcpyConfig(
            timeout=adb_config.timeout,
            server_jar_path=jar_path,
            server_version=_SCRCPY_BUNDLED_VERSION,
            virtual_display=virtual_display_config,
        )