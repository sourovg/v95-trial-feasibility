#!/usr/bin/env python3
"""Back-test the enrolment-rate method on finished trials (no look-ahead).

For each finished industry trial (same filters as the app's benchmarks), predict its
enrolment pace from the median patients/site/month of trials in the same indication and
phase that STARTED EARLIER, then compare with the pace it actually achieved.
predicted_months / actual_months = own_rate / prior_median_rate.

Run from the repo root:  python3 scripts/backtest.py
"""
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from v95 import analysis, ctgov  # noqa: E402

CASES = [
    ("Oncology", "EGFR non-small cell lung cancer"),
    ("Rare disease", "myasthenia gravis"),
    ("Common chronic", "atopic dermatitis"),
]
FRACTION = 0.6
MIN_PRIOR = 5


def finished(studies):
    out = []
    for t in studies:
        if t["sponsor_class"] != "INDUSTRY" or t["enroll_type"] != "ACTUAL" or not t["enroll"]:
            continue
        if t["status"] not in ("COMPLETED", "ACTIVE_NOT_RECRUITING") or t["pcd_type"] != "ACTUAL":
            continue
        ph = {"PHASE2", "PHASE3"} & set(t["phases"])
        a, b, n = analysis.parse_date(t["start"]), analysis.parse_date(t["pcd"]), len(t["locations"])
        if not ph or not a or not b or n < 5 or t["enroll"] < 30 or a.year < 2012:
            continue
        m = analysis.months_between(a, b)
        if m < 6:
            continue
        out.append({**t, "a": a, "n_sites": n, "months": m, "ph": "PHASE3" if "PHASE3" in ph else "PHASE2",
                    "rate": t["enroll"] / (n * m * FRACTION)})
    return out


def run(cond):
    raw, src, _ = ctgov.search(cond, advanced="AREA[StudyType]INTERVENTIONAL")
    rows = finished([ctgov.flat(s) for s in raw])
    res = []
    for t in rows:
        prior = [r["rate"] for r in rows if r["a"] < t["a"] and r["ph"] == t["ph"] and r["nct"] != t["nct"]]
        if len(prior) < MIN_PRIOR:
            continue
        med = statistics.median(prior)
        res.append({**t, "pred_rate": med, "ratio": t["rate"] / med, "n_prior": len(prior)})
    return res, src


def summary(res):
    if not res:
        return "no testable trials"
    r = [x["ratio"] for x in res]
    within = sum(1 for x in r if 1 / 1.3 <= x <= 1.3)
    within2 = sum(1 for x in r if 0.5 <= x <= 2)
    q = statistics.quantiles(r, n=4) if len(r) >= 4 else [min(r), statistics.median(r), max(r)]
    return (f"{len(r)} trials · predicted/actual time: median {statistics.median(r):.2f}x "
            f"(IQR {q[0]:.2f}–{q[2]:.2f}) · within ±30%: {within}/{len(r)} ({within/len(r):.0%}) · "
            f"within 2x: {within2}/{len(r)} ({within2/len(r):.0%})")


if __name__ == "__main__":
    lines = []
    for label, cond in CASES:
        res, src = run(cond)
        lines.append(f"## {label}: \"{cond}\" (data: {src})\n{summary(res)}\n")
        lines.append("| Trial | Phase | Start | Sites | Enrolled | Actual pts/site/mo | Predicted (prior median) | Predicted ÷ actual time |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for x in sorted(res, key=lambda x: x["a"]):
            lines.append(f"| {x['nct']} | {x['ph'][-1]} | {x['start']} | {x['n_sites']} | {x['enroll']} | {x['rate']:.3f} | {x['pred_rate']:.3f} | {x['ratio']:.2f}x |")
        lines.append("")
    print("\n".join(lines))
