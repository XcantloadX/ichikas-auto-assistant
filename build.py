import hashlib
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from subprocess import CompletedProcess

import click


@click.group()
def cli():
    """A build script for the application."""
    pass


def get_version() -> str:
    """Reads the version from pyproject.toml."""
    content = Path("pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^[\s]*version[\s]*=[\s]*"([^"]+)"', content, re.MULTILINE)
    if not match:
        raise RuntimeError("Version not found in pyproject.toml")
    return match.group(1)


def update_meta(version: str) -> None:
    """Writes the version to iaa/__meta__.py."""
    meta_path = Path("iaa") / "__meta__.py"
    meta_path.write_text(f'__VERSION__ = "{version}"\n', encoding="utf-8")
    click.echo(f"Updated {meta_path} with version {version}")


def run_command(command: list[str], cwd: Path | None = None) -> CompletedProcess:
    """Runs a command and checks for errors."""
    click.echo(f"Running command: {' '.join(command)}")
    result = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
    )
    if result.returncode != 0:
        click.echo(click.style(f"Error running command: {' '.join(command)}", fg="red"))
        click.echo(result.stdout)
        click.echo(result.stderr)
        raise subprocess.CalledProcessError(result.returncode, command)
    return result


def _create_archive(
    source_dir: Path,
    dest_file: Path,
    message: str,
    sevenzip_level: int,
) -> Path:
    """Creates a compressed archive."""
    has_7z = shutil.which("7z")
    dest_path = Path(dest_file)

    if has_7z:
        archive_path = dest_path.with_suffix(".7z")
        cmd = ["7z", "a", "-t7z", f"-mx={sevenzip_level}", str(archive_path), "./*"]
        run_command(cmd, cwd=source_dir)
    else:
        archive_path = Path(
            shutil.make_archive(
                base_name=str(dest_path), format="zip", root_dir=str(source_dir)
            )
        )

    click.echo(f"{message}: {archive_path}")
    return archive_path


def get_file_hash(path: Path) -> str:
    """Computes the SHA256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


@cli.command()
@click.option(
    "--backend",
    type=click.Choice(["pyinstaller", "nuitka"]),
    default="pyinstaller",
    help="The build backend to use.",
)
@click.option(
    "--build-diff",
    is_flag=True,
    help="Build a differential update package.",
)
def build(backend: str, build_diff: bool) -> None:
    """Builds the application."""
    repo_root = Path.cwd()
    build_dir = repo_root / "build"
    dist_dir_base = repo_root / "dist_app"
    exe_name = "iaa.exe"
    icon_path = repo_root / "assets" / "icon_round.ico"

    version = get_version()
    stamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

    update_meta(version)

    version_info = f"v{version}_{stamp}"
    dist_dir = dist_dir_base / version_info

    package_name_base = f"iaa_v{version}_{stamp}"
    package_output_path = dist_dir_base / package_name_base

    click.echo(f"Backend: {backend}")
    click.echo(f"Version: {version}")
    click.echo(f"Timestamp: {stamp}")
    click.echo(f"Dist directory: {dist_dir}")

    if dist_dir.exists():
        click.echo(f"Cleaning up previous dist directory: {dist_dir}")
        shutil.rmtree(dist_dir)

    built_dir = None
    if backend == "pyinstaller":
        click.echo("Building with PyInstaller...")
        app_name = Path(exe_name).stem
        pyinstaller_args = [
            sys.executable,
            "-m",
            "PyInstaller",
            "--onedir",
            # "--windowed",
            f"--icon={icon_path}",
            f"--distpath={build_dir}",
            f"--workpath={build_dir / 'work'}",
            f"--specpath={build_dir / 'spec'}",
            f"--name={app_name}",
            "--hidden-import=rapidocr_onnxruntime",
            "--hidden-import=kotonebot",
            "--hidden-import=kaa",
            "--hidden-import=iaa.res",
            "--hidden-import=iaa.res.sprites",
            "--hidden-import=uiautomator2",
            "--collect-all=rapidocr_onnxruntime",
            "--collect-all=kotonebot",
            "--collect-all=kaa",
            "--collect-all=uiautomator2",
            "--noconfirm",
            "launch_desktop.py",
        ]
        run_command(pyinstaller_args)
        built_dir = build_dir / app_name

    elif backend == "nuitka":
        click.echo("Building with Nuitka...")
        nuitka_args = [
            sys.executable,
            "-m",
            "nuitka",
            "--standalone",
            "--assume-yes-for-downloads",
            "--enable-plugin=tk-inter",
            f"--windows-icon-from-ico={icon_path}",
            f"--output-dir={build_dir}",
            f"--output-filename={exe_name}",
            "--include-package-data=rapidocr_onnxruntime",
            "--include-package-data=kotonebot",
            "--include-package-data=kaa",
            "--include-package-data=uiautomator2",
            "launch_desktop.py",
        ]
        run_command(nuitka_args)
        built_dir = build_dir / "launch_desktop.dist"

    if built_dir is None:
        click.echo(click.style("Build failed: built_dir is None", fg="red"))
        exit(1)

    built_exe_path = built_dir / exe_name
    if not built_exe_path.exists():
        click.echo(
            click.style(
                f"Build failed: executable not found at {built_exe_path}", fg="red"
            )
        )
        exit(1)

    click.echo("Copying files to distribution directory...")
    dist_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(built_dir, dist_dir, dirs_exist_ok=True)

    # Copy assets and resources
    shutil.copytree(repo_root / "assets", dist_dir / "assets", dirs_exist_ok=True)
    res_dest_dir = dist_dir / "assets" / "res_compiled"
    res_dest_dir.mkdir(exist_ok=True)
    shutil.copytree(repo_root / "iaa" / "res", res_dest_dir, dirs_exist_ok=True)

    click.echo("Creating package...")
    _create_archive(dist_dir, package_output_path, message="Packaged", sevenzip_level=2)

    click.echo(
        click.style(
            f"Build completed successfully using {backend} backend!", fg="green"
        )
    )

    if build_diff:
        click.echo("Building diff update package...")
        if not dist_dir_base.exists():
            click.echo(
                click.style(
                    f"BuildDiff: History output directory not found: {dist_dir_base}",
                    fg="yellow",
                )
            )
            return

        candidates = [
            d
            for d in dist_dir_base.iterdir()
            if d.is_dir() and d.resolve() != dist_dir.resolve()
        ]
        if not candidates:
            click.echo(
                click.style(
                    "BuildDiff: No previous version found for comparison.", fg="yellow"
                )
            )
            return

        candidates.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        prev_dir = candidates[0]
        click.echo(f"BuildDiff: Comparing with previous version: {prev_dir}")

        diff_rel_paths = []
        current_files = list(dist_dir.rglob("*"))

        for cf in current_files:
            if cf.is_dir():
                continue
            rel_path = cf.relative_to(dist_dir)
            prev_path = prev_dir / rel_path

            if not prev_path.exists():
                diff_rel_paths.append(rel_path)
            else:
                h1 = get_file_hash(cf)
                h2 = get_file_hash(prev_path)
                if h1 != h2:
                    diff_rel_paths.append(rel_path)

        if not diff_rel_paths:
            click.echo("BuildDiff: No file differences found.")
        else:
            staging_dir = build_dir / f"diff_update_{version_info}"
            if staging_dir.exists():
                shutil.rmtree(staging_dir)

            click.echo(
                f"Found {len(diff_rel_paths)} different files. Staging for diff package..."
            )
            for rel_path in diff_rel_paths:
                src = dist_dir / rel_path
                dst = staging_dir / rel_path
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)

            diff_package_name_base = f"iaa_v{version}_{stamp}_diff_update"
            diff_output_path = dist_dir_base / diff_package_name_base

            click.echo("Creating diff package...")
            _create_archive(
                staging_dir, diff_output_path, message="Diff packaged", sevenzip_level=9
            )


@cli.command()
def clean():
    """Removes build artifacts."""
    repo_root = Path.cwd()
    dist_dir_base = repo_root / "dist_app"
    click.echo("Cleaning up build artifacts...")

    # Directories to remove
    dirs_to_remove = [
        repo_root / "build",
        repo_root / "dist_app",
    ]
    for d in dirs_to_remove:
        if d.exists():
            click.echo(f"Removing directory: {d}")
            shutil.rmtree(d)

    # Files to remove
    files_to_remove = [
        repo_root / "iaa" / "__meta__.py",
    ]
    for f in files_to_remove:
        if f.exists():
            click.echo(f"Removing file: {f}")
            f.unlink()

    # Remove packaged archives
    for p in repo_root.glob("iaa_v*.7z"):
        click.echo(f"Removing archive: {p}")
        p.unlink()
    for p in repo_root.glob("iaa_v*.zip"):
        click.echo(f"Removing archive: {p}")
        p.unlink()
    for p in dist_dir_base.glob("iaa_v*.7z"):
        click.echo(f"Removing archive: {p}")
        p.unlink()
    for p in dist_dir_base.glob("iaa_v*.zip"):
        click.echo(f"Removing archive: {p}")
        p.unlink()

    click.echo(click.style("Cleanup complete!", fg="green"))


if __name__ == "__main__":
    cli()
