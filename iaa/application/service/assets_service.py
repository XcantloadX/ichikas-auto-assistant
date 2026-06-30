import os.path


class AssetsService:
    def __init__(self):
        pass

    @property
    def assets_root_path(self) -> str:
        """运行时 assets 根目录"""
        from .iaa_service import IaaService
        return os.path.join(IaaService.app_root(), 'assets')
