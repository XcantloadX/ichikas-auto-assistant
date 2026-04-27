# Ichika's Auto Assistant 一歌小助手

<small>相关项目：[ 
    <a href="https://github.com/XcantloadX/kotones-auto-assistant">琴音小助手</a>、
    <a href="https://github.com/XcantloadX/kotonebot">kotonebot 自动化框架</a>
]
</small>

<center><img src="./assets/icon_round.png" width="128"/></center>


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

## CLI 上手
除了 GUI 外，iaa 也支持以命令行方式调用。

```bash
# 查看帮助信息
iaa-cli.exe --help
# 查看可用任务
iaa-cli.exe list tasks
# 按配置执行常规任务
iaa-cli.exe run
# 显式执行一个或多个任务
iaa-cli.exe invoke start_game solo_live
# 执行单个任务
iaa-cli.exe invoke main_story
# 带参数执行自动演出
iaa-cli.exe invoke auto_live --count-mode specify --count 10 --loop-mode list --auto-mode game_auto
```

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
python -m iaa.main ... # 参数参考上面的 CLI 上手
```

（后续文档暂时可以参考 琴音小助手 的开发文档）

### 打包
执行 `just build` 后，`dist_app` 目录中会同时包含：
* `iaa.exe`：GUI 入口
* `iaa-cli.exe`：CLI 入口

### 发布
见 [doc/LOCAL_RELEASE.md](./doc/LOCAL_RELEASE.md)。

### 贡献
TODO

## 开源协议
一歌小助手以 GPLv3 协议开源。
