"""平台环境层。

统一封装桌面（Windows 源码运行 + PyInstaller / Nuitka 打包）与
Android（python-for-android / buildozer）两种环境下运行路径的解析,
供各业务模块获取 app_root / 资源目录 / 配置与数据目录。

调用方约定统一使用模块导入形式::

    from iaa.platform import env
    env.app_root()

不要使用 ``from iaa.platform.env import app_root`` 直接绑定名字,
否则测试中对模块重载（模拟 Android 环境）时无法感知 ``IS_ANDROID`` 的刷新。
"""

from . import env

__all__ = ['env']