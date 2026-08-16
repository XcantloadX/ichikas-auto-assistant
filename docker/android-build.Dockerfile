# docker/android-build.Dockerfile
# ------------------------------------------------------------------
# iaa Android APK 本地 Docker 化构建镜像（最小 bootstrap 底座）。
#
# 目的：提供一个「能跑共享 setup 脚本」的 ubuntu:22.04 底座，让本地 Docker 与 CI
#       共用 tools/android/setup_env.sh 这一份环境逻辑（单一来源），避免两套逻辑漂移。
#
# 硬约束（参考 notes/03-build-infra.md、notes/04-handover.md、notes/07-handover-v2.md）：
#   * 必须 ubuntu 22.04 —— 24.04 的 libtool 2.4.7 移除了 LT_SYS_SYMBOL_USCORE 宏，
#     libffi 的 autogen.sh 会失败；22.04（autoconf 2.71 + libtool 2.4.6）是
#     buildozer 官方 CI 验证环境。
#   * 宿主 Python 必须 <= 3.11 —— pyside6-android-deploy 对 sys.version_info
#     >= (3, 12) 直接抛错。
#   * 目标架构 x86_64 / API 35 / NDK r27c（与 CI 对齐）。
#
# 本镜像只提供「能跑 setup 脚本」的底座（curl/git/deadsnakes 前置等最小集），
# 不 COPY 仓库、不烤任何构建环境。全部环境（deadsnakes、rustup、venv、pip、
# buildozer check_root 补丁、NDK/SDK/wheels 下载）由
# tools/android/setup_env.sh 在容器启动（docker/entrypoint-build.sh）时幂等准备。
# 运行期由 wrapper 把仓库挂到 /workspace，entrypoint 调 setup_env.sh docker 后
# 调用 tools/android/build_android.py 完成构建。
# ------------------------------------------------------------------

FROM ubuntu:22.04

ARG DEBIAN_FRONTEND=noninteractive

# ---- 运行 tools/android/setup_env.sh 所需的最小系统集 ----
# 其余系统依赖（JDK / build-essential / libltdl-dev / cmake / python3.11 等）全部
# 由 setup_env.sh 在容器启动时安装，避免镜像 build 期烤环境、与 CI 重复维护两处。
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        wget \
        unzip \
        zip \
        git \
        rsync \
        gnupg \
        software-properties-common \
        python3 \
        python3-venv \
    && rm -rf /var/lib/apt/lists/*

# ---- 环境默认值 ----
# 仅保留脚本同样会设置的默认（运行时由 entrypoint 覆盖）；PATH / VIRTUAL_ENV
# 不在镜像里写死（运行时由 entrypoint 在 setup 之后设置，避免卷布局下被遮蔽）。
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64

# ---- 容器入口（构建时打入镜像，运行期由 wrapper 调用）----
COPY docker/entrypoint-build.sh /docker/entrypoint-build.sh
RUN chmod +x /docker/entrypoint-build.sh
