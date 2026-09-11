# Ichika's Auto Assistant

[Chinese](./README.md) | [English](./README.en.md)

<small>Related projects: [
    <a href="https://github.com/XcantloadX/kotones-auto-assistant">Kotone's Auto Assistant</a>,
    <a href="https://github.com/XcantloadX/kotonebot">kotonebot automation framework</a>
]
</small>

<center><img src="./assets/icon_round.png" width="128"/></center>

Ichika's Auto Assistant, abbreviated as iaa, is an automation script for daily tasks in Project SEKAI: COLORFUL STAGE!. It is built on the kotonebot automation framework and uses OpenCV to detect the screen state for automation.

> [!IMPORTANT]
> Ichika's Auto Assistant is **only intended for routine daily-task cleanup**. It does not and will not support cheating-related features, such as auto live behavior intended for ranking.

## Roadmap

* Reward claiming
    - [x] Claim gifts
    - [ ] Claim mission rewards, including pass rewards
* Watch ads (CM)
    - [x] Ads at Scramble Crossing
    - [ ] Ads in the music shop
* Auto live
    - [x] Basic functionality
    - [x] Farm live count / leader count (LIVE FINISH)
    - [x] Farm CLEAR count (complete 50 lives)
    - [x] Farm cleared-song count (complete 10 different songs)
* Multi-server support
    - [x] Taiwan server
    - [ ] Mainland China server
    - [ ] Global server
* Auto story
    - [x] Auto main story
    - [x] Auto current event story
* Area conversations
* Virtual live
* MySEKAI auto collection
* Native mobile runtime

## Disclaimer

By downloading and using Ichika's Auto Assistant, you acknowledge that you have read and agree to the following:

1. This project is **not cheat software** and does not modify game content.
2. You are responsible for any risk caused by using this project, including possible **account bans**.
3. This project is not affiliated with CraftEgg, Crypton Future Media, Colorful Palette, SEGA, Nuverse, or Ariel Network.
4. This project is provided for free and is **not allowed for commercial use**, including selling packaged builds of this project.
5. Any game assets used by this project, if any, come from SekaiViewer.

By continuing to download, install, or use this project, you confirm that you have fully read, understood, and agreed to the risks and terms above. If you do not agree, stop using this project immediately and delete all related files.

## CLI Quick Start

Besides the GUI, iaa can also be used from the command line.

```bash
# Show help
iaa-cli.exe --help
# List available tasks
iaa-cli.exe list tasks
# Run regular tasks according to the config
iaa-cli.exe run
# Explicitly run one or more tasks
iaa-cli.exe invoke start_game solo_live
# Run a single task
iaa-cli.exe invoke main_story
# Run auto live with parameters
iaa-cli.exe invoke auto_live --count-mode specify --count 10 --loop-mode list --auto-mode game_auto
```

## Development

Install `just` first, then run:

```powershell
# Configure the Python environment
just setup
# Build resource files
just res

# Start the GUI
uv run launch_desktop.py
# Or use VS Code to start "main (GUI)"

# Start the CLI
python -m iaa.main ... # See CLI Quick Start above for arguments
```

For now, later development documentation can refer to Kotone's Auto Assistant.

### Packaging

After running `just build`, the `dist_app` directory will contain:

* `iaa.exe`: GUI entry point
* `iaa-cli.exe`: CLI entry point

### Release

See [doc/LOCAL_RELEASE.md](./doc/LOCAL_RELEASE.md).

### Contributing

TODO

## License

Ichika's Auto Assistant is open source under the GPLv3 license.
