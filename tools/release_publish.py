from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


REPO_ROOT = Path(__file__).resolve().parent.parent
CHANGELOG_PATH = REPO_ROOT / 'doc' / 'CHANGELOG.md'
DIST_DIR = REPO_ROOT / 'dist_app'


class ReleaseError(RuntimeError):
    pass


@dataclass
class ReleaseContext:
    repo_slug: str
    tag: str
    previous_tag: str | None
    version: str
    release_body: str
    release_body_path: Path


def run_command(
    command: list[str],
    *,
    cwd: Path | None = None,
    check: bool = True,
    capture_output: bool = True,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=cwd or REPO_ROOT,
        text=True,
        encoding='utf-8',
        errors='replace',
        capture_output=capture_output,
        check=False,
    )
    if check and result.returncode != 0:
        stderr = (result.stderr or '').strip()
        stdout = (result.stdout or '').strip()
        detail = stderr or stdout or 'command failed'
        raise ReleaseError(f'Command failed ({result.returncode}): {" ".join(command)}\n{detail}')
    return result


def run_git(*args: str, cwd: Path | None = None) -> str:
    return run_command(['git', *args], cwd=cwd).stdout.strip()


def require_tool(name: str) -> None:
    if shutil.which(name):
        return
    raise ReleaseError(f'Required tool not found in PATH: {name}')

def list_tags() -> list[str]:
    output = run_git('tag', '--sort=-v:refname')
    return [line.strip() for line in output.splitlines() if line.strip()]


def resolve_tag_and_previous(tag_override: str | None, previous_override: str | None) -> tuple[str, str | None]:
    tags = list_tags()
    if not tags:
        raise ReleaseError('No git tags found in repository.')

    if tag_override:
        if tag_override not in tags:
            raise ReleaseError(f'Tag not found: {tag_override}')
        tag = tag_override
    else:
        tag = tags[0]

    if previous_override:
        if previous_override not in tags:
            raise ReleaseError(f'Previous tag not found: {previous_override}')
        return tag, previous_override

    index = tags.index(tag)
    previous = tags[index + 1] if index + 1 < len(tags) else None
    return tag, previous


def extract_version(tag: str) -> str:
    return tag[1:] if tag.startswith('v') else tag


def extract_changelog_section(tag: str) -> str:
    content = CHANGELOG_PATH.read_text(encoding='utf-8')
    pattern = re.compile(
        rf'^##\s+{re.escape(tag)}\s*$\n(?P<body>.*?)(?=^##\s+|\Z)',
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(content)
    if not match:
        raise ReleaseError(f'Unable to find CHANGELOG section for {tag} in {CHANGELOG_PATH}')
    return match.group('body').strip()


def format_commit_history(tag: str, previous_tag: str | None) -> str:
    revision_range = f'{previous_tag}..{tag}' if previous_tag else tag
    history = run_git('log', '--format=- %h %s', revision_range)
    if not history:
        raise ReleaseError(f'No commit history found for revision range {revision_range}')
    return history


def build_release_body(tag: str, previous_tag: str | None) -> str:
    return '\n\n'.join(
        [
            '## 更新日志',
            extract_changelog_section(tag),
            '## 完整历史',
            format_commit_history(tag, previous_tag),
        ]
    )


def parse_repo_slug(remote_url: str) -> str:
    ssh_match = re.match(r'git@github\.com:(?P<slug>[^/]+/[^/]+?)(?:\.git)?$', remote_url)
    if ssh_match:
        return ssh_match.group('slug')

    parsed = urlparse(remote_url)
    if parsed.netloc.lower() != 'github.com':
        raise ReleaseError(f'origin remote is not a GitHub repository: {remote_url}')

    path = parsed.path.lstrip('/').removesuffix('.git')
    if path.count('/') != 1:
        raise ReleaseError(f'Unable to parse GitHub repository slug from origin remote: {remote_url}')
    return path


def detect_repo_slug(repo_override: str | None) -> str:
    if repo_override:
        return repo_override
    remote_url = run_git('remote', 'get-url', 'origin')
    return parse_repo_slug(remote_url)


def ensure_gh_authenticated() -> None:
    require_tool('gh')
    status = run_command(['gh', 'auth', 'status'], check=False)
    if status.returncode != 0:
        detail = status.stderr.strip() or status.stdout.strip() or 'gh auth status failed'
        raise ReleaseError(f'GitHub CLI is not authenticated.\n{detail}')


def check_release_absent(repo_slug: str, tag: str, skip_check: bool) -> None:
    if skip_check:
        return
    result = run_command(['gh', 'release', 'view', tag, '--repo', repo_slug], check=False)
    if result.returncode == 0:
        raise ReleaseError(f'Release already exists for tag {tag} in {repo_slug}.')
    if result.returncode != 1:
        detail = result.stderr.strip() or result.stdout.strip() or 'gh release view failed'
        raise ReleaseError(f'Failed to query release state for {tag}.\n{detail}')


def build_locally() -> None:
    run_command(['uv', 'run', '--group', 'dev', 'python', 'build.py', 'build'], capture_output=False)


def find_release_asset(version: str, dist_dir: Path) -> Path:
    patterns = [f'iaa_v{version}_*.7z', f'iaa_v{version}_*.zip']
    matches: list[Path] = []
    for pattern in patterns:
        matches.extend(path.resolve() for path in dist_dir.glob(pattern) if path.is_file())
    unique_matches = sorted(set(matches))
    if not unique_matches:
        raise ReleaseError(f'No release asset found for version {version} under {dist_dir}')
    if len(unique_matches) != 1:
        joined = '\n'.join(str(path) for path in unique_matches)
        raise ReleaseError(f'Expected exactly one release asset for version {version}, found:\n{joined}')
    return unique_matches[0]


def create_release(repo_slug: str, tag: str, asset_path: Path, body_path: Path) -> None:
    run_command(
        [
            'gh',
            'release',
            'create',
            tag,
            str(asset_path),
            '--repo',
            repo_slug,
            '--draft',
            '--title',
            tag,
            '--notes-file',
            str(body_path),
        ],
        capture_output=False,
    )


def write_release_body(path: Path, body: str) -> Path:
    resolved = path.resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(body + '\n', encoding='utf-8')
    return resolved


def default_body_output_path() -> Path:
    return Path(tempfile.gettempdir()) / f'iaa-release-body-{uuid.uuid4().hex}.md'


def build_release_context(args: argparse.Namespace) -> ReleaseContext:
    repo_slug = detect_repo_slug(args.repo)
    tag, previous_tag = resolve_tag_and_previous(args.tag, args.previous_tag)
    version = extract_version(tag)
    body_path = args.body_output if args.body_output else default_body_output_path()
    release_body = build_release_body(tag, previous_tag)
    return ReleaseContext(
        repo_slug=repo_slug,
        tag=tag,
        previous_tag=previous_tag,
        version=version,
        release_body=release_body,
        release_body_path=write_release_body(body_path, release_body),
    )


def print_dry_run_summary(context: ReleaseContext, asset_hint: str) -> None:
    print(f'repository: {context.repo_slug}')
    print(f'tag: {context.tag}')
    print(f'previous_tag: {context.previous_tag or "<none>"}')
    print(f'version: {context.version}')
    print(f'body_file: {context.release_body_path}')
    print(f'asset: {asset_hint}')
    print('\nRelease body preview:\n')
    print(context.release_body)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Build and publish a local GitHub draft release.')
    parser.add_argument('--repo', help='GitHub repository in owner/name form. Defaults to origin remote.')
    parser.add_argument('--tag', help='Release tag to publish. Defaults to the latest git tag.')
    parser.add_argument('--previous-tag', help='Previous tag used for commit history.')
    parser.add_argument('--body-output', type=Path, help='Write the generated release notes to this path.')
    parser.add_argument('--dry-run', action='store_true', help='Generate metadata and validate prerequisites without publishing.')
    parser.add_argument(
        '--skip-release-check',
        action='store_true',
        help='Skip gh release existence checks. Useful for offline metadata validation.',
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    require_tool('git')
    require_tool('uv')
    try:
        context = build_release_context(args)

        if not args.skip_release_check:
            ensure_gh_authenticated()
        check_release_absent(context.repo_slug, context.tag, args.skip_release_check)

        if args.dry_run:
            asset_hint = str(DIST_DIR / f'iaa_v{context.version}_*.7z|zip')
            print_dry_run_summary(context, asset_hint)
            return 0

        build_locally()
        asset_path = find_release_asset(context.version, DIST_DIR)
        create_release(context.repo_slug, context.tag, asset_path, context.release_body_path)
        print(f'Created draft release {context.tag} with asset {asset_path}')
        return 0
    except ReleaseError as exc:
        print(f'Error: {exc}')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
