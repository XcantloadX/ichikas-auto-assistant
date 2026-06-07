from pydantic import BaseModel

from .schemas import (
    DeviceConfig,
    DeveloperConfig,
    GameConfig,
    TasksConfig,
)

CONFIG_VERSION_CODE = 4

class IaaConfig(BaseModel):
    version: int = CONFIG_VERSION_CODE
    name: str
    description: str
    device: DeviceConfig = DeviceConfig()
    game: GameConfig
    developer: DeveloperConfig = DeveloperConfig()
    tasks: TasksConfig = TasksConfig()
