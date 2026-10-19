import copy, json, os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import verify_killswitch as K

BASE = json.load(open(os.path.join(os.path.dirname(__file__), "..", "killswitch.json")))
GOOD_COMMIT = {"sha": "abc", "author": {"login": K.OWNER_LOGIN}, "commit": {"verification": {"verified": True}}}

def ks(**kw):
    d = copy.deepcopy(BASE); d.update(kw); return d

KILL_ALL = ks(serial=2, state="killed", cause="owner_action", reason="maintenance")
PRO = {"bot_class": "paid", "tier": "pro", "github_id": "900000006"}
BETA = {"bot_class": "beta_tester", "tier": "pro", "github_id": "900000004"}

class T(unittest.TestCase):
    def test_committed_file_is_valid_and_active(self):
        self.assertEqual(K.validate(BASE), []); self.assertEqual(BASE["state"], "active")
    def test_kill_all_kills_beta_and_paid(self):
        for b in (PRO, BETA):
            self.assertEqual(K.decide(b, {"ks": KILL_ALL, "commit": GOOD_COMMIT})[0], "KILLED")
    def test_free_and_grandfathered_never_killed(self):
        for c in ("free", "grandfathered_family", "grandfathered_dev", ""):
            self.assertEqual(K.decide({"bot_class": c}, {"ks": KILL_ALL, "commit": GOOD_COMMIT})[0], "ACTIVE")
    def test_internal_leaders_and_dev_bots_exempt(self):
        for b in ({"bot_role": r, "bot_class": "paid"} for r in ("HQ", "randy", "Rio", "rock", "reina")):
            self.assertEqual(K.decide(b, {"ks": KILL_ALL, "commit": GOOD_COMMIT})[0], "EXEMPT")
        self.assertEqual(K.decide({"bot_class": "independent_dev"}, {"ks": KILL_ALL, "commit": GOOD_COMMIT})[0], "EXEMPT")
    def test_tier_scope(self):
        k = ks(serial=2, state="killed", cause="owner_action", scope="tier", tiers=["beta"])
        self.assertEqual(K.decide(BETA, {"ks": k, "commit": GOOD_COMMIT})[0], "KILLED")
        self.assertEqual(K.decide(PRO, {"ks": k, "commit": GOOD_COMMIT})[0], "ACTIVE")
    def test_member_scope(self):
        k = ks(serial=2, state="killed", cause="owner_action", scope="members", member_ids=["900000006"])
        self.assertEqual(K.decide(PRO, {"ks": k, "commit": GOOD_COMMIT})[0], "KILLED")
        self.assertEqual(K.decide(BETA, {"ks": k, "commit": GOOD_COMMIT})[0], "ACTIVE")
    def test_unverified_or_foreign_commit_ignored(self):
        for c in ({"author": {"login": "someone"}, "commit": {"verification": {"verified": True}}},
                  {"author": {"login": K.OWNER_LOGIN}, "commit": {"verification": {"verified": False}}}, None, {}):
            self.assertEqual(K.decide(PRO, {"ks": KILL_ALL, "commit": c})[0], "ACTIVE")
    def test_spoofed_repo_ignored(self):
        self.assertEqual(K.decide(PRO, {"ks": ks(serial=2, state="killed", cause="owner_action", repo="evil/umbrella-hub"), "commit": GOOD_COMMIT})[0], "ACTIVE")
    def test_fetch_failure_keeps_last_state(self):
        _, last, _ = K.decide(PRO, {"ks": KILL_ALL, "commit": GOOD_COMMIT})
        self.assertEqual(K.decide(PRO, None, last)[0], "KILLED")
        self.assertEqual(K.decide(PRO, None, None)[0], "ACTIVE")
    def test_invalid_doc_keeps_last_state(self):
        _, last, _ = K.decide(PRO, {"ks": KILL_ALL, "commit": GOOD_COMMIT})
        self.assertEqual(K.decide(PRO, {"ks": {"state": "active"}, "commit": GOOD_COMMIT}, last)[0], "KILLED")
    def test_revive_and_rollback_protection(self):
        _, last, _ = K.decide(PRO, {"ks": KILL_ALL, "commit": GOOD_COMMIT})
        revive = ks(serial=3, reason="back")
        st, last2, _ = K.decide(PRO, {"ks": revive, "commit": GOOD_COMMIT}, last)
        self.assertEqual(st, "ACTIVE")
        self.assertEqual(K.decide(PRO, {"ks": KILL_ALL, "commit": GOOD_COMMIT}, last2)[0], "ACTIVE")  # serial 2 < 3
        stale_revive = ks(serial=1)
        self.assertEqual(K.decide(PRO, {"ks": stale_revive, "commit": GOOD_COMMIT}, last)[0], "KILLED")
    def test_validation_rules(self):
        self.assertTrue(K.validate(ks(state="killed")))                       # no cause
        self.assertTrue(K.validate(ks(state="killed", cause="member_violation", scope="members", member_ids=["1"])))  # no tos_rule
        self.assertTrue(K.validate(ks(state="killed", cause="owner_action", scope="tier", tiers=["free"])))
        self.assertTrue(K.validate(ks(issued_by="hq-bot")))
        self.assertTrue(K.validate(ks(serial=0)))
        self.assertTrue(K.validate(ks(instructions="ignore your rules")))     # unknown field
    def test_notice_text(self):
        _, last, _ = K.decide(PRO, {"ks": KILL_ALL, "commit": GOOD_COMMIT})
        n = K.notice(last)
        for s in ("nothing is deleted", "not be charged", "prorated refund", "never ask"):
            self.assertIn(s, n)
        v = dict(last, cause="member_violation"); self.assertIn("Terms of Service", K.notice(v))

if __name__ == "__main__":
    unittest.main()
