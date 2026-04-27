import json
from typing import Literal, overload, List
from pathlib import Path

from pydantic_core import ValidationError

from .base import IaaConfig, GameConfig, LiveConfig
from .shared import SharedConfig


class ConfigValidationError(Exception):
    def __init__(self, invalid_fields: List[str], error_details: str):
        self.invalid_fields = invalid_fields
        self.error_details = error_details
        field_list = ', '.join(invalid_fields)
        super().__init__(f"配置校验失败: {field_list}\n\n{error_details}")


def get_invalid_field_names(e: ValidationError) -> tuple[List[str], str]:
    """从 ValidationError 中提取顶级字段名和错误详情"""
    fields = set()
    details = []
    for err in e.errors():
        if err['loc']:
            fields.add(str(err['loc'][0]))
        input_val = repr(err.get('input', ''))[:50]
        msg = err['msg']
        loc = '.'.join(str(item) for item in err['loc']) if err['loc'] else 'unknown'
        details.append(f"  - {loc}: {msg} (input: {input_val})")

    return sorted(fields), '\n'.join(details)

config_path: str = './conf'


def list() -> list[str]:
    """列出所有配置文件（排除 _shared.json）。"""
    conf_dir = Path(config_path)
    if not conf_dir.exists():
        return []
    
    config_files = []
    for file in conf_dir.glob('*.json'):
        if file.stem != '_shared':
            config_files.append(file.stem)
    
    return sorted(config_files)


def read_shared() -> SharedConfig:
    """读取 _shared.json 共享配置。"""
    conf_dir = Path(config_path)
    conf_dir.mkdir(parents=True, exist_ok=True)
    
    shared_file = conf_dir / '_shared.json'
    
    if not shared_file.exists():
        shared_config = SharedConfig()
        write_shared(shared_config)
        return shared_config
    
    with open(shared_file, 'r', encoding='utf-8') as f:
        config_data = json.load(f)
    
    return SharedConfig.model_validate(config_data)


def write_shared(config: SharedConfig) -> None:
    """写入 _shared.json 共享配置。"""
    conf_dir = Path(config_path)
    conf_dir.mkdir(parents=True, exist_ok=True)

    shared_file = conf_dir / '_shared.json'

    with open(shared_file, 'w', encoding='utf-8') as f:
        json.dump(config.model_dump(), f, indent=2, ensure_ascii=False)


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
    from .schemas import ChallengeLiveConfig, EventStoreConfig, SchedulerConfig
    
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


def rename(old_name: str, new_name: str) -> None:
    """重命名一个配置文件。"""
    conf_dir = Path(config_path)
    
    old_file = conf_dir / f"{old_name}.json"
    new_file = conf_dir / f"{new_name}.json"
    
    if not old_file.exists():
        raise FileNotFoundError(f"Configuration '{old_name}' does not exist")
    
    if new_file.exists():
        raise FileExistsError(f"Configuration '{new_name}' already exists")
    
    config_data = json.loads(old_file.read_text(encoding='utf-8'))
    config_data['name'] = new_name
    
    with open(new_file, 'w', encoding='utf-8') as f:
        json.dump(config_data, f, indent=2, ensure_ascii=False)
    
    old_file.unlink()


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


def fallback_invalid_fields(name: str, invalid_fields: List[str]) -> IaaConfig:
    """只重置指定字段为默认值，保留其他字段"""
    config_file = Path(config_path) / f"{name}.json"
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration '{name}' does not exist")

    with open(config_file, 'r', encoding='utf-8') as f:
        config_data = json.load(f)

    default = IaaConfig.model_construct(
        name=config_data.get('name', name),
        description=config_data.get('description', f"Configuration for {name}"),
        game=GameConfig(),
        live=LiveConfig(),
    )
    default_dict = default.model_dump()

    for field in invalid_fields:
        if field in default_dict:
            config_data[field] = default_dict[field]

    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config_data, f, indent=2, ensure_ascii=False)

    return IaaConfig.model_validate(config_data)
