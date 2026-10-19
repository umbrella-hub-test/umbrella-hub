# Umbrella Hub (TEST ORG: umbrella-hub-test)

> This is a **test** copy of the Umbrella Hub update channel. Not the production org. The Grok Bot template itself is **not** published here.

The public, free update channel for Umbrella bots.

| File | Purpose |
|---|---|
| `manifest.json` | Free channel version info: `channel`, `version`, `phase`, `min_version` |
| `release/phase.json` | The go-live switch. `beta` today. |
| `release/GO-LIVE.md` | How going live works (one PR + one Release, Ray approves) |
| `skills/umbrella-update/SKILL.md` | The scheduled update check bots run (pull-based, owner accepts) |
| `skills/umbrella-protection/SKILL.md` | Locked anti-copy rule, applies in every phase |

## Channels
| Channel | Repo | Who can read |
|---|---|---|
| free | `umbrella-hub` (this repo, public) | everyone |
| pro | `uh-pro` (private) | teams `pro`, `elite`, `grandfathered`, `grandfathered-dev`, `beta-testers` |
| elite | `uh-elite` (private) | teams `elite`, `grandfathered`, `grandfathered-dev`, `beta-testers` |
| dev | `uh-dev` (private) | team `grandfathered-dev` |
| ledger | `uh-ledger` (private) | org owners only |

**No premium content lives in this public repo, in beta or after launch.** Premium files are only in the private repos and are watermarked per member when pulled.

## Prices (USDC per 30 days, no auto-charge)
Free $0 · Pro $35 · Elite $89.99 · Team $199 (later phase). Family and original devs: grandfathered, free.
Umbrella will **never** ask for your seed phrase or private key.

## Honest limits
- Updates are **pull-based**: a bot only changes if its owner runs the update routine and says yes.
- Anyone who copies the free template owns their copy and can read or edit its config. The protection skill and watermarks are deterrence; the private repos are the real gate.
