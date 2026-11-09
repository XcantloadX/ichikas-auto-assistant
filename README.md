# Ichika's Auto Assistant 一歌小助手

[中文](./README.md) | [English](./README.en.md)

<small>相关项目：[ 
    <a href="https://github.com/XcantloadX/kotones-auto-assistant">琴音小助手</a>、
    <a href="https://github.com/XcantloadX/kotonebot">kotonebot 自动化框架</a>
]
</small>

<center><img src="./iaa/assets/icon_round.png" width="128"/></center>


一歌小助手（简称 iaa）是一款适用于《世界计划：多彩舞台》的自动化日常脚本，基于 kotonebot 自动化框架编写而成，使用 OpenCV 对屏幕画面进行检测来实现自动化。

> [!IMPORTANT]  
> 一歌小助手 iaa **只用于清日常**，不可以也不会支持任何外挂性质的功能（如以冲榜为目的的自动演出）。

## 路线图
* 奖励领取
    - [x] 领取邮箱
    - [ ] 领取任务奖励（包括通行证）
* 看广告（CM）
    - [x] 交叉路口处的广告
    - [ ] 音乐商店的广告
* 自动演出
    - [x] 基本功能
    - [x] 刷演出次数/小队长次数（LIVE FINISH）
    - [x] 刷 CLEAR 次数（完成 50 次演出）
    - [x] 刷 CLEAR 歌曲次数（完成 10 首不同歌曲）
* 多服务器支持
  - [x] 台服
  - [ ] 国服
  - [ ] 国际服
* 自动剧情
    - [x] 自动主线剧情
    - [x] 自动当期剧情
* 地图对话
* 演唱会
* MySekai 自动采集
* 手机原生运行

## 声明
下载并使用一歌小助手即代表你已阅读并同意下述声明：
1. 本项目**并非外挂软件**，不会修改游戏内容。
2. 你需要自行承担使用本项目所带来的任何风险，如**账号封禁**等。
3. 本项目与 CraftEgg、克理普敦未来媒体、Colorful Palette、SEGA、朝夕光年、艾瑞尔网络无关。
4. 本项目免费提供，且**禁止用于商业用途**（如售卖本项目成品）。
5. 本项目用到的所有游戏资源（如有）均来自 SekaiViewer。

继续下载、安装或使用本项目，即表示你已完全阅读、理解并同意承担以上所有风险和条款。如果你不同意，请立即停止使用并删除本项目的所有相关文件。

## 安装

需要 Python 3.10（Windows）。

```bash
pip install ichikas-auto-assistant
```

普通用户推荐使用 [LmmPyLauncher](https://github.com/kotonebot/LmmPyLauncher) 启动器：双击 exe 即可自动安装 Python 环境、安装并自动更新本程序，见[下方集成说明](#通过-lmmpylauncher-分发)。

## 使用

程序包含图形界面与命令行两种方式，统一从 `iaa` 命令进入。配置与日志保存在**当前工作目录**下的 `conf/` 与 `logs/` 中（启动器会自动把工作目录设为 exe 所在目录）。

### 图形界面

```bash
iaa gui
```

### 命令行

```bash
# 查看帮助信息
iaa --help
# 查看可用任务
iaa list tasks
# 按配置执行常规任务
iaa run
# 显式执行一个或多个任务
iaa invoke start_game solo_live
# 执行单个任务
iaa invoke main_story
# 带参数执行自动演出
iaa invoke auto_live --count-mode specify --count 10 --loop-mode list --auto-mode game_auto
```

也可以用 `python -m iaa` 代替 `iaa`，两者等价。

## 开发
首先安装 just，然后：
```powershell
# 配置 Python 环境
just setup
# 构建资源文件
just res

# 启动 GUI
uv run launch_desktop.py
# 或使用 VSCode 启动 「main (GUI)」

# 启动 CLI
uv run launch_cli.py ... # 参数参考上面的 使用 -> 命令行
```

（后续文档暂时可以参考 琴音小助手 的开发文档）

### 构建与发布
```bash
# 构建 wheel（先清理 __pycache__、生成资源，再构建），产物在 dist/ 下
just wheel

# 编译启动器 exe，产物 dist/iaa.exe（GUI）与 dist/iaa-cli.exe（CLI），需 Rust 工具链
just launcher

# 两者一起
just build
```

发布：在 GitHub Actions 手动触发 **Publish** 工作流，它一次产出全部发布物，两个开关默认都勾选：

| 开关 | 作用 |
|---|---|
| `publish_pypi` | 把当次构建的 wheel 发到 PyPI（需已注册 `ichikas-auto-assistant` 项目并配置 Trusted Publisher） |
| `publish_release` | 创建**草稿** GitHub Release，tag/标题为 `v<iaa 版本>`，附件为 `launcher.v<launcher 版本>.zip`（内含 `iaa.exe` 与 `iaa-cli.exe`）与该版本的 wheel |

构建阶段总是同时产出 wheel 与启动器，因此即使两个开关都不勾，也能从这次运行的 artifact 里拿到产物。

版本号有两个，互不影响：**iaa 版本**来自 `iaa/__meta__.py` 的 `__VERSION__`（决定 tag、标题与 wheel 版本，发版前必须先改它，PyPI 不接受同一版本重复上传）；**launcher 版本**来自 `bootstrap/LmmPyLauncher/Cargo.toml` 的 `[package] version`（只决定 zip 附件名，启动器独立演进，iaa 升版本时它通常不变）。

Release 说明由 `tools/release_notes.py` 生成，结构固定为「更新说明 → 下载说明 → 完整历史」：`doc/CHANGELOG.md` 中 `## v<iaa 版本>` 的段落、固定的下载提示、上一发布 tag 到 HEAD 的提交列表。可本地预览：

```bash
python tools/release_notes.py version            # iaa 版本
python tools/release_notes.py launcher-version   # launcher 版本
python tools/release_notes.py body --output body.md
```

草稿创建后需到 Releases 页面人工确认再点 Publish。

### 通过 LmmPyLauncher 分发

分发给用户的是两个 exe，职责分离：

| 产物 | 用途 |
|---|---|
| `dist/iaa.exe` | 图形界面，双击即用；不接受命令行参数 |
| `dist/iaa-cli.exe` | 命令行，安装进度与任务输出直连控制台，参数与退出码透传 |

两者放在同一目录时共享 `python-3.10.11/`、`conf/`、`logs/`，只需安装/更新一次。

启动器源码以 git submodule 形式锁定在 `bootstrap/LmmPyLauncher`，编译期配置固定为 `bootstrap/launcher/launcher.json`：

```json
{
  "app_name": "一歌小助手",
  "python_version": "3.10.11",
  "python_path": "python-3.10.11\\python.exe",
  "install_packages": ["ichikas-auto-assistant"],
  "uninstall_packages": [],
  "entry_point": "iaa",
  "launch_command": "{python} -m {entry_point} gui",
  "launch_command_cli": "{python} -m {entry_point} {extra_args}",
  "icon": "icon.ico",
  "logoPath": "logo.png"
}
```

`launch_command` 供 GUI 版使用（不含 `{extra_args}`，即 GUI exe 不接受参数）；`launch_command_cli` 供 CLI 版使用，`{extra_args}` 会在该位置展开为用户传入的参数。

`just launcher` 依次执行：初始化 submodule → 以 `LMM_LAUNCHER_JSON` 指向上述配置 `cargo build --release --bins` → 把两个产物分别复制为 `dist/iaa.exe`、`dist/iaa-cli.exe`。启动器仓库的源码树不会被写入任何文件，因此升级启动器只需改动 submodule 的检出提交：

```bash
git -C bootstrap/LmmPyLauncher fetch --tags
git -C bootstrap/LmmPyLauncher checkout v0.1.x
git add bootstrap/LmmPyLauncher   # 提交新的子模块指针
```

`bootstrap/launcher/` 下的 `icon.ico`、`logo.png` 分别是 `iaa/assets/ichika.ico`、`iaa/assets/icon.png` 的副本（启动器按配置文件所在目录解析这两个相对路径），更换图标时两处需同步。

编译产物约 1GB，若仓库所在磁盘空间紧张，可用 `CARGO_TARGET_DIR` 把 target 目录挪到别的盘：

```powershell
$env:CARGO_TARGET_DIR = "D:\build\iaa-launcher"; just launcher
```

#### 命令行用法

`iaa-cli.exe` 不封装任何命令：命令行内容**全部原样**交给 `iaa`，退出码也原样返回，可直接嵌进脚本：

```powershell
dist\iaa-cli.exe list tasks
dist\iaa-cli.exe run
dist\iaa-cli.exe invoke auto_live --count-mode specify --count 10
dist\iaa-cli.exe --debug run > out.txt   # 输出可重定向
```

CLI 版**不承担任何环境准备**——不探镜像、不检查更新、不安装包、不部署 Python，找到解释器就直接启动，因此启动约 0.5 秒。**首次使用必须先双击一次 `iaa.exe`** 完成安装；否则 CLI 会提示「主程序尚未安装，请先运行图形界面版」并以退出码 1 结束。

#### 运行时行为

- 启动器会把工作目录切到 exe 所在目录，因此 `conf/`、`logs/` 落在 exe 旁边，与源码运行的目录约定一致。
- 每次启动先对比 PyPI 上的最新版本，有更新则自动 `pip install`。
- `--skip-update` 跳过更新检查；`--install-version=<ver>` 安装指定版本。

#### 已知限制

1. **包尚未发布到 PyPI 时**，启动会因查不到版本而失败。此时用本地 wheel 验证整条链路：

   ```powershell
   dist\iaa.exe --install-from-package=dist\ichikas_auto_assistant-26.10.1-py3-none-any.whl
   ```

   该参数安装完成后直接启动，并隐含跳过更新检查。

2. **Python 环境完全由启动器自己准备**：`launcher.json` 的 `python_path`（必填，相对 exe 目录）指向 `python-3.10.11\python.exe`。该文件不存在时启动器会提示并下载 embed 版 Python 到它的父目录，**不会**使用系统 PATH 上的 Python——所以不会因为机器上装了 3.11/3.13 而装不上，也不会污染用户的全局 site-packages。若要随包分发自己的 Python 发行版，把 `python_path` 指向那份发行版的 `python.exe` 即可（目录与版本不受 `python_version` 限制）。

3. **两个 exe 不要同时运行**：它们共享 `python-3.10.11/` 与 `conf/`，同时启动可能在更新包或写配置时互相干扰。
4. **GUI 版不接受参数**：传给 `dist\iaa.exe` 的未知开关会被丢弃，位置参数（如 `run`）会直接报错退出。命令行场景请用 `dist\iaa-cli.exe`。

### 贡献
TODO

## 开源协议
一歌小助手以 GPLv3 协议开源。
