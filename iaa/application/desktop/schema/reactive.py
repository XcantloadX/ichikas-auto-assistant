from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Generic, TypeVar, get_args, get_origin

from pydantic import BaseModel

T = TypeVar('T')


class Signal(Generic[T]):
    """A tiny reactive signal.

    :param value: Initial value.
    """

    def __init__(self, value: T):
        self._value = value
        self._subscribers: list[Callable[[T], None]] = []

    def get(self) -> T:
        """Return the current value."""
        return self._value

    def set(self, value: T) -> None:
        """Set value and notify subscribers when changed."""
        if value == self._value:
            return
        self._value = value
        for callback in tuple(self._subscribers):
            callback(value)

    def subscribe(self, callback: Callable[[T], None]) -> Callable[[], None]:
        """Register callback and return an unsubscribe function.

        :param callback: Subscriber callback.
        :return: Function that removes the callback.
        """
        self._subscribers.append(callback)

        def _unsubscribe() -> None:
            try:
                self._subscribers.remove(callback)
            except ValueError:
                pass

        return _unsubscribe


@dataclass
class ReactiveObject:
    """Runtime container for nested reactive state."""


def state_from_config(config: BaseModel) -> ReactiveObject:
    """Build a reactive tree from pydantic config.

    :param config: Source config model.
    :return: Reactive object tree.
    """

    def _build(value: Any) -> Any:
        if isinstance(value, BaseModel):
            container = ReactiveObject()
            for field_name in value.__class__.model_fields:
                setattr(container, field_name, _build(getattr(value, field_name)))
            return container
        return Signal(value)

    return _build(config)


def to_config(state: ReactiveObject, config_type: type[BaseModel]) -> BaseModel:
    """Materialize reactive state into a validated config model.

    :param state: Reactive tree built by :func:`state_from_config`.
    :param config_type: Root pydantic model type.
    :return: Validated pydantic model.
    """

    def _unwrap(value: Any, expected_type: Any | None = None) -> Any:
        if isinstance(value, Signal):
            return value.get()

        if isinstance(value, ReactiveObject):
            if isinstance(expected_type, type) and issubclass(expected_type, BaseModel):
                payload: dict[str, Any] = {}
                for field_name, field_info in expected_type.model_fields.items():
                    payload[field_name] = _unwrap(getattr(value, field_name), field_info.annotation)
                return payload
            payload = {}
            for key, attr in value.__dict__.items():
                payload[key] = _unwrap(attr)
            return payload

        origin = get_origin(expected_type)
        if origin is list:
            item_type = get_args(expected_type)[0] if get_args(expected_type) else None
            return [_unwrap(item, item_type) for item in value]

        if origin is dict:
            value_type = get_args(expected_type)[1] if len(get_args(expected_type)) > 1 else None
            return {k: _unwrap(v, value_type) for k, v in value.items()}

        return value

    payload = _unwrap(state, config_type)
    return config_type.model_validate(payload)
