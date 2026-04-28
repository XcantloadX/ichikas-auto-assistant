from pydantic import BaseModel

from .schemas import (
    ChallengeLiveConfig,
    CmConfig,
    DeveloperConfig,
    EventStoreConfig,
    GameConfig,
    LiveConfig,
    SchedulerConfig,
)

CONFIG_VERSION_CODE = 1

class IaaBaseTaskConfig(BaseModel):
    enabled: bool = False

class IaaConfig(BaseModel):
    version: int = CONFIG_VERSION_CODE
    name: str
    description: str
    game: GameConfig
    live: LiveConfig
    challenge_live: ChallengeLiveConfig = ChallengeLiveConfig()
    cm: CmConfig = CmConfig()
    event_shop: EventStoreConfig = EventStoreConfig()
    developer: DeveloperConfig = DeveloperConfig()
    scheduler: SchedulerConfig = SchedulerConfig()
