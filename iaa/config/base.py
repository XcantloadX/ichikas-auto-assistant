from typing import Literal
from pydantic import BaseModel

from .schemas import GameConfig, LiveConfig, SchedulerConfig, ChallengeLiveConfig, CmConfig

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
    scheduler: SchedulerConfig = SchedulerConfig()
