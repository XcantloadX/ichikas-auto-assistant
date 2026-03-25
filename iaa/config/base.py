from typing import Literal
from pydantic import BaseModel

from .schemas import GameConfig, LiveConfig, SchedulerConfig, ChallengeLiveConfig, CmConfig, EventStoreConfig

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
    scheduler: SchedulerConfig = SchedulerConfig()
