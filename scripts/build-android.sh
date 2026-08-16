#!/usr/bin/env bash
# scripts/build-android.sh —— 一键构建 iaa 的 Android APK（本地 Docker 化，
# Linux / macOS 主机）。与 scripts/build-android.ps1 功能一致（Windows 用 ps1）。
#
# 流程：
#   1) docker build -f docker/android-build.Dockerfile -t iaa-android-build .
#   2) docker run 挂载仓库（只读）+ 两个 Docker 命名卷，执行
#      /docker/entrypoint-build.sh
#   3) docker cp 从容器 /artifacts 取回 APK 到 $IAA_ANDROID_OUT（默认 <仓库根>/bin），
#      随后删除构建容器（即使构建失败也会执行）。
#
# 缓存全部在 Docker 命名卷内，主机不再挂载/创建任何缓存目录（旧的
# ~/.iaa-android-cache 布局已作废，不迁移、不兼容）：
#   iaa-android-app   → /build/app（构建工作目录，.buildozer 随卷持久化跨次增量）
#   iaa-android-cache → /root（NDK / SDK / wheels / cargo / rustup / buildozer / gradle）
# 首次运行会下载 NDK（约 1GB）/ SDK / PySide6 android wheel，属预期行为。
#
# 可用环境变量覆盖参数：
#   P4A_ARCH / ANDROID_API / PYSIDE_VERSION / ANDROID_NDK /
#   IAA_ANDROID_TAG / IAA_ANDROID_PLATFORM /
#   IAA_ANDROID_OUT / IAA_ANDROID_SKIP_BUILD / IAA_ANDROID_DRY_RUN
set -euo pipefail

# ---- 参数（默认与 CI 一致）----
ARCH="${P4A_ARCH:-x86_64}"
API="${ANDROID_API:-35}"
PYSIDE_VERSION="${PYSIDE_VERSION:-6.11.1}"
NDK_VERSION="${ANDROID_NDK:-r27c}"
TAG="${IAA_ANDROID_TAG:-iaa-android-build}"
PLATFORM="${IAA_ANDROID_PLATFORM:-linux/amd64}"
SKIP_BUILD="${IAA_ANDROID_SKIP_BUILD:-0}"
DRY_RUN="${IAA_ANDROID_DRY_RUN:-0}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
OUT_DIR="${IAA_ANDROID_OUT:-${REPO_ROOT}/bin}"

# 构建容器命名（时间戳后缀，避免与上次残留容器撞名）；docker cp / docker rm 复用它
CONTAINER="iaa-android-build-$(date +%Y%m%d-%H%M%S)"

mkdir -p "${OUT_DIR}"

echo ""
echo "=============================================="
echo "  iaa Android APK 一键构建（Docker 化）"
echo "=============================================="
echo "  仓库根   : ${REPO_ROOT}"
echo "  架构/API : ${ARCH} / ${API}   (NDK ${NDK_VERSION} / PySide6 ${PYSIDE_VERSION})"
echo "  输出目录 : ${OUT_DIR}"
echo "  镜像标签 : ${TAG}   (Platform: ${PLATFORM})"
echo "  缓存     : Docker 命名卷 iaa-android-app(→/build/app) + iaa-android-cache(→/root)"
echo ""

# ---- [1/3] docker build ----
if [ "${SKIP_BUILD}" = "1" ]; then
    echo "[1/3] 已指定 SKIP_BUILD=1，使用已有镜像 ${TAG}"
else
    echo "[1/3] 构建 Docker 镜像 ${TAG}（最小底座，通常 1-2 分钟；环境由 entrypoint 运行时准备）..."
    build_args=(build --platform "${PLATFORM}" --progress=plain \
        -f "${REPO_ROOT}/docker/android-build.Dockerfile" -t "${TAG}" "${REPO_ROOT}")
    if [ "${DRY_RUN}" = "1" ]; then
        echo "DRY-RUN> docker ${build_args[*]}"
    else
        t0=$(date +%s)
        docker "${build_args[@]}"
        t1=$(date +%s)
        echo "[1/3] 镜像构建完成，耗时 $(( (t1 - t0) / 60 )) 分 $(( (t1 - t0) % 60 )) 秒"
    fi
fi

# ---- [2/3] docker run：仓库只读 + 两个命名卷，执行入口脚本 ----
# 缓存全部收进 Docker 命名卷：iaa-android-app(→/build/app，构建目录，.buildozer
# 跨次增量) 与 iaa-android-cache(→/root，NDK/SDK/wheels/cargo/rustup/buildozer/gradle)。
# 产物留在容器内 /artifacts，跑完后 docker cp 取回，再删除容器（即使构建失败也执行）。
# 不用 --rm：容器需要有名字供 docker cp / docker rm 使用。
run_args=(run --name "${CONTAINER}" --platform "${PLATFORM}"
    -e "P4A_ARCH=${ARCH}"
    -e "ANDROID_API=${API}"
    -e "PYSIDE_VERSION=${PYSIDE_VERSION}"
    -e "ANDROID_NDK=${NDK_VERSION}"
    -v "${REPO_ROOT}:/workspace:ro"
    -v "iaa-android-app:/build/app"
    -v "iaa-android-cache:/root"
    "${TAG}"
    /docker/entrypoint-build.sh)

echo ""
echo "[2/3] 启动构建容器（NDK/SDK/wheels 已在命名卷则跳过下载）..."
echo "  命令: docker ${run_args[*]}"
if [ "${DRY_RUN}" = "1" ]; then
    echo "DRY-RUN: 不真正执行容器。"
    echo ""
    echo "[3/3] DRY-RUN 将执行："
    echo "  docker cp ${CONTAINER}:/artifacts/. ${OUT_DIR}"
    echo "  docker rm -f ${CONTAINER}"
    echo "DRY-RUN: 结束。"
else
    set +e
    docker "${run_args[@]}"
    RUN_STATUS=$?
    set -e
    # 无论成败都取回产物并清理容器（RUN_STATUS 保留用于最终退出码）
    echo ""
    echo "[3/3] docker cp 取回容器内 /artifacts 产物 -> 输出目录..."
    if docker cp "${CONTAINER}:/artifacts/." "${OUT_DIR}"; then
        echo "  docker cp 完成。"
    else
        echo "  docker cp 取回产物失败（容器可能未启动），忽略并继续清理。" >&2
    fi
    docker rm -f "${CONTAINER}" >/dev/null 2>&1 || true
    echo "  已清理容器 ${CONTAINER}"
    if [ "${RUN_STATUS}" -ne 0 ]; then
        echo "容器构建失败（退出码 ${RUN_STATUS}），详见上方日志。" >&2
        exit "${RUN_STATUS}"
    fi
fi

# ---- [3/3] 输出产物（非 dry-run 时 APK 已由上方 docker cp 落地）----
echo ""
echo "构建结束，产物如下："
count=$(find "${OUT_DIR}" -maxdepth 1 -name '*.apk' 2>/dev/null | wc -l)
if [ "${count}" -gt 0 ]; then
    for f in "${OUT_DIR}"/*.apk; do
        size=$(du -h "$f" | cut -f1)
        echo "  APK -> ${f}  (${size})"
    done
    first=$(find "${OUT_DIR}" -maxdepth 1 -name '*.apk' | head -n1)
    echo ""
    echo "安装到模拟器示例："
    echo "  adb install -r \"${first}\""
else
    echo "  未在输出目录找到 *.apk —— 构建可能失败或产物路径不一致，请查看上方日志。" >&2
fi