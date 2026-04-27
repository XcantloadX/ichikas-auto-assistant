import os
from typing import TYPE_CHECKING

from kotonebot import logging
from pydantic_core import ValidationError
from iaa.config import manager
from iaa.config.manager import ConfigValidationError
if TYPE_CHECKING:
    from .iaa_service import IaaService

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_NAME = 'default'


class ConfigService:
    def __init__(self, iaa_service: 'IaaService', config_name: str | None = None):
        self.iaa = iaa_service
        manager.config_path = os.path.join(self.iaa.root, 'conf')

        self.shared = manager.read_shared()

        def _use_default_name():
            configs = manager.list()
            if configs:
                return configs[0]
            return DEFAULT_CONFIG_NAME

        _config_name = config_name or self.shared.profiles.last_used
        if _config_name is None:
            _config_name = _use_default_name()
            self.shared.profiles.last_used = _config_name
            manager.write_shared(self.shared)
        try:
            self.conf = manager.read(
                _config_name,
                not_exist='create' if _config_name == DEFAULT_CONFIG_NAME and not manager.list() else 'raise',
            )
        except FileNotFoundError:
            # 如果上次用的不存在，改用默认的
            _config_name = _use_default_name()
            self.shared.profiles.last_used = _config_name
            manager.write_shared(self.shared)
            self.conf = manager.read(_config_name, not_exist='create' if _config_name == DEFAULT_CONFIG_NAME and not manager.list() else 'raise')
        except ValidationError as e:
            invalid_fields, error_details = manager.get_invalid_field_names(e)
            raise ConfigValidationError(invalid_fields, error_details)
        
        self._config_name: str = _config_name

    @property
    def current_config_name(self) -> str:
        return self._config_name

    def list(self) -> list[str]:
        return manager.list()

    def _default_config_name(self) -> str:
        configs = manager.list()
        if configs:
            return configs[0]
        return DEFAULT_CONFIG_NAME

    def save(self) -> None:
        logger.info(f"Save config: {self._config_name}")
        manager.write(self._config_name, self.conf)
        manager.write_shared(self.shared)

    def switch_config(self, name: str) -> None:
        if self.iaa.scheduler.running:
            raise RuntimeError("运行时不能切换配置，请先停止任务")

        self._config_name = name
        self.conf = manager.read(name)

        self.shared.profiles.last_used = name
        manager.write_shared(self.shared)

    def rename(self, old_name: str, new_name: str) -> bool:
        """重命名配置。

        :param old_name: 旧的配置名称。
        :param new_name: 新的配置名称。
        :return: 被重命名的配置是否为当前选中的配置。
        """
        is_current = old_name == self._config_name

        manager.rename(old_name, new_name)

        if is_current:
            self._config_name = new_name
            self.conf.name = new_name

        if is_current or self.shared.profiles.last_used == old_name:
            self.shared.profiles.last_used = new_name
            manager.write_shared(self.shared)

        return is_current

    def create(self, name: str) -> None:
        manager.create(name, exist='ok')
        self.switch_config(name)

    def delete(self, name: str) -> bool:
        """删除指定名称的配置。

        :param name: 要删除的配置的名称。
        :raises RuntimeError: 如果当前只剩下一个配置，抛出此异常。
        :return: 删除的配置是否为当前选中的配置。
        """
        configs = manager.list()
        if len(configs) <= 1:
            raise RuntimeError('至少需要保留一个配置')

        is_current = name == self._config_name
        manager.remove(name, not_exist='raise')

        if not is_current:
            if self.shared.profiles.last_used == name:
                self.shared.profiles.last_used = self._config_name
                manager.write_shared(self.shared)
            return False

        next_name = self._default_config_name()
        self._config_name = next_name
        self.conf = manager.read(next_name)
        self.shared.profiles.last_used = next_name
        manager.write_shared(self.shared)
        return True

    def save_shared(self) -> None:
        manager.write_shared(self.shared)
