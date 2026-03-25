from __future__ import annotations

from typing import Any, Callable, Generic, Optional, TypeVar, cast

T = TypeVar('T')


class PathRecorder:
    """Record attribute/item access path.

    The recorder itself is intentionally minimal and only used as an
    implementation detail behind :func:`of` and :func:`signal`.
    """

    def __init__(self, root: Any = None, path: Optional[list[tuple[str, Any]]] = None):
        self._root = root
        self._path: list[tuple[str, Any]] = path if path is not None else []

    def __getattr__(self, name: str) -> 'PathRecorder':
        return PathRecorder(self._root, self._path + [('attr', name)])

    def __getitem__(self, key: Any) -> 'PathRecorder':
        return PathRecorder(self._root, self._path + [('item', key)])

    def _get_recorder_info(self) -> tuple[Any, list[tuple[str, Any]]]:
        return self._root, self._path


def of(obj: T) -> T:
    """Create typed proxy root for path capture.

    :param obj: Real root object.
    :return: A typed proxy value for chaining.
    """
    return cast(T, PathRecorder(root=obj))


def _resolve(target: Any, path: list[tuple[str, Any]]) -> Any:
    current = target
    for op_type, key in path:
        if op_type == 'attr':
            current = getattr(current, key)
        elif op_type == 'item':
            current = current[key]
        else:
            raise ValueError(f'Unknown path operation: {op_type}')
    return current


def _resolve_parent(target: Any, path: list[tuple[str, Any]]) -> tuple[Any, str, Any]:
    if not path:
        raise ValueError('Path is empty.')

    current = target
    for op_type, key in path[:-1]:
        if op_type == 'attr':
            current = getattr(current, key)
        elif op_type == 'item':
            current = current[key]
        else:
            raise ValueError(f'Unknown path operation: {op_type}')

    last_op, last_key = path[-1]
    return current, last_op, last_key


class Signal(Generic[T]):
    """A lightweight signal abstraction.

    Signal supports both local values and reference-backed values.
    Reference-backed signals are created by :func:`signal`.

    :param value: Local initial value.
    :param getter: Optional read function for ref mode.
    :param setter: Optional write function for ref mode.
    """

    def __init__(
        self,
        value: T | None = None,
        *,
        getter: Callable[[], T] | None = None,
        setter: Callable[[T], None] | None = None,
    ):
        self._subscribers: list[Callable[[T], None]] = []
        self._getter = getter
        self._setter = setter
        self._value = value

    def get(self) -> T:
        """Return current value."""
        if self._getter is not None:
            return self._getter()
        return cast(T, self._value)

    @property
    def value(self) -> T:
        """Property-style getter."""
        return self.get()

    @value.setter
    def value(self, new_value: T) -> None:
        self.set(new_value)

    def set(self, value: T) -> None:
        """Set value and notify subscribers when changed."""
        old_value = self.get()
        if value == old_value:
            return

        if self._setter is not None:
            self._setter(value)
        else:
            self._value = value

        for callback in tuple(self._subscribers):
            callback(value)

    def subscribe(self, callback: Callable[[T], None]) -> Callable[[], None]:
        """Register callback and return an unsubscribe function."""
        self._subscribers.append(callback)

        def _unsubscribe() -> None:
            try:
                self._subscribers.remove(callback)
            except ValueError:
                pass

        return _unsubscribe


def signal(proxy: T) -> Signal[T]:
    """Create a reference-backed signal from a typed proxy path.

    :param proxy: Path expression based on :func:`of`.
    :return: Signal bound to the real object path.
    """
    if not isinstance(proxy, PathRecorder):
        raise TypeError('signal argument must be a proxy value created by of().')

    root, path = proxy._get_recorder_info()

    if not path:
        return Signal(getter=lambda: cast(T, root), setter=lambda new_value: None)

    def _getter() -> T:
        return cast(T, _resolve(root, path))

    def _setter(value: T) -> None:
        parent, last_op, last_key = _resolve_parent(root, path)
        if last_op == 'attr':
            setattr(parent, last_key, value)
            return
        if last_op == 'item':
            parent[last_key] = value
            return
        raise ValueError(f'Unknown path operation: {last_op}')

    return Signal(getter=_getter, setter=_setter)


def watch(source: Signal[T], callback: Callable[[T], None]) -> Callable[[], None]:
    """Subscribe to signal updates.

    :param source: Signal instance.
    :param callback: Callback on value change.
    :return: Unsubscribe callback.
    """
    return source.subscribe(callback)
