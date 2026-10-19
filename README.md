# Umbrella Hub (TEST ORG: umbrella-hub-test)

> This is a **test** copy of the Umbrella Hub update channel. Not the production org. The Grok Bot template itself is **not** published here.

The public, free update channel for Umbrella bots.

| File | Purpose |
|---|---|
| `manifest.json` | Free channel version info: `channel`, `version`, `phase`, `min_version` |
| `release/phase.json` | The go-live switch. `beta` today. |
| `release/killswitch.json` | The kill switch. `active` today. Only Ray changes it (`release/kill.sh` opens a PR; see `release/KILLSWITCH.md`) |
| `skills/umbrella-killswitch/SKILL.md` | Locked rule: beta and paid bots check the switch at session start and daily; when paused they stop work, keep all data, never charge |
| `release/GO-LIVE.md` | How going live works (one PR + one Release, Ray approves) |
| `skills/umbrella-update/SKILL.md` | The scheduled update check bots run (pull-based, owner accepts) |
| `skills/umbrella-protection/SKILL.md` | Locked anti-copy rule, applies in every phase |

## Channels
| Channel | Repo | Who can read |
|---|---|---|
| free | `umbrella-hub` (this repo, public) | everyone |
| pro | `uh-pro` (private) | teams `pro`, `elite`, `grandfathered`, `grandfathered-dev`, `beta-testers` |
| elite | `uh-elite` (private) | teams `elite`, `beta-testers` (+ grandfathered only via a **paid discounted** Elite/Team grant) |
| dev | `uh-dev` (private) | team `grandfathered-dev` |
| ledger | `uh-ledger` (private) | org owners only |

**No premium content lives in this public repo, in beta or after launch.** Premium files are only in the private repos and are watermarked per member when pulled.

## Prices (USDC per 30 days, no auto-charge)
Free $0 · Pro $35 · Elite $89.99 · Team $199 (later phase).
**Grandfathered** (family / original devs): Pro free only. Elite $53.99 / Team $119.40 (HQ 40% off). `grandfathered` → `uh-pro` only; `grandfathered-dev` keeps `uh-dev` + `uh-pro` (not free Elite). Owner and internal bots unchanged.
Umbrella will **never** ask for your seed phrase or private key.

## Honest limits
- The kill switch is **pull-based** too: a pause takes effect at each bot's next check, and an offline or modified copy can ignore it. Removing team access is the real backstop for premium content.
- Updates are **pull-based**: a bot only changes if its owner runs the update routine and says yes.
- Anyone who copies the free template owns their copy and can read or edit its config. The protection skill and watermarks are deterrence; the private repos are the real gate.
