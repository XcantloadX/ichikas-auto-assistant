# 本地 Draft Release

## 前置条件
- 已安装 `git`、`uv`、`gh`
- `gh auth status` 已通过

## 命令

宿主机构建并发布：
```powershell
uv run python tools/release_publish.py
```

只做校验和生成说明：
```powershell
uv run python tools/release_publish.py --dry-run
```

## 调试
```powershell
uv run python tools/release_publish.py --dry-run --skip-release-check
```
