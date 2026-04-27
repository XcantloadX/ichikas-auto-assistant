import os.path
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .iaa_service import IaaService

class AssetsService:
    def __init__(self, iaa_service: 'IaaService'):
        self.iaa = iaa_service

    @property
    def assets_root_path(self) -> str:
        """运行时 assets 根目录"""
        return os.path.join(self.iaa.root, 'assets')
