#!/usr/bin/env bash
# tools/android/setup_env.sh —— Android APK 构建环境准备脚本（单一来源）。
#
# 职责：把「Android APK 构建环境」的全部准备工作收进这一个脚本，**运行时执行**
#       （不是镜像 build 时），是环境定义的**唯一来源**。
#
# 三个消费方：
#   * CI：            .github/workflows/android-build.yml 在 job 运行时调用本脚本。
#   * 本地 Docker：   docker/entrypoint-build.sh 在容器启动时调用本脚本（MODE=docker）。
#   * 未来 devcontainer：.devcontainer 的 postCreate 也调用本脚本。
#
# 用法：setup_env.sh docker|ci
#   * docker：容器内 root 运行（无需 sudo）；python3.11 由本脚本经 deadsnakes PPA
#             安装；创建 venv；给 buildozer 打 check_root 补丁（root 非交互构建）。
#   * ci：    GitHub Actions ubuntu-22.04 runner 非 root 运行（apt 走 sudo）；
#             python3.11 由 actions/setup-python 提供（本脚本不装 python）；
#             不创建 venv、不打补丁（非 root 不触发 check_root）。
#   两模式的差异仅此几点：sudo / python3.11 来源 / venv / check_root 补丁。
#
# 可覆盖的环境变量（默认与 CI/镜像对齐）：
#   P4A_ARCH=x86_64  ANDROID_API=35  ANDROID_NDK=r27c
#   PYSIDE_VERSION=6.11.1  P4A_NDK_API=24
#
# 路径约定（两模式统一，全部落在 $HOME 下）：
#   wheels : $HOME/wheels
#   NDK    : $HOME/.pyside6_android_deploy/android-ndk/android-ndk-$ANDROID_NDK
#   SDK    : $HOME/android-sdk
#   venv   : $HOME/venv（仅 docker 模式）
# docker 模式 $HOME=/root，这些落在 iaa-android-cache 命名卷持久化；
# ci 模式 $HOME 就是 actions/cache 能缓存的位置。
#
# 所有步骤幂等：已存在则跳过；网络下载统一走 dl()（curl 全量重试 + speed 兜底，
# 同 CI / entrypoint 既有定义）。下载失败必须失败（set -euo pipefail）。
set -euo pipefail

# 非交互安装：本脚本在容器 / CI runner 运行时执行，均无 TTY。apt 若触发 tzdata
# 等 debconf 配置向导会卡死在交互界面（旧设计靠镜像 build 期的 ARG
# DEBIAN_FRONTEND=noninteractive 规避，运行时 setup 必须在脚本内重新设置）。
# 同时覆盖 add-apt-repository / python3.11 安装等其他潜在的交互提示。
export DEBIAN_FRONTEND=noninteractive

# ---- 模式与可覆盖参数 ----
MODE="${1:-}"
if [ "$MODE" != "docker" ] && [ "$MODE" != "ci" ]; then
    echo "用法: $0 docker|ci" >&2
    echo "  docker —— 容器内 root 运行（装 python3.11 / 建 venv / 打 check_root 补丁）" >&2
    echo "  ci     —— GitHub Actions runner 非 root 运行（sudo apt，python 由 setup-python 提供）" >&2
    exit 2
fi

: "${P4A_ARCH:=x86_64}"
: "${ANDROID_API:=35}"
: "${ANDROID_NDK:=r27c}"
: "${PYSIDE_VERSION:=6.11.1}"
: "${P4A_NDK_API:=24}"

# ---- 路径约定（两模式统一，全部 $HOME 下）----
WHEELS_DIR="$HOME/wheels"
NDK_DIR="$HOME/.pyside6_android_deploy/android-ndk/android-ndk-$ANDROID_NDK"
ANDROID_SDK_ROOT="$HOME/android-sdk"
VENV_DIR="$HOME/venv"

# apt 命令前缀：docker 模式 root 直接跑；ci 模式需要 sudo
APT=(apt-get)
[ "$MODE" = "ci" ] && APT=(sudo apt-get)

# 下载辅助：download.qt.io / dl.google.com 偶发断连，加大重试/超时（同 CI/entrypoint 的 dl()）
dl() {
    curl -fL --retry 8 --retry-all-errors --retry-delay 5 \
        --connect-timeout 30 --max-time 900 \
        --speed-limit 1024 --speed-time 60 -o "$1" "$2"
}

echo "=== setup_env.sh: mode=${MODE}, arch=${P4A_ARCH}, api=${ANDROID_API}, ndk=${ANDROID_NDK}, ndk-api=${P4A_NDK_API}, pyside=${PYSIDE_VERSION} ==="

# ---- [1] apt 系统依赖 ----
# p4a / buildozer / Qt 工具链的常规依赖。列表 = CI + Dockerfile + 容器补齐层
# （libltdl-dev / cmake，libffi / opencv recipe 需要）三处的并集，两模式统一。
APT_LIST=(
    openjdk-17-jdk-headless build-essential ccache
    autoconf automake libtool
    zlib1g-dev libffi-dev libssl-dev
    pkg-config ninja-build wget unzip zip curl
    git rsync python3-venv python3-pip
    libgl1 libglib2.0-0
    libltdl-dev cmake
)
# docker 模式额外：deadsnakes 需要 software-properties-common + gnupg。
# --no-install-recommends 会漏装 gnupg（gpg-agent），add-apt-repository 导入 PPA
# key 时 gpg 会因 agent 缺失失败，因此显式安装（见 Dockerfile 52-53 行注释）。
if [ "$MODE" = "docker" ]; then
    APT_LIST+=(software-properties-common gnupg)
fi

# apt 重试辅助：本脚本在容器/CI runner 运行时冷装系统依赖，archive.ubuntu.com
# 经代理偶发 502 / IncompleteRead（旧设计在镜像 build 期 apt，失败可见于 build
# 且层缓存可复用；运行时每次容器启动都要重下，需重试兜底）。失败必须最终失败。
apt_run() {
    local tries=3 attempt=1
    until "$@"; do
        attempt=$((attempt + 1))
        if [ "$attempt" -gt "$tries" ]; then
            echo "apt 操作连续 ${tries} 次失败：$*" >&2
            return 1
        fi
        echo "apt 操作失败（第 $((attempt - 1)) 次），5s 后重试..." >&2
        sleep 5
    done
}

need_apt=0
for pkg in "${APT_LIST[@]}"; do
    if ! dpkg -s "$pkg" >/dev/null 2>&1; then
        need_apt=1
        break
    fi
done
if [ "$need_apt" -eq 1 ]; then
    echo "=== [1] apt 系统依赖（缺失则安装）==="
    apt_run "${APT[@]}" update
    apt_run "${APT[@]}" install -y --no-install-recommends "${APT_LIST[@]}"
else
    echo "=== [1] apt 系统依赖已就绪，跳过 ==="
fi

# docker 模式额外：装宿主 python3.11（ubuntu 22.04 自带 python3.10，用 deadsnakes PPA 补齐）。
# Qt 工具链要求宿主 Python <= 3.11；deadsnakes 是官方推荐渠道（同 Dockerfile 50-60 行）。
if [ "$MODE" = "docker" ] && ! command -v python3.11 >/dev/null 2>&1; then
    echo "=== [1] 安装 python3.11（deadsnakes PPA）==="
    apt_run add-apt-repository -y ppa:deadsnakes/ppa
    apt_run apt-get update
    apt_run apt-get install -y --no-install-recommends python3.11 python3.11-venv python3.11-dev
fi

# p4a / buildozer 需要 JDK 17（Qt 官方工具链对齐版本）
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64

# ---- [2] rustup / cargo ----
# pydantic-core 的 p4a recipe（RustCompiledComponentsRecipe）需要宿主 rustup。
# docker 模式 $HOME=/root 是 iaa-android-cache 命名卷：全新卷会把镜像期装的 rustup
# 拷进来，但卷先于镜像存在/非空时可能缺失 → 缺失才重装（entrypoint 自愈逻辑，
# pydantic-core 编译依赖 rustup/cargo，见 notes/03-build-infra.md）。
if [ ! -x "$HOME/.cargo/bin/cargo" ]; then
    echo "=== [2] 安装 rustup（minimal / stable）==="
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \
        | sh -s -- -y --profile minimal --default-toolchain stable
fi
export PATH="$HOME/.cargo/bin:$PATH"

# ---- [3] 宿主 Python 与 pip 依赖 ----
# docker：创建 venv（Qt 工具链要求宿主 Python <= 3.11，venv 建在 $HOME 以便随
#         iaa-android-cache 卷持久化）。
# ci：python3.11 由 actions/setup-python 提供，直接复用，不建 venv。
if [ "$MODE" = "docker" ]; then
    if [ ! -x "$VENV_DIR/bin/python" ]; then
        echo "=== [3] 创建 venv（$VENV_DIR）==="
        /usr/bin/python3.11 -m venv "$VENV_DIR"
        "$VENV_DIR/bin/python" -m pip install --upgrade pip
    fi
    PY="$VENV_DIR/bin/python"
else
    PY="$(command -v python3)"
fi

# 主依赖 + requirements-android.txt + resgen host 依赖，幂等：PySide6/buildozer 可
# import 即视为已装齐（本脚本是环境准备的单一来源，齐全与否以该 guard 为准）。
if ! "$PY" -c 'import PySide6, buildozer' >/dev/null 2>&1; then
    echo "=== [3] pip 安装 PySide6/buildozer/cython/meson（版本与 CI/Dockerfile 对齐）==="
    "$PY" -m pip install --upgrade pip
    "$PY" -m pip install "PySide6==$PYSIDE_VERSION" "buildozer==1.5.0" "cython==0.29.33" meson

    # pyside6-android-deploy 运行时依赖（jinja2/pkginfo/tqdm/packaging==24.1），
    # 官方要求从对应 requirements-android.txt 安装精确版本；定位方式同 CI。
    echo "=== [3] pip 安装 pyside6-android-deploy 运行时依赖（requirements-android.txt）==="
    req="$("$PY" -c 'import PySide6.scripts, pathlib; print(pathlib.Path(PySide6.scripts.__file__).parent / "requirements-android.txt")')"
    "$PY" -m pip install -r "$req"

    # resgen host 依赖：tools/make_resources.py → kotonebot.devtools.resgen。
    # kotonebot 用 --no-deps（rapidocr/onnxruntime 为惰性导入，host 生成用不到）；
    # 其余为 make_resources 实际 import 需要（pydantic/rich/opencv(<5, kotonebot
    # 约束)/numpy/python-dotenv/mouse/typing-extensions/psutil，同 CI/Dockerfile）。
    echo "=== [3] pip 安装资源生成 host 依赖（kotonebot/resgen）==="
    "$PY" -m pip install --no-deps "kotonebot==0.19.1"
    "$PY" -m pip install pydantic rich "opencv-python<5.0" numpy python-dotenv mouse typing-extensions psutil
fi

# docker 模式额外：buildozer 1.5.0 的 check_root()（__init__.py 1041 附近）以 root 运行
# 且 default.spec 的 warn_on_root=1 时会 input() 交互确认；本容器 root 非交互构建，
# input() 直接 EOFError 崩溃（CI runner 非 root 所以不触发）。
# 补丁：把交互确认改为自动继续（等价始终 y），行为与 CI 对齐。
# 幂等：已打补丁则跳过（见 Dockerfile 74-91 行）。
if [ "$MODE" = "docker" ]; then
    echo "=== [3] 给 buildozer 打 check_root 补丁（docker root 非交互）==="
    "$PY" - <<'PY'
import pathlib, sys
p = pathlib.Path(sys.prefix) / 'lib' / 'python3.11' / 'site-packages' / 'buildozer' / '__init__.py'
s = p.read_text(encoding='utf-8')
old = """            cont = None
            while cont not in ('y', 'n'):
                cont = input('Are you sure you want to continue [y/n]? ')

            if cont == 'n':
                sys.exit()"""
new = """            cont = 'y'  # [container] root 非交互运行：自动继续（同 CI 非 root 行为）"""
if new in s:
    print('buildozer check_root 补丁已存在，跳过')
else:
    assert old in s, 'buildozer check_root block not found'
    p.write_text(s.replace(old, new), encoding='utf-8')
    print('已补丁 buildozer check_root（root 非交互自动继续）')
PY
fi

# ---- [4] PySide6 官方 android wheel（cp311 / android_$P4A_ARCH）----
mkdir -p "$WHEELS_DIR"
base="https://download.qt.io/official_releases/QtForPython"
if [ ! -s "$WHEELS_DIR/pyside6.whl" ]; then
    echo "=== [4] 下载 PySide6 android wheel（${PYSIDE_VERSION} / cp311 / android_${P4A_ARCH}）==="
    dl "$WHEELS_DIR/pyside6.whl" \
        "$base/pyside6/pyside6-$PYSIDE_VERSION-$PYSIDE_VERSION-cp311-cp311-android_$P4A_ARCH.whl"
fi
if [ ! -s "$WHEELS_DIR/shiboken6.whl" ]; then
    echo "=== [4] 下载 shiboken6 android wheel（${PYSIDE_VERSION} / cp311 / android_${P4A_ARCH}）==="
    dl "$WHEELS_DIR/shiboken6.whl" \
        "$base/shiboken6/shiboken6-$PYSIDE_VERSION-$PYSIDE_VERSION-cp311-cp311-android_$P4A_ARCH.whl"
fi
ls -lh "$WHEELS_DIR"

# ---- [5] Android NDK ----
# 路径与 Qt 工具缓存一致（~/.pyside6_android_deploy/android-ndk/...）。首次约 1GB。
if [ ! -d "$NDK_DIR" ]; then
    echo "=== [5] 下载 Android NDK ${ANDROID_NDK}（约 1GB，首次运行属预期）==="
    mkdir -p "$(dirname "$NDK_DIR")"
    dl /tmp/ndk-setup.zip \
        "https://dl.google.com/android/repository/android-ndk-$ANDROID_NDK-linux.zip"
    # 用 -o：幂等覆盖解压（重跑/续传中断时已有文件无提示覆盖，避免交互阻塞或非零退出）
    unzip -qo /tmp/ndk-setup.zip -d "$(dirname "$NDK_DIR")"
    rm -f /tmp/ndk-setup.zip
fi
test -f "$NDK_DIR/toolchains/llvm/prebuilt/linux-x86_64/bin/aarch64-linux-android21-clang"
echo "=== [5] NDK 就绪：${NDK_DIR} ==="

# ---- [6] Android SDK（cmdline-tools/latest + platform-tools + platforms + build-tools）----
if [ ! -x "$ANDROID_SDK_ROOT/cmdline-tools/latest/bin/sdkmanager" ]; then
    echo "=== [6] 下载 Android cmdline-tools ==="
    mkdir -p "$ANDROID_SDK_ROOT/cmdline-tools"
    dl /tmp/clt-setup.zip \
        "https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip"
    unzip -qo /tmp/clt-setup.zip -d "$ANDROID_SDK_ROOT/cmdline-tools"
    mv "$ANDROID_SDK_ROOT/cmdline-tools/cmdline-tools" \
       "$ANDROID_SDK_ROOT/cmdline-tools/latest"
    rm -f /tmp/clt-setup.zip
fi
export PATH="$ANDROID_SDK_ROOT/cmdline-tools/latest/bin:$PATH"

echo "=== [6] 接受 SDK license 并安装 platform-tools/platforms/build-tools ==="
# yes 在 sdkmanager 关闭 stdin 后收到 SIGPIPE(141)，pipefail 会把整个管道判为失败；
# 这里临时关 pipefail 只保留 sdkmanager 自身的退出码（失败照常失败）。
set +o pipefail
yes | sdkmanager --sdk_root="$ANDROID_SDK_ROOT" --licenses >/dev/null
set -o pipefail
sdkmanager --sdk_root="$ANDROID_SDK_ROOT" \
    "platform-tools" \
    "platforms;android-$ANDROID_API" \
    "build-tools;${ANDROID_API}.0.0"
test -f "$ANDROID_SDK_ROOT/platforms/android-$ANDROID_API/android.jar"
echo "=== [6] SDK 就绪：${ANDROID_SDK_ROOT} ==="
# 说明：这里刻意不给 buildozer 提供 legacy tools/bin/sdkmanager 软链——pass1
# （pyside6-android-deploy 内部）会因找不到 sdkmanager 快速失败，从而保留其生成的
# 已补丁 buildozer.spec / recipes / jars；软链由 build_android.py 在 pass2
# （buildozer 直接构建）前补上。见 .github/workflows/android-build.yml。

# ---- [7] 环境汇总 ----
PY_VERSION="$("$PY" --version 2>&1)"
echo ""
echo "=============================================="
echo "  Android 构建环境准备完成（mode=${MODE}）"
echo "=============================================="
echo "python  : ${PY}  (${PY_VERSION})"
if [ "$MODE" = "docker" ]; then
    echo "venv    : ${VENV_DIR}"
else
    echo "venv    : （ci 模式无 venv，使用 setup-python 提供的 python3）"
fi
echo "JAVA_HOME : ${JAVA_HOME}"
echo "ndk     : ${NDK_DIR}"
echo "sdk     : ${ANDROID_SDK_ROOT}"
echo "wheels  : ${WHEELS_DIR}"
echo "=============================================="