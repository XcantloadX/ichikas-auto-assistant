import unittest

from iaa.application.qt.models.mappings import SERVER_DISPLAY_MAP
from iaa.config.schemas import GameConfig
from iaa.definitions.consts import bundle_id_by_server, package_by_server
from iaa.i18n import TStr


class GlobalEnConfigTests(unittest.TestCase):
    def test_game_config_accepts_en_server(self) -> None:
        conf = GameConfig(server='en')

        self.assertEqual(conf.server, 'en')

    def test_global_package_and_bundle_mapping(self) -> None:
        self.assertEqual(package_by_server('en'), 'com.sega.ColorfulStage.en')
        self.assertEqual(bundle_id_by_server('en'), 'com.sega.ColorfulStage.en')

    def test_global_server_is_exposed_to_settings_options(self) -> None:
        self.assertIn('en', SERVER_DISPLAY_MAP)
        self.assertIsInstance(SERVER_DISPLAY_MAP['en'], TStr)


if __name__ == '__main__':
    unittest.main()
