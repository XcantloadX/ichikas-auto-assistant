import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from iaa.application.service.config_service import ConfigService
from iaa.config import manager


class ConfigServiceTests(unittest.TestCase):
    @staticmethod
    def make_host(root: str) -> SimpleNamespace:
        return SimpleNamespace(root=root, scheduler=SimpleNamespace(running=False))

    def test_missing_last_used_selects_first_existing_config_and_persists_it(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            manager.config_path = str(Path(root) / 'conf')
            manager.create('zeta')
            manager.create('alpha')

            service = ConfigService(self.make_host(root))

            self.assertEqual(service.current_config_name, 'alpha')
            self.assertEqual(manager.read_shared().profiles.last_used, 'alpha')
            self.assertFalse((Path(root) / 'conf' / 'default.json').exists())

    def test_rename_current_config_updates_current_name_and_last_used(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            manager.config_path = str(Path(root) / 'conf')
            manager.create('alpha')
            service = ConfigService(self.make_host(root))

            renamed_current = service.rename('alpha', 'beta')

            self.assertTrue(renamed_current)
            self.assertEqual(service.current_config_name, 'beta')
            self.assertEqual(service.conf.name, 'beta')
            self.assertEqual(manager.read_shared().profiles.last_used, 'beta')
            self.assertFalse((Path(root) / 'conf' / 'alpha.json').exists())
            self.assertTrue((Path(root) / 'conf' / 'beta.json').exists())

    def test_rename_non_current_config_does_not_switch_current_config(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            manager.config_path = str(Path(root) / 'conf')
            manager.create('alpha')
            manager.create('beta')
            service = ConfigService(self.make_host(root))

            renamed_current = service.rename('beta', 'gamma')

            self.assertFalse(renamed_current)
            self.assertEqual(service.current_config_name, 'alpha')
            self.assertEqual(manager.read_shared().profiles.last_used, 'alpha')
            self.assertTrue((Path(root) / 'conf' / 'gamma.json').exists())

    def test_create_switches_to_new_config_and_updates_last_used(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            manager.config_path = str(Path(root) / 'conf')
            manager.create('alpha')
            service = ConfigService(self.make_host(root))

            service.create('beta')

            self.assertEqual(service.current_config_name, 'beta')
            self.assertEqual(service.conf.name, 'beta')
            self.assertEqual(manager.read_shared().profiles.last_used, 'beta')
            self.assertTrue((Path(root) / 'conf' / 'beta.json').exists())

    def test_delete_non_current_config_keeps_current_config(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            manager.config_path = str(Path(root) / 'conf')
            manager.create('alpha')
            manager.create('beta')
            service = ConfigService(self.make_host(root))

            deleted_current = service.delete('beta')

            self.assertFalse(deleted_current)
            self.assertEqual(service.current_config_name, 'alpha')
            self.assertEqual(manager.read_shared().profiles.last_used, 'alpha')
            self.assertFalse((Path(root) / 'conf' / 'beta.json').exists())

    def test_delete_current_config_switches_to_remaining_config(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            manager.config_path = str(Path(root) / 'conf')
            manager.create('alpha')
            manager.create('beta')
            service = ConfigService(self.make_host(root))
            service.switch_config('beta')

            deleted_current = service.delete('beta')

            self.assertTrue(deleted_current)
            self.assertEqual(service.current_config_name, 'alpha')
            self.assertEqual(service.conf.name, 'alpha')
            self.assertEqual(manager.read_shared().profiles.last_used, 'alpha')
            self.assertFalse((Path(root) / 'conf' / 'beta.json').exists())

    def test_delete_only_profile_raises(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            manager.config_path = str(Path(root) / 'conf')
            manager.create('alpha')
            service = ConfigService(self.make_host(root))

            with self.assertRaisesRegex(RuntimeError, '至少需要保留一个配置'):
                service.delete('alpha')


if __name__ == '__main__':
    unittest.main()
