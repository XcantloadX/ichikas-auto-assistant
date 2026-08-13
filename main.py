"""p4a ``qt`` bootstrap 要求的 Android 入口（仓库根目录）。

python-for-android 强制应用根目录的入口文件名为 ``main.py``;PySide6 的
``pyside6-android-deploy`` 生成的 Android Activity 会加载本文件并调用
``android_main()``。平台分支（Android 用 ``QGuiApplication``、桌面用
``QApplication``）已在 :func:`iaa.application.qt.index.main` 内按
``iaa.platform.env.IS_ANDROID`` 处理,因此这里只做委托,不做重复的平台逻辑。

**注意 import 顺序**：p4a 的 opencv recipe 只装单个 ``cv2.so``（无
``cv2.typing`` 子包），而 ``iaa.application.qt.index`` 的 import 链会在
``iaa.application.service.config_service`` 处拉到 ``kotonebot``，其模块顶部
有 ``from cv2.typing import MatLike``。因此**必须先装桩再 import iaa**，
否则启动即 ``ModuleNotFoundError``（见 ``iaa/platform/android_stubs.py``）。
"""

from iaa.platform import android_stubs

# 必须在任何 import kotonebot / iaa 之前执行（见模块 docstring 的 NOTE）。
android_stubs.install_android_stubs()

from iaa.application.qt.index import android_main


if __name__ == '__main__':
    android_main()
