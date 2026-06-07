from typing import Callable, Generic, Literal, TypeVar

from dataclasses import dataclass

from .cm import cm
from .live import challenge_live, solo_live
from .start_game import start_game
from .story.activity_story import activity_story
from .story.main_story import farm_story
from .gift import gift
from .area_convos import area_convos
from .live.auto_live import auto_live
from .mission_rewards import collect_mission_rewards
from .event_shop import event_shop
from ._dump_item import _dump_item
from ._dump_sekai_home import _dump_sekai_home

from iaa.config.base import IaaConfig

TaskRegistry = dict[str, Callable[[], None]]

C = TypeVar('C')


@dataclass(frozen=True)
class TaskInfo(Generic[C]):
    task_id: str
    display_name: str
    kind: Literal['regular', 'manual']
    supports_kwargs: bool = False
    get_enabled: Callable[[C], bool] | None = None


IaaTaskInfo = TaskInfo[IaaConfig]

REGULAR_TASKS: TaskRegistry = {
    'start_game': start_game,
    '_dump_item': _dump_item,
    '_dump_sekai_home': _dump_sekai_home,
    'cm': cm,
    'solo_live': solo_live,
    'challenge_live': challenge_live,
    'activity_story': activity_story,
    'gift': gift,
    'area_convos': area_convos,
    'event_shop': event_shop,
}

MANUAL_TASKS: TaskRegistry = {
    'main_story': farm_story,
    'auto_live': auto_live,
    'mission_rewards': collect_mission_rewards,
    '_dump_sekai_home': _dump_sekai_home,
}


def name_from_id(task_id: str) -> str:
    """根据任务 id 返回可读名称。未知 id 返回原值。"""
    info = TASK_INFOS.get(task_id)
    return info.display_name if info else task_id


TASK_INFOS: dict[str, IaaTaskInfo] = {
    'start_game': IaaTaskInfo(
        'start_game', '启动游戏', 'regular',
        get_enabled=lambda c: c.tasks.is_enabled('start_game'),
    ),
    'cm': IaaTaskInfo(
        'cm', '自动 CM', 'regular',
        get_enabled=lambda c: c.tasks.is_enabled('cm'),
    ),
    'solo_live': IaaTaskInfo(
        'solo_live', '单人演出', 'regular',
        get_enabled=lambda c: c.tasks.is_enabled('solo_live'),
    ),
    'challenge_live': IaaTaskInfo(
        'challenge_live', '挑战演出', 'regular',
        get_enabled=lambda c: c.tasks.is_enabled('challenge_live'),
    ),
    'activity_story': IaaTaskInfo(
        'activity_story', '活动剧情', 'regular',
        get_enabled=lambda c: c.tasks.is_enabled('activity_story'),
    ),
    'gift': IaaTaskInfo(
        'gift', '领取礼物', 'regular',
        get_enabled=lambda c: c.tasks.is_enabled('gift'),
    ),
    'area_convos': IaaTaskInfo(
        'area_convos', '区域对话', 'regular',
        get_enabled=lambda c: c.tasks.is_enabled('area_convos'),
    ),
    'event_shop': IaaTaskInfo(
        'event_shop', '活动商店', 'regular',
        get_enabled=lambda c: c.tasks.is_enabled('event_shop'),
    ),
    '_dump_item': IaaTaskInfo(
        '_dump_item', '保存 ListView Item Icon', 'regular',
        get_enabled=None,
    ),
    '_dump_sekai_home': IaaTaskInfo(
        '_dump_sekai_home', 'dump 烤森', 'regular',
        get_enabled=lambda c: c.developer.dump_sekai_home_enabled,
    ),
    'main_story': IaaTaskInfo('main_story', '刷主线剧情', 'manual'),
    'auto_live': IaaTaskInfo('auto_live', '自动演出', 'manual', supports_kwargs=True),
    'mission_rewards': IaaTaskInfo('mission_rewards', '任务奖励', 'manual'),
}


def list_task_infos() -> list[IaaTaskInfo]:
    ordered_ids = [*REGULAR_TASKS.keys(), *MANUAL_TASKS.keys()]
    return [TASK_INFOS[task_id] for task_id in ordered_ids]
