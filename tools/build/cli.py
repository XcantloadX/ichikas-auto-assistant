import shutil
from datetime import datetime
from pathlib import Path

import click

from .archive import create_archive
from .bundle import BuildConfig, build_app


def _update_meta(name: str, version: str) -> None:
    meta_path = Path(name) / '__meta__.py'
    meta_path.write_text(f'__VERSION__ = "{version}"\n', encoding='utf-8')
    click.echo(f'Updated {meta_path} with version {version}')


@click.group()
def cli():
    """Build and package the application."""


def make_build_command(config: BuildConfig) -> click.Command:
    """Return a pre-configured build command bound to the given BuildConfig."""

    @cli.command()
    def build() -> None:
        """Build and package the application."""
        version = config.version
        stamp = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        dist_dir_base = Path.cwd() / 'dist_app'
        dist_dir = dist_dir_base / f'v{version}_{stamp}'
        package_output_path = dist_dir_base / f'{config.name}_v{version}_{stamp}'

        click.echo(f'Version: {version}')
        click.echo(f'Timestamp: {stamp}')

        _update_meta(config.name, version)

        try:
            bundle_dir = build_app(config)
        except Exception as exc:
            click.echo(click.style(f'Build failed: {exc}', fg='red'))
            raise SystemExit(1) from exc

        click.echo('Copying to distribution directory...')
        dist_dir.mkdir(parents=True, exist_ok=True)
        shutil.copytree(bundle_dir, dist_dir, dirs_exist_ok=True)

        click.echo('Creating package...')
        archive_path = create_archive(dist_dir, package_output_path, sevenzip_level=2)
        click.echo(f'Packaged: {archive_path}')
        click.echo(click.style('Build completed!', fg='green'))

    return build


def make_clean_command(config: BuildConfig) -> click.Command:
    """Return a pre-configured clean command bound to the given BuildConfig."""

    @cli.command()
    def clean() -> None:
        """Remove build artifacts."""
        repo_root = Path.cwd()
        click.echo('Cleaning up build artifacts...')

        for d in [
            repo_root / 'build' / config.name,
            repo_root / 'build' / 'work',
            repo_root / 'dist_app',
        ]:
            if d.exists():
                click.echo(f'Removing: {d}')
                shutil.rmtree(d)

        meta = repo_root / config.name / '__meta__.py'
        if meta.exists():
            click.echo(f'Removing: {meta}')
            meta.unlink()

        for pattern in (f'{config.name}_v*.7z', f'{config.name}_v*.zip'):
            for p in repo_root.glob(pattern):
                click.echo(f'Removing: {p}')
                p.unlink()

        click.echo(click.style('Cleanup complete!', fg='green'))

    return clean


def main(config: BuildConfig) -> None:
    """Entry point: register commands for config and invoke the CLI."""
    make_build_command(config)
    make_clean_command(config)
    cli()
