import shutil
import subprocess
from pathlib import Path


def create_archive(source_dir: Path, dest_file: Path, sevenzip_level: int = 2) -> Path:
    """Compress source_dir into a 7z or zip archive. Returns the created archive path."""
    dest_path = Path(dest_file)

    if shutil.which('7z'):
        archive_path = dest_path.with_suffix('.7z')
        subprocess.run(
            ['7z', 'a', '-t7z', f'-mx={sevenzip_level}', str(archive_path), './*'],
            cwd=source_dir,
            check=True,
        )
    else:
        archive_path = Path(
            shutil.make_archive(base_name=str(dest_path), format='zip', root_dir=str(source_dir))
        )

    return archive_path
