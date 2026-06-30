import re
import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


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
        detail = (result.stderr or '').strip() or (result.stdout or '').strip() or 'command failed'
        raise RuntimeError(f'Command failed ({result.returncode}): {" ".join(command)}\n{detail}')
    return result


def run_git(*args: str, cwd: Path | None = None) -> str:
    return run_command(['git', *args], cwd=cwd).stdout.strip()


def require_tool(name: str) -> None:
    if not shutil.which(name):
        raise RuntimeError(f'Required tool not found in PATH: {name}')


def list_tags() -> list[str]:
    output = run_git('tag', '--sort=-v:refname')
    return [line.strip() for line in output.splitlines() if line.strip()]


def extract_version(tag: str) -> str:
    return tag[1:] if tag.startswith('v') else tag


def read_pyproject_field(field: str) -> str:
    content = (REPO_ROOT / 'pyproject.toml').read_text(encoding='utf-8')
    match = re.search(rf'^\s*{re.escape(field)}\s*=\s*"([^"]+)"', content, re.MULTILINE)
    if not match:
        raise RuntimeError(f'Field "{field}" not found in pyproject.toml')
    return match.group(1)
