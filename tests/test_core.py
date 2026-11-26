import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["V95_OFFLINE"] = "1"

from v95 import analysis, epi  # noqa: E402
from v95 import pack as packmod  # noqa: E402

PROFILE = epi.PROFILES["egfr_pacc_1l"]


def trial(title, criteria="", conditions=None, status="RECRUITING"):
    return {"nct": "NCT00000001", "title": title, "official": "", "conditions": conditions or [], "keywords": [],
            "criteria": criteria, "status": status, "type": "INTERVENTIONAL", "locations": []}


class Funnel(unittest.TestCase):
    def test_multiplies(self):
        f = epi.run_funnel(PROFILE["countries"]["United States"])
        expect = 229410 * 0.82 * 0.58 * 0.15 * 0.135 * 0.80 * 0.55
        self.assertAlmostEqual(f["pool"][0], expect, places=3)
        self.assertAlmostEqual(f["enrollable"][0], expect * 0.081, places=3)
        self.assertLess(f["pool"][1], f["pool"][0])
        self.assertGreater(f["pool"][2], f["pool"][0])

    def test_override(self):
        f = epi.run_funnel(PROFILE["countries"]["United States"], {"tested": 0.4})
        g = epi.run_funnel(PROFILE["countries"]["United States"])
        self.assertAlmostEqual(f["pool"][0] * 2, g["pool"][0], places=3)

    def test_state_split_sums(self):
        rows = epi.state_split(1000)
        self.assertEqual(len(rows), 51)
        self.assertAlmostEqual(sum(r[2] for r in rows), 1000, places=6)


class Overlap(unittest.TestCase):
    def test_direct(self):
        t = trial("First-line study in advanced NSCLC with uncommon EGFR mutations", "Inclusion Criteria:\n* EGFR G719X")
        sc, _ = analysis.score_overlap(t, PROFILE)
        self.assertEqual(analysis.tier(sc), "Direct")

    def test_exclusion_text_ignored(self):
        t = trial("Advanced NSCLC first-line immunotherapy",
                  "Inclusion Criteria:\n* No sensitizing EGFR mutation\nExclusion Criteria:\n* EGFR G719X, L861Q")
        sc, why = analysis.score_overlap(t, PROFILE)
        self.assertEqual(analysis.tier(sc), "Low")

    def test_early_stage_penalised(self):
        t = trial("Adjuvant therapy in resectable EGFR NSCLC with uncommon mutations")
        sc, _ = analysis.score_overlap(t, PROFILE)
        self.assertNotEqual(analysis.tier(sc), "Direct")


class Enrolment(unittest.TestCase):
    def test_curve(self):
        curve, done = analysis.enrolment_curve(100, 10, 1.0, ramp_months=0)
        self.assertEqual(done, 10)
        _, done2 = analysis.enrolment_curve(100, 10, 1.0, ramp_months=6)
        self.assertGreater(done2, done)


class SnapshotPack(unittest.TestCase):
    def test_bundled_pack_builds_offline(self):
        p = packmod.build("NCT07185997")
        self.assertEqual(p["target"]["sponsor"], "ArriVent BioPharma, Inc.")
        self.assertGreater(len([c for c in p["competing"] if c["tier"] == "Direct"]), 5)
        self.assertGreaterEqual(p["bench"]["n"], 4)
        self.assertTrue(all(s["facility"].lower() != "research site" for s in p["sites"]))


if __name__ == "__main__":
    unittest.main()
