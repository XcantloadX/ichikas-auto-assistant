import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from ._utils import read_pyproject_field
from .prune_qt import prune_dist_directory


def _default_version() -> str:
    return read_pyproject_field('version')


@dataclass
class BuildConfig:
    """PyInstaller 打包配置。"""

    name: str
    """应用名称，用于 exe 名称、bundle 目录名和产物归档前缀。"""

    version: str = field(default_factory=_default_version)
    """版本号，默认从 pyproject.toml 的 version 字段读取。"""

    icon: str = 'assets/ichika.ico'
    """图标路径，相对于项目根目录。"""

    desktop_entry: str = 'launch_desktop.py'
    """桌面 GUI 可执行文件的入口脚本。"""

    cli_entry: str | None = 'launch_cli.py'
    """CLI 可执行文件的入口脚本。设为 None 则不构建 CLI exe。"""

    collect_packages: list[str] = field(default_factory=list)
    """项目特有的、需要 collect_all() 的包名列表。
    框架核心依赖（kotonebot、PySide6、uiautomator2、av、rapidocr_onnxruntime）已内置，无需重复声明。"""

    extra_datas: list[tuple[str, str]] = field(default_factory=list)
    """额外嵌入 PyInstaller bundle（_internal/）的 (源路径, 目标路径) 列表，路径相对于项目根目录。
    适用于需要通过 sys._MEIPASS 访问的运行时资源。"""

    extra_hidden_imports: list[str] = field(default_factory=list)
    """collect_packages 收集之外的额外隐式导入。"""

    qml_dirs: list[tuple[str, str]] | None = None
    """需要嵌入的 QML 目录列表，(源路径, 目标路径) 均相对于项目根目录。
    为 None 时自动从框架标准布局推导：
      {name}/application/qt/qml
      {name}/application/framework/dsl/qml
    可在此处通过赋值覆盖。"""

    runtime_copy: list[tuple[str, str]] = field(default_factory=list)
    """PyInstaller 完成后的文件复制操作列表，(源路径, bundle 内目标路径) 均相对于项目根目录。
    支持文件和目录（目录使用 dirs_exist_ok 合并）。
    可在此处追加项目特有的运行时资源复制。"""


def _resolve_qml_dirs(config: BuildConfig, root: Path) -> list[tuple[str, str]]:
    if config.qml_dirs is not None:
        return config.qml_dirs
    candidates = [
        (f'{config.name}/application/qt/qml', f'{config.name}/application/qt/qml'),
        (f'{config.name}/application/framework/dsl/qml', f'{config.name}/application/framework/dsl/qml'),
    ]
    return [(s, d) for s, d in candidates if (root / s).is_dir()]


# kotonebot 框架的核心依赖，所有下游项目均需 collect_all()。
# 可在 BuildConfig.collect_packages 追加项目特有的包。
_FRAMEWORK_COLLECT_PACKAGES = ['kotonebot', 'PySide6', 'uiautomator2', 'av', 'rapidocr_onnxruntime']


def collect_packages_for_spec(
    config: BuildConfig, root: Path
) -> tuple[list, list, list]:
    """为 BuildConfig 收集 PyInstaller 所需的 datas、binaries、hiddenimports。"""
    from PyInstaller.utils.hooks import collect_all

    qml_dirs = _resolve_qml_dirs(config, root)
    datas = [(str(root / s), d) for s, d in config.extra_datas]
    datas += [(str(root / s), d) for s, d in qml_dirs]
    binaries: list = []

    all_collect = _FRAMEWORK_COLLECT_PACKAGES + list(config.collect_packages)
    hiddenimports: list = all_collect + list(config.extra_hidden_imports)

    for pkg in all_collect:
        pkg_d, pkg_b, pkg_h = collect_all(pkg)
        datas += pkg_d
        binaries += pkg_b
        hiddenimports += pkg_h

    return datas, binaries, hiddenimports


def apply_spec(config: BuildConfig) -> None:
    """在 .spec 文件中调用，根据 BuildConfig 构建 PyInstaller 的 Analysis/EXE/COLLECT 对象。

    Analysis、PYZ、EXE、COLLECT 直接从 PyInstaller 导入，无需依赖 spec 执行环境注入的全局变量。
    """
    from PyInstaller.building.build_main import Analysis, COLLECT, EXE, PYZ

    root = Path.cwd()
    icon = [str(root / config.icon)]

    datas, binaries, hiddenimports = collect_packages_for_spec(config, root)

    desktop_analysis = Analysis(
        [str(root / config.desktop_entry)],
        pathex=[str(root)],
        binaries=binaries,
        datas=datas,
        hiddenimports=hiddenimports,
        hookspath=[],
        hooksconfig={},
        runtime_hooks=[],
        excludes=[],
        noarchive=False,
        optimize=0,
    )
    desktop_pyz = PYZ(desktop_analysis.pure)
    desktop_exe = EXE(
        desktop_pyz,
        desktop_analysis.scripts,
        desktop_analysis.dependencies,
        [],
        exclude_binaries=True,
        name=config.name,
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=True,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=icon,
    )

    collect_args = [desktop_exe, desktop_analysis.binaries, desktop_analysis.datas]

    if config.cli_entry:
        cli_datas, cli_binaries, cli_hiddenimports = collect_packages_for_spec(config, root)
        cli_analysis = Analysis(
            [str(root / config.cli_entry)],
            pathex=[str(root)],
            binaries=cli_binaries,
            datas=cli_datas,
            hiddenimports=cli_hiddenimports,
            hookspath=[],
            hooksconfig={},
            runtime_hooks=[],
            excludes=[],
            noarchive=False,
            optimize=0,
        )
        cli_pyz = PYZ(cli_analysis.pure)
        cli_exe = EXE(
            cli_pyz,
            cli_analysis.scripts,
            cli_analysis.dependencies,
            [],
            exclude_binaries=True,
            name=f'{config.name}-cli',
            debug=False,
            bootloader_ignore_signals=False,
            strip=False,
            upx=True,
            console=True,
            disable_windowed_traceback=False,
            argv_emulation=False,
            target_arch=None,
            codesign_identity=None,
            entitlements_file=None,
            icon=icon,
        )
        collect_args += [cli_exe, cli_analysis.binaries, cli_analysis.datas]

    COLLECT(
        *collect_args,
        strip=False,
        upx=True,
        upx_exclude=[],
        name=config.name,
    )


def _expected_executables(config: BuildConfig) -> list[str]:
    suffix = '.exe' if sys.platform == 'win32' else ''
    exes = [f'{config.name}{suffix}']
    if config.cli_entry:
        exes.append(f'{config.name}-cli{suffix}')
    return exes


def _apply_runtime_copy(config: BuildConfig, root: Path, bundle_dir: Path) -> None:
    for src_rel, dst_rel in config.runtime_copy:
        src = root / src_rel
        dst = bundle_dir / dst_rel
        if src.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
            shutil.copytree(src, dst, dirs_exist_ok=True)
        elif src.is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)


_SPEC_TEMPLATE = """\
from build import CONFIG
from tools.build.bundle import apply_spec
apply_spec(CONFIG)
"""


def build_app(config: BuildConfig) -> Path:
    """执行 PyInstaller 打包，完成后进行运行时资源复制和 Qt 裁剪。

    返回构建完成的 bundle 目录路径（可直接归档或检查）。
    """
    root = Path.cwd()
    build_root = root / 'build'

    spec_file = build_root / f'{config.name}.spec'
    spec_file.parent.mkdir(parents=True, exist_ok=True)
    spec_file.write_text(_SPEC_TEMPLATE, encoding='utf-8')

    subprocess.run(
        [
            sys.executable, '-m', 'PyInstaller',
            '--clean', '--noconfirm',
            f'--distpath={build_root}',
            f'--workpath={build_root / "work"}',
            str(spec_file),
        ],
        check=True,
    )

    bundle_dir = build_root / config.name
    for exe_name in _expected_executables(config):
        if not (bundle_dir / exe_name).exists():
            raise RuntimeError(f'构建失败：找不到预期的可执行文件 {bundle_dir / exe_name}')

    if config.runtime_copy:
        _apply_runtime_copy(config, root, bundle_dir)

    removed = prune_dist_directory(bundle_dir)
    if removed:
        print(f'Qt 裁剪完成：节省 {removed / 1024 / 1024:.1f} MB')

    return bundle_dir
