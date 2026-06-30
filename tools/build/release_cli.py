"""发布流程 CLI，供项目层 release.py 调用。"""

import os
import tempfile
import uuid
from pathlib import Path

import click

from ._utils import extract_version, list_tags, require_tool
from .release import (
    ReleaseConfig,
    build_release_body,
    check_release_absent,
    create_github_release,
    detect_repo_slug,
    ensure_gh_authenticated,
    find_release_asset,
    append_github_output,
)


def _resolve_tags(
    tag_override: str | None,
    previous_override: str | None,
) -> tuple[str, str | None]:
    tags = list_tags()
    if not tags:
        raise RuntimeError('仓库中找不到任何 git tag。')
    tag = tag_override or tags[0]
    if tag not in tags:
        raise RuntimeError(f'找不到 tag：{tag}')
    if previous_override:
        if previous_override not in tags:
            raise RuntimeError(f'找不到 previous tag：{previous_override}')
        return tag, previous_override
    index = tags.index(tag)
    return tag, (tags[index + 1] if index + 1 < len(tags) else None)


def _github_output_default() -> Path | None:
    raw = os.environ.get('GITHUB_OUTPUT')
    return Path(raw) if raw else None


def make_cli(config: ReleaseConfig) -> click.Group:
    """返回绑定了 ReleaseConfig 的 release CLI 命令组。"""

    @click.group()
    def cli():
        """发布流程工具。"""

    # ── CI 命令 ──────────────────────────────────────────────────────────

    @cli.command('prepare-body')
    @click.option('--body-output', type=Path, required=True, help='发布说明输出路径。')
    @click.option('--tag', default=None, help='发布 tag，默认使用最新 tag。')
    @click.option('--previous-tag', default=None, help='用于生成提交历史的上一个 tag。')
    @click.option(
        '--github-output',
        type=Path,
        default=_github_output_default(),
        help='GITHUB_OUTPUT 文件路径，用于向后续 step 传递变量。',
    )
    def prepare_body(
        body_output: Path,
        tag: str | None,
        previous_tag: str | None,
        github_output: Path | None,
    ) -> None:
        """生成发布说明文本，输出 tag/version/body_path 到 GITHUB_OUTPUT。（供 CI 使用）"""
        resolved_tag, resolved_prev = _resolve_tags(tag, previous_tag)
        body = build_release_body(config, resolved_tag, resolved_prev)
        body_output = body_output.resolve()
        body_output.write_text(body + '\n', encoding='utf-8')

        if github_output:
            append_github_output(github_output, {
                'tag': resolved_tag,
                'previous_tag': resolved_prev or '',
                'version': extract_version(resolved_tag),
                'body_path': str(body_output),
            })

        click.echo(f'tag={resolved_tag}')
        if resolved_prev:
            click.echo(f'previous_tag={resolved_prev}')
        click.echo(f'version={extract_version(resolved_tag)}')
        click.echo(f'body_path={body_output}')

    @cli.command('find-asset')
    @click.option('--version', required=True, help='不含前缀 v 的版本号。')
    @click.option(
        '--github-output',
        type=Path,
        default=_github_output_default(),
        help='GITHUB_OUTPUT 文件路径。',
    )
    def find_asset(version: str, github_output: Path | None) -> None:
        """在 dist_dir 中定位发布产物，输出路径到 GITHUB_OUTPUT。（供 CI 使用）"""
        asset = find_release_asset(config, version)
        if github_output:
            append_github_output(github_output, {'asset_path': str(asset)})
        click.echo(asset)

    # ── 本地命令 ─────────────────────────────────────────────────────────

    @cli.command('create')
    @click.option('--repo', default=None, help='GitHub 仓库（owner/name），默认从 origin 解析。')
    @click.option('--tag', default=None, help='发布 tag，默认使用最新 tag。')
    @click.option('--previous-tag', default=None)
    @click.option('--body-output', type=Path, default=None, help='发布说明输出路径（可选）。')
    @click.option('--dry-run', is_flag=True, help='仅生成元数据，不实际发布。')
    @click.option('--skip-release-check', is_flag=True, help='跳过 release 是否已存在的检查。')
    def create(
        repo: str | None,
        tag: str | None,
        previous_tag: str | None,
        body_output: Path | None,
        dry_run: bool,
        skip_release_check: bool,
    ) -> None:
        """查找构建产物并创建 GitHub draft release。（本地使用）"""
        require_tool('git')
        require_tool('gh')

        resolved_tag, resolved_prev = _resolve_tags(tag, previous_tag)
        version = extract_version(resolved_tag)
        repo_slug = detect_repo_slug(repo)
        body = build_release_body(config, resolved_tag, resolved_prev)

        body_path = body_output or Path(tempfile.gettempdir()) / f'release-body-{uuid.uuid4().hex}.md'
        body_path = body_path.resolve()
        body_path.parent.mkdir(parents=True, exist_ok=True)
        body_path.write_text(body + '\n', encoding='utf-8')

        if not skip_release_check:
            ensure_gh_authenticated()
        check_release_absent(repo_slug, resolved_tag, skip=skip_release_check)

        if dry_run:
            click.echo(f'repository:   {repo_slug}')
            click.echo(f'tag:          {resolved_tag}')
            click.echo(f'previous_tag: {resolved_prev or "<none>"}')
            click.echo(f'version:      {version}')
            click.echo(f'body_file:    {body_path}')
            click.echo(f'asset:        {config.dist_dir / f"{config.name}_v{version}_*.7z|zip"}')
            click.echo('\n发布说明预览：\n')
            click.echo(body)
            return

        asset_path = find_release_asset(config, version)
        create_github_release(repo_slug, resolved_tag, asset_path, body_path)
        click.echo(click.style(f'已创建 draft release {resolved_tag}，产物：{asset_path}', fg='green'))

    return cli


def main(config: ReleaseConfig) -> None:
    """注册命令并启动 CLI。"""
    make_cli(config)()
