# docker/android-build.Dockerfile
# ------------------------------------------------------------------
# iaa Android APK 本地 Docker 化构建镜像。
#
# 目的：把 .github/workflows/android-build.yml 的构建环境镜像进容器，
#       让 Windows(Docker Desktop) / Linux / macOS 主机本地即可产出 APK，
#       解耦对 GitHub Actions 的依赖。
#
# 硬约束（参考 notes/03-build-infra.md、notes/04-handover.md、notes/07-handover-v2.md）：
#   * 必须 ubuntu 22.04 —— 24.04 的 libtool 2.4.7 移除了 LT_SYS_SYMBOL_USCORE 宏，
#     libffi 的 autogen.sh 会失败；22.04（autoconf 2.71 + libtool 2.4.6）是
#     buildozer 官方 CI 验证环境。
#   * 宿主 Python 必须 <= 3.11 —— pyside6-android-deploy 对 sys.version_info
#     >= (3, 12) 直接抛错。
#   * 目标架构 x86_64 / API 35 / NDK r27c（与 CI 对齐）。
#
# 本镜像只装环境，不 COPY 仓库；运行期由 wrapper 把仓库挂到 /workspace，
# docker/entrypoint-build.sh 幂等补齐 NDK/SDK/wheels 后调用
# tools/android/build_android.py 完成构建。
# ------------------------------------------------------------------

FROM ubuntu:22.04

ARG DEBIAN_FRONTEND=noninteractive

# ---- 系统依赖：p4a / buildozer / Qt 工具链的常规依赖（与 CI 对齐）----
# libgl1 / libglib2.0-0：opencv-python(host 资源生成用) 在无图形容器里
# import 时需要 libGL.so.1 / libgthread-2.0.so.0，CI runner 自带，容器需显式装。
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        openjdk-17-jdk-headless \
        build-essential \
        ccache \
        autoconf automake libtool \
        zlib1g-dev libffi-dev libssl-dev \
        pkg-config \
        ninja-build \
        wget unzip zip curl \
        git \
        rsync \
        python3-venv python3-pip \
        libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# ---- Rust 工具链：pydantic-core 的 p4a recipe（RustCompiledComponentsRecipe）需要 ----
# rustup 默认装到 $HOME/.cargo（HOME=/root → /root/.cargo）。
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \
    | sh -s -- -y --profile minimal --default-toolchain stable

# ---- 宿主 Python 3.11：ubuntu 22.04 自带 python3.10，用 deadsnakes PPA 补齐 ----
# Qt 工具链要求宿主 Python <= 3.11；deadsnakes 是官方推荐渠道。
# 注：--no-install-recommends 会漏装 gnupg（gpg-agent），add-apt-repository
#     导入 PPA key 时 gpg 会因 agent 缺失失败，因此显式安装 gnupg。
RUN apt-get update \
    && apt-get install -y --no-install-recommends software-properties-common gnupg \
    && add-apt-repository -y ppa:deadsnakes/ppa \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        python3.11 python3.11-venv python3.11-dev \
    && rm -rf /var/lib/apt/lists/*

# ---- 构建用 venv：pyside6-android-deploy 要求宿主 Python <= 3.11 ----
RUN /usr/bin/python3.11 -m venv /opt/venv \
    && /opt/venv/bin/python -m pip install --upgrade pip

# ---- PySide6 桌面版 + buildozer + cython + meson（与 CI 对齐的精确版本）----
# 桌面版 PySide6 自带 pyside6-android-deploy 控制台脚本。
RUN /opt/venv/bin/pip install --no-cache-dir \
        "PySide6==6.11.1" \
        "buildozer==1.5.0" \
        "cython==0.29.33" \
        "meson"

# buildozer 1.5.0 的 check_root()（__init__.py 1041 附近）：当以 root 运行且
# default.spec 的 warn_on_root=1 时，会 input() 交互确认；本容器以 root 非交互
# 构建，input() 直接 EOFError 崩溃（CI runner 是非 root 用户所以不触发）。
# 补丁：把交互确认改为自动继续，等价于始终回答 y，行为与 CI 对齐。
RUN /usr/bin/python3.11 - <<'PY'
import pathlib
p = pathlib.Path('/opt/venv/lib/python3.11/site-packages/buildozer/__init__.py')
s = p.read_text(encoding='utf-8')
old = """            cont = None
            while cont not in ('y', 'n'):
                cont = input('Are you sure you want to continue [y/n]? ')

            if cont == 'n':
                sys.exit()"""
new = """            cont = 'y'  # [container] root 非交互运行：自动继续（同 CI 非 root 行为）"""
assert old in s, 'buildozer check_root block not found'
p.write_text(s.replace(old, new), encoding='utf-8')
PY

# ---- pyside6-android-deploy 运行时依赖（官方 requirements-android.txt，精确版本）----
# 定位 requirements-android.txt 的方式与 CI 一致：import PySide6.scripts 求路径
# （含 jinja2 / pkginfo / tqdm / packaging==24.1 等）。
RUN req="$(/opt/venv/bin/python -c 'import PySide6.scripts, pathlib; print(pathlib.Path(PySide6.scripts.__file__).parent / "requirements-android.txt")')" \
    && /opt/venv/bin/pip install --no-cache-dir -r "$req"

# ---- 资源生成 host 依赖（tools/make_resources.py → kotonebot.devtools.resgen）----
# kotonebot 用 --no-deps 安装（rapidocr/onnxruntime 为惰性导入，host 生成用不到）；
# 其余为 make_resources 实际 import 需要：pydantic/rich/opencv-python(<5,
# kotonebot 约束，禁 5.0+)/numpy/python-dotenv/mouse/typing-extensions/psutil。
# 与 CI 的"Install" 步骤保持一致。
RUN /opt/venv/bin/pip install --no-cache-dir --no-deps "kotonebot==0.19.1" \
    && /opt/venv/bin/pip install --no-cache-dir \
        pydantic \
        rich \
        "opencv-python<5.0" \
        numpy \
        python-dotenv \
        mouse \
        typing-extensions \
        psutil

# ---- 补装 CI runner 自带、p4a recipe 显式要求的系统依赖 ----
# * p4a 的 libffi recipe（pythonforandroid/recipes/libffi）autoreconf 时依赖
#   `LT_SYS_SYMBOL_USCORE` 宏，该宏由 libltdl-dev 提供的 /usr/share/aclocal/ltdl.m4
#   定义；只装 libtool（提供 libtool.m4）不够，缺它时 autoreconf 报
#   "possibly undefined macro: LT_SYS_SYMBOL_USCORE"（GitHub Actions ubuntu-22.04
#   runner 预装 libltdl-dev 所以 CI 不触发）。
# * p4a 的 opencv recipe（pythonforandroid/recipes/opencv）build_arch 里
#   shprint(sh.cmake, ...) 直接调 cmake，缺它时 pass2 报
#   "sh.CommandNotFound: cmake"（GitHub Actions runner 预装 cmake 所以 CI 不触发）。
# 单独一层放在后面，避免改动顶部 apt 层导致全量重 build。
RUN apt-get update \
    && apt-get install -y --no-install-recommends libltdl-dev cmake \
    && rm -rf /var/lib/apt/lists/*

# ---- 环境变量（与 CI 对齐）----
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH="/opt/venv/bin:/root/.cargo/bin:${PATH}"
ENV ANDROID_SDK_ROOT=/root/android-sdk
ENV ANDROID_NDK_ROOT=/root/.pyside6_android_deploy/android-ndk/android-ndk-r27c
# 声明虚拟环境，让 buildozer 的 install_platform 去掉 pip --user：
# buildozer/targets/android.py 只认 VIRTUAL_ENV/CONDA_PREFIX 才改用 venv 内安装；
# 本镜像工具都装在 /opt/venv，若不声明，buildozer 会按非 venv 走
# `pip install --user`，在 venv 内报
# "Can not perform a '--user' install. User site-packages are not visible in
# this virtualenv."（CI 的 setup-python 非 venv 所以不触发）。
ENV VIRTUAL_ENV=/opt/venv

# ---- 容器入口（构建时打入镜像，运行期由 wrapper 调用）----
COPY docker/entrypoint-build.sh /docker/entrypoint-build.sh
RUN chmod +x /docker/entrypoint-build.sh
