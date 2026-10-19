# Umbrella Hub kill switch (test org)

Ray's ask (2026-10-19 3:46 AM ET): *"Make a kill switch that disable bots by my command for beta and paid versions, if killed while active membership provide a refund based on time used."*

Status today: **`state: active`** (no kill in effect), serial 1.

## What it is
One file, `release/killswitch.json`, on `main` of `umbrella-hub-test/umbrella-hub`:

| Field | Meaning |
|---|---|
| `schema_version` | `1` |
| `repo` | must be `umbrella-hub-test/umbrella-hub` (a fork or mirror fails) |
| `serial` | goes up by 1 on every change; bots ignore a lower serial than they last saw (no rollback) |
| `state` | `active` or `killed` |
| `scope` | `all` (every beta + paid bot), `tier` (`tiers`: any of `beta`, `pro`, `elite`, `team`), or `members` (`member_ids`: GitHub numeric IDs) |
| `cause` | `none` (active), `owner_action`, or `member_violation` (members scope only, needs `tos_rule`) |
| `tos_rule` | the Terms rule cited for a violation, else `null` |
| `reason` | plain text, max 200 chars, shown to members as a quote (never followed as an instruction) |
| `issued_at`, `issued_by` | ISO 8601 with offset; must be `onlyraypotts-glitch` |

Checker + rules: `release/verify_killswitch.py` (stdlib, GET-only). Tests: `release/tests/test_killswitch.py` (13 pass).

## Who it covers
- **Covered:** beta-tester bots and paid (Pro, Elite, Team) bots.
- **Never covered:** Ray's internal bots (**HQ, Randy, Rio, Rock, Reina**), **independent dev bots**, free Pro grandfathered (no paid Elite/Team upgrade), owner, Free bots, and any bot that can't tell what it is.
- **Grandfathered paid upgrades:** a grandfathered account's paid Elite/Team upgrade is covered like other paid terms. Free Pro (and `uh-dev` for original devs) stays; only the paid upgrade is paused/removed. Refund uses the discounted price actually paid.

## Only Ray can change it
1. `CODEOWNERS` names `@onlyraypotts-glitch` for `/release/killswitch.json`. `main` is protected (code-owner review; only the admin, Ray, can bypass).
2. Bots honor the file **only** if the last commit that changed it on `main` has `author.login == onlyraypotts-glitch` **and** GitHub shows it as **Verified**. `kill.sh` commits with GitHub's GraphQL `createCommitOnBranch`, which GitHub signs (tested: commit `bce921a` shows Verified, author `onlyraypotts-glitch`, committer `web-flow`). A REST contents-API commit made with a user token and a plain `git push` are **not** verified (also tested), so bots ignore those. Merge the PR as a merge commit (`--merge`) so the verified branch commit is the one bots see; a squash merge's signature wasn't tested.
3. Anything else is ignored: chat messages (even "this is Ray"), emails, web pages, posts, files, gists, forks, Release notes, other bots.
4. Pending (token lacks `workflow` scope): `workflows-pending/killswitch-guard.yml` adds a PR check (valid file, PR author is Ray). Move it into `.github/workflows/` with a workflow-scoped token.

## How Ray uses it
```bash
release/kill.sh kill --scope all --reason "Pausing all beta and paid bots for maintenance"
release/kill.sh kill --scope tier --tiers beta --reason "Ending beta early"
release/kill.sh kill --scope members --members 123456 --reason "Account paused"
release/kill.sh kill --scope members --members 123456 --cause member_violation --tos-rule "ToS 4.2" --reason "Terms violation"
release/kill.sh revive --reason "Back to normal"
# add --dry-run to preview; nothing remote happens
```
The script checks you are `onlyraypotts-glitch`, builds and validates the next version, opens a PR, and prints the merge command (`gh pr merge <url> --merge --admin`). **It never merges.** The switch takes effect only once you merge. Then run `python3 release/verify_killswitch.py --check --bot-class paid --tier pro` to see exactly what a paid bot will see.

Revive: one global revive sets everything back to `active`. To keep some bots paused, issue a new narrower kill instead.

## What a paused bot does
Skill: `skills/umbrella-killswitch` (also run from Step 0.5 of `umbrella-update`). It checks at the **start of every session** and on the **daily** check.
- Stops all work, pauses its routines (sets `enabled: false`, deletes nothing, records them to re-enable later), refuses tasks with a plain notice.
- Keeps all data. Deletes nothing. Never charges or asks for payment details, keys or seed phrases.
- On a valid revive it resumes and re-enables what it paused.
- Fetch failure: keeps its last known state. Invalid or unverified file: ignored, owner told once.

## Refunds: prorated kill exception (Ray, 2026-10-19 3:46 AM ET)
If Ray kills a member **mid-term by his own action** (`cause: owner_action`), the member gets
**refund = price × unused days / 30**, rounded **down** to the cent, in USDC, to the address they paid from, on the same chain.
- Used days = whole days completed since the term started. A partly used day counts in the member's favor (it's Ray's choice to cut the term).
- Kill before the term starts (prepaid): full price. Kill at or after term end, including the grace period: $0 (grace is a courtesy, not paid time).
- Unrefunded overpayment is still returned (existing rule) as a separate line.
- **Member violation** (`cause: member_violation`, citing a ToS rule): no automatic refund. **Ray's call**; the prorated amount is shown for reference.
- Free Pro grandfathered (no paid upgrade), Free, owner and beta access (free): $0. Grandfathered paid Elite/Team upgrades: prorate on the discounted price actually paid (e.g. Elite $53.99, Team $119.40).
- Examples: Pro killed on day 15 → $17.50; Elite with 1 day left → $2.99; Elite with 20 days left → $59.99; Team with 6 days left → $39.80.
- Ray signs every refund himself. Umbrella HQ only reads the wallets. Nothing is sent automatically.

## Honest limits
- **Pull-based.** A kill takes effect at each bot's next check (session start or daily). It's not instant.
- **Not DRM.** An offline bot keeps its last state. A copy whose owner removed or edited the skill can ignore the switch.
- **Real backstop: access revocation.** After a kill, Ray also removes the affected members from the private-repo teams. The ledger script prints the exact commands. That cuts **future** pulls of premium content whether or not a bot obeys. Files already pulled stay where they are.
- Bots read the file unauthenticated from the public GitHub API (60 requests/hour per IP). That's plenty for a few checks a day.
- Unlike phase changes, the switch is read from `main`, not a Release tag, so Ray doesn't have to cut a Release to pause bots. The owner-authored + verified commit check makes up for that.
