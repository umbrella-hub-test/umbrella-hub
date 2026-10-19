#!/usr/bin/env bash
# Opens the go-live PR. Does NOT merge and does NOT create the Release.
# Usage: release/go-live.sh 2026-12-01 2026-12-01T23:59:59-05:00
set -euo pipefail
GO_LIVE_DATE="${1:?go_live_date}"; BETA_CUTOFF="${2:?beta_cutoff}"
REPO="umbrella-hub-test/umbrella-hub"   # change only when moving to the real org
git switch -c go-live
python3 - "$GO_LIVE_DATE" "$BETA_CUTOFF" <<'PY'
import json,sys
p=json.load(open("release/phase.json")); p.update(phase="live",go_live_date=sys.argv[1],beta_cutoff=sys.argv[2])
json.dump(p,open("release/phase.json","w"),indent=2); open("release/phase.json","a").write("\n")
m=json.load(open("manifest.json")); m.update(phase="live",version="1.0.0")
json.dump(m,open("manifest.json","w"),indent=2); open("manifest.json","a").write("\n")
PY
git commit -am "Go live: phase beta -> live (go_live_date=$GO_LIVE_DATE)"
git push -u origin go-live
gh pr create -R "$REPO" --base main --head go-live --title "GO LIVE: phase -> live" \
  --body "Flips release/phase.json to live. Needs @onlyraypotts-glitch approval. After merge: gh release create v1.0.0-live -R $REPO --target main --title 'Umbrella Hub v1.0.0 (live)' --notes-file release/RELEASE-NOTES-live.md"
echo "PR opened. Nothing is live until it is merged AND the v1.0.0-live Release exists."
