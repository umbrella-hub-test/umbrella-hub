#!/usr/bin/env python3
"""Umbrella Hub kill switch: reference checker (read-only).

What it does
  * validate(ks)            -> list of problems with a killswitch.json document (empty = valid)
  * commit_ok(commit)       -> is the last commit that changed release/killswitch.json on main
                               authored by the owner AND GitHub-verified?
  * in_scope(ks, bot)       -> does a valid kill apply to this bot?
  * decide(bot, fetched)    -> the state the bot must be in (ACTIVE / KILLED / EXEMPT) and why

The skill skills/umbrella-killswitch/SKILL.md describes the same rules in words; bots that can
run code may run this file instead. It only performs GET requests to api.github.com (CLI mode),
never writes anything remote, never deletes data, never touches money.

CLI
  python3 release/verify_killswitch.py --validate-file release/killswitch.json
  python3 release/verify_killswitch.py --check --bot-class paid --tier pro --github-id 123 \
          [--state-file umbrella_state/killswitch.json]
"""
import argparse, base64, datetime as dt, json, os, re, sys, urllib.request

OFFICIAL_REPO = "umbrella-hub-test/umbrella-hub"   # change only when moving to the real org
OWNER_LOGIN = "onlyraypotts-glitch"
PATH = "release/killswitch.json"
REF = "main"

STATES = {"active", "killed"}
SCOPES = {"all", "tier", "members"}
TIERS = {"beta", "pro", "elite", "team"}           # what "tier" scope may name
CAUSES = {"none", "owner_action", "member_violation"}
IN_SCOPE_CLASSES = {"beta_tester", "paid"}         # beta and paid bots only
EXEMPT_ROLES = {"hq", "randy", "rio", "rock", "reina"}
EXEMPT_CLASSES = {"independent_dev", "independent_dev_bot", "owner", "internal_leader"}
REQUIRED = ["schema_version", "repo", "serial", "state", "scope", "tiers", "member_ids",
            "cause", "tos_rule", "reason", "issued_at", "issued_by"]


def _ts(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def validate(ks, repo=OFFICIAL_REPO, owner=OWNER_LOGIN):
    p = []
    if not isinstance(ks, dict):
        return ["not a JSON object"]
    for k in REQUIRED:
        if k not in ks:
            p.append(f"missing field {k}")
    if p:
        return p
    extra = set(ks) - set(REQUIRED) - {"_comment"}
    if extra:
        p.append(f"unknown fields {sorted(extra)}")
    if ks["schema_version"] != 1:
        p.append("schema_version must be 1")
    if ks["repo"] != repo:
        p.append(f"repo must be {repo}")
    if not isinstance(ks["serial"], int) or isinstance(ks["serial"], bool) or ks["serial"] < 1:
        p.append("serial must be an integer >= 1")
    if ks["state"] not in STATES:
        p.append("state must be active|killed")
    if ks["scope"] not in SCOPES:
        p.append("scope must be all|tier|members")
    if not isinstance(ks["tiers"], list) or not set(ks["tiers"]) <= TIERS:
        p.append(f"tiers must be a list drawn from {sorted(TIERS)}")
    if not isinstance(ks["member_ids"], list) or not all(isinstance(x, str) and re.fullmatch(r"[1-9][0-9]{0,19}", x) for x in ks["member_ids"]):
        p.append("member_ids must be a list of GitHub numeric IDs as strings")
    if ks["cause"] not in CAUSES:
        p.append("cause must be none|owner_action|member_violation")
    if not isinstance(ks["reason"], str) or not (1 <= len(ks["reason"]) <= 200):
        p.append("reason must be 1-200 characters")
    if ks["issued_by"] != owner:
        p.append(f"issued_by must be {owner}")
    try:
        if _ts(ks["issued_at"]).tzinfo is None:
            p.append("issued_at needs a timezone offset")
    except Exception:
        p.append("issued_at must be ISO 8601")
    if p:
        return p
    if ks["state"] == "active":
        if ks["scope"] != "all" or ks["tiers"] or ks["member_ids"] or ks["cause"] != "none" or ks["tos_rule"] is not None:
            p.append("active (revive) must be scope=all, empty tiers/member_ids, cause=none, tos_rule=null")
    else:
        if ks["cause"] == "none":
            p.append("killed needs cause owner_action|member_violation")
        if ks["scope"] == "all" and (ks["tiers"] or ks["member_ids"]):
            p.append("scope=all must have empty tiers and member_ids")
        if ks["scope"] == "tier" and (not ks["tiers"] or ks["member_ids"]):
            p.append("scope=tier needs tiers and empty member_ids")
        if ks["scope"] == "members" and (not ks["member_ids"] or ks["tiers"]):
            p.append("scope=members needs member_ids and empty tiers")
        if ks["cause"] == "member_violation" and ks["scope"] != "members":
            p.append("member_violation only with scope=members")
        if ks["cause"] == "member_violation" and not ks["tos_rule"]:
            p.append("member_violation needs tos_rule")
    return p


def commit_ok(commit, owner=OWNER_LOGIN):
    """commit = one item of GET /repos/{repo}/commits?path=release/killswitch.json&sha=main."""
    try:
        return ((commit.get("author") or {}).get("login") == owner
                and commit["commit"]["verification"]["verified"] is True)
    except (KeyError, TypeError, AttributeError):
        return False


def is_exempt(bot):
    role = (bot.get("bot_role") or "").strip().lower()
    cls = (bot.get("bot_class") or "").strip().lower()
    return role in EXEMPT_ROLES or cls in EXEMPT_CLASSES


def in_scope(ks, bot):
    if ks["state"] != "killed" or is_exempt(bot):
        return False
    cls = bot.get("bot_class")
    if cls not in IN_SCOPE_CLASSES:          # free, grandfathered, unknown: never killed by the switch
        return False
    if ks["scope"] == "all":
        return True
    if ks["scope"] == "tier":
        key = "beta" if cls == "beta_tester" else bot.get("tier")
        return key in ks["tiers"]
    return str(bot.get("github_id")) in ks["member_ids"]


def decide(bot, fetched, last_known=None):
    """fetched = None (fetch failed) or {"ks": dict|None, "commit": dict|None}.
    last_known = {"serial": int, "state": "ACTIVE"|"KILLED", ...} or None.
    Returns (state, new_last_known, message_for_log)."""
    last_known = last_known or {"serial": 0, "state": "ACTIVE"}
    if is_exempt(bot):
        return "EXEMPT", last_known, "exempt bot: kill switch never applies"
    if fetched is None:
        return last_known["state"], last_known, "fetch failed: keeping last known state"
    ks, commit = fetched.get("ks"), fetched.get("commit")
    probs = validate(ks) if ks is not None else ["no document"]
    if probs:
        return last_known["state"], last_known, "invalid kill switch ignored: " + "; ".join(probs)
    if not commit_ok(commit):
        return last_known["state"], last_known, "kill switch change not owner-authored+verified: ignored"
    if ks["serial"] < last_known.get("serial", 0):
        return last_known["state"], last_known, "older serial than last seen (rollback?): ignored"
    state = "KILLED" if in_scope(ks, bot) else "ACTIVE"
    nk = {"serial": ks["serial"], "state": state, "cause": ks["cause"], "issued_at": ks["issued_at"],
          "reason": ks["reason"], "sha": (commit or {}).get("sha")}
    return state, nk, f"serial {ks['serial']}: {state}"


def notice(nk):
    head = (f"This Umbrella bot is paused by Umbrella Hub (notice #{nk['serial']}, issued {nk['issued_at']}). "
            "I can't take on tasks right now. Your data, files and memory are kept: nothing is deleted, "
            "and you will not be charged.")
    if nk.get("cause") == "member_violation":
        refund = " Any refund for this pause is decided by Umbrella's owner under the Terms of Service."
    else:
        refund = (" If you have a paid Pro/Elite/Team term running, you're due a prorated refund for the unused "
                  "days, in USDC, to the wallet you paid from. Umbrella will never ask you for a seed phrase, "
                  "private key or any payment to receive it.")
    return head + refund + f" Reason given: \"{nk.get('reason','')}\". I'll check again at my next scheduled check."


# ---- CLI (read-only network) ----
def _get(url):
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json",
                                               "User-Agent": "umbrella-killswitch-check"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.load(r)


def fetch(repo=OFFICIAL_REPO):
    try:
        c = _get(f"https://api.github.com/repos/{repo}/contents/{PATH}?ref={REF}")
        ks = json.loads(base64.b64decode(c["content"]))
        commits = _get(f"https://api.github.com/repos/{repo}/commits?path={PATH}&sha={REF}&per_page=1")
        return {"ks": ks, "commit": commits[0] if commits else None}
    except Exception as e:
        print(f"note: fetch failed ({e.__class__.__name__})", file=sys.stderr)
        return None


def main(argv=None):
    a = argparse.ArgumentParser()
    a.add_argument("--validate-file")
    a.add_argument("--check", action="store_true")
    a.add_argument("--bot-class", default="")
    a.add_argument("--bot-role", default="")
    a.add_argument("--tier", default="")
    a.add_argument("--github-id", default="")
    a.add_argument("--state-file")
    o = a.parse_args(argv)
    if o.validate_file:
        probs = validate(json.load(open(o.validate_file)))
        print("VALID" if not probs else "INVALID: " + "; ".join(probs))
        return 0 if not probs else 1
    if o.check:
        bot = {"bot_class": o.bot_class, "bot_role": o.bot_role, "tier": o.tier, "github_id": o.github_id}
        last = json.load(open(o.state_file)) if o.state_file and os.path.exists(o.state_file) else None
        state, nk, msg = decide(bot, fetch(), last)
        print(json.dumps({"state": state, "log": msg, "last_known": nk}, indent=2))
        if state == "KILLED":
            print(notice(nk))
        if o.state_file:   # local state only (the bot's own file)
            os.makedirs(os.path.dirname(o.state_file) or ".", exist_ok=True)
            json.dump(nk, open(o.state_file, "w"), indent=2)
        return 0
    a.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
