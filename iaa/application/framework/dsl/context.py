from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from iaa.config.base import IaaConfig
from iaa.config.shared import SharedConfig


class FormMeta(BaseModel):
    """表单运行时元数据。

    这里存放用于渲染和联动的选项列表，不参与业务配置持久化。
    字段名保持与前端约定一致，便于直接 JSON 序列化。
    """

    profiles: list[dict[str, Any]] = Field(default_factory=list)
    emulators: list[dict[str, Any]] = Field(default_factory=list)
    servers: list[dict[str, Any]] = Field(default_factory=list)
    linkAccounts: list[dict[str, Any]] = Field(default_factory=list)
    controlImpls: list[dict[str, Any]] = Field(default_factory=list)
    resolutionMethods: list[dict[str, Any]] = Field(default_factory=list)
    songNames: list[str] = Field(default_factory=list)
    apMultipliers: list[str] = Field(default_factory=list)
    challengeCharacterGroups: list[dict[str, Any]] = Field(default_factory=list)
    challengeCharacters: list[dict[str, Any]] = Field(default_factory=list)
    challengeAwards: list[dict[str, Any]] = Field(default_factory=list)
    eventShopItems: list[dict[str, Any]] = Field(default_factory=list)
    mumuInstances: list[dict[str, Any]] = Field(default_factory=list)


class FormContext(BaseModel):
    """DSL 与引擎使用的强类型上下文。"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    conf: IaaConfig
    shared: SharedConfig
    meta: FormMeta
