from iaa.platform import env


class AssetsService:
    def __init__(self):
        pass

    @property
    def assets_root_path(self) -> str:
        """运行时 assets 根目录"""
        return env.asset_dir()
