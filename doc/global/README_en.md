# Global / EN Server Support Notes

This folder tracks Global / EN server compatibility work for Ichika's Auto
Assistant (IAA).

IAA is a daily-automation tool for Project Sekai built on kotonebot and screen
recognition. These notes follow the upstream project's safety boundary: Global
support work should focus on ordinary daily automation and must not introduce
cheat-like behavior, ranking automation, account modification, or bypasses.

## Current conclusion

Global / EN is **not supported as a stock configuration yet**.

The current evidence shows that Global support is possible, but it still needs a
proper implementation path. Several local candidate patches worked in one test
environment, but those results must not be treated as official support until
they are reviewed, merged, and reproduced by maintainers.

## Key blockers

| Area | Current finding | Impact |
| --- | --- | --- |
| Server selection | The GUI currently exposes JP, TW, and CN, but not Global / EN. | A valid Global profile cannot be selected. |
| Package mapping | The tested Global package is `com.sega.ColorfulStage.en`; the JP profile targets `com.sega.pjsekai`. | Stock IAA cannot launch the Global app through a normal server setting. |
| Resource variant | The useful Global resource variant is `en`; inherited JP resources are only a baseline. | Global needs tested EN resources for English text and changed navigation labels. |
| Home navigation | JP `Hud.ButtonLive` did not match the Global `SHOW` button. | Tasks that enter shows need an EN override or a non-text detector. |
| Startup flow | `start_game` reached a blank white loading frame and fell into repeated fallback clicks in the local probe. | Startup recovery needs safer unknown/loading-state handling before Global is considered supported. |
| Capture backend | In the recorded environment, Nemu IPC returned all-white Global frames; ADB and Scrcpy captured usable frames. | Capture backend compatibility must be documented and retested on more setups. |
| CM / ads | Global ad providers vary; English `Watch Ad` and reward text require EN recognition. | CM support should remain partial/unknown until provider exits, redirects, and reward states are retested. |

## What worked in local candidate testing

The following results are useful evidence, but they are **not stock support**.
They used temporary local package mapping, generated EN resources, or candidate
task changes.

| Flow | Candidate result | Still missing |
| --- | --- | --- |
| `solo_live` | One bounded list-mode game-Auto show completed and returned home. | Other modes, script Auto, auto-unit setup, insufficient energy, recovery items, and changed result flows. |
| `auto_live` | One bounded list-mode game-Auto run completed and returned home. | Broader modes and scheduled regular task behavior. |
| `mission_rewards` | One no-reward run and one fresh claim completed; English overlay was dismissed. | Different tab counts, reward sets, pass states, and future UI changes. |
| `gift` | One fresh two-item claim completed; English confirmation dialog was dismissed. | Other gift types and future dialog variations. |
| startup pop-ups | Observed login bonus, monthly subscription, and News states were handled. | Consent, maintenance, update, and other promotional dialogs. |
| `challenge_live` | One Minori Auto Play challenge show completed with temporary English templates. | Stock task still stalls on English text; weekly reward flow untested. |
| `area_convos` | One area was cleared with temporary English story-skip resources. | Stock skip flow is broken; task can report completion even when unread badges remain; multi-area traversal is incomplete. |
| `cm` | One bounded reward was claimed; one ambiguous provider return stopped safely. | Provider-independent handling is not verified; empty-frame provider transition needs retesting. |
| `activity_story` | World Link route and no-unread branch were exercised with generated EN resources. | Unread-story chain from home to completion remains unverified. |
| `event_shop` | World Link shop scan completed with no purchase because targets were absent. | Ordinary event layout, purchase confirmation, and insufficient-currency paths. |

## Status language

Use these terms consistently:

| Status | Meaning |
| --- | --- |
| Verified working | Reproduced successfully in a documented Global test environment. Only use this when the exact implementation under review was tested. |
| Known broken | Reproduced failure with enough evidence to investigate. |
| Untested | No Global test result has been recorded. |
| Unknown | Evidence exists, but it is incomplete, conflicting, local-only, or no longer current. |
| Candidate verified | A local or proposed patch worked in a bounded Global test, but stock support is not confirmed. |

## Recommended implementation order

Keep Global work reviewable. Small PRs are much safer than one large "Global
support" PR.

1. Add a selectable Global / EN server profile and package mapping.
2. Add the `en` resource variant without claiming broad support.
3. Verify capture backend behavior and document known backend limitations.
4. Add the minimum EN resources needed for home recognition and safe startup.
5. Add low-risk reward flows first: Gifts and Missions.
6. Add bounded show flows: `solo_live` / `auto_live` with explicit counts.
7. Add stories, area conversations, and event shop only after bounded smoke
   tests are reproducible.
8. Leave CM / advertisement support for last because provider behavior varies
   by region, account, time, and ad network.

## Files in this folder

| File | Purpose |
| --- | --- |
| [`STATUS_MATRIX.md`](./STATUS_MATRIX.md) | Maintainer-facing stock vs candidate status table. |
| [`SMOKE_TEST_CHECKLIST.md`](./SMOKE_TEST_CHECKLIST.md) | Reusable Global test checklist for future maintainers. |
| [`TEST_LOG_2026-06-14_to_2026-06-16.md`](./TEST_LOG_2026-06-14_to_2026-06-16.md) | Condensed record of the first Global compatibility investigation. |
| [`REPORT_TEMPLATE.md`](./REPORT_TEMPLATE.md) | Template for future Global test reports or issues. |

## Evidence and privacy rules

Do not attach raw screenshots or logs without review.

- Blur player names, user IDs, transfer/account screens, and any other private
  account identifiers.
- Do not publish full logs if they include local paths, account state, device
  identifiers, or screenshots with private information.
- Record the IAA commit, game version, emulator, backend, resolution, and time
  zone with every test.
- Mark inconclusive results as `Unknown`, not `Verified working`.
- Do not claim Global support from inherited JP resources. A reused template is
  only valid after it is tested against representative Global frames.
