# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

ROOT = Path.cwd()
ICON = ROOT / 'assets' / 'icon_round.ico'


def collect_package_assets():
    datas = []
    binaries = []
    hiddenimports = ['rapidocr_onnxruntime', 'kotonebot', 'kaa', 'iaa.res', 'uiautomator2', 'av']
    for package in ('rapidocr_onnxruntime', 'kotonebot', 'kaa', 'uiautomator2', 'av'):
        pkg_datas, pkg_binaries, pkg_hiddenimports = collect_all(package)
        datas += pkg_datas
        binaries += pkg_binaries
        hiddenimports += pkg_hiddenimports
    datas.append((str(ROOT / 'assets' / 'scrcpy.jar'), 'assets'))
    return datas, binaries, hiddenimports


desktop_datas, desktop_binaries, desktop_hiddenimports = collect_package_assets()
desktop_analysis = Analysis(
    [str(ROOT / 'launch_desktop.py')],
    pathex=[str(ROOT)],
    binaries=desktop_binaries,
    datas=desktop_datas,
    hiddenimports=desktop_hiddenimports,
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
    name='iaa',
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
    icon=[str(ICON)],
)


cli_datas, cli_binaries, cli_hiddenimports = collect_package_assets()
cli_analysis = Analysis(
    [str(ROOT / 'launch_cli.py')],
    pathex=[str(ROOT)],
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
    name='iaa-cli',
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
    icon=[str(ICON)],
)


coll = COLLECT(
    desktop_exe,
    desktop_analysis.binaries,
    desktop_analysis.datas,
    cli_exe,
    cli_analysis.binaries,
    cli_analysis.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='iaa',
)
