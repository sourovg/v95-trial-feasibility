#!/usr/bin/env python3
"""Cohortia (V95) feasibility demo. Zero dependencies: Python 3.10+ standard library only.

  python3 app.py serve [--port 8095]      # web app at http://localhost:8095
  python3 app.py snapshot-all             # refresh bundled offline data (demo trials + worked example)
  python3 app.py pack NCT07185997         # key numbers in the terminal
  python3 app.py snapshot NCT07185997     # refresh the bundled offline data for a trial
Set V95_OFFLINE=1 to use only cached/bundled data.
"""
import argparse
import os
import shutil

from v95 import ctgov
from v95 import pack as packmod
from v95.web import serve


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")
    s = sub.add_parser("serve"); s.add_argument("--port", type=int, default=8095)
    p = sub.add_parser("pack"); p.add_argument("nct", nargs="?", default="NCT07185997")
    n = sub.add_parser("snapshot"); n.add_argument("nct", nargs="?", default="NCT07185997")
    sub.add_parser("snapshot-all", help="refresh offline data for the demo trials and the worked example request")
    a = ap.parse_args()
    if a.cmd == "pack":
        r = packmod.build(a.nct.upper())
        t = r["target"]
        print(f"{t['nct']}  {t['title']}\n{t['sponsor']} · target {t['enroll']} · {len(t['locations'])} sites")
        for c, f in r["funnels"].items():
            print(f"  {c:14} pool/yr {f['pool'][0]:>8,.0f}  enrol-any/yr {f['enrollable'][0]:>6,.0f}  direct competitors {f['direct_competitors']}")
        tiers = {}
        for c in r["competing"]:
            tiers[c["tier"]] = tiers.get(c["tier"], 0) + 1
        print("  competing trials:", tiers)
        for k, v in r["scenario"]["runs"].items():
            print(f"  {k:18} {v['rate']:.3f} pts/site/mo -> {v['months']} months")
        print(f"  data source: {r['src_all']}")
        return
    if a.cmd == "snapshot":
        ctgov.OFFLINE = False
        if os.path.isdir(ctgov.CACHE):
            shutil.rmtree(ctgov.CACHE)
        packmod.build(a.nct.upper())
        os.makedirs(ctgov.SNAPSHOT, exist_ok=True)
        for f in os.listdir(ctgov.CACHE):
            shutil.copy(os.path.join(ctgov.CACHE, f), ctgov.SNAPSHOT)
        print("Snapshot saved to", ctgov.SNAPSHOT)
        return
    if a.cmd == "snapshot-all":
        from v95 import intake, project, survey
        from v95.server import EXAMPLES
        ctgov.OFFLINE = False
        if os.path.isdir(ctgov.CACHE):
            shutil.rmtree(ctgov.CACHE)
        for nct, *_ in EXAMPLES:
            packmod.build(nct)
        req = intake.normalise(dict(intake.EXAMPLE))
        project.analyse({"req": req, "questions": survey.design(req), "settings": {}})
        if os.path.isdir(ctgov.SNAPSHOT):
            shutil.rmtree(ctgov.SNAPSHOT)
        shutil.copytree(ctgov.CACHE, ctgov.SNAPSHOT)
        print(len(os.listdir(ctgov.SNAPSHOT)), "files saved to", ctgov.SNAPSHOT)
        return
    serve(getattr(a, "port", 8095))


if __name__ == "__main__":
    main()
