from dataclasses import dataclass
from threading import Lock
from typing import Literal


@dataclass
class AutoLiveRequest:
    count_mode: Literal['specify', 'all']
    count: int | None
    loop_mode: Literal['single', 'list']
    auto_mode: Literal['none', 'game_auto', 'script_auto']
    debug_enabled: bool = False


_auto_live_request_lock = Lock()
_auto_live_request: AutoLiveRequest | None = None


def set_auto_live_request(request: AutoLiveRequest) -> None:
    global _auto_live_request
    with _auto_live_request_lock:
        _auto_live_request = request


def consume_auto_live_request() -> AutoLiveRequest | None:
    global _auto_live_request
    with _auto_live_request_lock:
        request = _auto_live_request
        _auto_live_request = None
        return request
