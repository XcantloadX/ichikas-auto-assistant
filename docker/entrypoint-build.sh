#!/usr/bin/env bash
# docker/entrypoint-build.sh —— 容器内一键 Android APK 构建入口（幂等）。
#
# 职责（环境逻辑收敛到 tools/android/setup_env.sh，单一来源）：
#   a. 顶部调用 `bash /workspace/tools/android/setup_env.sh docker`：幂等准备
#      全部环境（python3.11 + venv + pip 依赖 + rustup + NDK + SDK + wheels +
#      buildozer check_root 补丁），并把 JAVA_HOME / PATH（cargo bin 等）export 到
#      当前 shell。
#   b. setup 之后按运行时约定补设 VIRTUAL_ENV / PATH / ANDROID_SDK_ROOT /
#      ANDROID_NDK_ROOT（路径统一 $HOME 下，与 CI 一致）。
#   c. 加固 p4a 源码下载（P4A_HTTP_VIA_CURL 补丁，对不稳定网络幂等）。
#   d. 调用 /workspace/tools/android/build_android.py 完成 prep/resgen/
#      pass1/patch/pass2/collect，并透传其退出码。
#
# 架构 / API 允许用环境变量覆盖（wrapper 会传 -e）：
#   P4A_ARCH / ANDROID_API / ANDROID_NDK / PYSIDE_VERSION / P4A_NDK_API。
#
# 约定：环境准备失败必须失败（set -euo pipefail）；
# build_android.py 内部 pass1 的容错由它自己处理，这里不干预。
set -euo pipefail

# ---- 可覆盖参数（默认与 CI 一致）----
: "${P4A_ARCH:=x86_64}"
: "${ANDROID_API:=35}"
: "${ANDROID_NDK:=r27c}"
: "${PYSIDE_VERSION:=6.11.1}"
: "${P4A_NDK_API:=24}"

# ---- 0. 运行时统一 setup：环境单一来源（docker 模式）----
# 仓库挂载在 /workspace（只读），脚本在 /workspace/tools/android/setup_env.sh。
# 脚本幂等：首次运行下载 NDK/SDK/wheels（落 iaa-android-cache 命名卷 = $HOME），
# 之后跳过；会把 JAVA_HOME 与 PATH（cargo bin 等）export 到当前 shell。
echo "=== [entrypoint] 调用共享 setup_env.sh（docker 模式）==="
bash /workspace/tools/android/setup_env.sh docker

# ---- setup 之后按运行时约定补设环境 ----
# 路径统一 $HOME 下（与 setup_env.sh 两模式一致）：
#   SDK=$HOME/android-sdk；NDK=$HOME/.pyside6_android_deploy/android-ndk。
# VIRTUAL_ENV 必须显式声明（仅 docker 模式脚本建 venv，路径 $HOME/venv），否则
# buildozer 的 install_platform 会按非 venv 走 `pip install --user`，在 venv 内报
# "Can not perform a '--user' install. User site-packages are not visible in this
# virtualenv."
export ANDROID_SDK_ROOT="$HOME/android-sdk"
export ANDROID_NDK_ROOT="$HOME/.pyside6_android_deploy/android-ndk"
export VIRTUAL_ENV="$HOME/venv"
export PATH="$HOME/venv/bin:$HOME/.cargo/bin:${ANDROID_SDK_ROOT}/cmdline-tools/latest/bin:${PATH}"
export JAVA_HOME="${JAVA_HOME:-/usr/lib/jvm/java-17-openjdk-amd64}"

NDK_DIR="${ANDROID_NDK_ROOT}/android-ndk-${ANDROID_NDK}"
WHEELS_DIR="$HOME/wheels"

echo "=== [entrypoint] 环境 ==="
echo "python     : $($HOME/venv/bin/python --version 2>&1)"
echo "arch/api   : ${P4A_ARCH} / ${ANDROID_API}"
echo "ndk        : ${ANDROID_NDK} (api=${P4A_NDK_API})"
echo "sdk root   : ${ANDROID_SDK_ROOT}"
echo "ndk root   : ${NDK_DIR}"
echo "wheels dir : ${WHEELS_DIR}"
echo ""

# ---- d0. 加固 p4a 源码下载（对不稳定网络幂等补丁）----
# p4a 由 buildozer 在首次 pass2 时 clone 到 app 缓存（/build/app/.buildozer/...）。
# 其 download_file 用 urlretrieve：GitHub codeload 的 chunked 传输中途断连会抛
# IncompleteRead（非 OSError，p4a 自带的 5 次重试不生效），导致 opencv 等大源码
# 包下载在 ~100MB 处直接失败（见 notes/13-local-docker-build.md）。这里幂等改为
# curl 下载：--retry-all-errors 全量重试 + -C - 断点续传 + speed 兜底。clone 缺失
# 时先补 clone（buildozer 见已存在会跳过内嵌 clone），保证补丁在首次即生效。
P4A_CLONE_DIR="/build/app/.buildozer/android/platform/python-for-android"
if [ ! -d "${P4A_CLONE_DIR}/.git" ]; then
  echo "=== [entrypoint] 预 clone python-for-android（develop）供下载补丁 ==="
  mkdir -p "$(dirname "${P4A_CLONE_DIR}")"
  git clone -b develop --single-branch \
    https://github.com/kivy/python-for-android.git "${P4A_CLONE_DIR}"
fi
"$HOME/venv/bin/python" - "${P4A_CLONE_DIR}" <<'PY'
import pathlib, sys
repo = pathlib.Path(sys.argv[1])
p = repo / 'pythonforandroid' / 'recipe.py'
s = p.read_text(encoding='utf-8')
if 'P4A_HTTP_VIA_CURL' in s:
    print('[entrypoint] p4a download 补丁已存在，跳过')
else:
    anchor = "        if parsed_url.scheme in ('http', 'https'):\n"
    assert anchor in s, 'p4a recipe.py 锚点未找到，无法打补丁'
    patch = (
        "        if parsed_url.scheme in ('http', 'https') and environ.get('P4A_HTTP_VIA_CURL') == '1':\n"
        "            from shutil import which\n"
        "            curl = which('curl') or 'curl'\n"
        "            if cwd:\n"
        "                target = join(cwd, target)\n"
        "            subprocess.check_call([curl, '-fL', '--retry', '8',\n"
        "                                   '--retry-all-errors', '--retry-delay', '5',\n"
        "                                   '--connect-timeout', '30', '--max-time', '1800',\n"
        "                                   '--speed-limit', '1024', '--speed-time', '60',\n"
        "                                   '-C', '-', '-o', target, url])\n"
        "            return target\n"
        "\n"
    )
    p.write_text(s.replace(anchor, patch + anchor, 1), encoding='utf-8')
    print('[entrypoint] 已补丁 p4a download_file -> curl（断点续传+重试）')
PY
export P4A_HTTP_VIA_CURL=1

# ---- d. 调用共享构建脚本（透传其退出码）----
echo "=== [entrypoint] 开始 Android APK 构建（build_android.py）==="
exec "$HOME/venv/bin/python" /workspace/tools/android/build_android.py \
  --repo=/workspace \
  --app-dir=/build/app \
  --wheels-dir="${WHEELS_DIR}" \
  --sdk-dir="${ANDROID_SDK_ROOT}" \
  --ndk-dir="${NDK_DIR}" \
  --output=/artifacts \
  --arch "${P4A_ARCH}" \
  --api "${ANDROID_API}" \
  --ndk-api "${P4A_NDK_API}" \
  --ndk-version "${ANDROID_NDK}" \
  --pyside-version "${PYSIDE_VERSION}"
