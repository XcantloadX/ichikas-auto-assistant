"""p4a ``qt`` bootstrap 要求的 Android 入口（仓库根目录）。

python-for-android 强制应用根目录的入口文件名为 ``main.py``;PySide6 的
``pyside6-android-deploy`` 生成的 Android Activity 会加载本文件并调用
``android_main()``。平台分支（Android 用 ``QGuiApplication``、桌面用
``QApplication``）已在 :func:`iaa.application.qt.index.main` 内按
``iaa.platform.env.IS_ANDROID`` 处理,因此这里只做委托,不做重复的平台逻辑。
"""

from iaa.application.qt.index import android_main


if __name__ == '__main__':
    android_main()
