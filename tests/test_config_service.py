import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from iaa.application.service.config_service import ConfigService
from iaa.application.service.iaa_service import IaaService
from iaa.config import manager
from iaa.i18n import TStr


class ConfigServiceTests(unittest.TestCase):
    """针对 release 版 ConfigService（``config_name``/``is_running`` 签名）的测试。

    ``ConfigService.__init__`` 会用 ``IaaService.app_root()`` 重置 ``manager.config_path``，
    因此这里通过 patch ``app_root`` 把配置目录隔离到临时目录。
    """

    def make_service(self, root: str) -> ConfigService:
        with patch.object(IaaService, 'app_root', staticmethod(lambda: root)):
            return ConfigService()

    def test_missing_last_used_selects_first_existing_config_and_persists_it(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            manager.config_path = str(Path(root) / 'conf')
            manager.create('zeta')
            manager.create('alpha')

            service = self.make_service(root)

            self.assertEqual(service.current_config_name, 'alpha')
            self.assertEqual(manager.read_shared().profiles.last_used, 'alpha')
            self.assertFalse((Path(root) / 'conf' / 'default.json').exists())

    def test_rename_current_config_updates_current_name_and_last_used(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            manager.config_path = str(Path(root) / 'conf')
            manager.create('alpha')
            service = self.make_service(root)

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
            service = self.make_service(root)
            # manager.list() 按修改时间排序，显式切到 alpha 保证 rename 的是非当前配置
            service.switch_config('alpha')

            renamed_current = service.rename('beta', 'gamma')

            self.assertFalse(renamed_current)
            self.assertEqual(service.current_config_name, 'alpha')
            self.assertEqual(manager.read_shared().profiles.last_used, 'alpha')
            self.assertTrue((Path(root) / 'conf' / 'gamma.json').exists())

    def test_create_switches_to_new_config_and_updates_last_used(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            manager.config_path = str(Path(root) / 'conf')
            manager.create('alpha')
            service = self.make_service(root)

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
            service = self.make_service(root)

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
            service = self.make_service(root)
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
            service = self.make_service(root)

            with self.assertRaises(RuntimeError) as ctx:
                service.delete('alpha')
            self.assertIsInstance(ctx.exception.args[0], TStr)
            self.assertEqual(ctx.exception.args[0].zh_CN, '至少需要保留一个配置')


if __name__ == '__main__':
    unittest.main()
