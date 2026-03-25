import os
import json
from typing import Literal, overload, Union
from pathlib import Path

from .base import IaaConfig

config_path: str = './conf'


def list() -> list[str]:
    """列出所有配置文件。"""
    conf_dir = Path(config_path)
    if not conf_dir.exists():
        return []
    
    config_files = []
    for file in conf_dir.glob('*.json'):
        config_files.append(file.stem)
    
    return sorted(config_files)


def create(name: str, *, exist: Literal['raise', 'ok'] = 'raise') -> None:
    """创建一个新的配置文件。"""
    conf_dir = Path(config_path)
    conf_dir.mkdir(parents=True, exist_ok=True)
    
    config_file = conf_dir / f"{name}.json"
    
    if config_file.exists():
        if exist == 'raise':
            raise FileExistsError(f"Configuration '{name}' already exists")
        return
    
    # 创建默认配置
    from .base import GameConfig, LiveConfig
    from .schemas import SchedulerConfig, ChallengeLiveConfig, EventStoreConfig
    
    default_config = IaaConfig(
        name=name,
        description=f"Configuration for {name}",
        game=GameConfig(),
        live=LiveConfig(),
        challenge_live=ChallengeLiveConfig(),
        event_shop=EventStoreConfig(),
        scheduler=SchedulerConfig(),
    )
    
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(default_config.model_dump(), f, indent=2, ensure_ascii=False)


def remove(name: str, *, not_exist: Literal['raise', 'ok'] = 'raise') -> None:
    """删除一个配置文件。"""
    config_file = Path(config_path) / f"{name}.json"
    
    if not config_file.exists():
        if not_exist == 'raise':
            raise FileNotFoundError(f"Configuration '{name}' does not exist")
        return
    
    config_file.unlink()


@overload
def read(name: str, *, not_exist: Literal['raise', 'create'] | IaaConfig = 'raise') -> IaaConfig: ...

@overload
def read(name: str, *, not_exist: None = None) -> IaaConfig | None: ...

def read(name: str, *, not_exist: Literal['raise', 'create'] | IaaConfig | None = 'raise') -> IaaConfig | None:
    """读取一个配置文件。
    
    :param name: 配置文件名称
    :param not_exist: 当配置不存在时的处理方式，'raise' 抛出异常，'create' 创建默认配置，None 返回 None，或直接提供默认值。
    :return: 配置对象或 None
    """
    config_file = Path(config_path) / f"{name}.json"
    
    if not config_file.exists():
        if not_exist == 'raise':
            raise FileNotFoundError(f"Configuration '{name}' does not exist")
        elif not_exist == 'create':
            create(name, exist='ok')
            return read(name)
        elif not_exist is None:
            return None
        elif isinstance(not_exist, IaaConfig):
            return not_exist
        else:
            raise ValueError(f"Invalid non_exist value: {not_exist}")
    
    with open(config_file, 'r', encoding='utf-8') as f:
        config_data = json.load(f)
    
    return IaaConfig.model_validate(config_data)


def write(name: str, config: IaaConfig) -> None:
    """写入一个配置文件。"""
    conf_dir = Path(config_path)
    conf_dir.mkdir(parents=True, exist_ok=True)
    
    config_file = conf_dir / f"{name}.json"
    
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config.model_dump(), f, indent=2, ensure_ascii=False)
