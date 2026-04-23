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
    def __init__(self, iaa_service: 'IaaService'):
        self.iaa = iaa_service
        manager.config_path = os.path.join(self.iaa.root, 'conf')
        try:
            self.conf = manager.read(DEFAULT_CONFIG_NAME, not_exist='create')
        except ValidationError as e:
            invalid_fields, error_details = manager.get_invalid_field_names(e)
            raise ConfigValidationError(invalid_fields, error_details)

    def list(self) -> list[str]:
        return manager.list()

    def save(self) -> None:
        logger.info(f"Save config: {DEFAULT_CONFIG_NAME}")
        manager.write(DEFAULT_CONFIG_NAME, self.conf)