"""
PySide6/Qt pruning for PyInstaller builds.

Keep-list strategy: only modules the app actually needs are preserved.
The app uses QtQuick/QML desktop UI with no WebEngine, 3D, multimedia, etc.

Standalone usage:
    python -m tools.build.prune_qt <dist-directory>
"""

import re
import shutil
from pathlib import Path

# .pyd modules to KEEP (base name without .pyd)
PYSIDE6_KEEP_MODULES = {
    'QtCore',
    'QtGui',
    'QtWidgets',
    'QtQml',
    'QtQuick',
    # QuickControls2 — core + impl + all built-in styles
    'QtQuickControls2',
    'QtQuickControls2Impl',
    'QtQuickControls2Basic',
    'QtQuickControls2BasicStyleImpl',
    'QtQuickControls2Fusion',
    'QtQuickControls2FusionStyleImpl',
    'QtQuickControls2Imagine',
    'QtQuickControls2ImagineStyleImpl',
    'QtQuickControls2Material',
    'QtQuickControls2MaterialStyleImpl',
    'QtQuickControls2Universal',
    'QtQuickControls2UniversalStyleImpl',
    'QtQuickControls2FluentWinUI3StyleImpl',
    'QtQuickControls2WindowsStyleImpl',
    'QtQuickTemplates2',
    # QML engine transitive dependencies
    'QtQmlMeta',
    'QtQmlModels',
    'QtQmlWorkerScript',
    'QtNetwork',
    'QtOpenGL',
    # QML plugin modules
    'QtQuickDialogs2',
    'QtQuickDialogs2QuickImpl',
    'QtQuickDialogs2Utils',
    'QtQuickEffects',
    'QtQuickLayouts',
    'QtQuickShapes',
    'QtQmlLocalStorage',
    'QtSql',
    # Assets
    'QtSvg',
}

_KEEP_QML_DIRS = {'QtQml', 'QtQuick'}

_KEEP_PLUGIN_DIRS = {
    'generic',
    'iconengines',
    'imageformats',
    'platforminputcontexts',
    'platforms',
    'renderers',
    'styles',
    'tls',
}

TOOL_EXE_NAMES = {
    'assistant.exe', 'designer.exe', 'linguist.exe', 'lupdate.exe',
    'lrelease.exe', 'uic.exe', 'qmlformat.exe', 'qmlimportscanner.exe',
    'qmllint.exe', 'qmltyperegistrar.exe', 'qmlcachegen.exe', 'qsb.exe',
    'svgtoqml.exe', 'balsam.exe', 'balsamui.exe', 'qmlls.exe',
}


def _remove(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file() or path.is_symlink():
        size = path.stat().st_size
        path.unlink()
        return size
    size = sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
    shutil.rmtree(path)
    return size


def _parse_qt_module_from_dll(dll_name: str) -> str | None:
    m = re.search(r'^Qt6(.+)\.dll$', dll_name)
    return 'Qt' + m.group(1) if m else None


def _parse_qt_module_from_pyd(pyd_name: str) -> str | None:
    m = re.search(r'^(Qt.+)\.pyd$', pyd_name)
    return m.group(1) if m else None


def prune_pyside6_dir(pyside6_dir: Path) -> int:
    """Remove unused PySide6 files from a package tree. Returns bytes removed."""
    if not pyside6_dir.is_dir():
        return 0

    removed = 0

    for pyd in pyside6_dir.glob('*.pyd'):
        mod = _parse_qt_module_from_pyd(pyd.name)
        if mod is None or mod not in PYSIDE6_KEEP_MODULES:
            removed += pyd.stat().st_size
            pyd.unlink()

    _dll_exclude_keywords = [
        'opengl32sw',
        'avcodec-', 'avformat-', 'avutil-', 'swscale-', 'swresample-',
    ]
    for dll in pyside6_dir.glob('*.dll'):
        mod = _parse_qt_module_from_dll(dll.name)
        if mod is not None and mod not in PYSIDE6_KEEP_MODULES:
            removed += dll.stat().st_size
            dll.unlink()
            continue
        if any(k in dll.name.lower() for k in _dll_exclude_keywords):
            removed += dll.stat().st_size
            dll.unlink()

    qml_root = pyside6_dir / 'qml'
    if qml_root.is_dir():
        for child in qml_root.iterdir():
            if child.is_dir() and child.name not in _KEEP_QML_DIRS:
                removed += _remove(child)
        for pattern in (
            'QtQuick/VirtualKeyboard', 'QtQuick/Particles', 'QtQuick/Pdf',
            'QtQuick/Scene2D', 'QtQuick/Scene3D', 'QtQuick/Timeline',
            'QtQuick/VectorImage', 'QtQuick/tooling', 'QtQuick/Controls/designer',
        ):
            removed += _remove(qml_root / pattern)

    plugins_root = pyside6_dir / 'plugins'
    if plugins_root.is_dir():
        for child in plugins_root.iterdir():
            if child.is_dir() and child.name not in _KEEP_PLUGIN_DIRS:
                removed += _remove(child)
        for name in ('openglrenderer.dll', 'qdirect2d.dll'):
            for f in plugins_root.rglob(name):
                removed += _remove(f)

    for exe_name in TOOL_EXE_NAMES:
        removed += _remove(pyside6_dir / exe_name)
    for f in pyside6_dir.glob('**/*.pyi'):
        removed += f.stat().st_size
        f.unlink()
    for f in pyside6_dir.glob('**/*.lib'):
        removed += f.stat().st_size
        f.unlink()
    removed += _remove(pyside6_dir / 'QtWebEngineProcess.exe')

    for pattern in ('translations', 'include', 'typesystems', 'doc', 'scripts',
                    'support', 'resources', 'metatypes'):
        removed += _remove(pyside6_dir / pattern)

    return removed


def prune_dist_directory(dist_dir: Path) -> int:
    """Remove unused PySide6/Qt files from a PyInstaller dist directory. Returns bytes removed."""
    internal_dir = dist_dir / '_internal'
    if not internal_dir.is_dir():
        return 0

    removed = prune_pyside6_dir(internal_dir / 'PySide6')

    for dll in internal_dir.glob('Qt6*.dll'):
        mod = _parse_qt_module_from_dll(dll.name)
        if mod is not None and mod not in PYSIDE6_KEEP_MODULES:
            removed += dll.stat().st_size
            dll.unlink()

    # 仅删除 _internal 根目录下 Qt 附带的 FFmpeg DLL；勿动 av.libs/（PyAV/scrcpy 运行时依赖）。
    for pattern in ('avcodec-*', 'avformat-*', 'avutil-*', 'swscale-*', 'swresample-*'):
        for dll in internal_dir.glob(pattern):
            removed += dll.stat().st_size
            dll.unlink()

    return removed


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print('Usage: python -m tools.build.prune_qt <dist-directory>')
        sys.exit(1)

    target = Path(sys.argv[1])
    if not target.is_dir():
        print(f'Not a directory: {target}')
        sys.exit(1)

    if (target / '_internal').is_dir():
        removed = prune_dist_directory(target)
        label = 'dist'
    else:
        removed = prune_pyside6_dir(target)
        label = 'PySide6'

    print(f'Pruned {label}: {removed / 1024 / 1024:.1f} MB removed')
