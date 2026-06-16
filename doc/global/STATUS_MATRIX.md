# Global / EN Status Matrix

This matrix separates **stock upstream behavior** from **local candidate patch
behavior**. Do not collapse those two columns. A flow that works with local
patches is still not stock Global support.

## Test environment used for the first investigation

| Detail | Value |
| --- | --- |
| IAA version / commit | `26.05b2` / `4478949` |
| Global game version | `5.3.5.Luna` |
| Test dates | 2026-06-14 to 2026-06-16 |
| Host OS | Windows 10 Home 64-bit, build 19045 |
| Emulator | MuMu Player Global `5.30.2.3616` / MuMu 12 v5, instance `0` |
| Game package | `com.sega.ColorfulStage.en` |
| Game language | English |
| IAA UI language | Chinese |
| Capture backends tested | Nemu IPC, ADB, Scrcpy |
| Working capture backends in this environment | ADB and Scrcpy |
| Problematic backend in this environment | Nemu IPC returned all-white Global frames |
| Important caveat | Temporary local workarounds were used for some probes. They are not stock support. |

## Configuration and device layer

| Area | Stock Global status | Candidate / local finding | Evidence / blocker |
| --- | --- | --- | --- |
| Desktop GUI launch | Works | N/A | GUI opened on Windows. UI is currently Chinese. |
| Global / EN server option | Known broken | Not implemented | Server selector showed JP, TW, CN only. |
| Global package mapping | Known broken | Local override launched Global | Stock JP profile targets `com.sega.pjsekai`; Global package is `com.sega.ColorfulStage.en`. |
| MuMu Player Global discovery | Known broken in tested setup | Local `.venv` registry fallback worked | MuMu Player Global used `MuMuPlayerGlobal` registry key; stock kotonebot checked `MuMuPlayer`. |
| MuMu startup | Works after discovery workaround | N/A | With **Check and start** enabled, runtime ADB port was assigned. |
| Nemu IPC capture | Known broken in tested setup | Not fixed | Returned all-white 960 x 540 frames while Global Unity activity was focused. |
| ADB capture | Works in tested setup | N/A | Captured visible Global loading/title frames at 960 x 540. |
| Scrcpy capture | Works in tested setup | N/A | Captured visible Global title screen at 960 x 544, scaled for recognition. |
| `start_game` | Known broken | Local guard prevented blind clicks | Global launched, then blank white loading frame caused `go_home()` fallback clicks at `(1, 367)`. |

## Resource compatibility

| Resource / UI area | Stock JP resource on Global | Candidate / EN status | Notes |
| --- | --- | --- | --- |
| `Login.IconNotification` | Matched | Can likely reuse after retest | Matched Global News dialog. |
| `Daily.ButtonGift` | Matched | Can likely reuse after retest | Matched unobstructed Global home / area frame. |
| `Daily.ButtonMission` | Matched | Can likely reuse after retest | Matched unobstructed Global home / area frame. |
| `Hud.IconCrystal` | Matched | Can likely reuse after retest | Matched unobstructed Global home / area frame. |
| `Login.ButtonMenu` | Matched | Can likely reuse after retest | Matched unobstructed Global home / area frame. |
| `Hud.ButtonLive` | Did not match | EN `SHOW` resource needed | Global bottom navigation says `SHOW`, not `LIVE`. |
| `Hud.ButtonStory` | Did not match | EN or non-text detector needed | Failed on recorded Global home frame. |
| `Map.IconNewAreaConvo` | Matched | Can likely reuse after retest | Matched visible Global `NEW!` badges. |
| `Scene.Intersection.BuildingLogo` | Matched | Can likely reuse after retest | Matched Global Scramble Crossing frame. |
| `Scene.Intersection.IconCm` | Matched | Can likely reuse after retest | Matched Global `Watch Ads` bubble across shifted viewports. |
| `Cm.ButtonPlayCm` | Did not match | EN `Watch Ad` resource needed | English ad-selection buttons differ. |
| `Cm.TextAwardClaimed` | Did not match | EN reward text resource needed | Global overlay uses English `Claimed rewards.` text. |
| CM ad close / skip | Did not match tested provider | Unknown | Provider redirected to Google Play; ad controls vary. |
| `Hud.ButtonClaimAll` | Did not match Missions | EN `Claim All` resource needed | JP template scored below threshold on Global Missions. |
| Gift confirmation dialog | Not handled by baseline task | EN `CommonDialog` resources worked | Global uses persistent `Claimed the following items.` dialog. |
| Challenge character prompt | Did not match | EN text resource needed | Global prompt is `Please select a character.` |
| Score-rank completion | Did not match threshold | EN `SCORE RANK` resource needed | Required for post-show wait in tested flows. |

## Automation task status

| Task / flow | Stock Global status | Candidate / local status | Notes |
| --- | --- | --- | --- |
| `gift` | Known broken | Candidate verified for one fresh two-item claim | Stock task does not dismiss Global confirmation dialog after successful claim. |
| `mission_rewards` | Known broken | Candidate verified for no-reward and one fresh claim path | Stock task cannot recognize English `Claim All` and does not dismiss persistent reward overlay. |
| `solo_live` | Blocked / unknown | Candidate verified for one bounded list-mode game-Auto show | Requires Global package mapping and EN resource variant. Other modes untested. |
| `auto_live` | Blocked / unknown | Candidate verified for one bounded list-mode game-Auto run | One explicit count run completed and returned home. Scheduled behavior untested. |
| `challenge_live` | Known broken | Partial local compatibility | Completed one Minori Auto Play run only with temporary English character-prompt and score-rank resources. Weekly reward untested. |
| `area_convos` | Known broken / unknown | Partial local compatibility | Existing JP map/story menu resources matched, but English skip flow needs EN resources. Current task can falsely report completion. |
| `cm` | Known broken / unknown | Partial candidate evidence | Baseline cannot recognize English `Watch Ad`; candidate handled one reward and one ambiguous return. Provider coverage incomplete. |
| `activity_story` | Unknown | Partial candidate evidence | World Link route and no-unread branch worked. Unread story chain from home remains unverified. |
| `event_shop` | Unknown | Partial candidate evidence | World Link shop scan worked with no purchase. Ordinary event inventory and purchase paths unverified. |
| `main_story` | Untested | Not recommended as smoke test yet | JP `Hud.ButtonStory` failed on current Global home frame. |
| Scheduled regular run | Untested | Not recommended yet | Test individual flows first. |
| CLI task discovery | Works | N/A | Task listing is side-effect free. |
| CLI task invocation | Untested for stock Global | Use bounded local probes only | Stock tasks perform navigation/account actions. |
| GUI task launch | Untested for stock Global | Not recommended yet | Global profile is not selectable. |

## Safe next tests

Prefer low-risk, bounded, reproducible tests:

1. Verify Global / EN profile selection after package mapping is implemented.
2. Retest ADB and Scrcpy capture on a clean Global title/home frame.
3. Confirm home recognition using the EN `SHOW` resource.
4. Run `gift` with a small pending gift set.
5. Run `mission_rewards` with one known pending badge.
6. Run `solo_live` or `auto_live` only with explicit count `1` and a known start page.
7. Retest Challenge Live only when a daily attempt is naturally available.
8. Retest stories and event shop only with clear account-state expectations.
9. Retest CM last because it consumes daily ad opportunities and provider paths vary.

## Do not mark as supported yet

Do not mark the following as fully supported from the current evidence:

- Global / EN as a selectable stock server.
- Startup from app closed to recognized home.
- Nemu IPC capture on MuMu Player Global.
- CM / advertisement provider cleanup.
- Full scheduled regular-task execution.
- Story and event shop completion across all event types.
- Challenge weekly reward selection.
- Any task that only worked through temporary local `.venv` overrides.
