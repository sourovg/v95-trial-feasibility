"""Assemble one feasibility pack for one public trial."""
from datetime import date

from . import analysis, ctgov, epi


def build(nct, params=None):
    params = params or {}
    raw, src_trial = ctgov.study(nct)
    target = ctgov.flat(raw)
    pkey = epi.TRIAL_PROFILES.get(nct)
    profile = epi.PROFILES.get(pkey) if pkey else None
    generic = profile is None
    if generic:
        cond = target["conditions"][0] if target["conditions"] else target["title"]
        profile = {"name": cond + " (generic profile: type your own epidemiology)", "search_cond": cond,
                   "countries": {"United States": epi.GENERIC_STEPS}}
    cond = params.get("cond") or profile["search_cond"]

    # Similar trials, any status, interventional (for sites and benchmarks), and active ones (competition)
    all_raw, src_all, q_all = ctgov.search(cond, advanced="AREA[StudyType]INTERVENTIONAL")
    studies = [ctgov.flat(s) for s in all_raw]

    comp = analysis.competing(target, studies, profile)
    sites = analysis.site_track_record(target, studies, comp)
    frac = float(params.get("enrol_fraction", 0.6))
    bench_rows, bench = analysis.benchmarks(studies, frac, profile)

    # Funnels per country, with overrides from the form: o_<country>_<step>=value
    funnels = {}
    for country, steps in profile["countries"].items():
        ov = {}
        for s in steps:
            v = params.get(f"o_{country}_{s['key']}")
            if v not in (None, ""):
                try:
                    ov[s["key"]] = float(v)
                except ValueError:
                    pass
        f = epi.run_funnel(steps, ov)
        direct = sum(1 for c in comp if c["tier"] == "Direct" and country in c["countries"])
        f["direct_competitors"] = direct
        f["fair_share"] = tuple(x / (1 + direct) for x in f["enrollable"])
        f["target_sites"] = sum(1 for l in target["locations"] if l["country"] == country)
        funnels[country] = f

    # Enrolment scenario
    n_target = int(params.get("target_n") or target["enroll"] or 100)
    n_sites = int(params.get("sites") or len(target["locations"]) or 20)
    ramp = int(params.get("ramp", 9))
    scen = {}
    for label, r in (("Slow (P25)", bench["p25"]), ("Typical (median)", bench["median"]), ("Fast (P75)", bench["p75"])):
        curve, done = analysis.enrolment_curve(n_target, n_sites, r, ramp)
        scen[label] = {"rate": r, "curve": curve, "months": done}

    start = analysis.parse_date(target["start"])
    pcd = analysis.parse_date(target["pcd"])
    return {
        "nct": nct, "target": target, "src_trial": src_trial, "profile": profile, "profile_key": pkey,
        "generic": generic, "cond": cond, "q_all": q_all, "src_all": src_all, "n_similar": len(studies),
        "criteria": analysis.split_criteria(target["criteria"]),
        "competing": comp, "sites": sites, "bench_rows": bench_rows, "bench": bench, "enrol_fraction": frac,
        "funnels": funnels, "state_split": epi.state_split(funnels["United States"]["pool"][0]) if "United States" in funnels else [],
        "scenario": {"n": n_target, "sites": n_sites, "ramp": ramp, "runs": scen},
        "posted_window_months": analysis.months_between(start, pcd) if start and pcd else None,
        "generated": date.today().isoformat(),
        "sources": epi.SRC,
    }
