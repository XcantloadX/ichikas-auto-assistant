# buildozer.spec —— iaa Android(qqt bootstrap) 打包配置骨架。
#
# 【重要】两套用法，二选一：
#
# 1) 官方路线（推荐，CI 默认）：
#    pyside6-android-deploy 会依据 pysidedeploy.spec 生成/覆盖本文件。若本文件
#    “已存在”，工具会原样使用（不覆盖任何键）※。因此仓库里这一份只作为
#    “骨架/参考”，CI 步骤会把本文件挪到 buildozer.spec.sample，让工具先生成一份
#    完整的 Qt 配置，再用 tools/android 的补丁逻辑把下面的“硬编码”段合并进去。
#    ※ 参见 pyside-setup sources/pyside-tools/deploy_lib/android/buildozer.py
#      Buildozer.initialize：buildozer.spec 已存在会 warning 后直接复用。
#
# 2) 全手动模式：
#    保留本文件不动，把“自动生成”段的值替换成真实值（跑过一遍官方生成后回填），
#    然后 buildozer android debug 直接打包。适用于脱离 pyside6-android-deploy 的
#    兜底/排查场景。
#
# 键值注释标记：
#   [自动生成]  由 pyside6-android-deploy 写入，不要手工维护
#   [硬编码]    本仓库需要固定下来的值，CI 补丁步骤会合并
#   [参考]      仅作参考

[app]

# 应用名。官方工具会用 pysidedeploy.spec 的 title 覆盖。 [自动生成]
title = iaa

# 包名与包域。官方工具生成为 org.<title>。 [自动生成]
package.name = iaa
package.domain = org.iaa

# 版本号：每次发布手动递增。 [硬编码]
version = 26.07b1

# 入口。p4a 依赖 root 目录 main.py，这里保持默认即可。
source.dir = .
source.include_exts = py,png,jpg,ttf,qml,js,txt,mp3,ogg

# p4a 需求列表：逗号分隔，逗号后不能有空格。
# ---------------------------------------------------------------
# 首版 APK 的需求设计（“只够点亮 QML GUI”口径，详见 notes/03-build-infra.md）：
#
#   * python3/hostpython3 必须 pin 到 3.11.x —— 官方 android wheel 只有 cp311；
#     p4a python3 默认 3.14，hostpython3 有“与 python3 同版本”的 guard。
#   * pydantic-core 用 p4a 内置 recipe(v2026.05.09+，Rust 编译)；PyPI 无 android
#     轮子。recipe 固定 2.41.4 → 必须配套 pydantic==2.12.3。
#   * numpy 走 p4a recipe（默认 v2.3.0；桌面 pin 的 numpy<2.0 仅是桌面约束）。
#     opencv recipe(4.12.0) 自带 depends=[numpy]，不必显式列。
#   * p4a 对无 recipe 的纯 Python 依赖用 pip install --target ... --no-deps
#     安装 → 传递依赖不会自动装，必须把运行期需要的包全部显式列出。
#   * onnxruntime/rapidocr/thefuzz(+rapidfuzz) 首版不装（启动链不 import）。
#   * 工具生成的 requirements = python3,shiboken6,PySide6 —— 下面的
#     python3==3.11.9/hostpython3==3.11.9 与依赖清单由 CI 补丁步骤并入。 [硬编码]
requirements = python3==3.11.9,hostpython3==3.11.9,shiboken6,PySide6

# Android 权限：INTERNET 是 requests/遥测/更新所需。QML 初次需要
# 读 sdcard 之类的暂不加，按需迭代。 [硬编码]
android.permissions = INTERNET

# 打包架构：目标模拟器 x86_64。qt bootstrap 单架构构建。 [自动生成]
android.archs = x86_64

# 目标/最低 API：Android 15 = 35；numpy recipe 要求 minapi>=24。 [硬编码]
android.api = 35
android.minapi = 24
android.ndk_api = 24

# 允许自动下载并接受 SDK license（CI 无交互）。 [硬编码]
android.accept_sdk_license = True

android.sdk = 35
android.ndk_path =  # [自动生成] 由官方工具写入
android.sdk_path =  # [自动生成] 由官方工具写入

# 保持屏幕常亮（自动化任务运行期避免息屏）。 [硬编码]
android.wakelock = True

# Qt 专用：p4a 用 qt bootstrap。 [自动生成]
p4a.bootstrap = qt
# 生成的 PySide6/shiboken6 recipe 目录（官方工具生成到 <project>/deployment/recipes）。 [自动生成]
p4a.local_recipes =
# 官方工具把 Qt 模块校验、预加载库、Java 初始化类拼进这些 extra args。 [自动生成]
p4a.extra_args = --qt-libs=<modules...> --load-local-libs=<...> --init-classes=<...>

# Qt 官方工具强制 p4a 走 develop 分支（内含 PySide6/shiboken6 动态 recipe 支持）。 [自动生成]
p4a.branch = develop

# 需要打进 APK 的额外 jar（Qt 官方工具从 wheel 提取）。 [自动生成]
android.add_jars =

# P4a 本地 recipe 目录（除官方自动生成的 PySide6/shiboken6 之外，如
# onnxruntime/社区 recipe 可放这里）。 [参考]
# p4a.local_recipes = ${p4a.local_recipes},./p4a_local_recipes

[buildozer]

# 产物输出目录。官方工具会写为真实路径。 [自动生成]
bin_dir = ./bin

# 构建/缓存目录（p4a storage dir）。 [自动生成]
build_dir = ./.buildozer

log_level = 2

warn_on_root = 1

[app:android]

# CI 无交互环境：忽略 setup.py/pyproject.toml 的项目安装
# （默认行为，buildozer 会传 --ignore-setup-py）。
# p4a.setup_py = False