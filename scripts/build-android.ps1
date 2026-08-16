<#
.SYNOPSIS
   一键构建 iaa 的 Android APK（本地 Docker 化，Windows / Docker Desktop 主机）。

.DESCRIPTION
   把 .github/workflows/android-build.yml 的构建环境镜像进容器（ubuntu:22.04 +
   JDK17 + rustup + Python3.11 + PySide6 工具链），让本地直接产出 APK：
     1) docker build -f docker/android-build.Dockerfile -t iaa-android-build .
     2) docker run 挂载仓库（只读）+ 两个 Docker 命名卷，执行
        /docker/entrypoint-build.sh（幂等补齐 NDK/SDK/wheels 后调用
        tools/android/build_android.py）
     3) docker cp 从容器 /artifacts 取回 APK 到 -OutDir（默认 <仓库根>\bin），
        随后删除构建容器（try/finally 兜底，无论成败都会清理）

   缓存全部在 Docker 命名卷内，主机不再挂载/创建任何缓存目录（旧的
   $HOME\.iaa-android-cache 布局已作废，不迁移、不兼容）：
   * iaa-android-app   → /build/app（构建工作目录；stage_prep 会把 /workspace
     源码复制进卷内再编译，.buildozer 随卷持久化，支持跨次增量）
   * iaa-android-cache → /root（NDK / SDK / wheels / cargo / rustup /
     buildozer / gradle 全在卷内）
   首次运行会下载 NDK（约 1GB）/ SDK / PySide6 android wheel，属预期行为；
   后续运行因卷已缓存而跳过下载。

.EXAMPLE
   .\scripts\build-android.ps1
   .\scripts\build-android.ps1 -SkipBuild          # 跳过镜像构建，直接用已有镜像
   .\scripts\build-android.ps1 -OutDir .\myapk -Arch aarch64 -Api 35
   .\scripts\build-android.ps1 -DryRun             # 只打印要执行的 docker 命令
   .\scripts\build-android.ps1 -Help               # 显示本帮助

.PARAMETER Arch
   目标架构，默认 x86_64（模拟器）。传给容器 P4A_ARCH。
.PARAMETER Api
   目标 Android API，默认 35。传给容器 ANDROID_API。
.PARAMETER PysideVersion
   PySide6 版本，默认 6.11.1（镜像内置，通常无需改）。
.PARAMETER NdkVersion
   Android NDK 版本，默认 r27c（镜像内置，通常无需改）。
.PARAMETER OutDir
   APK 输出目录，默认 <仓库根>\bin。构建完成后由 docker cp 从容器内 /artifacts
   落地到此目录。
.PARAMETER Tag
   镜像标签，默认 iaa-android-build。
.PARAMETER Platform
   Docker 平台，默认 linux/amd64（NDK 预编译工具为 x86_64；Apple Silicon 主机会
   走 qemu/Rosetta 模拟，速度偏慢但可用）。
.PARAMETER SkipBuild
   跳过 docker build，直接用已有镜像运行。
.PARAMETER DryRun
   只打印将执行的 docker 命令，不真正执行（自检用）。
.PARAMETER Help
   显示本帮助。
#>
[CmdletBinding()]
param(
    [string]$Arch = 'x86_64',
    [int]$Api = 35,
    [string]$PysideVersion = '6.11.1',
    [string]$NdkVersion = 'r27c',
    [string]$OutDir = '',
    [string]$Tag = 'iaa-android-build',
    [string]$Platform = 'linux/amd64',
    [switch]$SkipBuild,
    [switch]$DryRun,
    [switch]$Help
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

# 中文提示输出统一用 UTF-8，避免重定向/管道时按系统代码页乱码
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

if ($Help) {
    Get-Help $MyInvocation.MyCommand.Path -Full
    exit 0
}

# ---- 路径解析：仓库根 = 本脚本上一级；输出目录给默认值并确保存在 ----
$RepoRoot = (Get-Item (Join-Path $PSScriptRoot '..')).FullName
if (-not $OutDir)   { $OutDir = Join-Path $RepoRoot 'bin' }        # 与 buildozer bin_dir 同名，天然 gitignored
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

# Windows 主机下 Docker Desktop 的 bind mount 源路径要求正斜杠盘符形式（E:/...）。
# 仓库根用作 :ro 只读挂载源；OutDir 只作 docker cp 的目标，用系统原生路径即可。
$repo = $RepoRoot.Replace('\', '/')

# 构建容器固定命名（时间戳后缀，避免与上次残留容器撞名）；docker cp / docker rm 复用它
$Container = 'iaa-android-build-' + (Get-Date -Format 'yyyyMMdd-HHmmss')

Write-Host ''
Write-Host '==============================================' -ForegroundColor Cyan
Write-Host '  iaa Android APK 一键构建（Docker 化）' -ForegroundColor Cyan
Write-Host '==============================================' -ForegroundColor Cyan
Write-Host "  仓库根   : $RepoRoot"
Write-Host "  架构/API : $Arch / $Api   (NDK $NdkVersion / PySide6 $PysideVersion)"
Write-Host "  输出目录 : $OutDir"
Write-Host "  镜像标签 : $Tag   (Platform: $Platform)"
Write-Host '  缓存     : Docker 命名卷 iaa-android-app(→/build/app) + iaa-android-cache(→/root)'
Write-Host ''

# ---- [1/3] docker build ----
$dockerFile = Join-Path $RepoRoot 'docker\android-build.Dockerfile'
if (-not $SkipBuild) {
    Write-Host '[1/3] 构建 Docker 镜像 iaa-android-build（首次约 10-25 分钟）...'
    $buildArgs = @('build', '--platform', $Platform, '--progress=plain',
        '-f', $dockerFile, '-t', $Tag, $RepoRoot)
    if ($DryRun) {
        Write-Host ('DRY-RUN> docker ' + ($buildArgs -join ' '))
    } else {
        $sw = [System.Diagnostics.Stopwatch]::StartNew()
        & docker @buildArgs
        $sw.Stop()
        if ($LASTEXITCODE -ne 0) {
            throw "docker build 失败（退出码 $LASTEXITCODE），耗时 $([math]::Round($sw.Elapsed.TotalMinutes,1)) 分钟"
        }
        Write-Host ("[1/3] 镜像构建完成，耗时 {0} 分 {1} 秒" -f [math]::Floor($sw.Elapsed.TotalMinutes), $sw.Elapsed.Seconds)
    }
} else {
    Write-Host "[1/3] 已指定 -SkipBuild，使用已有镜像 $Tag"
}

# ---- [2/3] docker run：仓库只读 + 两个命名卷，执行入口脚本 ----
# 缓存全部收进 Docker 命名卷：iaa-android-app(→/build/app，构建目录，.buildozer
# 跨次增量) 与 iaa-android-cache(→/root，NDK/SDK/wheels/cargo/rustup/buildozer/gradle)。
# 产物留在容器内 /artifacts，跑完后 docker cp 取回再删除容器（try/finally 兜底）。
# 不再用 --rm：容器需要有名字供 docker cp / docker rm 使用。
# -v 值不要手写包引号：PowerShell 原生参数传递会把字面引号原样传给 docker，
# 卷 spec 解析会把尾随引号当 mode 解析（invalid mode: .../android-sdk"），
# 导致 exit 125。路径含空格时 splatting 会自动加引号，无需手包。
$runArgs = @('run', '--name', $Container, '--platform', $Platform)
$runArgs += '-e', "P4A_ARCH=$Arch"
$runArgs += '-e', "ANDROID_API=$Api"
$runArgs += '-e', "PYSIDE_VERSION=$PysideVersion"
$runArgs += '-e', "ANDROID_NDK=$NdkVersion"
$runArgs += '-v', "${repo}:/workspace:ro"
$runArgs += '-v', 'iaa-android-app:/build/app'
$runArgs += '-v', 'iaa-android-cache:/root'
$runArgs += $Tag, '/docker/entrypoint-build.sh'

Write-Host ''
Write-Host '[2/3] 启动构建容器（NDK/SDK/wheels 已在命名卷则跳过下载）...'
Write-Host ('  命令: docker ' + ($runArgs -join ' '))
$runStatus = 0
if (-not $DryRun) {
    try {
        & docker @runArgs
        $runStatus = $LASTEXITCODE
    } finally {
        # 无论成败都取回产物并清理容器（try/finally 保证 docker rm 一定执行）
        Write-Host ''
        Write-Host '[3/3] docker cp 取回容器内 /artifacts 产物 -> 输出目录...'
        try {
            & docker cp "${Container}:/artifacts/." $OutDir
            if ($LASTEXITCODE -ne 0) {
                Write-Host '  docker cp 取回产物失败（容器可能未启动），忽略并继续清理。' -ForegroundColor Yellow
            } else {
                Write-Host '  docker cp 完成。'
            }
        } catch {
            # cp 异常（如 docker 不可用）不掩盖原始构建结果，仅提示
            Write-Host '  docker cp 取回产物失败（容器可能未启动），忽略并继续清理。' -ForegroundColor Yellow
        } finally {
            & docker rm -f $Container 2>$null | Out-Null
            Write-Host ('  已清理容器 ' + $Container)
        }
    }
    if ($runStatus -ne 0) {
        Write-Host ("容器构建失败（退出码 {0}），详见上方日志。" -f $runStatus) -ForegroundColor Red
        Write-Host '提示：若报"drive not shared / path not mounted"，请在 Docker Desktop 设置里共享对应盘符。' -ForegroundColor Yellow
        exit 1
    }
} else {
    Write-Host 'DRY-RUN: 不真正执行容器。'
    Write-Host ''
    Write-Host '[3/3] DRY-RUN 将执行：'
    Write-Host ('  docker cp ' + "${Container}:/artifacts/." + ' ' + $OutDir)
    Write-Host ('  docker rm -f ' + $Container)
    Write-Host 'DRY-RUN: 结束。'
}

# ---- [3/3] 输出产物（非 dry-run 时 APK 已由 finally 里的 docker cp 落地）----
Write-Host ''
Write-Host '构建结束，产物如下：'
$apks = Get-ChildItem -Path $OutDir -Filter '*.apk' -File -ErrorAction SilentlyContinue
if ($apks) {
    foreach ($a in $apks) {
        Write-Host ("  APK -> {0}  ({1} MB)" -f $a.FullName, [math]::Round($a.Length / 1MB, 1)) -ForegroundColor Green
    }
    Write-Host ''
    Write-Host '安装到模拟器示例：'
    Write-Host ('  adb install -r "{0}"' -f $apks[0].FullName)
} else {
    Write-Host '  未在输出目录找到 *.apk —— 构建可能失败或产物路径不一致，请查看上方日志。' -ForegroundColor Yellow
}