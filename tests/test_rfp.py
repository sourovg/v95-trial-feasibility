import os
import tempfile
import threading
import unittest
import urllib.parse
import urllib.request

os.environ["V95_OFFLINE"] = "1"
os.environ["COHORTIA_AI"] = "0"
os.environ["COHORTIA_DB"] = os.path.join(tempfile.mkdtemp(), "t.db")

from v95 import ctgov, intake, project, store, survey  # noqa: E402

ctgov.OFFLINE = True


class TestIntake(unittest.TestCase):
    def test_example_text_parses(self):
        f, prov = intake.parse(intake.EXAMPLE_TEXT)
        self.assertEqual(f["study_type"], "obs_prospective")
        self.assertEqual(f["indication"], "abd_onc_surgery_nutrition")
        self.assertEqual(f["design"], "Cross-sectional (point prevalence)")
        self.assertEqual(f["countries"], ["Argentina", "Brazil", "Chile", "Colombia", "Mexico", "Peru"])
        self.assertIn("study_type", prov)

    def test_interventional_phase(self):
        f, _ = intake.parse("A randomised phase 3 trial in plaque psoriasis in Germany and Spain")
        self.assertEqual(f["study_type"], "interventional")
        self.assertEqual(f["phase"], "Phase 3")
        self.assertEqual(f["indication"], "psoriasis")
        self.assertEqual(f["countries"], ["Germany", "Spain"])


class TestSurvey(unittest.TestCase):
    def test_five_pillars_and_rules(self):
        req = intake.normalise(dict(intake.EXAMPLE))
        qs = survey.design(req)
        self.assertEqual({q["pillar"] for q in qs}, {p for p, _, _ in survey.PILLARS})
        ids = {q["id"] for q in qs}
        self.assertIn("pr_screen", ids)       # nutrition rule
        self.assertIn("de_consecutive", ids)  # observational rule
        self.assertNotIn("de_random", ids)    # interventional-only


class TestModel(unittest.TestCase):
    def test_simulate_reaches_target(self):
        cs = [{"country": "A", "startup": 2, "reach": 1000, "score": 80}, {"country": "B", "startup": 4, "reach": 500, "score": 50}]
        r = project.simulate(cs, 300, 2.0, 10, ramp=1)
        self.assertIsNotNone(r["months"])
        self.assertGreaterEqual(sum(r["per_country"].values()), 300)

    def test_worked_example_offline(self):
        req = intake.normalise(dict(intake.EXAMPLE))
        a = project.analyse({"req": req, "questions": survey.design(req), "settings": {}})
        self.assertEqual(len(a["countries"]), 6)
        self.assertEqual(a["countries"][0]["country"], "Brazil")
        # n = 1.96^2 * .44 * .56 / .04^2 * 1.5
        self.assertEqual(a["ss"]["n"], 888)
        self.assertTrue(a["risks"])


class TestWebFlow(unittest.TestCase):
    def test_create_invite_simulate(self):
        from http.server import ThreadingHTTPServer
        from v95 import web
        srv = ThreadingHTTPServer(("127.0.0.1", 0), web.Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{srv.server_address[1]}"

        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *a):
                return None
        op = urllib.request.build_opener(NoRedirect)

        def post(path, data):
            try:
                op.open(base + path, urllib.parse.urlencode(data, doseq=True).encode())
            except urllib.error.HTTPError as ex:
                return ex.headers.get("Location")
        loc = post("/new", {**intake.EXAMPLE, "action": "create"})
        self.assertTrue(loc.startswith("/p/FR-"))
        pid = loc.split("/")[-1]
        for tab in ("overview", "benchmark", "countries", "investigators", "scenario", "proposal"):
            body = urllib.request.urlopen(f"{base}/p/{pid}?tab={tab}").read().decode()
            self.assertNotIn("Something went wrong", body, tab)
        a = project.analyse(store.get_project(pid), [])
        post(f"/p/{pid}/invite", {"site": [s["key"] for s in a["sites"][:5]]})
        post(f"/p/{pid}/simulate", {})
        inv = store.invites(pid)
        self.assertEqual(len(inv), 5)
        self.assertTrue(all(i["status"] != "draft" for i in inv))
        tok = inv[0]["token"]
        self.assertIn("Feasibility questionnaire", urllib.request.urlopen(f"{base}/s/{tok}").read().decode())
        srv.shutdown()


if __name__ == "__main__":
    unittest.main()
