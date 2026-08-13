"""env 平台环境层测试。

覆盖两条主路径:
- 桌面（无任何 ANDROID_* 环境变量）:app_root 为仓库根、config_dir 等路径语义。
- Android 模拟（monkeypatch 注入 ANDROID_PRIVATE / ANDROID_APP_PATH 并重载模块）:
  IS_ANDROID 判定、私有目录下 conf/logs 的落点。

由于 IS_ANDROID 是模块导入时计算,模拟 Android 时通过
``importlib.reload`` 让判定按当前环境变量重新计算;测试结束后再次 reload
恢复桌面状态,避免影响同进程内的其它测试模块。
"""

import importlib
import os
import tempfile
import unittest
from importlib import resources
from unittest import mock

from iaa.platform import env

import iaa.platform.env as env_module

# 仓库内真实存在的 sprite 文件,供集成断言使用
_KNOWN_SPRITE = '25edd61e-46a4-4c93-8d86-80c5defb8bb7_cn_template.png'
_KNOWN_ASSET = 'ichika_chibi.png'


def _strip_android_vars() -> None:
    for key in [k for k in os.environ if k.startswith('ANDROID_')]:
        os.environ.pop(key)


class EnvDesktopTests(unittest.TestCase):
    """桌面环境（无 ANDROID_* 变量）的行为回归。"""

    def setUp(self) -> None:
        # 强制桌面环境:清掉可能的 ANDROID_* 变量后重载,使 IS_ANDROID 准确反映当前环境
        _strip_android_vars()
        importlib.reload(env_module)

    def test_is_not_android_on_desktop(self) -> None:
        self.assertFalse(env.IS_ANDROID)

    def test_app_root_is_repo_root_and_exists(self) -> None:
        root = env.app_root()
        # 仓库根应包含 conf/、assets/、iaa/ 这几级对业务关键的内容
        self.assertTrue(os.path.isdir(root))
        self.assertTrue(os.path.isdir(os.path.join(root, 'conf')))
        self.assertTrue(os.path.isdir(os.path.join(root, 'assets')))
        self.assertTrue(os.path.isdir(os.path.join(root, 'iaa')))
        # 与「从 iaa/platform 上溯两级」的推导一致
        expected = os.path.abspath(os.path.join(os.path.dirname(env.__file__), '..', '..'))
        self.assertEqual(root, expected)

    def test_config_dir_equals_app_root_conf(self) -> None:
        self.assertEqual(env.config_dir(), os.path.join(env.app_root(), 'conf'))

    def test_data_dir_is_app_root_itself(self) -> None:
        self.assertEqual(env.data_dir(), env.app_root())
        self.assertTrue(os.path.isdir(env.data_dir()))

    def test_logs_dir_under_data_dir(self) -> None:
        self.assertEqual(env.logs_dir(), os.path.join(env.data_dir(), 'logs'))
        self.assertTrue(os.path.isdir(env.logs_dir()))

    def test_sprite_root_points_to_iaa_res(self) -> None:
        root = env.sprite_root()
        self.assertTrue(root.replace('\\', '/').endswith('/iaa/res'))
        self.assertTrue(os.path.isdir(root))

    def test_asset_path_resolves_repo_assets(self) -> None:
        path = env.asset_path(_KNOWN_ASSET)
        self.assertTrue(path.replace('\\', '/').endswith(f'/assets/{_KNOWN_ASSET}'))
        self.assertTrue(os.path.isfile(path))

    def test_utils_delegates_to_env(self) -> None:
        from iaa.utils import asset_path as utils_asset_path
        from iaa.utils import sprite_path as utils_sprite_path

        # utils.asset_path 应委托给 env.asset_path,结果一致
        self.assertEqual(utils_asset_path(_KNOWN_ASSET), env.asset_path(_KNOWN_ASSET))
        # sprite_path 应解析到 iaa/res 下真实存在的文件
        sprite = utils_sprite_path(_KNOWN_SPRITE)
        self.assertTrue(os.path.isfile(sprite))


class EnvAndroidTests(unittest.TestCase):
    """Android（p4a）环境模拟:注入 ANDROID_* 变量后重载模块。"""

    def _restore_desktop(self) -> None:
        # 退出模拟后环境变量已还原,重载回桌面状态,避免污染同进程其它测试
        importlib.reload(env_module)
        self.assertFalse(env.IS_ANDROID)

    def test_detects_android_private(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            private = os.path.join(tmp, 'files')
            os.makedirs(private)
            with mock.patch.dict(os.environ, {'ANDROID_PRIVATE': private}):
                importlib.reload(env_module)
                self.assertTrue(env.IS_ANDROID)
                self.assertEqual(env.app_root(), private)
                # config_dir 应指向私有目录下自动创建的 conf
                conf = env.config_dir()
                self.assertEqual(conf, os.path.join(private, 'conf'))
                self.assertTrue(os.path.isdir(conf))
                # data_dir 即私有根目录本身,logs 在其下
                self.assertEqual(env.data_dir(), private)
                logs = env.logs_dir()
                self.assertEqual(logs, os.path.join(private, 'logs'))
                self.assertTrue(os.path.isdir(logs))
                # Android 不提供独立 assets 目录
                with self.assertRaises(NotImplementedError):
                    env.asset_dir()
                # sprite 资源走包内 iaa.res
                self.assertEqual(env.sprite_root(), str(resources.files('iaa.res')))
            self._restore_desktop()

    def test_app_path_takes_precedence_over_private(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            private = os.path.join(tmp, 'files')
            app_path = os.path.join(tmp, 'app')
            os.makedirs(private)
            os.makedirs(app_path)
            with mock.patch.dict(os.environ, {
                'ANDROID_PRIVATE': private,
                'ANDROID_APP_PATH': app_path,
            }):
                importlib.reload(env_module)
                self.assertTrue(env.IS_ANDROID)
                self.assertEqual(env.app_root(), app_path)
                self.assertEqual(env.config_dir(), os.path.join(app_path, 'conf'))
            self._restore_desktop()

    def test_app_path_alone_counts_as_android(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app_path = os.path.join(tmp, 'app')
            os.makedirs(app_path)
            with mock.patch.dict(os.environ, {'ANDROID_APP_PATH': app_path}):
                importlib.reload(env_module)
                self.assertTrue(env.IS_ANDROID)
                self.assertEqual(env.app_root(), app_path)
            self._restore_desktop()


if __name__ == '__main__':
    unittest.main()