# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

ROOT = Path.cwd()
ICON = ROOT / 'assets' / 'icon_round.ico'

# Keep QtQuick/Controls runtime for current desktop UI and drop heavy optional stacks.
PYSIDE6_PATH_EXCLUDE_KEYWORDS = (
    '/translations/',
    '/resources/qtwebengine',
    '/resources/icudtl.dat',
    '/resources/v8_context_snapshot',
    '/include/',
    '/typesystems/',
    '/doc/',
    '/scripts/',
    '/support/',
    '/qml/qtwebengine/',
    '/qml/qt3d/',
    '/qml/qtquick3d/',
    '/qml/qtcharts/',
    '/qml/qtdatavisualization/',
    '/qml/qtgraphs/',
    '/qml/qtmultimedia/',
    '/plugins/multimedia/',
)

PYSIDE6_FILE_EXCLUDE_KEYWORDS = (
    'qt6webengine',
    'qtwebengine',
    'qt6webchannel',
    'qtwebchannel',
    'qt6multimedia',
    'qtmultimedia',
    'avcodec-',
    'avformat-',
    'avutil-',
    'swscale-',
    'swresample-',
    'qt63d',
    'qt6quick3d',
    'qtquick3d',
    'qt6charts',
    'qtcharts',
    'qt6datavisualization',
    'qtdatavisualization',
    'qt6graphs',
    'qtgraphs',
)

PYSIDE6_TOOL_EXE_NAMES = {
    'assistant.exe',
    'designer.exe',
    'linguist.exe',
    'lupdate.exe',
    'lrelease.exe',
    'uic.exe',
    'qmlformat.exe',
    'qmlimportscanner.exe',
    'qmllint.exe',
    'qmltyperegistrar.exe',
    'qmlcachegen.exe',
    'qsb.exe',
    'svgtoqml.exe',
    'balsam.exe',
    'balsamui.exe',
    'qmlls.exe',
}

PYSIDE6_HIDDENIMPORT_EXCLUDE_KEYWORDS = (
    'pyside6.qtwebengine',
    'pyside6.qtwebchannel',
    'pyside6.qtmultimedia',
    'pyside6.qt3d',
    'pyside6.qtquick3d',
    'pyside6.qtcharts',
    'pyside6.qtdatavisualization',
    'pyside6.qtgraphs',
)


def _should_exclude_pyside6_file(src_path: str) -> bool:
    normalized = src_path.replace('\\', '/').lower()
    file_name = Path(src_path).name.lower()
    if file_name.endswith('.pyi') or file_name.endswith('.lib'):
        return True
    if file_name in PYSIDE6_TOOL_EXE_NAMES:
        return True
    if any(token in normalized for token in PYSIDE6_PATH_EXCLUDE_KEYWORDS):
        return True
    if any(token in file_name for token in PYSIDE6_FILE_EXCLUDE_KEYWORDS):
        return True
    return False


def _filter_pyside6_assets(datas, binaries, hiddenimports):
    datas = [item for item in datas if not _should_exclude_pyside6_file(item[0])]
    binaries = [item for item in binaries if not _should_exclude_pyside6_file(item[0])]
    hiddenimports = [
        mod
        for mod in hiddenimports
        if not any(token in mod.lower() for token in PYSIDE6_HIDDENIMPORT_EXCLUDE_KEYWORDS)
    ]
    return datas, binaries, hiddenimports


def collect_package_assets():
    datas = []
    binaries = []
    hiddenimports = ['rapidocr_onnxruntime', 'kotonebot', 'kaa', 'iaa.res', 'uiautomator2', 'av', 'PySide6']
    for package in ('rapidocr_onnxruntime', 'kotonebot', 'kaa', 'uiautomator2', 'av', 'PySide6'):
        pkg_datas, pkg_binaries, pkg_hiddenimports = collect_all(package)
        if package == 'PySide6':
            pkg_datas, pkg_binaries, pkg_hiddenimports = _filter_pyside6_assets(
                pkg_datas,
                pkg_binaries,
                pkg_hiddenimports,
            )
        datas += pkg_datas
        binaries += pkg_binaries
        hiddenimports += pkg_hiddenimports
    datas.append((str(ROOT / 'assets' / 'scrcpy.jar'), 'assets'))
    datas.append((str(ROOT / 'iaa' / 'application' / 'qt' / 'qml'), 'iaa/application/qt/qml'))
    datas.append((str(ROOT / 'iaa' / 'application' / 'framework' / 'dsl' / 'qml'), 'iaa/application/framework/dsl/qml'))
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
