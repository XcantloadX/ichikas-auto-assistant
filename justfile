set windows-shell := ["powershell", "-c"]
set shell := ["pwsh", "-c"]

default:
    @just --list

setup:
    uv sync --group dev
    uv run ./tools/make_resources.py

res:
    uv run ./tools/make_resources.py

wheel:
    uv run python -c "import pathlib, shutil; [shutil.rmtree(p) for p in pathlib.Path('iaa').rglob('__pycache__')]"
    uv run ./tools/make_resources.py -p
    uv build --wheel

# 编译启动器 exe：dist/iaa.exe（GUI）+ dist/iaa-cli.exe（CLI）
# 启动器源码以 submodule 形式锁定在 bootstrap/LmmPyLauncher（当前 0.1.7）。
# 两个 bin 由同一份源码树产出，编译期配置由 LMM_LAUNCHER_JSON 指向本仓库的
# bootstrap/launcher/launcher.json；启动器源码树保持干净，升级启动器只需更新
# submodule 的检出提交。
# 可用 CARGO_TARGET_DIR 把编译产物放到别的盘（产物约 1GB）。
launcher:
    git submodule update --init bootstrap/LmmPyLauncher
    $env:LMM_LAUNCHER_JSON = (Resolve-Path bootstrap/launcher/launcher.json).Path; cargo build --release --bins --manifest-path bootstrap/LmmPyLauncher/Cargo.toml
    $t = if ($env:CARGO_TARGET_DIR) { $env:CARGO_TARGET_DIR } else { "bootstrap/LmmPyLauncher/target" }; New-Item -ItemType Directory -Force -Path dist | Out-Null; Copy-Item "$t/release/LmmPyLauncher.exe" dist/iaa.exe -Force; Copy-Item "$t/release/LmmPyLauncherCli.exe" dist/iaa-cli.exe -Force

# wheel + 启动器 exe
build: wheel launcher