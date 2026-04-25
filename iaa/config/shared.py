from pydantic import BaseModel


class TelemetryConfig(BaseModel):
    sentry: bool | None = None


class ProfilesConfig(BaseModel):
    last_used: str | None = None


class InterfaceConfig(BaseModel):
    window_style: str = ''


class SharedConfig(BaseModel):
    profiles: ProfilesConfig = ProfilesConfig()
    telemetry: TelemetryConfig = TelemetryConfig()
    interface: InterfaceConfig = InterfaceConfig()
