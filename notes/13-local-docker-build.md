# 本地 Docker 化 Android APK 构建（全进 Docker 内部）

日期：2026-08-16
分支：`feat/p4a-android`
构建：E2E 验证通过（本机 `iaa-26.07b1-x86_64-debug.apk`，352.7 MB）

## 一、为什么"全进 Docker 内部"

旧设计（bind-mount）把 NDK/SDK/wheels/构建目录缓存在主机 `$HOME\.iaa-android-cache`，
Windows 主机 + Docker Desktop 上坑多：路径大小写、NTFS 权限、bind-mount 未共享盘符、
主机目录与容器内 `/root`/`.buildozer` 的 inode/符号链接语义不一致。新设计把这些**全部
收进 Docker 命名卷**，主机只提供：

- 仓库源码：`-v <repo>:/workspace:ro` **只读**挂载。容器内从不写 `/workspace`，
  源码在卷内另有一份可写副本（`stage_prep` 复制进 app 卷）。
- 产物：构建完 `docker cp <容器>:/artifacts/. <OutDir>` 取回，容器随即 `docker rm -f`。

主机零缓存目录、零挂载进构建的写路径，Windows 侧的共享盘符/大小写问题不再影响构建。

## 二、命名卷布局

| 命名卷 | 挂载点 | 内容 |
| --- | --- | --- |
| `iaa-android-app` | `/build/app` | 构建工作目录（`stage_prep` 复制进的可写源码、`buildozer.spec`、`.buildozer` 全量构建产物，跨次增量） |
| `iaa-android-cache` | `/root` | NDK / SDK / wheels / cargo / rustup / ccache / buildozer / gradle 全部缓存 |

- 产物（APK）留容器内 `/artifacts`，跑完 `docker cp` 取回（构建容器不挂 `/artifacts` 到主机）。
- 构建容器固定命名 `iaa-android-build-<时间戳>`，复用同一名字做 `docker cp` / `docker rm -f`；
  wrapper 用 `try/finally` 兜底，无论成败都清理容器。

## 三、用法

```powershell
# 默认 x86_64 / API 35 / NDK r27c / PySide6 6.11.1，输出到 <仓库根>\bin
.\scripts\build-android.ps1

# 镜像已构建过：跳过 docker build，直接用已有镜像
.\scripts\build-android.ps1 -SkipBuild

# 自检：只打印将执行的 docker 命令，不真跑
.\scripts\build-android.ps1 -DryRun

# 常用覆盖
.\scripts\build-android.ps1 -SkipBuild -Arch aarch64 -Api 35 -OutDir .\myapk
```

参数：`-Arch`（默认 x86_64，模拟器）/ `-Api`（35）/ `-PysideVersion`（6.11.1，镜像内置）/
`-NdkVersion`（r27c）/ `-OutDir`（默认 `<仓库根>\bin`）/ `-Tag` / `-Platform`
（linux/amd64）/ `-SkipBuild` / `-DryRun` / `-Help`。

Linux/macOS 用 `scripts/build-android.sh`，参数一致（环境变量 `P4A_ARCH` / `ANDROID_API` /
`IAA_ANDROID_OUT` / `IAA_ANDROID_SKIP_BUILD` 等）。

镜像 `docker/android-build.Dockerfile`：ubuntu 22.04 + JDK17 + rustup + Python3.11（deadsnakes）
+ `/opt/venv`（PySide6 桌面版 / buildozer 1.5.0 / cython / kotonebot host 依赖）。
容器入口 `docker/entrypoint-build.sh` 幂等补齐 NDK/SDK/wheels 后调用
`tools/android/build_android.py`（prep → resgen → pass1 → patch → pass2 → collect，阶段与 CI 对齐）。

## 四、首次运行成本 vs 增量

- **首次**（命名卷为空）：下载 NDK ~1.9GB / SDK ~736MB / PySide6 android wheel 81MB +
  编译 numpy / opencv / pydantic-core（rust）/ shiboken6 等 p4a recipe + gradle 打包 PySide6，
  合计约 30–60 分钟（视网络与核数）。下载源：`dl.google.com` / `download.qt.io` /
  GitHub codeload / rustup。
- **增量**：`.buildozer` 与 `state.db` 在 app 卷内跨次保留，NDK/SDK/wheels 在 cache 卷内幂等跳过；
  recipe 已 built 的直接跳过，源码变更只重编相关部分。
- 修 bug 重跑时只重编受影响 recipe：本机 E2E 中 pydantic-core/shiboken6 已编译成功、
  opencv 缺 cmake 失败 → 补 cmake 重跑，opencv 单独从源码重编，其余跳过。

## 五、坑与解决

1. **`EXCLUDED_NAMES` 误伤 `resources/jp`（本机 E2E 实踩，已修）**
   `build_android.py` 的 `EXCLUDED_NAMES` 原含 `'jp'`，本意排除根目录本地产物 `jp/`，
   但 fnmatch 按名字匹配会连 `resources/jp` 一起排除——而 `resources/jp` 是 **variant
   prefab 的 base 定义**（cn/tw 是 variant 覆盖）。缺它时 resgen 报
   `kotonebot.devtools.errors.ValidationError: variant prefab requires base definition:
   CommonDialog.TextAwardClaimedOk`，pass1 前直接失败。修法：`_ignore` 改为
   `_make_ignore(repo_dir)` 工厂，仅当被复制目录 == 仓库根时才剔除 `jp`（见
   `tools/android/build_android.py`）。
2. **opencv recipe 缺 cmake（本机 E2E 实踩，已修）**
   p4a opencv recipe `build_arch` 直接 `shprint(sh.cmake, ...)`，容器镜像没装 cmake →
   `sh.CommandNotFound: cmake`。GitHub Actions ubuntu-22.04 runner 预装 cmake，所以 CI 不触发。
   修法：`docker/android-build.Dockerfile` 底部独立层补装 `cmake`（放在 libltdl-dev 同一层，
   避免改动顶部 apt 层导致全量重 build）。
3. **`EXCLUDED_NAMES` 防 pass1 扫描崩溃（既有设计）**
   根目录本地产物（`dist_app` / `iaa-backend` / `tmp` / `agent-tools` / `mcps` /
   `terminals` / `*.egg-info` / 点目录）不属应用源码，若混入 app-dir，pass1 的
   pyside6-android-deploy 会整树按 UTF-8 读源码，扫到 `dist_app` 打包自带的 cv2 等二进制
   `.py` 时报 UnicodeDecodeError，buildozer.spec 生成不出来。
4. **容器 root 下 buildozer check_root 交互确认崩溃（既有设计）**
   buildozer 1.5.0 的 `check_root()` 在 root 运行时 `input()` 直接 EOFError。Dockerfile
   内已补丁为自动 `cont = 'y'`（CI runner 非 root，不触发）。
5. **全新命名卷里 rustup 缺失 → entrypoint 自愈（既有设计）**
   `/root` 是 cache 卷：首次挂载全新卷会把镜像内 `/root/.cargo` 拷进来，但卷非空/先于
   镜像存在时镜像期装的 rustup 会被遮蔽。entrypoint 检测 `$HOME/.cargo/bin/cargo` 缺失
   就重装（pydantic-core recipe 依赖 rustup/cargo）。
6. **`yes | sdkmanager` SIGPIPE（既有设计）**
   `yes` 在 sdkmanager 关闭 stdin 后收 SIGPIPE(141)，pipefail 会把整条管道判失败；
   entrypoint 临时 `set +o pipefail` 只保留 sdkmanager 自身退出码。
7. **`unzip -qo` 卷内幂等覆盖（既有设计）**
   NDK/cmdline-tools 解压用 `-o` 无提示覆盖，重跑/续传中断时不交互阻塞、不因已存在文件
   返回非零。下载统一走 `curl -fL --retry 8 --retry-all-errors -C -`（断点续传 + speed 兜底）。
8. **p4a download_file 用 urlretrieve 大文件断连即败（既有设计）**
   GitHub codeload chunked 传输中途断连抛 IncompleteRead（非 OSError，p4a 自带 5 次重试
   不生效），opencv 等大源码包在 ~100MB 处失败。entrypoint 幂等补丁 p4a `recipe.py`：
   `P4A_HTTP_VIA_CURL=1` 时走 curl 全量重试 + `-C -` 续传（预 clone develop 分支保证
   补丁首次即生效）。
9. **sdkmanager legacy 软链只在 pass2 前补（既有设计）**
   buildozer 只认 `$SDK/tools/bin/sdkmanager`；cmdline-tools 布局在
   `cmdline-tools/latest/bin`。`build_android.py::_ensure_sdkmanager_legacy_link` 在 pass2
   前补软链。不能提前：pass1 内部的 buildozer 若找到软链会真的去跑完整构建（掩盖
   pyside6-android-deploy 的失败容错）。

## 六、与旧 bind-mount 设计 / CI 的差异

| 维度 | 旧设计 / CI | 新设计（本机 Docker） |
| --- | --- | --- |
| 源码 | bind-mount 可写；CI 直接 checkout | `:ro` 挂载，卷内副本可写 |
| 缓存位置 | 主机 `$HOME\.iaa-android-cache` | Docker 命名卷（app/cache） |
| 产物取回 | 挂载 /artifacts 到主机 | `docker cp` + `docker rm -f` |
| 主机缓存目录 | 有 | 无 |
| 增量 | 主机目录跨次保留 | 卷内 `.buildozer` 跨次保留，效果一致 |
| 首次成本 | 同（要下 NDK/SDK/wheels） | 同 |
| 已作废 | 旧 `$HOME\.iaa-android-cache` 布局不迁移、不兼容 | — |

CI（`.github/workflows/android-build.yml`）维持原状；`build_android.py` 阶段与 CI 严格
对齐，本机 Docker 只是把 CI 的构建环境搬进容器并补齐容器化特有的坑（上面 4/5/6/7/8）。

## 七、产物路径与调试方法

- **APK**：`<OutDir>`（默认 `<仓库根>\bin`）。容器内 `/artifacts` 只存在到 `docker rm -f` 前。
- **构建日志**：容器 stdout（wrapper 重定向后即构建日志）；buildozer 详细日志在 app 卷
  `.buildozer/` 下。构建容器已删时用临时容器只读查看卷：
  ```bash
  docker run --rm -v iaa-android-app:/build/app alpine:latest sh -c \
    'ls /build/app/.buildozer/; tail /build/app/.buildozer/android/platform/buildozer.log'
  ```
- **生成的 spec**：`/build/app/buildozer.spec`（pass1 生成 + patch 并入仓库
  `requirements/p4a.txt`）；`buildozer.spec.sample` 是 prep 挪走的仓库原始 spec。
- **recipe 构建状态**：`/build/app/.buildozer/android/platform/build-x86_64/state.db`；
  各 recipe 源码/产物在 `.../build/other_builds/<name>/...`。
- **缓存卷**：NDK `~/.pyside6_android_deploy/android-ndk/android-ndk-r27c`（约 1.9GB）、
  SDK `/root/android-sdk`（约 736MB）、wheels `/root/wheels`（81MB）、ccache `/root/.cache/ccache`。

## 八、本机 E2E 验证记录

- Run 1（`-SkipBuild`，镜像 91cc580c）：entrypoint 幂等补齐 NDK/SDK/wheels 成功（~2 分钟，
  10MB/s，容器时区 UTC），resgen 失败 → **坑 1**（jp 排除误伤 resources/jp）。已修。
- Run 2：resgen 通过，pass1/patch 通过，pass2 编完 numpy/pydantic-core/shiboken6，
  opencv 报 `CommandNotFound: cmake` → **坑 2**。已修（重建镜像）。
- Run 3（镜像 60942bb，含 cmake）：prep → resgen → pass1 → patch → pass2（重编
  numpy/pydantic-core/shiboken6/opencv/pyside6，两次 gradle assembleDebug：2m2s + 13s）
  → collect → `docker cp` 成功。
- 最终产物：`E:\GithubRepos\ichikas-auto-assistant\bin\iaa-26.07b1-x86_64-debug.apk`
  （352.7 MB，09:51:18，zip 结构含 classes.dex / classes2.dex / META-INF，签名由 gradle
  debug keystore 完成）。
- 模拟器冒烟：本机 MuMu 运行中但 `adb` 无设备（127.0.0.1:5557 及各常见端口不通），
  安装/启动冒烟未执行（不强求）。
- 共享文件修改：
  - `tools/android/build_android.py`：`EXCLUDED_NAMES` 移除 `jp`（改由
    `_make_ignore(repo_dir)` 仅根级剔除），CLI 契约未变。
  - `docker/android-build.Dockerfile`：libltdl 层追加 `cmake`（opencv recipe 需要）。