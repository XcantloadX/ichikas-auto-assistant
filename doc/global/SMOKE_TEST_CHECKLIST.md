# Global / EN Smoke Test Checklist

Use this checklist for future Global / EN compatibility runs.

The goal is not to prove everything works in one run. The goal is to collect
small, reproducible, low-risk evidence without hiding failures.

## Rules

- Test one feature at a time.
- Start from a known page.
- Use bounded runs whenever possible.
- Stop immediately after an unexpected action, page transition, or repeated
  click loop.
- Preserve evidence before retrying.
- Do not run broad scheduled automation until individual tasks are understood.
- Do not claim support from local-only patches unless the implementation under
  review includes those changes.
- Do not use automation for ranking, cheating, account modification, or bypasses.

## Environment

Record this table for every session.

| Detail | Value |
| --- | --- |
| IAA commit / version | |
| Branch / PR | |
| Global game version | |
| Test date and time zone | |
| Tester | |
| Host OS | |
| Emulator / device | |
| Game package | `com.sega.ColorfulStage.en` |
| Game language | English |
| IAA UI language | |
| Capture backend | |
| Screen resolution | |
| Display scaling / DPI | |
| Account state relevant to test | |
| Network/ad-provider notes | |
| Local patches or overrides used | |

## Preparation

- [ ] Confirm the test branch and commit.
- [ ] Confirm whether Global / EN is a real selectable server option.
- [ ] Confirm the target package is `com.sega.ColorfulStage.en`.
- [ ] Confirm the resource variant being used.
- [ ] Confirm the capture backend before task execution.
- [ ] Disable or avoid unrelated tasks.
- [ ] Prepare sanitized screenshot/log output location.
- [ ] Record the starting game page.
- [ ] Record whether the account has pending gifts, missions, ads, challenge attempt, stories, or event-shop targets.

## Connection and capture

- [ ] Launch the IAA GUI.
- [ ] Open the server selector and record available server choices.
- [ ] Launch or connect to MuMu / emulator / device.
- [ ] Confirm foreground package before task execution.
- [ ] Capture one title or home frame through the selected backend.
- [ ] If testing MuMu Player Global, record whether discovery uses the expected registry key.
- [ ] Compare ADB or Scrcpy if Nemu IPC returns blank/white/empty frames.
- [ ] Do not validate templates using a backend that does not expose the rendered Global frame.

## Startup and home recognition

- [ ] Launch Global from a stopped app state.
- [ ] Record loading screens and pop-ups.
- [ ] Confirm whether the startup flow reaches title, News, or home.
- [ ] Confirm that unexpected pages do not trigger blind repeated clicks.
- [ ] Verify home recognition from an unobstructed Global home / area page.
- [ ] Verify the Global `SHOW` navigation control.
- [ ] Verify back/home recovery from at least one safe non-home page.

## Resource checks

Before implementing an EN resource, test whether the JP resource works on a
representative Global frame.

| Resource | Result | Notes |
| --- | --- | --- |
| `Login.IconNotification` | | |
| `Daily.ButtonGift` | | |
| `Daily.ButtonMission` | | |
| `Hud.IconCrystal` | | |
| `Login.ButtonMenu` | | |
| `Hud.ButtonLive` / Global `SHOW` | | |
| `Hud.ButtonStory` | | |
| `Map.ButtonOpenMap` | | |
| `Map.IconNewAreaConvo` | | |
| `Scene.Intersection.IconCm` | | |
| `Cm.ButtonPlayCm` / Global `Watch Ad` | | |
| `Hud.ButtonClaimAll` / Global `Claim All` | | |
| Reward/confirmation dialog text | | |
| Score-rank completion text | | |

Possible results:

- `Matched`
- `Did not match`
- `Needs EN template`
- `Needs non-text detector`
- `Not applicable`
- `Untested`

## Gift test

Run only if a pending gift exists or if testing the empty state.

- [ ] Start from recognized home.
- [ ] Open Gifts.
- [ ] Confirm the Gift page is loaded before clicking.
- [ ] If gifts exist, record visible gift types without exposing account info.
- [ ] Click `Claim All` once.
- [ ] Confirm whether a persistent English confirmation dialog appears.
- [ ] Dismiss the dialog with a tested EN resource.
- [ ] Confirm return home.
- [ ] Run empty-state path only if safe.
- [ ] Record final status.

## Mission rewards test

Run only with a known badge state.

- [ ] Start from recognized home.
- [ ] Open Missions.
- [ ] Wait for the page to load.
- [ ] Record tab count and badged indices.
- [ ] Confirm `Claim All` recognition on the active tab.
- [ ] Claim only expected badged tabs.
- [ ] Dismiss each reward overlay before refreshing the sidebar.
- [ ] Confirm final badge list is empty.
- [ ] Record final status.

## Solo live / auto live test

Use the smallest bounded run.

- [ ] Start from recognized home.
- [ ] Use explicit count `1`.
- [ ] Use a known play mode, preferably game Auto for the first smoke test.
- [ ] Use a known Bonus Energy multiplier.
- [ ] Disable auto-unit setup unless that is the test target.
- [ ] Confirm Show entry through Global `SHOW`.
- [ ] Confirm song selection.
- [ ] Confirm unit selection.
- [ ] Confirm Bonus Energy dialog handling.
- [ ] Confirm Auto Play settings.
- [ ] Watch for the optional Note Speed dialog.
- [ ] Confirm show start.
- [ ] Confirm score-rank / completion detection.
- [ ] Confirm result settlement.
- [ ] Confirm return home.
- [ ] Record energy before/after if relevant.

## Challenge Live test

Only run when a daily attempt is naturally available.

- [ ] Confirm daily indicator before the run.
- [ ] Record selected character.
- [ ] Confirm character-selection prompt recognition.
- [ ] Confirm group and character resources.
- [ ] Use Auto Play if available and appropriate.
- [ ] Confirm score-rank / completion detection.
- [ ] Confirm return home.
- [ ] Confirm daily indicator is absent after the run.
- [ ] If day 7 weekly reward appears, record the flow separately.

## Area conversations test

This changes account state by marking conversations read.

- [ ] Start in a known area.
- [ ] Record whether unread badges are visible.
- [ ] Confirm map entry if testing area traversal.
- [ ] Confirm `NEW!` marker recognition.
- [ ] Enter only the intended area.
- [ ] Confirm story-menu recognition.
- [ ] Confirm English `Skip` and `Skip the story?` resources.
- [ ] After task completion, perform an independent full sweep.
- [ ] Confirm the map no longer shows `NEW!` for the tested area.
- [ ] Do not trust a single `cleared` log line without visual verification.

## Current event story test

This changes story read state and may collect rewards.

- [ ] Record event type.
- [ ] Record whether unread story episodes are available.
- [ ] Confirm event-story entry.
- [ ] Confirm voice-data dialog handling.
- [ ] Confirm story menu and skip resources.
- [ ] Confirm next-episode handling if applicable.
- [ ] Confirm final return to episode list.
- [ ] Separately test the no-unread branch.

## Event shop test

Avoid purchases unless the test target is controlled and expected.

- [ ] Record event type: ordinary, World Link, or other.
- [ ] Confirm event-shop entry resource.
- [ ] Confirm inventory layout.
- [ ] Confirm configured purchase target.
- [ ] Confirm currency availability.
- [ ] If no target is present, verify safe no-purchase exit.
- [ ] If purchase is tested, record confirmation and final currency state.
- [ ] Test insufficient-currency behavior separately.

## CM / advertisement test

CM tests consume daily ad opportunities and may leave the game.

- [ ] Start from Scramble Crossing or the intended CM entry page.
- [ ] Confirm `Watch Ads` bubble recognition.
- [ ] Open the ad-selection page.
- [ ] Record visible reward cards and remaining count.
- [ ] Confirm English `Watch Ad` button recognition.
- [ ] Run only one ad for the first smoke test.
- [ ] Record provider path: in-game, Google Play, Meta/Facebook, browser, or other.
- [ ] Record whether the provider returns automatically.
- [ ] Record whether Home/relaunch recovery was needed.
- [ ] Confirm reward overlay or failure state.
- [ ] Confirm selection-page ambiguous return stops safely.
- [ ] Confirm no indefinite polling.
- [ ] Do not mark full CM support until multiple providers are tested uninterrupted.

## Evidence review

- [ ] Redact player username.
- [ ] Redact user ID.
- [ ] Redact transfer/account screens.
- [ ] Remove local paths or secrets from logs.
- [ ] Include timestamp, task name, branch, and commit.
- [ ] Attach only the smallest useful screenshot set.
- [ ] Mark inconclusive results as `Unknown`.
- [ ] Clearly label local-only workarounds.
