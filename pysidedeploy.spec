[app]
title = iaa
project_dir =
input_file =
exec_directory =
icon =

[python]
packages = Nuitka==4.0
android_packages = buildozer==1.5.0,cython==0.29.33

[qt]
qml_files =
excluded_qml_plugins =
modules =

[android]
wheel_pyside =
wheel_shiboken =
plugins =

[nuitka]
mode = onefile
extra_args = --quiet --noinclude-qt-translations

[buildozer]
mode = debug
recipe_dir =
jars_dir =
ndk_path =
sdk_path =
local_libs =
arch = x86_64