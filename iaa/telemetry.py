import logging
import os
import sys
from asyncio import CancelledError

from kotonebot.errors import UserFriendlyError

from iaa import __VERSION__
from iaa.config import manager
from iaa.platform import env

logger = logging.getLogger(__name__)

SENTRY_DSN = 'http://efb1a54675734ab18ae8e6732d31dac0@bugsink.1ichika.de/2'


def _root_dir() -> str:
    return env.app_root()


def _load_shared():
    manager.config_path = os.path.join(_root_dir(), 'conf')
    return manager.read_shared()


def is_dev() -> bool:
    # 桌面保真:源码/调试解释器（以 python 开头的可执行名）视为开发环境。
    # Android 打包版恒为 False（视为生产）,避免 p4a 下 sys.executable 指向
    # 解释器目录而误判为开发环境、意外跳过遥测。
    if env.IS_ANDROID:
        return False
    return os.path.basename(sys.executable).startswith('python')


def is_enabled() -> bool:
    shared = _load_shared()
    return bool(shared.telemetry.sentry)


def setup() -> None:
    if is_dev():
        logger.info('Development mode detected, telemetry disabled.')
        return

    shared = _load_shared()
    if not shared.telemetry.sentry:
        logger.info('Telemetry disabled or pending consent.')
        return

    import sentry_sdk

    sentry_sdk.init(
        SENTRY_DSN,
        send_default_pii=False,
        max_request_body_size='always',
        server_name='iaa',
        release=__VERSION__,
        traces_sample_rate=0,
        send_client_reports=False,
        auto_session_tracking=False,
        ignore_errors=[KeyboardInterrupt, CancelledError, UserFriendlyError],
    )
    logger.info('Telemetry initialized.')


class _DummySentry:
    def __call__(self, *args, **kwargs):
        return self

    def __getattr__(self, item):
        return self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return None


def use_sentry():
    if is_dev():
        return _DummySentry()
    import sentry_sdk

    return sentry_sdk
