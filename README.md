# Ichika's Auto Assistant 一歌小助手
<small><center>相关项目：[ 
    <a href="https://github.com/XcantloadX/kotones-auto-assistant">琴音小助手</a>、
    <a href="https://github.com/XcantloadX/kotonebot">kotonebot 自动化框架</a>
]
</center></small>


一歌小助手（简称 iaa）是一款适用于《世界计划：多彩舞台》的自动化日常脚本，基于 kotonebot 自动化框架编写而成，使用 OpenCV 对屏幕画面进行检测来实现自动化。

> [!IMPORTANT]  
> 一歌小助手 iaa **只用于清日常**，不可以也不会支持任何外挂性质的功能（如以冲榜为目的的自动演出）。

## 功能与 TODO
近期规划（按顺序）：
* 奖励领取
    - [ ] 领取邮箱
    - [ ] 领取任务奖励（包括通行证）
* 看广告（CM）
    - [x] 交叉路口处的广告
    - [ ] 音乐商店的广告
* 自动演出
    - [x] 基本功能
    - [ ] 刷演出次数/小队长次数（LIVE FINISH）
    - [ ] 刷 CLEAR 次数（完成 50 次演出）
    - [x] 刷 CLEAR 歌曲次数（完成 10 首不同歌曲）
* 国服支持
* 手机原生运行


远期规划（按顺序）：
* 自动地图对话
* 自动剧情
    * 自动主线剧情
    * 自动档期剧情
* 台服与国际服支持
* 自动看演唱会
* MySekai 自动采集（待定）

## 声明
下载并使用一歌小助手即代表你已阅读并同意下述声明：
1. 本项目**并非外挂软件**，不会修改游戏内容。
2. 你需要自行承担使用本项目所带来的任何风险，如**账号封禁**等。
3. 本项目与 CraftEgg、克理普敦未来媒体、Colorful Palette、SEGA、朝夕光年、艾瑞尔网络无关。
4. 本项目免费提供，且**禁止用于商业用途**（如售卖本项目成品）。
5. 本项目用到的所有游戏资源（如有）均来自 SekaiViewer。

继续下载、安装或使用本项目，即表示你已完全阅读、理解并同意承担以上所有风险和条款。如果你不同意，请立即停止使用并删除本项目的所有相关文件。

## 源码执行
```bash
# 如果你没安装 uv 需要先安装
uv sync
uv pip install -e .
uv run tools/make_resources.py
uv run iaa/main.py
```

## Flask API + Flutter 界面
项目已提供新的 Flask API 与 Flutter 界面（桌面友好，兼顾移动端），功能点来源于旧 Tkinter 界面，详见 `doc/gui_features.md`。

1. 启动 API（默认 5000 端口）：
   ```bash
   uv run launch_api.py
   ```
2. 运行 Flutter 界面（需要本地安装 Flutter SDK）：
   ```bash
   cd flutter_client
   flutter pub get
   flutter run -d chrome --dart-define=IAA_API_BASE=http://localhost:5000/api
   ```

## 开发
TODO

（暂时可以参考 琴音小助手 的开发文档）

## 贡献
TODO

## 开源协议
一歌小助手以 GPLv3 协议开源。
