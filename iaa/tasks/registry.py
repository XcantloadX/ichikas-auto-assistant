from typing import Callable


from dataclasses import dataclass
from typing import Literal

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

TaskRegistry = dict[str, Callable[[], None]]


@dataclass(frozen=True)
class TaskInfo:
    task_id: str
    display_name: str
    kind: Literal['regular', 'manual']
    supports_kwargs: bool = False

REGULAR_TASKS: TaskRegistry = {
    'start_game': start_game,
    '_dump_item': _dump_item,
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
}


def name_from_id(task_id: str) -> str:
    """根据任务 id 返回可读名称。未知 id 返回原值。"""
    mapping: dict[str, str] = {
        'start_game': '启动游戏',
        'cm': '自动 CM',
        'solo_live': '单人演出',
        'challenge_live': '挑战演出',
        'activity_story': '活动剧情',
        'gift': '领取礼物',
        'area_convos': '区域对话',
        'event_shop': '活动商店',
        'main_story': '刷主线剧情',
        'auto_live': '自动演出',
        'mission_rewards': '任务奖励',
    }
    return mapping.get(task_id, task_id)


TASK_INFOS: dict[str, TaskInfo] = {
    'start_game': TaskInfo('start_game', '启动游戏', 'regular'),
    'cm': TaskInfo('cm', '自动 CM', 'regular'),
    'solo_live': TaskInfo('solo_live', '单人演出', 'regular'),
    'challenge_live': TaskInfo('challenge_live', '挑战演出', 'regular'),
    'activity_story': TaskInfo('activity_story', '活动剧情', 'regular'),
    'gift': TaskInfo('gift', '领取礼物', 'regular'),
    'area_convos': TaskInfo('area_convos', '区域对话', 'regular'),
    'event_shop': TaskInfo('event_shop', '活动商店', 'regular'),
    '_dump_item': TaskInfo('_dump_item', '保存 ListView Item Icon', 'regular'),
    'main_story': TaskInfo('main_story', '刷主线剧情', 'manual'),
    'auto_live': TaskInfo('auto_live', '自动演出', 'manual', supports_kwargs=True),
    'mission_rewards': TaskInfo('mission_rewards', '任务奖励', 'manual'),
}


def list_task_infos() -> list[TaskInfo]:
    ordered_ids = [*REGULAR_TASKS.keys(), *MANUAL_TASKS.keys()]
    return [TASK_INFOS[task_id] for task_id in ordered_ids]
