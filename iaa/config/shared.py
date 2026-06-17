from typing import Annotated, Literal

from pydantic import BaseModel, Field

VERSION = 2


class TelemetryConfig(BaseModel):
    sentry: bool | None = None


class ProfilesConfig(BaseModel):
    last_used: str | None = None


class InterfaceConfig(BaseModel):
    window_style: str = ''
    theme_color: str | None = None
    color_scheme: Literal['auto', 'light', 'dark'] = 'auto'


class CustomPushData(BaseModel):
    type: Literal['custom'] = 'custom'
    command: str = ''


class DiscordPushData(BaseModel):
    type: Literal['discord'] = 'discord'
    webhook_url: str = ''


PushData = Annotated[CustomPushData | DiscordPushData, Field(discriminator='type')]


class PushConfig(BaseModel):
    enabled: bool = False
    data: PushData = Field(default_factory=CustomPushData)


class NotifyConfig(BaseModel):
    system: bool = True
    push: PushConfig = PushConfig()


class HotkeysConfig(BaseModel):
    start: str | None = None
    stop: str | None = None


class SharedConfig(BaseModel):
    version: int = VERSION
    profiles: ProfilesConfig = ProfilesConfig()
    telemetry: TelemetryConfig = TelemetryConfig()
    interface: InterfaceConfig = InterfaceConfig()
    notify: NotifyConfig = NotifyConfig()
    hotkeys: HotkeysConfig = HotkeysConfig()
