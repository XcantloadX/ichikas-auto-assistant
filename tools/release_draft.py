from __future__ import annotations

import argparse
import os
import re
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CHANGELOG = REPO_ROOT / 'doc' / 'CHANGELOG.md'
DEFAULT_DIST_DIR = REPO_ROOT / 'dist_app'


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


def list_tags() -> list[str]:
    output = run_git('tag', '--sort=-v:refname')
    return [line.strip() for line in output.splitlines() if line.strip()]


def get_latest_and_previous_tag() -> tuple[str, str | None]:
    tags = list_tags()
    if not tags:
        raise RuntimeError('No git tags found in repository')
    latest = tags[0]
    previous = tags[1] if len(tags) > 1 else None
    return latest, previous


def extract_version(tag: str) -> str:
    return tag[1:] if tag.startswith('v') else tag


def extract_changelog_section(changelog_path: Path, tag: str) -> str:
    content = changelog_path.read_text(encoding='utf-8')
    pattern = re.compile(
        rf'^##\s+{re.escape(tag)}\s*$\n(?P<body>.*?)(?=^##\s+|\Z)',
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(content)
    if not match:
        raise RuntimeError(f'Unable to find CHANGELOG section for tag {tag} in {changelog_path}')
    return match.group('body').strip()


def format_commit_history(tag: str, previous_tag: str | None) -> str:
    revision_range = f'{previous_tag}..{tag}' if previous_tag else tag
    output = run_git('log', '--format=- %h %s', revision_range)
    history = output.strip()
    if not history:
        raise RuntimeError(f'No commit history found for revision range {revision_range}')
    return history


def build_release_body(tag: str, previous_tag: str | None, changelog_path: Path) -> str:
    changelog = extract_changelog_section(changelog_path, tag)
    history = format_commit_history(tag, previous_tag)
    return '\n\n'.join(
        [
            '## 更新日志',
            changelog,
            '## 完整历史',
            history,
        ]
    )


def append_github_output(path: Path, values: dict[str, str]) -> None:
    with path.open('a', encoding='utf-8', newline='\n') as fh:
        for key, value in values.items():
            fh.write(f'{key}={value}\n')


def command_prepare_body(args: argparse.Namespace) -> int:
    tag, previous_tag = get_latest_and_previous_tag()
    body_output = args.body_output.resolve()
    changelog_path = args.changelog.resolve()
    body = build_release_body(tag=tag, previous_tag=previous_tag, changelog_path=changelog_path)
    body_output.write_text(body + '\n', encoding='utf-8')

    if args.github_output:
        append_github_output(
            args.github_output,
            {
                'tag': tag,
                'previous_tag': previous_tag or '',
                'version': extract_version(tag),
                'body_path': str(body_output),
            },
        )

    print(f'tag={tag}')
    if previous_tag:
        print(f'previous_tag={previous_tag}')
    print(f'version={extract_version(tag)}')
    print(f'body_path={body_output}')
    return 0


def find_release_asset(version: str, dist_dir: Path) -> Path:
    patterns = [f'iaa_v{version}_*.7z', f'iaa_v{version}_*.zip']
    matches: list[Path] = []
    for pattern in patterns:
        matches.extend(path for path in dist_dir.glob(pattern) if path.is_file())

    unique_matches = sorted({path.resolve() for path in matches})
    if not unique_matches:
        raise RuntimeError(f'No release asset found for version {version} under {dist_dir}')
    if len(unique_matches) != 1:
        joined = ', '.join(str(path) for path in unique_matches)
        raise RuntimeError(f'Expected exactly one release asset for version {version}, found: {joined}')
    return unique_matches[0]


def command_find_asset(args: argparse.Namespace) -> int:
    asset = find_release_asset(version=args.version, dist_dir=args.dist_dir.resolve())

    if args.github_output:
        append_github_output(args.github_output, {'asset_path': str(asset)})

    print(asset)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Prepare metadata for GitHub draft releases.')
    subparsers = parser.add_subparsers(dest='command', required=True)

    prepare_body = subparsers.add_parser(
        'prepare-body',
        help='Resolve the latest tag and generate the release body from CHANGELOG and git history.',
    )
    prepare_body.add_argument(
        '--changelog',
        type=Path,
        default=DEFAULT_CHANGELOG,
        help=f'Path to CHANGELOG.md (default: {DEFAULT_CHANGELOG})',
    )
    prepare_body.add_argument(
        '--body-output',
        type=Path,
        required=True,
        help='Output path for the generated release markdown.',
    )
    prepare_body.add_argument(
        '--github-output',
        type=Path,
        default=Path(os.environ['GITHUB_OUTPUT']) if os.environ.get('GITHUB_OUTPUT') else None,
        help='Optional path to append GitHub Actions outputs.',
    )
    prepare_body.set_defaults(func=command_prepare_body)

    find_asset = subparsers.add_parser(
        'find-asset',
        help='Find the unique build artifact for a version in dist_app.',
    )
    find_asset.add_argument('--version', required=True, help='Version without the leading v prefix.')
    find_asset.add_argument(
        '--dist-dir',
        type=Path,
        default=DEFAULT_DIST_DIR,
        help=f'Path to the build output directory (default: {DEFAULT_DIST_DIR})',
    )
    find_asset.add_argument(
        '--github-output',
        type=Path,
        default=Path(os.environ['GITHUB_OUTPUT']) if os.environ.get('GITHUB_OUTPUT') else None,
        help='Optional path to append GitHub Actions outputs.',
    )
    find_asset.set_defaults(func=command_find_asset)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == '__main__':
    raise SystemExit(main())
