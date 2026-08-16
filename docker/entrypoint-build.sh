#!/usr/bin/env bash
# docker/entrypoint-build.sh —— 容器内一键 Android APK 构建入口（幂等）。
#
# 职责（与 .github/workflows/android-build.yml 的预装/下载步骤对齐）：
#   a. NDK   ：/root/.pyside6_android_deploy/android-ndk/android-ndk-r27c
#   b. SDK   ：/root/android-sdk（cmdline-tools/latest + platform-tools +
#              platforms;android-$API + build-tools;$API.0.0）
#   c. wheels：/root/wheels/pyside6.whl 与 /root/wheels/shiboken6.whl（Qt 官方 android wheel）
#   d. 调用 /workspace/tools/android/build_android.py 完成 prep/resgen/
#      pass1/patch/pass2/collect，并透传其退出码。
#
# 架构 / API 允许用环境变量覆盖（wrapper 会传 -e）：
#   P4A_ARCH / ANDROID_API / ANDROID_NDK / PYSIDE_VERSION / P4A_NDK_API。
#
# 约定：NDK/SDK/wheels 下载失败必须失败（set -euo pipefail）；
# build_android.py 内部 pass1 的容错由它自己处理，这里不干预。
set -euo pipefail

# ---- 可覆盖参数（默认与 CI 一致）----
: "${P4A_ARCH:=x86_64}"
: "${ANDROID_API:=35}"
: "${ANDROID_NDK:=r27c}"
: "${PYSIDE_VERSION:=6.11.1}"
: "${P4A_NDK_API:=24}"

ANDROID_NDK_ROOT="/root/.pyside6_android_deploy/android-ndk"
NDK_DIR="${ANDROID_NDK_ROOT}/android-ndk-${ANDROID_NDK}"
ANDROID_SDK_ROOT="/root/android-sdk"
# wheels 与 NDK/SDK/cargo/rustup/buildozer/gradle 一样收进 /root（= iaa-android-cache
# 命名卷），跨次运行幂等复用，不再依赖主机挂载目录。
WHEELS_DIR="/root/wheels"

# 路径导出：buildozer / sdkmanager / pyside6-android-deploy 都依赖这些
export PATH="/opt/venv/bin:/root/.cargo/bin:${ANDROID_SDK_ROOT}/cmdline-tools/latest/bin:${PATH}"
export JAVA_HOME="${JAVA_HOME:-/usr/lib/jvm/java-17-openjdk-amd64}"
export ANDROID_SDK_ROOT ANDROID_NDK_ROOT

echo "=== [entrypoint] 环境 ==="
echo "python     : $(/opt/venv/bin/python --version 2>&1)"
echo "arch/api   : ${P4A_ARCH} / ${ANDROID_API}"
echo "ndk        : ${ANDROID_NDK} (api=${P4A_NDK_API})"
echo "sdk root   : ${ANDROID_SDK_ROOT}"
echo "ndk root   : ${NDK_DIR}"
echo "wheels dir : ${WHEELS_DIR}"
echo ""

# 下载辅助：download.qt.io 会 302 到镜像，SSL 偶发断连，加大重试/超时（同 CI）
dl() {
  curl -fL --retry 8 --retry-all-errors --retry-delay 5 \
    --connect-timeout 30 --max-time 900 \
    --speed-limit 1024 --speed-time 60 -o "$1" "$2"
}

# ---- 0. rustup 自愈 ----
# /root 是 iaa-android-cache 命名卷：首次挂载的全新卷会把镜像内 /root/.cargo 拷进来，
# 但一旦卷非空（或先于镜像存在），镜像构建期装的 rustup 就可能缺失/被遮蔽；因此
# 这里不依赖镜像内容，缺失则在卷内重装。这是卷布局下的既有能力，删除会破坏首次
# 构建，务必保留。
# （pydantic-core 的 p4a recipe 依赖 rustup/cargo，见 notes/03-build-infra.md。）
if [ ! -x "$HOME/.cargo/bin/cargo" ]; then
  echo "=== [entrypoint] 检测到 cargo 缺失（命名卷内无 rustup），重装 rustup ==="
  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \
    | sh -s -- -y --profile minimal --default-toolchain stable
  export PATH="/root/.cargo/bin:${PATH}"
fi
cargo --version

# ---- a. NDK：首次运行约 1GB，下载到挂载缓存，之后幂等跳过 ----
if [ ! -d "${NDK_DIR}" ]; then
  echo "=== [entrypoint] 下载 Android NDK ${ANDROID_NDK}（约 1GB，首次运行属预期）==="
  mkdir -p "${ANDROID_NDK_ROOT}"
  dl /tmp/ndk.zip \
    "https://dl.google.com/android/repository/android-ndk-${ANDROID_NDK}-linux.zip"
  # 用 -o：幂等覆盖解压（缓存进命名卷后无 NTFS 大小写问题，但重跑/续传中断时
  # 已有文件需无提示覆盖，避免交互阻塞或 unzip 返回非零）。
  unzip -qo /tmp/ndk.zip -d "${ANDROID_NDK_ROOT}"
  rm -f /tmp/ndk.zip
fi
test -f "${NDK_DIR}/toolchains/llvm/prebuilt/linux-x86_64/bin/aarch64-linux-android21-clang"
echo "NDK 就绪：${NDK_DIR}"

# ---- b. SDK：cmdline-tools/latest + platform-tools + platforms + build-tools ----
if [ ! -x "${ANDROID_SDK_ROOT}/cmdline-tools/latest/bin/sdkmanager" ]; then
  echo "=== [entrypoint] 下载 Android cmdline-tools ==="
  mkdir -p "${ANDROID_SDK_ROOT}/cmdline-tools"
  dl /tmp/clt.zip \
    "https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip"
  unzip -qo /tmp/clt.zip -d "${ANDROID_SDK_ROOT}/cmdline-tools"
  mv "${ANDROID_SDK_ROOT}/cmdline-tools/cmdline-tools" \
     "${ANDROID_SDK_ROOT}/cmdline-tools/latest"
  rm -f /tmp/clt.zip
fi

echo "=== [entrypoint] 接受 SDK license 并安装 platform-tools/platforms/build-tools ==="
# yes 在 sdkmanager 关闭 stdin 后会收到 SIGPIPE(141)，pipefail 会把整个管道判为
# 失败；这里临时关 pipefail 只保留 sdkmanager 自身的退出码（失败照常失败）。
set +o pipefail
yes | sdkmanager --sdk_root="${ANDROID_SDK_ROOT}" --licenses >/dev/null
set -o pipefail
sdkmanager --sdk_root="${ANDROID_SDK_ROOT}" \
  "platform-tools" \
  "platforms;android-${ANDROID_API}" \
  "build-tools;${ANDROID_API}.0.0"
test -f "${ANDROID_SDK_ROOT}/platforms/android-${ANDROID_API}/android.jar"
echo "SDK 就绪：${ANDROID_SDK_ROOT}"
# 说明：这里刻意不给 buildozer 提供 legacy tools/bin/sdkmanager 软链——pass1
# （pyside6-android-deploy 内部）会因找不到 sdkmanager 快速失败，从而保留其
# 生成的已补丁 buildozer.spec / recipes / jars；软链由 build_android.py 在
# pass2（buildozer 直接构建）前补上。见 .github/workflows/android-build.yml。

# ---- c. wheels：Qt 官方 android wheel（cp311 / android_$P4A_ARCH），下载到 /root/wheels ----
# 目录在 iaa-android-cache 命名卷内持久化，幂等跳过已存在文件。
mkdir -p "${WHEELS_DIR}"
base="https://download.qt.io/official_releases/QtForPython"
if [ ! -s "${WHEELS_DIR}/pyside6.whl" ]; then
  echo "=== [entrypoint] 下载 PySide6 android wheel（${PYSIDE_VERSION} / cp311 / android_${P4A_ARCH}）==="
  dl "${WHEELS_DIR}/pyside6.whl" \
    "${base}/pyside6/pyside6-${PYSIDE_VERSION}-${PYSIDE_VERSION}-cp311-cp311-android_${P4A_ARCH}.whl"
fi
if [ ! -s "${WHEELS_DIR}/shiboken6.whl" ]; then
  dl "${WHEELS_DIR}/shiboken6.whl" \
    "${base}/shiboken6/shiboken6-${PYSIDE_VERSION}-${PYSIDE_VERSION}-cp311-cp311-android_${P4A_ARCH}.whl"
fi
ls -lh "${WHEELS_DIR}"

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
/opt/venv/bin/python - "${P4A_CLONE_DIR}" <<'PY'
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
exec /opt/venv/bin/python /workspace/tools/android/build_android.py \
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
