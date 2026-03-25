set windows-shell := ["powershell", "-c"]
set shell := ["pwsh", "-c"]

default:
    @just --list

setup:
    uv sync --group dev

res:
    uv run ./tools/make_resources.py

build:
    uv run build.py build