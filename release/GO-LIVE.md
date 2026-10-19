# Go-live procedure (one PR + one Release)

Status today: **phase = beta**. Do not run this until Ray says "go live".

## What "go live" is
1. One pull request that edits only `release/phase.json`:
   - `"phase": "beta"` -> `"phase": "live"`
   - `"go_live_date": "<ISO 8601 date, ET>"`
   - `"beta_cutoff": "<ISO 8601 date-time, ET>"` (when beta-testers team access ends)
   - and bumps `manifest.json` `phase` to `live` and `version` to `1.0.0`.
2. CODEOWNERS (`@onlyraypotts-glitch`) must approve; branch protection on `main` requires a code-owner review.
3. After merge, Ray creates the Release `v1.0.0-live` from `main` (or `release/go-live.sh` does it for him after his typed yes).

Bots only react to a **Release** whose tag ends in `-live` AND whose `release/phase.json` at that tag says `"live"`. A phase edit on `main` with no Release does nothing.

## Rollback
Publish a new Release (e.g. `v1.0.1-beta`) with `phase: "beta"`. Bots that already reset keep their backups (`umbrella-backups/`) and can restore with "restore my Umbrella backup".

## Honest limits
- Pull-based: bots only see this if their owner installed the `umbrella-update` routine and accepts the change.
- Ray is currently the only org owner and admin. GitHub does not let you approve your own PR, so the protection is set with "admins can bypass" (enforce_admins off): it stops anyone else from flipping the phase, while Ray merges his own go-live PR as admin.
