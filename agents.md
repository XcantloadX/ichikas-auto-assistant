# Agent 编码约定

本文件记录 AI agent 在本仓库写代码时应遵守的注释与文档规范。

## 公开 API 文档（reStructuredText）

对外暴露的公开 API（公开类、公开方法、模块级公开函数）必须写 docstring，并使用 **reStructuredText** 风格标注参数与返回值。

至少覆盖：

- `:param <name>:` — 每个参数
- `:return:` — 返回值（无返回值可省略）
- `:raises <Exception>:` — 会主动抛出的、调用方需要知道的异常

按需补充 `:type`、`:rtype`、`.. NOTE::` 等。

示例：

```python
def resolve_host(
    self,
    device_conf: DeviceConfig,
    *,
    policy: LifecyclePolicy,
    impl_hint: str,
) -> ResolvedHost:
    """按 lifecycle 类型解析出可运行的 host/instance。

    :param device_conf: 设备配置。
    :param policy: 生命周期策略，决定未运行时是报错还是尝试启动。
    :param impl_hint: 控制实现提示，用于校验 lifecycle 兼容性。
    :return: 解析结果，含 host 与可选的 ``stop_callback``。
    :raises UserFriendlyError: 设备未运行或配置无效时。
    :raises ValueError: lifecycle 类型未知时。
    """
```

私有方法（`_` 前缀）不强制完整 rst，但复杂逻辑仍应写清意图。

## 数据类 / Pydantic / 枚举的成员文档

**不要把成员说明集中在类 docstring 里**（不要用 `:ivar`、`:cvar` 罗列字段）。

- 类 docstring 只写整体用途、设计意图、跨字段约束。
- **每个成员各自写 docstring**（三引号字符串），紧跟在该成员声明的**下一行**。

不要用 `#:` 属性注释或行尾 `#` 注释代替成员 docstring。

### dataclass

参考 `iaa/game_ui/scrollable.py` 中的 `ScrollProgress`：

```python
@dataclass
class ResolvedHost:
    """lifecycle 解析结果。只含 host/instance，不含 device driver。"""

    host: HostProtocol
    """已解析的 host 或 instance 对象。"""

    started_by_us: bool
    """本次是否由 factory 启动 host。"""
```

### Enum

参考 `iaa/definitions/enums.py` 中的 `ChallengeLiveAward`：

```python
class LifecyclePolicy(Enum):
    """设备生命周期策略。"""

    REQUIRE_RUNNING = 'require_running'
    """必须已在运行，否则报错（画面预览用）。"""

    CHECK_AND_START = 'check_and_start'
    """按 lifecycle 的 ``check_and_start`` 决定是否自动启动（任务执行用）。"""
```

### Pydantic `BaseModel`

参考 `iaa/config/schemas.py` 中的 `LiveConfig`、`GameConfig`：

```python
class LiveConfig(BaseModel):
    count: int | None = None
    """
    指定次数。
    """

    auto_set_unit: bool = False
    """演出前是否自动编队。"""
```

单行说明用同一行 docstring；多行说明用三引号块，均放在字段声明之后。

## 重构时保留注释

逻辑搬迁（例如从 `SchedulerService` 抽到 `DeviceFactory`）时，**技术注释随代码走**，不要只留实现、丢掉原因说明。典型内容：

- 特殊分支的设计原因（如 AVD + qemu_grpc 的 gRPC token 说明）
- 跨层解耦约定（如 `_ensure_device_started` 与设备创建正交）
- 线程/生命周期约束（如 `.. NOTE::` 要求与任务同线程调用）