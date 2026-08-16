set windows-shell := ["powershell", "-c"]
set shell := ["pwsh", "-c"]

default:
    @just --list

setup:
    uv sync --group dev
    uv run ./tools/make_resources.py

res:
    uv run ./tools/make_resources.py

build:
    uv run build.py build

# Docker 化本地构建 Android APK（调用 scripts/build-android.ps1，见其 -Help）
android-docker:
    pwsh ./scripts/build-android.ps1