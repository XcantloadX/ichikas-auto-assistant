# pyside6-android-deploy 的部署配置。
#
# 该文件由 Qt 官方的 pyside6-android-deploy 工具读取（默认 ./pysidedeploy.spec，
# 可用 -c 覆盖）。工具会基于这里的值生成 buildozer.spec 并驱动 buildozer/pm4a
# 的 qqt  bootstrap 打包。
# 结构参考 Qt for Python 官方模板：sources/pyside-tools/deploy_lib/default.spec
# 说明：留空的键交给工具自动推断（扫描 main.py/PySide6 import/QML import）。

[app]

# 应用显示名（也是 buildozer 的 package.name/domain 基础）。默认是从 main.py 推断。
title = iaa

# 项目根目录。默认：input_file 所在目录。留空即可（仓库根目录）。
project_dir =

# 源文件入口点路径。默认：main.py。p4a 要求必须是 main.py。
input_file =

# 生成的可执行输出目录。留空使用 project_dir。
exec_directory =

# 应用图标，建议 512x512 png（Android 自适应图标）。留空使用默认图标。
icon =

[python]

# 桌面部署（Nuitka）用，Android 部署不使用。
packages = Nuitka==4.0

# Android 部署：工具会把这些装进当前 venv 并驱动 buildozer。
# buildozer 1.5.0 为 Qt 官方 pin 的版本（配合 p4a develop）。
android_packages = buildozer==1.5.0,cython==0.29.33

[qt]

# 需要的 QML 文件（逗号分隔）。留空由工具自动收集。
qml_files =

# 需要排除的 qml 插件二进制。
excluded_qml_plugins =

# Qt 模块（逗号分隔）。留空由工具扫描 Python/PySide6 import 与 QML import 自动推断。
# 本应用需要：Core,Gui,Network,Qml,Quick,QuickControls2（FluentWinUI3 样式）、
# QuickLayouts、QuickEffects、QuickTemplates2、QuickDialogs、QtQml.Models。
# 首次建议留空让工具推断；若 APK 启动报“找不到 Qt module/plugin”再显式填列。
modules =

[android]

# PySide6 Android wheel 路径（也可用命令行 --wheel-pyside 覆盖）。
wheel_pyside =

# Shiboken6 Android wheel 路径（也可用命令行 --wheel-shiboken 覆盖）。
wheel_shiboken =

# 需要复制到 app libs 目录的 Android 插件（逗号分隔）。留空自动推断。
plugins =

[nuitka]

# 桌面用，Android 不涉及。
mode = onefile
extra_args = --quiet --noinclude-qt-translations

[buildozer]

# release 生成 .aab，debug 生成 .apk。首个 APK 用 debug。
mode = debug

# PySide6/shiboken6 动态生成的 p4a recipe 目录。留空由工具生成到 <project>/deployment/recipes。
recipe_dir =

# 额外的 Qt Android jar 目录。留空由工具从 wheel 提取到 <project>/deployment。
jars_dir =

# Android NDK 路径。CI 里可指向工具缓存 ~/.pyside6_android_deploy/android-ndk/android-ndk-r27c；
# 留空则工具自动下载 NDK r27c。
ndk_path =

# Android SDK 路径。CI 里可指向预装的 SDK；留空则 buildozer 自动下载（需在
# buildozer.spec 里设 android.accept_sdk_license = True）。
sdk_path =

# 启动时需要预加载的其他 .so（逗号分隔）。留空自动推断。
local_libs =

# 部署架构：x86_64（目标模拟器 Android 15/API 35）。官方 wheel 只有 aarch64、x86_64。
arch = x86_64