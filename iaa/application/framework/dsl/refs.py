from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Generic, Optional, TypeVar, cast

T = TypeVar('T')
U = TypeVar('U')
R = TypeVar('R')


class PathRecorder(Generic[T]):
    """记录属性/索引路径，用于声明式构造 Ref。"""

    def __init__(self, path: Optional[list[tuple[str, Any]]] = None) -> None:
        self._path: list[tuple[str, Any]] = path if path is not None else []

    def __getattr__(self, name: str) -> 'PathRecorder[Any]':
        return PathRecorder(self._path + [('attr', name)])

    def __getitem__(self, key: Any) -> 'PathRecorder[Any]':
        return PathRecorder(self._path + [('item', key)])

    def path_info(self) -> list[tuple[str, Any]]:
        return list(self._path)


def of(type_hint: type[T]) -> T:
    """创建路径代理。

    参数仅用于类型提示，运行时不会被使用。
    """

    _ = type_hint
    return cast(T, PathRecorder())


def _traverse(target: Any, path: list[tuple[str, Any]]) -> tuple[Any, str, Any]:
    current = target
    for op_type, key in path[:-1]:
        if op_type == 'attr':
            current = getattr(current, key)
        else:
            current = current[key]
    last_op, last_key = path[-1]
    return current, last_op, last_key


@dataclass(slots=True)
class Ref(Generic[R, T]):
    """对上下文中某个值的读写绑定。"""

    get_fn: Callable[[R], T]
    set_fn: Callable[[R, T], None]

    def get(self, root: R) -> T:
        return self.get_fn(root)

    def set(self, root: R, value: T) -> None:
        self.set_fn(root, value)

    def map(self, to_ui: Callable[[T], U], from_ui: Callable[[U], T]) -> 'Ref[R, U]':
        return Ref(
            get_fn=lambda root: to_ui(self.get(root)),
            set_fn=lambda root, value: self.set(root, from_ui(value)),
        )


def custom_ref(get_fn: Callable[[R], T], set_fn: Callable[[R, T], None]) -> Ref[R, T]:
    return Ref(get_fn=get_fn, set_fn=set_fn)


def ref(proxy: T) -> Ref[Any, T]:
    if not isinstance(proxy, PathRecorder):
        raise TypeError('ref argument must be created from of(type_hint)')

    path = proxy.path_info()
    if not path:
        raise ValueError('Cannot create ref from empty path')

    def _getter(root: Any) -> T:
        parent, last_op, last_key = _traverse(root, path)
        if last_op == 'attr':
            return cast(T, getattr(parent, last_key))
        return cast(T, parent[last_key])

    def _setter(root: Any, value: T) -> None:
        parent, last_op, last_key = _traverse(root, path)
        if last_op == 'attr':
            setattr(parent, last_key, value)
            return
        parent[last_key] = value

    return Ref(get_fn=_getter, set_fn=_setter)
