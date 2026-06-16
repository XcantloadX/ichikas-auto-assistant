# Ichika's Auto Assistant 一歌小助手

<small>Related projects: [
    <a href="https://github.com/XcantloadX/kotones-auto-assistant">Kotone's Auto Assistant</a>,
    <a href="https://github.com/XcantloadX/kotonebot">kotonebot automation framework</a>
]
</small>

<center><img src="./assets/icon_round.png" width="128"/></center>


Ichika's Auto Assistant, abbreviated as IAA, is an automation script for daily tasks in *Project SEKAI: Colorful Stage!*. It is built on the kotonebot automation framework and uses OpenCV to detect on-screen images for automation.

> [!IMPORTANT]  
> Ichika's Auto Assistant is **only intended for daily task automation**. It cannot and will not support any cheat-like functionality, such as automated shows for ranking purposes.

## Roadmap

* Reward collection
    - [x] Claim gifts from the gift box
    - [ ] Claim mission rewards, including pass rewards
* Watch ads / CM
    - [x] Ads at Scramble Crossing
    - [ ] Ads in the music shop
* Auto live
    - [x] Basic functionality
    - [x] Farm live count / leader count (`LIVE FINISH`)
    - [x] Farm `CLEAR` count, such as completing 50 shows
    - [x] Farm song-clear count, such as clearing 10 different songs
* Multi-server support
  - [x] Taiwan server
  - [ ] Mainland China server
  - [ ] International / Global server
* Auto story
    - [x] Auto main story
    - [x] Auto current event story
* Area conversations
* Virtual live
* MySekai auto collection
* Native mobile support

## Disclaimer

By downloading and using Ichika's Auto Assistant, you confirm that you have read and agree to the following disclaimer:

1. This project is **not cheat software** and does not modify any game content.
2. You are solely responsible for any risks caused by using this project, including but not limited to **account bans**.
3. This project is not affiliated with CraftEgg, Crypton Future Media, Colorful Palette, SEGA, ByteDance, or Ariel Network.
4. This project is provided free of charge and is **not allowed to be used for commercial purposes**, such as selling packaged builds of this project.
5. All game assets used by this project, if any, come from SekaiViewer.

By continuing to download, install, or use this project, you confirm that you have fully read, understood, and agreed to accept all of the above risks and terms. If you do not agree, stop using this project immediately and delete all related files.

## CLI Quick Start

In addition to the GUI, IAA can also be used from the command line.

```bash
# Show help
iaa-cli.exe --help
# List available tasks
iaa-cli.exe list tasks
# Run regular tasks according to the current configuration
iaa-cli.exe run
# Explicitly run one or more tasks
iaa-cli.exe invoke start_game solo_live
# Run a single task
iaa-cli.exe invoke main_story
# Run auto live with arguments
iaa-cli.exe invoke auto_live --count-mode specify --count 10 --loop-mode list --auto-mode game_auto
```

## Development

Install `just` first, then run:

```powershell
# Set up the Python environment
just setup
# Build resource files
just res

# Start the GUI
uv run launch_desktop.py
# Or start "main (GUI)" from VS Code

# Start the CLI
python -m iaa.main ... # See the CLI Quick Start section above for arguments
```

For now, later documentation can refer to Kotone's Auto Assistant development documentation.

### Packaging

After running `just build`, the `dist_app` directory will contain both:

* `iaa.exe`: GUI entry point
* `iaa-cli.exe`: CLI entry point

### Release

See [doc/LOCAL_RELEASE.md](./doc/LOCAL_RELEASE.md).

### Contributing

TODO

## License

Ichika's Auto Assistant is open-sourced under the GPLv3 license.
