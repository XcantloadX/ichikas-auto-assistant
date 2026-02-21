set windows-shell := ["powershell", "-c"]
set shell := ["pwsh", "-c"]

default:
    @just --list

res:
    uv run .\tools\make_resources.py

build:
    uv run build.py build