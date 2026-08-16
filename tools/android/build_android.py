"""Android APK 构建脚本（p4a + PySide6），对齐 GitHub Actions workflow。

把强耦合在 ``.github/workflows/android-build.yml`` 的构建逻辑抽成独立脚本，
供 CI 与本地 Docker 容器共用。构建在 Linux 上执行；脚本自身应运行在已装好
pyside6-android-deploy / buildozer / kotonebot host 依赖的 Python venv 中，
工具二进制（pyside6-android-deploy / buildozer / python3）优先从脚本所在
venv 的 bin 解析，找不到再回退 PATH。

阶段顺序固定，严格对齐 CI：

    a) prep    复制仓库 → app-dir（排除 .git/.venv/缓存等，保留已有 .buildozer）
               并把 buildozer.spec 挪为 buildozer.spec.sample
    a1) arch   把 --arch 写进 app-dir 的 pysidedeploy.spec（[buildozer] arch），
               pass1 据此生成对应 android.archs（幂等，仅变化时写回）
    b) resgen  在 app-dir 执行 make_resources.py --production，断言产物
    c) pass1   pyside6-android-deploy 生成 buildozer.spec（容忍失败）
    d) patch   调用同仓库 patch_buildozer_spec.py 补丁 spec
    e) pass2   buildozer -v android debug 完整构建
    f) collect 收集 *.apk 到 --output

不要重蹈覆辙的坑（详见 notes/04-handover.md、notes/07-handover-v2.md）：
pass2 绝不能重跑 pyside6-android-deploy（其 cleanup() 会 purge 补丁后的 spec）；
sdkmanager legacy 软链只在 pass2 前补，否则 pass1 内部的 buildozer 会真去构建。
"""

import argparse
import configparser
import fnmatch
import os
import pathlib
import shutil
import subprocess
import sys

# prep 阶段复制仓库时排除的条目（与 workflow rsync --exclude 对齐）。
# 排除项在 app-dir 里已存在时保留不动，支持 .buildozer 增量构建。
# 下面除 workflow 原有条目外，还有本仓库根目录存在、但 CI checkout 里没有的
# 本地产物/工具目录：它们不属于 iaa 应用源码，若混入 app-dir，pass1 的
# pyside6-android-deploy 会整树扫描并按 UTF-8 读取源码文件，扫到 dist_app 里
# 打包自带的 cv2 等二进制 .py 文件时报 UnicodeDecodeError，导致 buildozer.spec
# 生成不出来（详见 notes/13-local-docker-build.md）。
# 注意：根级本地目录 ``jp`` 不在此列——它由 _make_ignore 在复制仓库根时单独剔除，
# 避免 fnmatch 按名字匹配误伤 resources/jp（JP 区资源的 variant base 定义，
# resgen 必须读到）。见 notes/13-local-docker-build.md。
EXCLUDED_NAMES = (
    '.git',
    '.venv',
    '__pycache__',
    '.ruff_cache',
    '.pytest_cache',
    '.buildozer',
    # 本地开发/工具目录（CI checkout 不含，排除不改变 CI 语义；本地可避免
    # pass1 扫描崩溃并显著加快 prep 复制）：
    '.idea',
    '.vscode',
    '.claude',
    '.commandcode',
    '.kotonebot',
    '.agents',
    'deployment',
    'build',
    'dist',
    'dumps*',
    'logs',
    'conf',
    'dist_app',
    'iaa-backend',
    'tmp',
    'agent-tools',
    'mcps',
    'terminals',
    '*.egg-info',
)

# p4a / buildozer 需要 JDK 17（Qt 官方工具链对齐版本）。
DEFAULT_JAVA_HOME = '/usr/lib/jvm/java-17-openjdk-amd64'

# CI 里 pass2 补进 PATH 的两个目录：rustup cargo（pydantic-core recipe 需要）、
# buildozer 缓存的 ant。
DEFAULT_CARGO_BIN = pathlib.Path.home() / '.cargo' / 'bin'
DEFAULT_ANT_BIN = pathlib.Path.home() / '.buildozer' / 'android' / 'platform' / 'apache-ant-1.9.4' / 'bin'


class BuildError(RuntimeError):
    """构建失败，带阶段上下文（由 main 统一打印后非零退出）。"""


def _banner(title):
    print(f'\n========== {title} ==========')


def _venv_bin_dir():
    """脚本自身 venv 的 bin/Scripts 目录。

    :return: ``Path(sys.executable).parent``。
    """
    return pathlib.Path(sys.executable).parent


def _resolve_tool(name):
    """按“venv bin → PATH”顺序解析工具可执行文件。

    :param name: 工具名（如 pyside6-android-deploy、buildozer）。
    :return: 可执行文件路径字符串；找不到返回 None。
    """
    for cand in (name, name + '.exe', name + '.cmd', name + '.bat'):
        p = _venv_bin_dir() / cand
        if p.exists():
            return str(p)
    return shutil.which(name)


def _resolve_python():
    """解析 python3：优先 venv bin，找不到回退当前解释器。

    Windows venv 没有 python3 入口，直接用正在运行本脚本的解释器（sys.executable）
    即正确 venv python，保证 CI 与容器内通用。

    :return: python3 可执行文件路径字符串。
    """
    for cand in ('python3', 'python3.exe', 'python3.bat'):
        p = _venv_bin_dir() / cand
        if p.exists():
            return str(p)
    return sys.executable


def _base_env():
    """构建用环境：JAVA_HOME 默认 JDK17，PATH 前置 venv bin / cargo / ant。

    :return: 基于 ``os.environ`` 拷贝的环境 dict。
    """
    env = os.environ.copy()
    env['JAVA_HOME'] = os.environ.get('JAVA_HOME', DEFAULT_JAVA_HOME)
    paths = [
        str(_venv_bin_dir()),
        str(DEFAULT_CARGO_BIN),
        str(DEFAULT_ANT_BIN),
        env.get('PATH', ''),
    ]
    env['PATH'] = os.pathsep.join(paths)
    return env


def _run(cmd, cwd, env, step, tolerate=False):
    """执行子进程命令并处理退出码。

    :param cmd: 命令参数列表。
    :param cwd: 工作目录。
    :param env: 环境 dict。
    :param step: 阶段名（用于报错上下文）。
    :param tolerate: 是否容忍非零退出码（pass1 用，对齐 workflow 的 ``|| true``）。
    :raises BuildError: 命令无法启动，或（tolerate=False 时）退出码非零。
    """
    print(f'[cmd] {" ".join(cmd)}')
    try:
        proc = subprocess.run(cmd, cwd=str(cwd), env=env)
    except OSError as exc:
        raise BuildError(f'{step}：无法执行 {cmd[0]}：{exc}') from exc
    if proc.returncode != 0 and not tolerate:
        raise BuildError(f'{step}：命令失败，退出码 {proc.returncode}，见上方输出')
    return proc


def _make_ignore(repo_dir):
    """copytree 的 ignore 回调工厂：剔除 EXCLUDED_NAMES。

    根级本地产物 ``jp`` 只在复制仓库根时剔除：fnmatch 按名字匹配，若直接放进
    EXCLUDED_NAMES 会误伤 ``resources/jp``——那是 JP 区资源（variant prefab 的
    base 定义），resgen 必须读到，缺了会报
    ``variant prefab requires base definition: ...``（见 notes/13-local-docker-build.md）。

    :param repo_dir: 仓库根目录。
    :return: copytree ignore 回调函数。
    """
    repo_root = pathlib.Path(repo_dir).resolve()

    def _ignore(_directory, names):
        directory = pathlib.Path(_directory).resolve()
        return [
            n for n in names
            if (directory == repo_root and n == 'jp')
            or any(fnmatch.fnmatch(n, pat) for pat in EXCLUDED_NAMES)
        ]

    return _ignore


def _ensure_sdkmanager_legacy_link(sdk_dir):
    """若 SDK 是 cmdline-tools 布局，补建 buildozer 需要的 legacy 软链。

    buildozer 的 _sdkmanager 只认 ``$SDK/tools/bin/sdkmanager``（buildozer/targets/
    android.py 的 sdkmanager_path property）；cmdline-tools 安装布局在
    ``cmdline-tools/latest/bin``。软链只在 pass2 前补，避免 pass1 内部的 buildozer
    真的去跑完整构建（见 notes/04-handover.md）。

    :param sdk_dir: Android SDK 根目录。
    """
    latest = sdk_dir / 'cmdline-tools' / 'latest' / 'bin' / 'sdkmanager'
    if not latest.exists():
        print(f'sdkmanager cmdline-tools 布局未找到（{latest}），跳过 legacy 软链')
        return
    tools_bin = sdk_dir / 'tools' / 'bin'
    tools_bin.mkdir(parents=True, exist_ok=True)
    link = tools_bin / 'sdkmanager'
    if link.is_symlink() or link.exists():
        link.unlink()
    try:
        os.symlink(str(latest), str(link))
    except OSError:
        # 个别环境不支持符号链接：退化为复制，Linux 上同样可用。
        shutil.copy2(str(latest), str(link))
    print(f'sdkmanager legacy 软链: {link} -> {latest}')


def stage_prep(repo_dir, app_dir):
    """阶段 a：复制仓库 → app-dir（排除构建无关项，保留已有 .buildozer）。

    :param repo_dir: 仓库根目录。
    :param app_dir: 应用构建目录。
    :raises BuildError: 复制失败。
    """
    _banner('a) prep：复制仓库到 app 目录')
    print(f'repo   = {repo_dir}')
    print(f'app    = {app_dir}')
    app_dir.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copytree(repo_dir, app_dir, dirs_exist_ok=True, symlinks=True,
                        ignore=_make_ignore(repo_dir))
    except OSError as exc:
        raise BuildError(f'a) prep：复制 {repo_dir} → {app_dir} 失败：{exc}') from exc
    spec = app_dir / 'buildozer.spec'
    if spec.exists():
        # 官方工具发现 buildozer.spec 已存在会跳过自动配置：挪成 .sample，
        # 让工具先生成一份完整 Qt 配置（含 recipes 引用、--qt-libs、jars）。
        spec.replace(app_dir / 'buildozer.spec.sample')
        print('buildozer.spec -> buildozer.spec.sample')


def _apply_deploy_arch(app_dir, arch):
    """把目标架构写入 app-dir 的 pysidedeploy.spec（prep 后、pass1 前）。

    pyside6-android-deploy 生成 buildozer.spec 时，``android.archs`` 来自
    pysidedeploy.spec 的 ``[buildozer] arch``：仓库根的 pysidedeploy.spec 写死
    x86_64，prep 会把它原样复制进 app-dir。若不在这里把 ``--arch`` 真正写进 spec，
    该参数只影响打印，无论怎么传永远只会产出 x86_64。这里用 configparser 原地改，
    保留其它键；缺 ``[buildozer]`` 段或 ``arch`` 键时创建。仅在值变化时写回并打印
    变更，目标 arch 始终打印（幂等：已是目标值则不动）。

    :param app_dir: 应用构建目录（含 prep 复制进来的 pysidedeploy.spec）。
    :param arch: 目标架构（如 x86_64 / aarch64）。
    :raises OSError: 读取或写入失败。
    """
    spec = app_dir / 'pysidedeploy.spec'
    cp = configparser.ConfigParser(
        comment_prefixes='#', inline_comment_prefixes=None, interpolation=None)
    cp.read(spec, encoding='utf-8')
    if not cp.has_section('buildozer'):
        cp.add_section('buildozer')
    current = cp.get('buildozer', 'arch', fallback=None)
    print(f'pysidedeploy.spec [buildozer] arch = '
          f'{current if current is not None else "(缺失)"} -> 目标 {arch}')
    if current == arch:
        print('arch 已是目标值，无需修改（幂等）')
        return
    cp.set('buildozer', 'arch', arch)
    with spec.open('w', encoding='utf-8') as f:
        cp.write(f, space_around_delimiters=True)
    print(f'已写入 {spec}：[buildozer] arch = {arch}')


def stage_resgen(app_dir):
    """阶段 b：生成资源代码 iaa/tasks/R.py 与 iaa/res，并断言产物存在。

    make_resources.py 走 kotonebot.devtools.resgen，需 host 侧安装 kotonebot
    （环境准备由 CI / Docker 负责）。生成的 iaa/res 会随 buildozer 打进 APK。

    :param app_dir: 应用构建目录。
    :raises BuildError: 生成命令失败或产物缺失。
    """
    _banner('b) resgen：生成 iaa 资源')
    python = _resolve_python()
    cmd = [python, 'tools/make_resources.py', '--production']
    _run(cmd, app_dir, _base_env(), 'b) resgen')
    r_py = app_dir / 'iaa' / 'tasks' / 'R.py'
    res_dir = app_dir / 'iaa' / 'res'
    if not r_py.is_file() or not res_dir.is_dir():
        raise BuildError(
            f'b) resgen：产物缺失，期望 {r_py}（文件）与 {res_dir}（目录）。\n'
            '   请确认 host 环境已安装 kotonebot 及其生成依赖（见 notes/10-resources-generation.md）。')
    print(f'ok: {r_py} / {res_dir}')


def stage_pass1(app_dir, wheels_dir, sdk_dir, ndk_dir):
    """阶段 c：pyside6-android-deploy 生成 buildozer.spec（容忍失败）。

    pass1 失败也继续（对齐 workflow 的 ``|| true``）：生成的 buildozer.spec 与
    deployment/ 会被下一步补丁复用。结束后 buildozer.spec 必须存在。

    :param app_dir: 应用构建目录。
    :param wheels_dir: 存放 pyside6.whl / shiboken6.whl 的目录。
    :param sdk_dir: Android SDK 根目录。
    :param ndk_dir: Android NDK 根目录。
    :raises BuildError: 工具缺失、wheel 缺失，或 buildozer.spec 未生成。
    """
    _banner('c) pass1：pyside6-android-deploy 生成 buildozer.spec')
    deploy = _resolve_tool('pyside6-android-deploy')
    if not deploy:
        raise BuildError(
            'c) pass1：找不到 pyside6-android-deploy。\n'
            '   需在脚本所在 venv 安装 PySide6 桌面版（自带该控制台脚本）。')
    wheel_pyside = wheels_dir / 'pyside6.whl'
    wheel_shiboken = wheels_dir / 'shiboken6.whl'
    for wheel in (wheel_pyside, wheel_shiboken):
        if not wheel.is_file():
            raise BuildError(f'c) pass1：缺少 wheel：{wheel}')
    cmd = [
        deploy,
        f'--wheel-pyside={wheel_pyside}',
        f'--wheel-shiboken={wheel_shiboken}',
        f'--ndk-path={ndk_dir}',
        f'--sdk-path={sdk_dir}',
        '--keep-deployment-files',
        '--force',
        '--name', 'iaa',
        '--verbose',
        '-c', 'pysidedeploy.spec',
    ]
    _run(cmd, app_dir, _base_env(), 'c) pass1', tolerate=True)
    spec = app_dir / 'buildozer.spec'
    if not spec.is_file():
        raise BuildError(
            'c) pass1：pyside6-android-deploy 结束后未生成 buildozer.spec。\n'
            '   请检查上方 pass1 输出与以下位置排查：\n'
            f'   - {app_dir / "deployment"}/（动态 recipes / jar）\n'
            f'   - {app_dir / ".buildozer" / "buildozer.log"}（构建日志）\n'
            '   常见原因：SDK/NDK 路径不对、Qt android wheel 与宿主 python 版本不匹配。')
    print(f'ok: {spec}')


def stage_patch(app_dir, repo_dir):
    """阶段 d：调用同仓库 patch_buildozer_spec.py 补丁 buildozer.spec。

    :param app_dir: 应用构建目录。
    :param repo_dir: 仓库根目录（提供 requirements/p4a.txt）。
    :raises BuildError: 补丁脚本缺失或补丁失败。
    """
    _banner('d) patch：并入仓库依赖与构建参数')
    script = pathlib.Path(__file__).resolve().parent / 'patch_buildozer_spec.py'
    if not script.is_file():
        raise BuildError(f'd) patch：找不到补丁脚本：{script}')
    p4a_txt = repo_dir / 'requirements' / 'p4a.txt'
    cmd = [_resolve_python(), str(script), str(app_dir / 'buildozer.spec'), str(p4a_txt)]
    _run(cmd, app_dir, _base_env(), 'd) patch')


def stage_pass2(app_dir, sdk_dir):
    """阶段 e：buildozer -v android debug 完整构建（补 sdkmanager legacy 软链）。

    这里直接调 buildozer 而非重跑 pyside6-android-deploy：再跑一次 --force 会
    cleanup() 掉补丁后的 spec（见 pyside-tools/android_deploy.py 的 cleanup()），
    这是本构建链最大的坑之一。

    :param app_dir: 应用构建目录。
    :param sdk_dir: Android SDK 根目录。
    :raises BuildError: 工具缺失或构建失败。
    """
    _banner('e) pass2：buildozer -v android debug')
    buildozer = _resolve_tool('buildozer')
    if not buildozer:
        raise BuildError('e) pass2：找不到 buildozer（需安装 buildozer==1.5.0）')
    _ensure_sdkmanager_legacy_link(sdk_dir)
    cmd = [buildozer, '-v', 'android', 'debug']
    _run(cmd, app_dir, _base_env(), 'e) pass2')


def stage_collect(app_dir, output_dir):
    """阶段 f：收集 *.apk 到输出目录。

    :param app_dir: 应用构建目录。
    :param output_dir: APK 输出目录。
    :raises BuildError: 未找到任何 APK 或复制失败。
    """
    _banner('f) collect：收集 APK')
    output_dir.mkdir(parents=True, exist_ok=True)
    apks = sorted(app_dir.rglob('*.apk'))
    if not apks:
        raise BuildError(f'f) collect：{app_dir}（含 .buildozer）下未找到 *.apk')
    for apk in apks:
        dest = output_dir / apk.name
        shutil.copy2(apk, dest)
        print(f'copied: {apk} -> {dest}')
    print(f'ok: {output_dir}')


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='构建 Android APK（p4a + PySide6），严格对齐 CI workflow 阶段。')
    parser.add_argument('--repo', required=True, help='仓库根目录')
    parser.add_argument('--app-dir', required=True, help='应用构建目录（会被 prep 填充）')
    parser.add_argument(
        '--wheels-dir', required=True,
        help='PySide6 android wheel 目录（pyside6.whl / shiboken6.whl）')
    parser.add_argument('--sdk-dir', required=True, help='Android SDK 根目录')
    parser.add_argument('--ndk-dir', required=True, help='Android NDK 根目录')
    parser.add_argument('--arch', default='x86_64', help='目标架构（默认 x86_64）')
    parser.add_argument('--api', type=int, default=35, help='目标 API（默认 35）')
    parser.add_argument('--ndk-api', type=int, default=24, help='NDK API（默认 24）')
    parser.add_argument('--ndk-version', default='r27c', help='NDK 版本（默认 r27c）')
    parser.add_argument('--output', required=True, help='APK 输出目录')
    parser.add_argument('--pyside-version', default='6.11.1', help='PySide6 版本（默认 6.11.1）')
    args = parser.parse_args(argv)

    repo_dir = pathlib.Path(args.repo)
    app_dir = pathlib.Path(args.app_dir)
    wheels_dir = pathlib.Path(args.wheels_dir)
    sdk_dir = pathlib.Path(args.sdk_dir)
    ndk_dir = pathlib.Path(args.ndk_dir)
    output_dir = pathlib.Path(args.output)

    print(f'pyside {args.pyside_version} / arch {args.arch} / api {args.api} '
          f'/ ndk-api {args.ndk_api} / ndk {args.ndk_version}')

    try:
        stage_prep(repo_dir, app_dir)
        _apply_deploy_arch(app_dir, args.arch)
        stage_resgen(app_dir)
        stage_pass1(app_dir, wheels_dir, sdk_dir, ndk_dir)
        stage_patch(app_dir, repo_dir)
        stage_pass2(app_dir, sdk_dir)
        stage_collect(app_dir, output_dir)
    except BuildError as exc:
        print(f'\n[ERROR] {exc}', file=sys.stderr)
        return 1

    print(f'\n完成：APK 已收集到 {output_dir}')
    return 0


if __name__ == '__main__':
    sys.exit(main())