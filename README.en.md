# Ichika's Auto Assistant

[Chinese](./README.md) | [English](./README.en.md)

<small>Related projects: [
    <a href="https://github.com/XcantloadX/kotones-auto-assistant">Kotone's Auto Assistant</a>,
    <a href="https://github.com/XcantloadX/kotonebot">kotonebot automation framework</a>
]
</small>

<center><img src="./iaa/assets/icon_round.png" width="128"/></center>

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

## Installation

Python 3.10 (Windows) is required.

```bash
pip install ichikas-auto-assistant
```

For regular users, the [LmmPyLauncher](https://github.com/kotonebot/LmmPyLauncher) launcher is recommended: double-click the exe and it will automatically set up Python, install and auto-update this program. See the [LmmPyLauncher section](#distributing-via-lmmpylauncher) below.

## Usage

The program provides both a GUI and a command line, unified under the `iaa` command. Configuration and logs are stored in `conf/` and `logs/` under the **current working directory** (the launcher sets the working directory to the exe location automatically).

### GUI

```bash
iaa gui
```

### CLI

```bash
# Show help
iaa --help
# List available tasks
iaa list tasks
# Run regular tasks according to the config
iaa run
# Explicitly run one or more tasks
iaa invoke start_game solo_live
# Run a single task
iaa invoke main_story
# Run auto live with parameters
iaa invoke auto_live --count-mode specify --count 10 --loop-mode list --auto-mode game_auto
```

`python -m iaa` is equivalent to `iaa`.

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
uv run launch_cli.py ... # See Usage -> CLI above for arguments
```

For now, later development documentation can refer to Kotone's Auto Assistant.

### Building and releasing

```bash
# Build the wheel (cleans __pycache__, generates resources, then builds); output goes to dist/
just wheel

# Build the launcher exes -> dist/iaa.exe (GUI) and dist/iaa-cli.exe (CLI); needs the Rust toolchain
just launcher

# Both
just build
```

Releasing: trigger the **Publish** workflow manually in GitHub Actions. It produces every artifact in
one run, and both switches are on by default:

| Switch | Effect |
|---|---|
| `publish_pypi` | Upload the wheel built in this run to PyPI (requires registering `ichikas-auto-assistant` on PyPI and configuring the Trusted Publisher first) |
| `publish_release` | Create a **draft** GitHub Release tagged/titled `v<iaa version>` with `launcher.v<launcher version>.zip` (containing `iaa.exe` and `iaa-cli.exe`) and the matching wheel attached |

The build stage always produces both the wheel and the launcher, so even with both switches off the
run's artifacts hold everything.

There are two independent versions: the **iaa version** (`__VERSION__` in `iaa/__meta__.py`, which
drives the tag, title and wheel version — bump it before releasing, since PyPI rejects re-uploading an
existing version) and the **launcher version** (`[package] version` in
`bootstrap/LmmPyLauncher/Cargo.toml`, which only names the zip — the launcher evolves on its own
schedule and usually stays put across iaa releases).

Release notes are generated by `tools/release_notes.py` in a fixed order — release notes, download
note, full history — from the `## v<iaa version>` section of `doc/CHANGELOG.md`, a fixed download note,
and the commit list between the previous release tag and HEAD. Preview locally:

```bash
python tools/release_notes.py version            # iaa version
python tools/release_notes.py launcher-version   # launcher version
python tools/release_notes.py body --output body.md
```

The draft must be published manually from the Releases page.

### Distributing via LmmPyLauncher

Two exes are shipped, with distinct roles:

| Artifact | Purpose |
|---|---|
| `dist/iaa.exe` | GUI, double-click to run; takes no command-line arguments |
| `dist/iaa-cli.exe` | CLI, install progress and task output go straight to the console, arguments and exit code pass through |

Placed in the same directory they share `python-3.10.11/`, `conf/` and `logs/`, so installation and
updates happen once.

The launcher source is pinned as a git submodule at `bootstrap/LmmPyLauncher` (currently 0.1.7),
and its compile-time config lives at `bootstrap/launcher/launcher.json`:

```json
{
  "app_name": "一歌小助手",
  "python_version": "3.10.11",
  "python_dist_dir": "",
  "install_packages": ["ichikas-auto-assistant"],
  "uninstall_packages": [],
  "entry_point": "iaa",
  "launch_command": "{python} -m {entry_point} gui",
  "launch_command_cli": "{python} -m {entry_point} {extra_args}",
  "icon": "icon.ico",
  "logoPath": "logo.png"
}
```

`launch_command` serves the GUI build (no `{extra_args}`, i.e. the GUI exe accepts no arguments);
`launch_command_cli` serves the CLI build, where `{extra_args}` expands to whatever the user passed.

`just launcher` initializes the submodule, runs `cargo build --release --bins` with
`LMM_LAUNCHER_JSON` pointing at that config, and copies both binaries to `dist/iaa.exe` and
`dist/iaa-cli.exe`. Nothing is written into the launcher repository, so upgrading the launcher only
means moving the submodule checkout:

```bash
git -C bootstrap/LmmPyLauncher fetch --tags
git -C bootstrap/LmmPyLauncher checkout v0.1.x
git add bootstrap/LmmPyLauncher   # commit the new submodule pointer
```

`icon.ico` and `logo.png` under `bootstrap/launcher/` are copies of `iaa/assets/ichika.ico` and
`iaa/assets/icon.png` (the launcher resolves both relative to the config file directory), so keep
them in sync when the artwork changes.

The build produces roughly 1 GB of intermediates. If the repository drive is short on space, move
the target directory elsewhere:

```powershell
$env:CARGO_TARGET_DIR = "D:\build\iaa-launcher"; just launcher
```

#### Command-line usage

`iaa-cli.exe` wraps nothing: **every** argument is forwarded verbatim to `iaa`, and its exit code
becomes the process exit code — safe to embed in scripts:

```powershell
dist\iaa-cli.exe list tasks
dist\iaa-cli.exe run
dist\iaa-cli.exe invoke auto_live --count-mode specify --count 10
dist\iaa-cli.exe --debug run > out.txt   # output can be redirected
```

The CLI build performs **no environment setup** — no mirror probing, no update check, no package
install, no Python deployment. It locates an interpreter and starts, which takes about 0.5 s.
**Double-click `iaa.exe` once before using it**; otherwise the CLI reports "not installed, run the
GUI once" and exits with code 1.

#### Runtime behaviour

- The launcher switches the working directory to the exe location, so `conf/` and `logs/` end up
  next to the exe — same convention as running from source.
- Each start compares against the latest version on PyPI and auto-installs updates.
- `--skip-update` skips the update check; `--install-version=<ver>` installs a specific version.

#### Known limitations

1. **Before the package is published to PyPI**, a double-click fails because no version can be
   resolved. Verify the full chain with a local wheel instead:

   ```powershell
   dist\iaa.exe --install-from-package=dist\ichikas_auto_assistant-26.10.1-py3-none-any.whl
   ```

   That flag installs and then launches immediately, and implies `--skip-update`.

2. **Python version constraint**: this package declares `requires-python ~=3.10.0`. The launcher
   prefers the `python-3.10.11` it deployed next to the exe, but falls back to the `python` on
   PATH — if that is 3.11/3.12, pip rejects the install with "no matching distribution". To rule
   this out, ship a Python 3.10 distribution directory alongside the exe and point
   `python_dist_dir` at it (relative to the exe directory).

3. **Do not run both exes at the same time**: they share `python-3.10.11/` and `conf/`, so
   concurrent starts can collide while updating packages or writing config.
4. **The GUI build takes no arguments**: unknown switches passed to `dist\iaa.exe` are dropped, and
   positionals such as `run` abort with an error. Use `dist\iaa-cli.exe` for command-line work.

### Contributing

TODO

## License

Ichika's Auto Assistant is open source under the GPLv3 license.
