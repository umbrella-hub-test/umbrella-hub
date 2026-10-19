#!/usr/bin/env bash
# Umbrella Hub kill switch: PREPARES a PR. Never merges it. Ray merges.
#
#   release/kill.sh kill   --scope all                       --reason "..." [--cause owner_action]
#   release/kill.sh kill   --scope tier    --tiers pro,elite --reason "..."
#   release/kill.sh kill   --scope members --members 123,456 --reason "..." [--cause member_violation --tos-rule "ToS 4.2"]
#   release/kill.sh revive --reason "..."
#   add --dry-run to any of the above: prints the new file, touches nothing remote.
#
# What a real run does (only as onlyraypotts-glitch):
#   1. reads release/killswitch.json on main, builds the next version (serial+1), validates it
#   2. creates branch killswitch-<serial> and commits the file through the GitHub API
#      (GitHub signs API commits, so the commit is "Verified" and authored by you)
#   3. opens the PR and prints the merge command, the refund dry-run and the access-revocation plan
# Bots only obey the switch after the PR is merged into main.
set -euo pipefail
REPO="umbrella-hub-test/umbrella-hub"   # change only when moving to the real org
OWNER="onlyraypotts-glitch"
FILE="release/killswitch.json"
HERE="$(cd "$(dirname "$0")" && pwd)"

ACTION="${1:-}"; shift || true
SCOPE="all"; TIERS=""; MEMBERS=""; REASON=""; CAUSE=""; TOS=""; DRY=0
while [ $# -gt 0 ]; do
  case "$1" in
    --scope) SCOPE="$2"; shift 2;;
    --tiers) TIERS="$2"; shift 2;;
    --members) MEMBERS="$2"; shift 2;;
    --reason) REASON="$2"; shift 2;;
    --cause) CAUSE="$2"; shift 2;;
    --tos-rule) TOS="$2"; shift 2;;
    --dry-run) DRY=1; shift;;
    *) echo "unknown arg $1" >&2; exit 2;;
  esac
done
case "$ACTION" in kill|revive) ;; *) sed -n '2,10p' "$0"; exit 2;; esac
[ -n "$REASON" ] || { echo "--reason is required" >&2; exit 2; }

if [ "$DRY" = 1 ]; then
  CURRENT="$(cat "$HERE/killswitch.json")"
else
  ME="$(gh api user --jq .login)"
  [ "$ME" = "$OWNER" ] || { echo "REFUSING: only $OWNER may prepare a kill switch change (you are $ME)." >&2; exit 1; }
  CURRENT="$(gh api "repos/$REPO/contents/$FILE?ref=main" --jq .content | base64 -d)"
fi

NEW="$(CURRENT="$CURRENT" python3 - "$ACTION" "$SCOPE" "$TIERS" "$MEMBERS" "$REASON" "$CAUSE" "$TOS" <<'PY'
import json, os, sys, datetime as dt
action, scope, tiers, members, reason, cause, tos = sys.argv[1:8]
cur = json.loads(os.environ["CURRENT"])
now = dt.datetime.now().astimezone().replace(microsecond=0).isoformat()
new = dict(cur, serial=cur["serial"] + 1, issued_at=now, reason=reason, issued_by="onlyraypotts-glitch")
if action == "revive":
    new.update(state="active", scope="all", tiers=[], member_ids=[], cause="none", tos_rule=None)
else:
    new.update(state="killed", scope=scope,
               tiers=[t for t in tiers.split(",") if t] if scope == "tier" else [],
               member_ids=[m for m in members.split(",") if m] if scope == "members" else [],
               cause=cause or "owner_action", tos_rule=tos or None)
print(json.dumps(new, indent=2))
PY
)"
TMP="$(mktemp)"; printf '%s\n' "$NEW" > "$TMP"
python3 "$HERE/verify_killswitch.py" --validate-file "$TMP" || { echo "REFUSING: new kill switch is invalid; nothing done." >&2; rm -f "$TMP"; exit 1; }
SERIAL="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["serial"])' "$TMP")"
STATE="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["state"])' "$TMP")"
echo "---- proposed $FILE (serial $SERIAL, $STATE) ----"; cat "$TMP"

FOLLOWUP="After you merge:
  * bots pick it up at their next check (session start or daily); offline/modified copies may not.
  * cut private-repo access too (works even if a bot ignores the switch):
      cd uh-ledger && python3 scripts/prorated_refund.py --killswitch <path to merged killswitch.json>
    prints the refund queue for you to sign AND the exact team-removal commands. Nothing is sent or removed by it.
  * revive later with: release/kill.sh revive --reason \"...\" (team access must be re-added by hand)."

if [ "$DRY" = 1 ]; then
  echo "DRY-RUN: no branch, no commit, no PR."; echo "$FOLLOWUP"; rm -f "$TMP"; exit 0
fi

BR="killswitch-$SERIAL"
MAIN_SHA="$(gh api "repos/$REPO/git/ref/heads/main" --jq .object.sha)"
FILE_SHA="$(gh api "repos/$REPO/contents/$FILE?ref=main" --jq .sha)"
gh api -X POST "repos/$REPO/git/refs" -f ref="refs/heads/$BR" -f sha="$MAIN_SHA" >/dev/null
gh api -X PUT "repos/$REPO/contents/$FILE" -f message="Kill switch #$SERIAL: $STATE ($SCOPE) - $REASON" \
  -f content="$(base64 -w0 "$TMP")" -f sha="$FILE_SHA" -f branch="$BR" >/dev/null
rm -f "$TMP"
URL="$(gh pr create -R "$REPO" --base main --head "$BR" --title "KILL SWITCH #$SERIAL: $STATE ($SCOPE)" \
  --body "Changes only \`$FILE\`. Prepared by release/kill.sh. Bots obey it only after this is merged into main by @$OWNER. Not merged by the script.")"
echo "PR opened (NOT merged): $URL"
echo "To make it effective: gh pr merge $URL --squash --admin"
echo "$FOLLOWUP"
