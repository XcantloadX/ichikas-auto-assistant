from __future__ import annotations

from typing import Callable, Protocol, Union, runtime_checkable


@runtime_checkable
class Translatable(Protocol):
    """可翻译对象协议。实现此协议的对象可在 DSL 的任何文本字段中使用。"""

    def resolve(self, language: str) -> str: ...


# DSL 中所有文本字段（label、help_text、title、placeholder 等）均接受此类型：
# - str：无需翻译的静态文本
# - Translatable：实现了 resolve(language) 的对象（如 TStr）
# - Callable[[str], str]：接收语言码并返回字符串的函数，用于需要动态拼接的场景
LabelT = Union[str, Translatable, Callable[[str], str]]
