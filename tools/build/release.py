"""GitHub 发布工具，适用于 kotonebot 框架下游项目。"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from ._utils import REPO_ROOT, require_tool, run_command, run_git


@dataclass
class ReleaseConfig:
    """GitHub 发布配置。"""

    name: str
    """应用名称，用于生成产物文件名匹配模式：{name}_v{version}_*.7z / *.zip。"""

    changelog: Path = field(default_factory=lambda: Path('doc/CHANGELOG.md'))
    """CHANGELOG.md 路径，相对于项目根目录。"""

    dist_dir: Path = field(default_factory=lambda: Path('dist_app'))
    """构建产物目录，相对于项目根目录。"""


# ── Changelog ──────────────────────────────────────────────────────────────


def extract_changelog_section(config: ReleaseConfig, tag: str) -> str:
    """从 CHANGELOG.md 中提取指定 tag 对应的章节内容。"""
    changelog_path = REPO_ROOT / config.changelog
    content = changelog_path.read_text(encoding='utf-8')
    pattern = re.compile(
        rf'^##\s+{re.escape(tag)}\s*$\n(?P<body>.*?)(?=^##\s+|\Z)',
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(content)
    if not match:
        raise RuntimeError(f'在 {changelog_path} 中找不到 tag {tag} 对应的章节')
    return match.group('body').strip()


def format_commit_history(tag: str, previous_tag: str | None) -> str:
    """格式化两个 tag 之间的提交历史。"""
    revision_range = f'{previous_tag}..{tag}' if previous_tag else tag
    history = run_git('log', '--format=- %h %s', revision_range)
    if not history:
        raise RuntimeError(f'找不到 {revision_range} 的提交历史')
    return history


def build_release_body(config: ReleaseConfig, tag: str, previous_tag: str | None) -> str:
    """生成发布说明正文（更新日志 + 完整提交历史）。"""
    changelog = extract_changelog_section(config, tag)
    history = format_commit_history(tag, previous_tag)
    return '\n\n'.join(['## 更新日志', changelog, '## 完整历史', history])


# ── 产物查找 ────────────────────────────────────────────────────────────────


def find_release_asset(config: ReleaseConfig, version: str) -> Path:
    """在 dist_dir 中查找与版本号匹配的唯一发布产物。"""
    dist_dir = REPO_ROOT / config.dist_dir
    matches: list[Path] = []
    for pattern in [f'{config.name}_v{version}_*.7z', f'{config.name}_v{version}_*.zip']:
        matches.extend(p.resolve() for p in dist_dir.glob(pattern) if p.is_file())
    unique = sorted(set(matches))
    if not unique:
        raise RuntimeError(f'在 {dist_dir} 中找不到版本 {version} 的发布产物')
    if len(unique) != 1:
        raise RuntimeError(f'版本 {version} 匹配到多个产物：\n' + '\n'.join(str(p) for p in unique))
    return unique[0]


# ── GitHub 操作 ─────────────────────────────────────────────────────────────


def parse_repo_slug(remote_url: str) -> str:
    """从 git remote URL 解析 GitHub 仓库 slug（owner/name）。"""
    ssh_match = re.match(r'git@github\.com:(?P<slug>[^/]+/[^/]+?)(?:\.git)?$', remote_url)
    if ssh_match:
        return ssh_match.group('slug')
    parsed = urlparse(remote_url)
    if parsed.netloc.lower() != 'github.com':
        raise RuntimeError(f'origin remote 不是 GitHub 仓库：{remote_url}')
    path = parsed.path.lstrip('/').removesuffix('.git')
    if path.count('/') != 1:
        raise RuntimeError(f'无法从 remote URL 解析仓库 slug：{remote_url}')
    return path


def detect_repo_slug(repo_override: str | None = None) -> str:
    """获取当前仓库的 GitHub slug，优先使用手动传入值。"""
    if repo_override:
        return repo_override
    return parse_repo_slug(run_git('remote', 'get-url', 'origin'))


def ensure_gh_authenticated() -> None:
    """确认 gh CLI 已登录，未登录则抛出异常。"""
    require_tool('gh')
    status = run_command(['gh', 'auth', 'status'], check=False)
    if status.returncode != 0:
        detail = status.stderr.strip() or status.stdout.strip() or 'gh auth status 失败'
        raise RuntimeError(f'GitHub CLI 未登录。\n{detail}')


def check_release_absent(repo_slug: str, tag: str, *, skip: bool = False) -> None:
    """检查指定 tag 的 release 是否已存在，已存在则抛出异常。"""
    if skip:
        return
    result = run_command(['gh', 'release', 'view', tag, '--repo', repo_slug], check=False)
    if result.returncode == 0:
        raise RuntimeError(f'{repo_slug} 中 tag {tag} 的 release 已存在')
    if result.returncode != 1:
        detail = result.stderr.strip() or result.stdout.strip() or 'gh release view 失败'
        raise RuntimeError(f'查询 {tag} 的 release 状态失败。\n{detail}')


def create_github_release(
    repo_slug: str, tag: str, asset_path: Path, body_path: Path
) -> None:
    """通过 gh CLI 创建 draft release 并上传产物。"""
    run_command(
        [
            'gh', 'release', 'create', tag, str(asset_path),
            '--repo', repo_slug,
            '--draft',
            '--title', tag,
            '--notes-file', str(body_path),
        ],
        capture_output=False,
    )


# ── CI 工具 ─────────────────────────────────────────────────────────────────


def append_github_output(path: Path, values: dict[str, str]) -> None:
    """向 GitHub Actions 的 GITHUB_OUTPUT 文件追加输出变量。"""
    with path.open('a', encoding='utf-8', newline='\n') as fh:
        for key, value in values.items():
            fh.write(f'{key}={value}\n')
