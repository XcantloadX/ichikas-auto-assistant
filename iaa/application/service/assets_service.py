from iaa.utils import assets_root


class AssetsService:
    def __init__(self):
        pass

    @property
    def assets_root_path(self) -> str:
        """运行时 assets 根目录（随包分发的 ``iaa/assets``）"""
        return assets_root()
