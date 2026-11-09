"""生成 GitHub Release 的说明文本。

标题顺序固定为：更新说明 → 下载说明 → 完整历史。

    ## 更新说明
    <doc/CHANGELOG.md 中对应版本的段落>

    ## 下载说明
    <固定的分发指引，zip 名带 launcher 版本>

    ## 完整历史
    - <short> <subject>        （上一个发布 tag 到 HEAD）

这里有两个相互独立的版本号：

- **iaa 版本**：`iaa/__meta__.py` 的 `__VERSION__`，决定 release 的 tag/标题，也是 wheel 的版本；
- **launcher 版本**：`bootstrap/LmmPyLauncher/Cargo.toml` 的 `[package] version`，
  决定附件名 `launcher.v<ver>.zip`。启动器独立演进，iaa 升版本时它通常不变，
  所以不能用 iaa 版本去命名。

与旧的 release_draft.py 的另一处差别是版本来源：旧实现取"仓库里最新的 tag"，
本实现直接读版本文件，因为现在的流程是"先跑工作流、由它顺手打 tag"，
触发时 tag 可能还不存在。

用法：
    python tools/release_notes.py version                      # iaa 版本，如 26.11
    python tools/release_notes.py launcher-version             # launcher 版本，如 0.1.7
    python tools/release_notes.py body --output body.md        # 完整说明
"""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CHANGELOG = REPO_ROOT / 'doc' / 'CHANGELOG.md'
DEFAULT_META = REPO_ROOT / 'iaa' / '__meta__.py'
DEFAULT_LAUNCHER_MANIFEST = REPO_ROOT / 'bootstrap' / 'LmmPyLauncher' / 'Cargo.toml'

# 完整历史的条数上限：仅在没有上一个 tag 时生效，避免首次发布时贴进整部历史
HISTORY_LIMIT = 50

DOWNLOAD_NOTE = """## 下载说明
下载「launcher.v{launcher_version}.zip」后解压，双击「iaa.exe」，安装并启动小助手。
已安装用户可直接正常启动，自动更新，无需重复下载。"""

_VERSION_RE = re.compile(
    r'^(\d+)\.(\d+)(?:\.(\d+))?(?:\.(\d+))?'
    r'(?:[-.]?(?:b|beta)(\d+)|[-.]?(?:rc)(\d+))?',
    re.IGNORECASE,
)


def run_git(*args: str) -> str:
    result = subprocess.run(
        ['git', *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='strict',
        check=False,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or 'git command failed'
        raise RuntimeError(f'git {" ".join(args)} failed: {message}')
    return result.stdout.strip()


def read_version(meta_path: Path = DEFAULT_META) -> str:
    """从 iaa/__meta__.py 读取 iaa 版本号。"""
    content = meta_path.read_text(encoding='utf-8')
    match = re.search(r'^__VERSION__\s*=\s*[\'"]([^\'"]+)[\'"]', content, re.MULTILINE)
    if match is None:
        raise RuntimeError(f'Unable to find __VERSION__ in {meta_path}')
    return match.group(1)


def read_launcher_version(manifest_path: Path = DEFAULT_LAUNCHER_MANIFEST) -> str:
    """从启动器的 Cargo.toml 读取 [package] version。

    只认 [package] 段内的 version，避免误取依赖项的版本号。
    """
    if not manifest_path.is_file():
        raise RuntimeError(
            f'{manifest_path} not found. Run '
            '`git submodule update --init bootstrap/LmmPyLauncher`, '
            'or pass --launcher-version explicitly.'
        )
    in_package = False
    for line in manifest_path.read_text(encoding='utf-8').splitlines():
        stripped = line.strip()
        if stripped.startswith('[') and stripped.endswith(']'):
            in_package = stripped == '[package]'
            continue
        if not in_package:
            continue
        match = re.match(r'version\s*=\s*[\'"]([^\'"]+)[\'"]', stripped)
        if match is not None:
            return match.group(1)
    raise RuntimeError(f'Unable to find [package] version in {manifest_path}')


def version_key(value: str) -> tuple[int, ...]:
    """把 tag/版本号转换成可比较的元组，非法形式排在最前（视为更旧）。"""
    match = _VERSION_RE.match(value.lstrip('vV'))
    if match is None:
        return (0, 0, 0, 0, 0, 0)
    major, minor, patch, build, beta, rc = match.groups()
    if beta is not None:
        stage, seq = 0, int(beta)
    elif rc is not None:
        stage, seq = 1, int(rc)
    else:
        stage, seq = 2, 0
    return (int(major), int(minor), int(patch or 0), int(build or 0), stage, seq)


def list_tags() -> list[str]:
    output = run_git('tag', '--sort=-v:refname')
    return [line.strip() for line in output.splitlines() if line.strip()]


def find_previous_tag(version: str) -> str | None:
    """找出严格早于当前版本的最新 tag；没有则返回 None。"""
    current = version_key(version)
    older = [tag for tag in list_tags() if version_key(tag) < current]
    if not older:
        return None
    return max(older, key=version_key)


def extract_changelog_section(changelog_path: Path, tag: str) -> str:
    content = changelog_path.read_text(encoding='utf-8')
    pattern = re.compile(
        rf'^##\s+{re.escape(tag)}\s*$\n(?P<body>.*?)(?=^##\s+|\Z)',
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(content)
    if match is None:
        raise RuntimeError(f'Unable to find CHANGELOG section for tag {tag} in {changelog_path}')
    body = match.group('body').strip()
    if not body:
        raise RuntimeError(f'CHANGELOG section for tag {tag} is empty')
    return body


def format_commit_history(previous_tag: str | None) -> str:
    """上一个 tag 到 HEAD 的提交列表；无上一个 tag 时取最近若干条。"""
    if previous_tag is None:
        args = ('log', f'--max-count={HISTORY_LIMIT}', '--format=- %h %s', 'HEAD')
    else:
        args = ('log', '--format=- %h %s', f'{previous_tag}..HEAD')
    history = run_git(*args).strip()
    if not history:
        raise RuntimeError(f'No commit history found for the range of {previous_tag or "HEAD"}')
    return history


def build_release_body(
    version: str,
    launcher_version: str,
    changelog_path: Path = DEFAULT_CHANGELOG,
) -> str:
    tag = f'v{version}'
    changelog = extract_changelog_section(changelog_path, tag)
    history = format_commit_history(find_previous_tag(version))
    return '\n\n'.join(
        [
            '## 更新说明',
            changelog,
            DOWNLOAD_NOTE.format(launcher_version=launcher_version),
            '## 完整历史',
            history,
        ]
    ) + '\n'


def command_version(args: argparse.Namespace) -> int:
    print(read_version())
    return 0


def command_launcher_version(args: argparse.Namespace) -> int:
    print(read_launcher_version())
    return 0


def command_body(args: argparse.Namespace) -> int:
    version = args.version or read_version()
    launcher_version = args.launcher_version or read_launcher_version()
    body = build_release_body(version, launcher_version, args.changelog)
    args.output.write_text(body, encoding='utf-8')
    print(f'Release body for v{version} (launcher {launcher_version}) written to {args.output}')
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Prepare release notes from CHANGELOG and git history.')
    subparsers = parser.add_subparsers(dest='command', required=True)

    version_parser = subparsers.add_parser('version', help='Print the iaa version from iaa/__meta__.py.')
    version_parser.set_defaults(func=command_version)

    launcher_parser = subparsers.add_parser(
        'launcher-version',
        help='Print the launcher version from bootstrap/LmmPyLauncher/Cargo.toml.',
    )
    launcher_parser.set_defaults(func=command_launcher_version)

    body_parser = subparsers.add_parser('body', help='Generate the release body markdown.')
    body_parser.add_argument('--output', type=Path, required=True, help='Output markdown path.')
    body_parser.add_argument(
        '--version',
        default=None,
        help='Override the iaa version (default: read from iaa/__meta__.py).',
    )
    body_parser.add_argument(
        '--launcher-version',
        default=None,
        help='Override the launcher version (default: read from its Cargo.toml).',
    )
    body_parser.add_argument(
        '--changelog',
        type=Path,
        default=DEFAULT_CHANGELOG,
        help=f'Path to CHANGELOG.md (default: {DEFAULT_CHANGELOG})',
    )
    body_parser.set_defaults(func=command_body)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == '__main__':
    raise SystemExit(main())
