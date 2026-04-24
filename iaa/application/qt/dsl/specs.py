from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from typing import Any, Callable

from .context import FormContext
from .refs import Ref

Predicate = Callable[[FormContext], bool]
OptionsProvider = Callable[[FormContext], list[Any]]
Validator = Callable[[Any, FormContext], str | None]
OnChangeHook = Callable[[FormContext, Any], None]


@dataclass(slots=True)
class FieldSpec:
    """单个表单字段的静态定义。

    这个对象只描述“页面应该长什么样”和“字段如何计算”，不保存任何运行时 UI 状态。
    运行时值、可见性、启用状态、错误信息等都由 FormEngine 基于 state 重新计算。

    Attributes:
        key: 字段的业务路径，使用点号路径表达式，例如 ``game.emulator``。
        kind: 字段类型，例如 ``text`` / ``select`` / ``segmented`` / ``checkbox``。
        label: 页面上展示给用户的标签文本；为 ``None`` 时不展示标签。
        default: 字段默认值；保留给 DSL 使用，不直接参与运行时计算。
        visible: 可见性规则。可以是布尔值，也可以是接收 state 的 predicate。
        enabled: 可用性规则。可以是布尔值，也可以是接收 state 的 predicate。
        options: 下拉或可选项来源。可以是静态列表，也可以是接收 state 的 provider。
        props: 控件私有属性，交给 QML 渲染层原样使用。
        validators: 字段校验函数列表，按顺序执行，返回首个错误信息。
        on_change: 字段值变更后的同步钩子，用于执行联动归一化逻辑。
    """

    key: str
    kind: str
    label: str | None
    ref: Ref[FormContext, Any]

    default: Any = None
    visible: Predicate | bool = True
    enabled: Predicate | bool = True
    options: OptionsProvider | list[Any] | None = None

    props: dict[str, Any] = field(default_factory=dict)
    validators: list[Validator] = field(default_factory=list)
    on_change: OnChangeHook | None = None


@dataclass(slots=True)
class GroupSpec:
    """表单中的一个分组。

    分组只负责把字段聚合在一起，不承载任何交互逻辑。
    QML 渲染层会按 groups 顺序逐个绘制。
    """

    title: str
    fields: list[FieldSpec]


@dataclass(slots=True)
class FormSpec:
    """整张配置页的静态定义。

    它是 DSL 的最终产物，由 FormPage 收集多个 GroupSpec 后生成。
    FormEngine 以此为输入，结合 state 生成 runtime JSON。
    """

    title: str
    groups: list[GroupSpec]


_current_page: ContextVar['FormPage | None'] = ContextVar('dsl_current_page', default=None)
_current_group: ContextVar[GroupSpec | None] = ContextVar('dsl_current_group', default=None)


class FormPage:
    """表单页面构建上下文。

    用法：

    .. code-block:: python

        with FormPage("配置") as page:
            with Group("游戏设置"):
                Text(...)

    进入上下文后，后续创建的 Group/Field 会自动注册到当前页面。
    退出上下文后，构建器状态会恢复，避免跨页面污染。
    """

    def __init__(self, title: str) -> None:
        """创建一个新的页面构建器。

        Args:
            title: 页面标题，会作为 QML 页面标题和 runtime 标题。
        """
        self.title = title
        self._groups: list[GroupSpec] = []
        self._hooks: list[Callable[[FormContext], None]] = []
        self._token: Token['FormPage | None'] | None = None

    def __enter__(self) -> 'FormPage':
        """进入页面构建上下文。"""
        self._token = _current_page.set(self)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """退出页面构建上下文，并恢复之前的页面栈。"""
        if self._token is not None:
            _current_page.reset(self._token)
            self._token = None

    def add_group(self, group: GroupSpec) -> None:
        """把一个分组追加到当前页面。"""
        self._groups.append(group)

    def add_hook(self, hook: Callable[[FormContext], None]) -> None:
        """注册一个页面级归一化钩子。

        页面级 hook 会在字段 on_change 之后执行，通常用于跨字段联动。
        """
        self._hooks.append(hook)

    @property
    def spec(self) -> FormSpec:
        """导出当前页面的静态定义。"""
        return FormSpec(title=self.title, groups=list(self._groups))

    @property
    def hooks(self) -> list[Callable[[FormContext], None]]:
        """导出当前页面注册的页面级 hook 列表。"""
        return list(self._hooks)


class Group:
    """分组构建上下文。

    用法：

    .. code-block:: python

        with Group("游戏设置"):
            Text(...)

    在 Group 上下文内创建的字段会自动挂到当前分组。
    """

    def __init__(self, title: str) -> None:
        """创建一个分组构建器。

        Args:
            title: 分组标题。
        """
        self.title = title
        self._group_spec = GroupSpec(title=title, fields=[])
        self._token: Token[GroupSpec | None] | None = None

    def __enter__(self) -> 'Group':
        """进入分组构建上下文。"""
        page = _require_current_page()
        page.add_group(self._group_spec)
        self._token = _current_group.set(self._group_spec)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """退出分组构建上下文，并恢复之前的分组栈。"""
        if self._token is not None:
            _current_group.reset(self._token)
            self._token = None


def _require_current_page() -> FormPage:
    """获取当前页面构建器。

    如果在没有 ``with FormPage(...)`` 的情况下定义分组，会直接抛出异常，
    这样可以尽早暴露 DSL 使用错误。
    """
    page = _current_page.get()
    if page is None:
        raise RuntimeError('FormPage context is required before defining groups')
    return page


def _require_current_group() -> GroupSpec:
    """获取当前分组构建器。

    字段必须定义在 ``with Group(...)`` 内部，否则无法知道该字段属于哪个分组。
    """
    group = _current_group.get()
    if group is None:
        raise RuntimeError('Group context is required before defining fields')
    return group


def _append_field(field: FieldSpec) -> FieldSpec:
    """把字段追加到当前分组，并返回字段本身。

    这样 builder 调用既能完成注册，也能保留字段对象，方便后续拼装 hook 或测试。
    """
    group = _require_current_group()
    group.fields.append(field)
    return field


def Text(
    key: str,
    label: str | None,
    *,
    ref: Ref[FormContext, Any],
    default: Any = None,
    visible: Predicate | bool = True,
    enabled: Predicate | bool = True,
    options: OptionsProvider | list[Any] | None = None,
    placeholder: str | None = None,
    props: dict[str, Any] | None = None,
    validators: list[Validator] | None = None,
    on_change: OnChangeHook | None = None,
) -> FieldSpec:
    """声明一个文本输入字段。

    Args:
        key: 字段路径，使用点号表示嵌套路径。
        label: 字段显示名称；传 ``None`` 时不展示标签。
        default: 默认值。
        visible: 可见性规则。
        enabled: 启用规则。
        options: 预留参数，文本字段通常不使用，但保留以便 DSL 统一。
        placeholder: 文本框占位提示。
        props: QML 渲染层的扩展属性。
        validators: 校验器列表。
        on_change: 值变化后的联动钩子。
    """
    merged_props = {} if props is None else dict(props)
    if placeholder is not None:
        merged_props['placeholder'] = placeholder
    return _append_field(
        FieldSpec(
            key=key,
            kind='text',
            label=label,
            ref=ref,
            default=default,
            visible=visible,
            enabled=enabled,
            options=options,
            props=merged_props,
            validators=[] if validators is None else validators,
            on_change=on_change,
        )
    )


def Select(
    key: str,
    label: str | None,
    *,
    ref: Ref[FormContext, Any],
    default: Any = None,
    visible: Predicate | bool = True,
    enabled: Predicate | bool = True,
    options: OptionsProvider | list[Any] | None = None,
    with_reset_button: bool = False,
    props: dict[str, Any] | None = None,
    validators: list[Validator] | None = None,
    on_change: OnChangeHook | None = None,
) -> FieldSpec:
    """声明一个普通选择字段。

    这个类型适合下拉框一类的单选 UI，QML 渲染层会根据 options 决定可选项。
    """
    merged_props = {} if props is None else dict(props)
    if with_reset_button:
        merged_props['withResetButton'] = True
    return _append_field(
        FieldSpec(
            key=key,
            kind='select',
            label=label,
            ref=ref,
            default=default,
            visible=visible,
            enabled=enabled,
            options=options,
            props=merged_props,
            validators=[] if validators is None else validators,
            on_change=on_change,
        )
    )


def Segmented(
    key: str,
    label: str | None,
    *,
    ref: Ref[FormContext, Any],
    default: Any = None,
    visible: Predicate | bool = True,
    enabled: Predicate | bool = True,
    options: OptionsProvider | list[Any] | None = None,
    props: dict[str, Any] | None = None,
    validators: list[Validator] | None = None,
    on_change: OnChangeHook | None = None,
) -> FieldSpec:
    """声明一个分段按钮字段。

    这个类型用于互斥选项切换，例如模拟器、服务器、控制方式等。
    """
    return _append_field(
        FieldSpec(
            key=key,
            kind='segmented',
            label=label,
            ref=ref,
            default=default,
            visible=visible,
            enabled=enabled,
            options=options,
            props={} if props is None else props,
            validators=[] if validators is None else validators,
            on_change=on_change,
        )
    )


def Checkbox(
    key: str,
    label: str | None,
    *,
    ref: Ref[FormContext, Any],
    default: Any = None,
    visible: Predicate | bool = True,
    enabled: Predicate | bool = True,
    options: OptionsProvider | list[Any] | None = None,
    props: dict[str, Any] | None = None,
    validators: list[Validator] | None = None,
    on_change: OnChangeHook | None = None,
) -> FieldSpec:
    """声明一个布尔开关字段。

    适用于勾选框、开关类 UI。
    """
    return _append_field(
        FieldSpec(
            key=key,
            kind='checkbox',
            label=label,
            ref=ref,
            default=default,
            visible=visible,
            enabled=enabled,
            options=options,
            props={} if props is None else props,
            validators=[] if validators is None else validators,
            on_change=on_change,
        )
    )


def Custom(
    key: str,
    label: str | None,
    kind: str,
    *,
    ref: Ref[FormContext, Any],
    default: Any = None,
    visible: Predicate | bool = True,
    enabled: Predicate | bool = True,
    options: OptionsProvider | list[Any] | None = None,
    props: dict[str, Any] | None = None,
    validators: list[Validator] | None = None,
    on_change: OnChangeHook | None = None,
) -> FieldSpec:
    """声明一个自定义字段类型。

    当内置字段不足以描述 UI 时使用，例如 ``mumu_picker`` 或 ``transfer_list``。
    ``kind`` 由 QML 渲染层根据注册表选择对应控件。
    """
    return _append_field(
        FieldSpec(
            key=key,
            kind=kind,
            label=label,
            ref=ref,
            default=default,
            visible=visible,
            enabled=enabled,
            options=options,
            props={} if props is None else props,
            validators=[] if validators is None else validators,
            on_change=on_change,
        )
    )


def TransferList(
    key: str,
    label: str | None,
    *,
    ref: Ref[FormContext, Any],
    default: Any = None,
    visible: Predicate | bool = True,
    enabled: Predicate | bool = True,
    options: OptionsProvider | list[Any] | None = None,
    reorderable: bool = False,
    height: int = 220,
    props: dict[str, Any] | None = None,
    validators: list[Validator] | None = None,
    on_change: OnChangeHook | None = None,
) -> FieldSpec:
    """声明一个穿梭框字段。"""
    merged_props = {} if props is None else dict(props)
    merged_props['reorderable'] = reorderable
    merged_props['height'] = height
    return _append_field(
        FieldSpec(
            key=key,
            kind='transfer_list',
            label=label,
            ref=ref,
            default=default,
            visible=visible,
            enabled=enabled,
            options=options,
            props=merged_props,
            validators=[] if validators is None else validators,
            on_change=on_change,
        )
    )
