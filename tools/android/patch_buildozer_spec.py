"""buildozer.spec 补丁工具（Android 构建专用）。

把仓库的 Android 依赖与构建参数并入 ``pyside6-android-deploy`` 生成的
``buildozer.spec``。语义与 ``.github/workflows/android-build.yml`` 的
"Merge iaa requirements" 步骤完全一致：

* ``requirements`` = ``python3==3.11.9,hostpython3==3.11.9,shiboken6,PySide6``
  + ``requirements/p4a.txt`` 中全部非空、非 ``#`` 行（逗号连接，逗号后无空格）。
* 写死一批硬编码键（accept_sdk_license / wakelock / api / minapi / ndk_api /
  permissions / title / version / android.numeric_version），与仓库 buildozer.spec
  骨架的 ``[硬编码]`` 段一致。
* ``source.include_exts``：当前值不含 ``ttf`` 时追加 ``,ttf,txt``
  （QML FontLoader 需要 ttf 进包）。
* ``p4a.extra_args`` 中 ``--qt-libs`` 模块列表重排为 ``Core`` 首位
  （JNI 启动崩溃修复，见 notes/05-root-cause-jni.md）；找不到 ``--qt-libs``
  时打印 warning 但不失败。

用法::

    python tools/android/patch_buildozer_spec.py buildozer.spec [requirements/p4a.txt]

脚本只原地修改 SPEC_PATH，保留其它键，并打印变更摘要。
"""

import argparse
import configparser
import pathlib
import re

# 基础 requirements：目标 Python 与 Qt 绑定（与仓库 buildozer.spec 骨架一致）。
# p4a python3 默认 3.14，与 Qt android wheel 的 cp311 冲突，必须 pin 3.11.9。
REQUIREMENTS_BASE = 'python3==3.11.9,hostpython3==3.11.9,shiboken6,PySide6'

# 补丁阶段写死的键值（buildozer.spec 骨架里标注的 [硬编码] 段）。
# android.numeric_version：仓库版本号 '26.07b1' 非数值点分格式，
# p4a 打包必须显式 versionCode，否则工具会报错。
HARDCODED_OPTIONS = {
    'android.accept_sdk_license': 'True',
    'android.wakelock': 'True',
    'android.api': '35',
    'android.minapi': '24',
    'android.ndk_api': '24',
    'android.permissions': 'INTERNET',
    'title': 'iaa',
    'version': '26.07b1',
    'android.numeric_version': '2607',
}

# 工具生成的 include_exts 缺失时的兜底值（仅当键不存在时使用）。
DEFAULT_INCLUDE_EXTS = 'py,png,jpg,qml,js'

# 解析 p4a.extra_args 中的 --qt-libs=<模块列表>：模块列表以空格为界，
# 其余前缀/后缀原样保留（[^ ]+ 限制模块列表内不含空格）。
_QT_LIBS_RE = re.compile(r'(.*--qt-libs=)([^ ]+)(.*)')


def read_extra_requirements(p4a_txt_path):
    """读取 p4a.txt 里的“额外”依赖清单。

    :param p4a_txt_path: requirements/p4a.txt 路径。
    :return: 非空、非 ``#`` 注释行的依赖列表（每行已 strip）。
    :raises OSError: 文件读取失败。
    """
    extra = []
    for line in pathlib.Path(p4a_txt_path).read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        extra.append(line)
    return extra


def reorder_qt_libs(extra_args):
    """重排 ``p4a.extra_args`` 中 ``--qt-libs`` 的模块列表，使 ``Core`` 居首。

    JVM 只对 System.load 显式加载的库调用 JNI_OnLoad；被 dlopen 拉入的依赖库
    不会触发。Qt6Core 的 JNI_OnLoad 注册全局 JavaVM（g_javaVM），若 Qt6Quick
    先加载，其 JNI_OnLoad 里 QJniEnvironment::getJniEnv() 会因 g_javaVM 为空
    SIGSEGV。工具用 ``list(set(...))`` 生成顺序随机，故强制 Core 排到首位。

    :param extra_args: ``p4a.extra_args`` 原始值。
    :return: ``(新值, 重排后的模块列表或 None)``。找不到 ``--qt-libs`` 时
        新值等于原值，模块列表为 ``None``。
    """
    m = _QT_LIBS_RE.match(extra_args)
    if not m:
        return extra_args, None
    modules = m.group(2).split(',')
    reordered = ['Core'] + [x for x in modules if x != 'Core']
    return m.group(1) + ','.join(reordered) + m.group(3), reordered


def patch_buildozer_spec(spec_path, p4a_txt_path):
    """原地补丁 buildozer.spec，返回变更摘要。

    :param spec_path: buildozer.spec 路径。
    :param p4a_txt_path: requirements/p4a.txt 路径。
    :return: 摘要 dict，含 ``requirements``、``include_exts``、
        ``qt_libs``（重排后的模块列表或 None）等键。
    :raises FileNotFoundError: spec 或 p4a.txt 不存在。
    :raises ValueError: spec 缺少 ``[app]`` 段。
    :raises OSError: 写入失败。
    """
    spec_path = pathlib.Path(spec_path)
    p4a_txt_path = pathlib.Path(p4a_txt_path)
    if not spec_path.is_file():
        raise FileNotFoundError(f'buildozer.spec 不存在：{spec_path}')
    if not p4a_txt_path.is_file():
        raise FileNotFoundError(f'p4a.txt 不存在：{p4a_txt_path}')

    extra = read_extra_requirements(p4a_txt_path)
    requirements = REQUIREMENTS_BASE + ',' + ','.join(extra)

    # 与 workflow 内联补丁相同的解析参数：'#' 视为注释、不支持行内注释、
    # 不做插值（避免键值里的 % 被误当作插值）。
    cp = configparser.ConfigParser(
        comment_prefixes='#', inline_comment_prefixes=None, interpolation=None)
    cp.read(spec_path, encoding='utf-8')
    try:
        app = cp['app']
    except KeyError:
        raise ValueError(f'buildozer.spec 缺少 [app] 段：{spec_path}') from None

    app['requirements'] = requirements
    for key, value in HARDCODED_OPTIONS.items():
        app[key] = value

    # 工具生成的 include_exts 缺 ttf/txt（QML FontLoader 需要 ttf 进包）；
    # 已含 ttf 时不再重复追加。
    cur_exts = app.get('source.include_exts', DEFAULT_INCLUDE_EXTS)
    if 'ttf' not in cur_exts:
        app['source.include_exts'] = cur_exts + ',ttf,txt'
    include_exts = app['source.include_exts']

    extra_args = app.get('p4a.extra_args', '')
    new_extra_args, qt_libs = reorder_qt_libs(extra_args)
    app['p4a.extra_args'] = new_extra_args

    with spec_path.open('w', encoding='utf-8') as f:
        cp.write(f, space_around_delimiters=True)

    return {
        'requirements': requirements,
        'include_exts': include_exts,
        'qt_libs': qt_libs,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='补丁 buildozer.spec，并入仓库 Android 依赖与构建参数。')
    parser.add_argument('spec_path', help='buildozer.spec 路径')
    parser.add_argument(
        'p4a_txt_path', nargs='?', default=None,
        help='requirements/p4a.txt 路径（默认取 spec 同目录的 requirements/p4a.txt）')
    args = parser.parse_args(argv)

    spec_path = pathlib.Path(args.spec_path)
    p4a_txt_path = pathlib.Path(args.p4a_txt_path) if args.p4a_txt_path \
        else spec_path.parent / 'requirements' / 'p4a.txt'

    summary = patch_buildozer_spec(spec_path, p4a_txt_path)

    print(f'patched requirements = {summary["requirements"]}')
    print(f'source.include_exts = {summary["include_exts"]}')
    if summary['qt_libs'] is not None:
        print(f'reordered --qt-libs = {",".join(summary["qt_libs"])}')
    else:
        print('::warning::--qt-libs not found in p4a.extra_args')
    print('hardcoded options set = ' + ', '.join(sorted(HARDCODED_OPTIONS)))
    print(f'patched spec: {spec_path}')
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())