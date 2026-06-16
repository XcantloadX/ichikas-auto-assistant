"""
QEMU gRPC 截图与触摸实现。

Android Emulator（AVD/QEMU）内置了一个 gRPC 服务（EmulatorController），
与 Android Studio 设备管理器使用相同接口。本模块通过该服务直接读取截图、
注入触摸事件，不经过 ADB/USB 层，延迟更低。

使用前提：启动 AVD 时需传入 ``-grpc <port>`` 参数（默认 8554）。
scheduler 在 lifecycle=avd + impl=qemu_grpc 时会自动注入该参数。

鉴权说明
--------
Android Emulator 的 gRPC 服务默认拒绝所有未鉴权请求（见
``<sdk>/emulator/lib/emulator_access.json`` 的 allowlist，未匹配的方法
永远被拒绝），``streamScreenshot`` / ``sendTouch`` 均在此列。
scheduler 因此还会注入 ``-grpc-use-token``，emulator 启动后会在
discovery 文件（``pid_<qemu_pid>.ini``，位置见 ``_discovery_dirs``）中
写出明文 ``grpc.token``。``create_qemu_grpc_device`` 通过 ``grpc.port``
字段匹配到对应 discovery 文件并读取该 token，之后每次 gRPC 调用都附带
``authorization: Bearer <token>`` metadata。

Proto 说明
----------
截图使用 ``streamScreenshot``（gRPC server-side streaming），
请求 format=RGBA8888(1) 使服务端返回 RGBA8888 裸像素（format=PNG(0) 返回 PNG 编码），
后台线程持续消费最新帧，``screenshot()`` 零阻塞返回。
触摸使用 ``sendTouch``（一元 RPC）。
请求/响应消息仅覆盖本模块所需的字段，手动编解码（见 _encode_* / _decode_*）。

参考协议定义：
  https://android.googlesource.com/platform/external/qemu/+/refs/heads/master/
  android/android-emu/android/emulation/control/emulator_controller.proto
"""

from __future__ import annotations

import logging
import os
import sys
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING, Literal, cast

import cv2
import numpy as np
from cv2.typing import MatLike
from google.protobuf import descriptor_pb2, descriptor_pool, message_factory

from kotonebot.client.protocol import (
    AndroidCommandable,
    Lifecycle,
    MultiTouchable,
    Screenshotable,
    TouchDriver,
)

if TYPE_CHECKING:
    from iaa.application.service.avd import AvdInstance
    from kotonebot.client.device import Device

_DEFAULT_GRPC_PORT = 8554
_GRPC_CALL_TIMEOUT = 30.0
_STREAM_DEADLINE = 300.0
_STREAM_RECONNECT_DELAY = 2.0
_METHOD_STREAM_SCREENSHOT = '/android.emulation.control.EmulatorController/streamScreenshot'
_METHOD_TOUCH = '/android.emulation.control.EmulatorController/sendTouch'
_TOKEN_LOOKUP_TIMEOUT = 10.0

logger = logging.getLogger(__name__)


# ── gRPC 鉴权 token 发现 ────────────────────────────────────────────────────


def _discovery_dirs() -> list[Path]:
    """返回各平台 emulator discovery 目录的候选路径（不保证存在）。

    参考官方 aemu-grpc 库（android/android-grpc/python/aemu-grpc）的发现逻辑：
    每个候选根目录下实际文件位于 ``<root>/avd/running/pid_<qemu_pid>.ini``。
    """
    roots: list[Path] = []
    if sys.platform == 'win32':
        local_app_data = os.environ.get('LOCALAPPDATA', '').strip()
        if local_app_data:
            roots.append(Path(local_app_data) / 'Temp')
    elif sys.platform == 'darwin':
        roots.append(Path.home() / 'Library' / 'Caches' / 'TemporaryItems')
    else:
        xdg_runtime = os.environ.get('XDG_RUNTIME_DIR', '').strip()
        if xdg_runtime:
            roots.append(Path(xdg_runtime))
        else:
            roots.append(Path('/run/user') / str(os.getuid()))  # type: ignore[attr-defined]
    roots.append(Path.home() / '.android')  # 各平台均会兜底扫描这个目录
    return [root / 'avd' / 'running' for root in roots]


def _parse_discovery_ini(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    try:
        text = path.read_text(encoding='utf-8', errors='ignore')
    except OSError:
        return result
    for line in text.splitlines():
        line = line.strip()
        if not line or '=' not in line:
            continue
        key, _, value = line.partition('=')
        result[key.strip()] = value.strip()
    return result


def _find_grpc_token(grpc_port: int, timeout: float = _TOKEN_LOOKUP_TIMEOUT) -> str | None:
    """在 discovery 目录中查找指定 ``grpc_port`` 对应实例的鉴权 token。

    discovery 文件由 emulator 进程启动时写出，可能比 AVD 启动调用稍晚出现，
    因此这里短暂轮询。

    找到对应实例但未写出 ``grpc.token``（用户自行在 extra_args 中配置了
    ``-grpc-use-jwt`` 而非 ``-grpc-use-token``）时返回 None——这种情况下
    本模块本来就不支持 JWT 鉴权，调用方需自行决定如何处理。

    若在超时时间内始终找不到对应 discovery 文件，则直接抛错而不是静默
    返回 None：scheduler 已经强制注入 ``-grpc-use-token``，正常情况下
    discovery 文件必然存在；找不到大概率是发现逻辑本身的问题（路径不对/
    权限/emulator 版本不兼容），继续无鉴权调用只会让后续陷入与本问题
    相同的 UNAUTHENTICATED 重连死循环，不如尽早暴露。
    """
    deadline = time.monotonic() + timeout
    while True:
        for d in _discovery_dirs():
            if not d.is_dir():
                continue
            for ini in d.glob('pid_*.ini'):
                data = _parse_discovery_ini(ini)
                if data.get('grpc.port') == str(grpc_port):
                    return data.get('grpc.token')
        if time.monotonic() >= deadline:
            raise RuntimeError(
                f'QemuGrpcImpl: 未找到 grpc.port={grpc_port} 对应的 emulator '
                f'discovery 文件（已等待 {timeout:.0f}s）。请确认 AVD 已正常启动。'
            )
        time.sleep(0.5)


# ── Protobuf 描述符 ───────────────────────────────────────────────────────────
_ImageClass = None


def _get_image_class():
    global _ImageClass
    if _ImageClass is not None:
        return _ImageClass

    fdp = descriptor_pb2.FileDescriptorProto()
    fdp.name = '_qemu_grpc.proto'
    fdp.package = '_qemu'
    fdp.syntax = 'proto3'

    e = fdp.enum_type.add()
    e.name = '_Fmt'
    e.value.add(name='ZERO', number=0)
    e.value.add(name='PNG', number=1)

    rot = fdp.message_type.add()
    rot.name = '_Rot'
    r1 = rot.field.add()
    r1.name = 'r'
    r1.number = 1
    r1.type = descriptor_pb2.FieldDescriptorProto.TYPE_ENUM
    r1.type_name = '._qemu._Fmt'
    r1.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL

    imgfmt = fdp.message_type.add()
    imgfmt.name = '_ImageFormat'
    f1 = imgfmt.field.add()
    f1.name = 'fmt'
    f1.number = 1
    f1.type = descriptor_pb2.FieldDescriptorProto.TYPE_ENUM
    f1.type_name = '._qemu._Fmt'
    f1.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    f2 = imgfmt.field.add()
    f2.name = 'rot'
    f2.number = 2
    f2.type = descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE
    f2.type_name = '._qemu._Rot'
    f2.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    f3 = imgfmt.field.add()
    f3.name = 'w'
    f3.number = 3
    f3.type = descriptor_pb2.FieldDescriptorProto.TYPE_UINT32
    f3.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    f4 = imgfmt.field.add()
    f4.name = 'h'
    f4.number = 4
    f4.type = descriptor_pb2.FieldDescriptorProto.TYPE_UINT32
    f4.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL

    img = fdp.message_type.add()
    img.name = '_Image'
    i1 = img.field.add()
    i1.name = 'fmt'
    i1.number = 1
    i1.type = descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE
    i1.type_name = '._qemu._ImageFormat'
    i1.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    i4 = img.field.add()
    i4.name = 'img'
    i4.number = 4
    i4.type = descriptor_pb2.FieldDescriptorProto.TYPE_BYTES
    i4.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL

    serialized = fdp.SerializeToString()
    pool = descriptor_pool.Default()
    pool.AddSerializedFile(serialized)
    _ImageClass = message_factory.GetMessageClass(
        pool.FindMessageTypeByName('_qemu._Image')
    )
    return _ImageClass


# 模块加载时预热，避免线程首次调用时的竞态
_get_image_class()


# ── Touch 编解码 ──────────────────────────────────────────────────────────────


def _enc_varint(n: int) -> bytes:
    buf = bytearray()
    while n > 0x7F:
        buf.append(0x80 | (n & 0x7F))
        n >>= 7
    buf.append(n)
    return bytes(buf)


def _varint_field(field_no: int, value: int) -> bytes:
    return _enc_varint((field_no << 3) | 0) + _enc_varint(value)


def _bytes_field(field_no: int, data: bytes) -> bytes:
    return _enc_varint((field_no << 3) | 2) + _enc_varint(len(data)) + data


def _encode_touch(x: int, y: int, identifier: int, pressure: bool) -> bytes:
    out = _varint_field(1, x)
    out += _varint_field(2, y)
    out += _varint_field(3, identifier)
    out += _varint_field(4, 1 if pressure else 0)
    return out


def _encode_touch_event(touches: list[tuple[int, int, int, bool]]) -> bytes:
    out = b''
    for touch in touches:
        out += _bytes_field(1, _encode_touch(*touch))
    return out


# ── QemuGrpcImpl ──────────────────────────────────────────────────────────────


class QemuGrpcImpl(
    Screenshotable, Lifecycle, TouchDriver, MultiTouchable, AndroidCommandable
):
    """
    通过 Android Emulator gRPC 服务（EmulatorController）截图与触摸控制。

    后台线程持续从 streamScreenshot 消费帧并覆盖存储最新原始数据，
    screenshot() 零阻塞，始终返回最新帧。

    截图路径：streamScreenshot → RGBA8888 裸像素 → 后台线程解析 → BGRA → BGR
    触摸路径：gRPC sendTouch
    设备命令：通过 adbutils 调用 ADB shell 实现。
    """

    max_contacts: int = 10
    _FIRST_FRAME_TIMEOUT = 120.0

    def __init__(self, grpc_port: int, adb_serial: str, token: str | None = None) -> None:
        from adbutils import adb

        self._port = grpc_port
        self._adb = adb.device(adb_serial)
        self._token = token
        self._channel = None
        self._fn_touch = None
        self._stop_event = threading.Event()
        self._consumer_thread: threading.Thread | None = None
        self._latest: tuple[bytes, int, int] | None = None
        self._first_frame_event = threading.Event()
        self._width: int = 0
        self._height: int = 0

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        import grpc

        self._channel = grpc.insecure_channel(
            f'localhost:{self._port}',
            # 消费者线程在 next() 上阻塞，channel 关闭后 next() 立即退出
            options=[('grpc.use_local_subchannel_pool', 1)],
        )
        self._fn_touch = self._channel.unary_unary(_METHOD_TOUCH)
        self._stop_event.clear()
        self._first_frame_event.clear()

        self._consumer_thread = threading.Thread(
            target=self._consumer_loop, daemon=True, name='qemu-grpc-consumer'
        )
        self._consumer_thread.start()

        logger.info('QemuGrpcImpl: consumer thread started (localhost:%d)', self._port)

    def stop(self) -> None:
        self._stop_event.set()
        if self._channel:
            self._channel.close()
        if self._consumer_thread and self._consumer_thread.is_alive():
            self._consumer_thread.join(timeout=5)
        self._channel = None
        self._fn_touch = None
        self._consumer_thread = None

    # ── 鉴权 ──────────────────────────────────────────────────────────────

    @property
    def _auth_metadata(self) -> list[tuple[str, str]] | None:
        if not self._token:
            return None
        return [('authorization', f'Bearer {self._token}')]

    # ── 后台消费者 ─────────────────────────────────────────────────────────

    def _open_stream(self):
        if self._channel is None:
            raise RuntimeError('gRPC channel not initialized')
        call = self._channel.unary_stream(_METHOD_STREAM_SCREENSHOT)
        return call(
            _varint_field(1, 1), # ImageFormat{format=RGBA8888(1)}
            timeout=_STREAM_DEADLINE,
            metadata=self._auth_metadata,
        )

    def _consumer_loop(self) -> None:
        import grpc

        logger.debug('QemuGrpcImpl: consumer loop started')
        stream_iter = None

        while not self._stop_event.is_set():
            if stream_iter is None:
                try:
                    stream_iter = self._open_stream()
                    logger.debug('QemuGrpcImpl: stream established')
                except grpc.RpcError as exc:
                    if self._stop_event.is_set():
                        break
                    logger.warning(
                        'QemuGrpcImpl: stream open failed (%s), retry in %.0fs',
                        exc.code(),
                        _STREAM_RECONNECT_DELAY,
                    )
                    self._stop_event.wait(_STREAM_RECONNECT_DELAY)
                    continue

            try:
                resp = next(stream_iter)
            except StopIteration:
                stream_iter = None
                logger.debug('QemuGrpcImpl: stream ended, reconnecting')
                continue
            except grpc.RpcError as exc:
                stream_iter = None
                if self._stop_event.is_set():
                    break
                if exc.code() == grpc.StatusCode.FAILED_PRECONDITION:
                    logger.debug('QemuGrpcImpl: display not ready yet, retry...')
                    self._stop_event.wait(_STREAM_RECONNECT_DELAY)
                else:
                    logger.warning(
                        'QemuGrpcImpl: stream error %s, reconnecting in %.0fs',
                        exc.code(),
                        _STREAM_RECONNECT_DELAY,
                    )
                    self._stop_event.wait(_STREAM_RECONNECT_DELAY)
                continue

            # 用 protobuf 库解码 Image 消息，提取 image bytes + 宽高
            try:
                img_cls = _get_image_class()
                obj = img_cls()
                obj.ParseFromString(resp)
                img_bytes = bytes(obj.img)  # type: ignore[attr-defined]
                w = obj.fmt.w  # type: ignore[attr-defined]
                h = obj.fmt.h  # type: ignore[attr-defined]
                if img_bytes and w and h:
                    self._latest = (img_bytes, w, h)
                    self._first_frame_event.set()
                else:
                    logger.warning(
                        'QemuGrpcImpl: incomplete frame (img=%d w=%d h=%d)',
                        len(img_bytes),
                        w,
                        h,
                    )
            except Exception as exc:
                logger.error('QemuGrpcImpl: failed to parse Image proto: %s', exc)

    # ── Screenshotable ────────────────────────────────────────────────────────

    @property
    def screen_size(self) -> tuple[int, int]:
        return self._width, self._height

    def detect_orientation(self) -> Literal['portrait', 'landscape'] | None:
        if not (self._width and self._height):
            self.screenshot()
        if self._width and self._height:
            return 'landscape' if self._width >= self._height else 'portrait'
        return None

    def screenshot(self) -> MatLike:
        if not self._first_frame_event.wait(timeout=self._FIRST_FRAME_TIMEOUT):
            raise TimeoutError(
                'QemuGrpcImpl: no frame received within %.0fs'
                % self._FIRST_FRAME_TIMEOUT
            )

        # 无需加锁。赋值原子操作，而且写方每次写数据都会产生新的 self._latest 对象
        latest = self._latest
        assert latest is not None
        img_bytes, w, h = latest

        arr = np.frombuffer(img_bytes, dtype=np.uint8)
        rgba = arr.reshape(int(h), int(w), 4)
        bgr = cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGR)

        if w != self._width or h != self._height:
            logger.debug(
                'QemuGrpcImpl: display size changed %dx%d → %dx%d',
                self._width,
                self._height,
                w,
                h,
            )
            self._width, self._height = w, h
        return bgr

    # ── TouchDriver ───────────────────────────────────────────────────────────

    def touch_down(self, x: int, y: int, contact_id: int = 0) -> None:
        fn = self._fn_touch
        if fn is None:
            raise RuntimeError('gRPC not started')
        fn(
            _encode_touch_event([(x, y, contact_id, True)]),
            timeout=_GRPC_CALL_TIMEOUT,
            metadata=self._auth_metadata,
        )

    def touch_move(self, x: int, y: int, contact_id: int = 0) -> None:
        fn = self._fn_touch
        if fn is None:
            raise RuntimeError('gRPC not started')
        fn(
            _encode_touch_event([(x, y, contact_id, True)]),
            timeout=_GRPC_CALL_TIMEOUT,
            metadata=self._auth_metadata,
        )

    def touch_up(self, x: int, y: int, contact_id: int = 0) -> None:
        fn = self._fn_touch
        if fn is None:
            raise RuntimeError('gRPC not started')
        fn(
            _encode_touch_event([(x, y, contact_id, False)]),
            timeout=_GRPC_CALL_TIMEOUT,
            metadata=self._auth_metadata,
        )

    # click / swipe 满足 Touchable 结构协议（Device.setup() 检测用）
    # ── MultiTouchable ────────────────────────────────────────────────────────

    def multi_touch_down(self, x: int, y: int, pointer_id: int) -> None:
        self.touch_down(x, y, pointer_id)

    def multi_touch_up(self, x: int, y: int, pointer_id: int) -> None:
        self.touch_up(x, y, pointer_id)

    # ── Touchable ─────────────────────────────────────────────────────────────

    def click(self, x: int, y: int) -> None:
        self.touch_down(x, y)
        self.touch_up(x, y)

    def swipe(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        duration: float | None = None,
    ) -> None:
        dur = duration or 0.3
        steps = max(10, int(dur * 60))
        interval = dur / steps
        self.touch_down(x1, y1)
        for i in range(1, steps):
            t = i / steps
            self.touch_move(
                int(x1 + (x2 - x1) * t),
                int(y1 + (y2 - y1) * t),
            )
            time.sleep(interval)
        self.touch_up(x2, y2)

    # ── AndroidCommandable ────────────────────────────────────────────────────

    def launch_app(self, package_name: str) -> None:
        self._adb.shell(f'monkey -p {package_name} 1')

    def current_package(self) -> str | None:
        result = cast(
            str, self._adb.shell('dumpsys activity top | grep ACTIVITY | tail -n 1')
        ).strip()
        if not result:
            return None
        try:
            _, activity, *_ = result.split(' ')
            return activity.split('/')[0]
        except (ValueError, IndexError):
            logger.warning('QemuGrpcImpl: failed to parse current package: %s', result)
            return None

    def adb_shell(self, cmd: str) -> str:
        return cast(str, self._adb.shell(cmd))

    def install_apk(self, path: str) -> None:
        self._adb.install(path)


def create_qemu_grpc_device(avd_instance: 'AvdInstance') -> 'Device':
    """
    为已启动的 AVD 实例创建使用 QEMU gRPC 后端的 Device。

    gRPC 端口从 avd_instance._extra_args 中的 ``-grpc <port>`` 读取；
    scheduler 在调用本函数前已保证该参数存在。

    :param avd_instance: 已完成 wait_available() 的 AvdInstance。
    :raises RuntimeError: AVD 尚未启动或 serial 未发现。
    """
    if avd_instance.adb_serial is None:
        raise RuntimeError(
            f'AVD "{avd_instance._avd_name}" 的 ADB serial 尚未发现，'
            '请先启动 AVD 并调用 wait_available()。'
        )

    from kotonebot.client.device import AndroidDevice

    try:
        idx = avd_instance._extra_args.index('-grpc')
        port = int(avd_instance._extra_args[idx + 1])
    except (ValueError, IndexError):
        port = _DEFAULT_GRPC_PORT

    token = _find_grpc_token(port)
    impl = QemuGrpcImpl(grpc_port=port, adb_serial=avd_instance.adb_serial, token=token)
    device = AndroidDevice()
    device.setup(components=[impl])
    return device
