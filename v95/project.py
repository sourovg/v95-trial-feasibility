"""The four feasibility pillars, computed from a structured request.

  1 Benchmark analysis      similar studies (registries), enrolment pace, published figures
  2 Country evaluation      patients, research activity, start-up time, competition → weighted score
  3 Investigator insights   candidate sites/investigators + survey results
  4 Scenario & risk         sample size, timelines by scenario, risk register, recommendation

Labels: F verified fact (registry/GLOBOCAN), S published figure, E estimate (our arithmetic), J judgment (editable).
"""
import math
import re
import statistics
from collections import Counter, defaultdict
from datetime import date

from . import analysis, catalog, registries

ACTIVE = {"RECRUITING", "NOT_YET_RECRUITING", "ENROLLING_BY_INVITATION"}
DEFAULT_WEIGHTS = {"pool": 30, "experience": 25, "startup": 20, "competition": 15, "evidence": 10}
WEIGHT_LABELS = {"pool": "Patient pool", "experience": "Research experience", "startup": "Start-up speed",
                 "competition": "Low competition", "evidence": "Published evidence"}
Z = 1.96


def _f(d, k, default):
    try:
        v = d.get(k)
        return default if v in (None, "") else float(v)
    except (TypeError, ValueError):
        return default


def _country_of(locs, countries):
    return {l["country"] for l in locs if l["country"] in countries}


def _site_name(f):
    return re.sub(r"\s+", " ", f or "").strip()


def isrctn_query(ind):
    if ind["id"] == "abd_onc_surgery_nutrition":
        return "malnutrition AND surgery AND cancer"
    return ind["cond"].split(" OR ")[0]


# ------------------------------------------------------------------ pillar 1

_NUT = r"malnutrition|malnourish|nutrition|nutritional|cachexia|sarcopenia|immunonutrition|supplement|prehabilitation|enteral|parenteral|dietary"
_ABD = r"gastric|stomach|gastrectomy|colorectal|colon|rectal|colectomy|pancrea|liver|hepat|esophag|oesophag|gastrointestinal|abdominal|digestive|biliary|gallbladder"
_SURG = r"surg|resection|operat|ectomy|perioperative|\beras\b"
_CAN = r"cancer|neoplas|tumou?r|carcinoma|oncolog|malignan|adenocarcinoma"


def relevance(t, ind):
    """Direct = clearly the same topic; Partial = related. From title, conditions and keywords only."""
    meta = " ".join([t["title"], " ".join(t["conditions"]), " ".join(t["keywords"])]).lower()
    if ind["id"] == "abd_onc_surgery_nutrition":
        can, nut, abd, surg = (bool(re.search(p, meta)) for p in (_CAN, _NUT, _ABD, _SURG))
        if can and nut and surg:
            return "Direct"
        return "Partial" if can and (nut or (abd and surg)) else "Low"
    words = [w.strip().lower() for w in ind["cond"].split(" OR ")]
    return "Direct" if any(w in meta for w in words) else "Partial"


def benchmark(req, ind):
    countries = req["countries"]
    region, src_r, url_r = registries.ctgov_search(ind["cond"], ind["term"], countries)
    for t in region:
        t["rel"] = relevance(t, ind)
    world, src_w, url_w = registries.ctgov_search(ind["cond"], ind["term"], None, max_pages=2)
    obs_wanted = req.get("study_type", "").startswith("obs") or req.get("study_type") == "registry"

    def pace(rows):
        out = []
        for t in rows:
            if t["enroll_type"] != "ACTUAL" or not t["enroll"] or t["pcd_type"] != "ACTUAL" or t["status"] != "COMPLETED":
                continue
            a, b, n = analysis.parse_date(t["start"]), analysis.parse_date(t["pcd"]), max(len(t["locations"]), 1)
            if not a or not b or a.year < 2010:
                continue
            m = analysis.months_between(a, b)
            if m < 2 or t["enroll"] < 20:
                continue
            out.append({**t, "n_sites": n, "months": m, "rate": t["enroll"] / (n * m)})
        return out

    paced = pace(world)
    same_type = [r for r in paced if (r["type"] == "OBSERVATIONAL") == obs_wanted]
    multi = [r for r in same_type if r["n_sites"] >= 3]
    basis = multi if len(multi) >= 6 else same_type if len(same_type) >= 6 else paced

    def summ(vals):
        if len(vals) >= 4:
            q = statistics.quantiles(vals, n=4)
            return {"n": len(vals), "p25": q[0], "median": q[1], "p75": q[2]}
        if vals:
            return {"n": len(vals), "p25": min(vals), "median": statistics.median(vals), "p75": max(vals)}
        return {"n": 0, "p25": None, "median": None, "p75": None}

    region_rows = sorted(region, key=lambda t: (t["status"] not in ACTIVE, -(int((t["start"] or "0")[:4]))))
    types = Counter("Observational" if t["type"] == "OBSERVATIONAL" else "Interventional" for t in region)
    by_status = Counter("Recruiting / not yet" if t["status"] in ACTIVE else "Completed" if t["status"] == "COMPLETED" else "Other" for t in region)
    years = Counter(int(t["start"][:4]) for t in region if t["start"])
    isr = registries.isrctn_search(isrctn_query(ind), limit=100)
    for t in isr["trials"]:
        t["rel"] = relevance({"title": t["title"], "conditions": [], "keywords": []}, ind)
    isr["relevant"] = [t for t in isr["trials"] if t["rel"] != "Low"]
    pm_total, pm_src, pm_url = registries.pubmed_count(registries.pubmed_term(ind))
    return {
        "region": region_rows, "region_src": src_r, "region_url": url_r,
        "world_n": len(world), "world_src": src_w, "world_url": url_w,
        "types": dict(types), "by_status": dict(by_status), "years": dict(sorted(years.items())),
        "paced": sorted(basis, key=lambda r: r["rate"]),
        "pace_basis": ("multi-centre " if basis is multi else "") + ("observational" if obs_wanted and basis is not paced else "interventional" if basis is not paced else "all") + " completed studies",
        "rate": summ([r["rate"] for r in basis]),
        "size": summ([r["enroll"] for r in basis]),
        "duration": summ([r["months"] for r in basis]),
        "sites": summ([r["n_sites"] for r in basis]),
        "isrctn": isr, "pubmed_total": pm_total, "pubmed_url": pm_url,
        "literature": catalog.LITERATURE.get(ind["id"], []),
    }


# ------------------------------------------------------------------ pillar 2

def patients(req, ind, country, ov):
    """Patient funnel for one country. Returns rows [(label, value, tag, note)], reachable/yr."""
    g = catalog.globocan().get(country)
    rows = []
    if ind["globocan"] and g:
        inc = sum(g["sites"].get(s, 0) for s in ind["globocan"])
        rows.append(("New cases per year", inc, "F", "GLOBOCAN 2024: " + ", ".join(ind["globocan"]).lower()))
        if ind["id"] in ("abd_onc_surgery_nutrition", "gi_cancer_surgery"):
            res = _f(ov, "resection", 0.40)
            rows.append(("Undergo surgical resection", inc * res, "J", f"{res:.0%} of new cases; varies by tumour and stage"))
            base = inc * res
        else:
            el = _f(ov, "eligible", 0.30)
            rows.append(("Meet the study's key criteria", inc * el, "J", f"{el:.0%} of new cases"))
            base = inc * el
    elif g and _f(ov, "prev100k", 0) > 0:
        p = _f(ov, "prev100k", 0)
        rows.append(("Population", g["pop"], "F", catalog.GLOBOCAN_LABEL))
        base = g["pop"] * p / 1e5
        rows.append((f"Living with the condition ({p:g} per 100,000)", base, "J", "prevalence entered by user"))
    else:
        return rows, None
    reach = _f(ov, "reach", 0.25)
    rows.append(("Treated at hospitals that can do research", base * reach, "J", f"{reach:.0%} of the above"))
    return rows, base * reach


def countries_eval(req, ind, bench, ov, weights):
    countries = req["countries"]
    obs = req.get("study_type", "").startswith("obs") or req.get("study_type") == "registry"
    per = {}
    for c in countries:
        studies = [t for t in bench["region"] if t["rel"] != "Low" and c in _country_of(t["locations"], [c])]
        active = [t for t in studies if t["status"] in ACTIVE and t["rel"] != "Low"]
        sites = {_site_name(l["facility"]) for t in studies for l in t["locations"] if l["country"] == c and l["facility"]}
        rows, reach = patients(req, ind, c, ov)
        pm, _, pm_url = registries.pubmed_count(registries.pubmed_term(ind) + f" AND {c}[Affiliation]")
        su = catalog.STARTUP.get(c, (4, 6))[0 if obs else 1]
        su = _f(ov, f"startup_{c}", su)
        per[c] = {"country": c, "studies": len(studies), "active": len(active), "sites": len(sites), "funnel": rows, "reach": reach,
                  "pubmed": pm, "pubmed_url": pm_url, "startup": su, "law": catalog.DATA_LAW.get(c, "check local law"),
                  "active_list": active[:8]}
    # normalise each metric to 0–100 across the selected countries
    def norm(vals, higher=True, log=False):
        xs = [math.log10(v + 1) if log else v for v in vals]
        lo, hi = min(xs), max(xs)
        if hi - lo < 1e-9:
            return [70.0] * len(xs)
        return [100 * ((x - lo) / (hi - lo) if higher else (hi - x) / (hi - lo)) for x in xs]
    cs = list(per)
    if not cs:
        return []
    metrics = {
        "pool": norm([per[c]["reach"] or 0 for c in cs], True, True),
        "experience": norm([per[c]["studies"] + 0.5 * per[c]["sites"] for c in cs], True, True),
        "startup": norm([per[c]["startup"] for c in cs], False),
        "competition": norm([per[c]["active"] / max((per[c]["reach"] or 1) / 1000, 0.1) for c in cs], False),
        "evidence": norm([per[c]["pubmed"] or 0 for c in cs], True, True),
    }
    tw = sum(weights.values()) or 1
    for i, c in enumerate(cs):
        per[c]["metrics"] = {k: metrics[k][i] for k in metrics}
        per[c]["score"] = sum(weights[k] * metrics[k][i] for k in weights) / tw
        s = per[c]["score"]
        per[c]["tier"] = "Priority" if s >= 65 else "Include" if s >= 40 else "Backup"
    return sorted(per.values(), key=lambda r: -r["score"])


# ------------------------------------------------------------------ pillar 3

def site_candidates(req, bench):
    countries = req["countries"]
    agg = defaultdict(lambda: {"studies": set(), "completed": 0, "active": 0, "industry": 0, "investigators": Counter(), "last": 0})
    for t in bench["region"]:
        if t["rel"] == "Low":
            continue
        locs = [l for l in t["locations"] if l["country"] in countries and l["facility"]]
        for l in locs:
            k = (_site_name(l["facility"]), l["city"], l["country"])
            if analysis.site_key(l)[0] in ("", "research site", "local institution"):
                continue
            a = agg[k]
            if t["nct"] in a["studies"]:
                continue
            a["studies"].add(t["nct"])
            a["direct"] = a.get("direct", 0) + (t["rel"] == "Direct")
            a["completed"] += t["status"] == "COMPLETED"
            a["active"] += t["status"] in ACTIVE
            a["industry"] += t["sponsor_class"] == "INDUSTRY"
            a["last"] = max(a["last"], int((t["start"] or "0")[:4] or 0))
            for o in t.get("officials", []):
                if o["name"] and (len(locs) <= 2 or _aff_match(o["aff"], l["facility"])):
                    a["investigators"][_clean_name(o["name"])] += 1
    out = []
    for (fac, city, country), a in agg.items():
        n = len(a["studies"])
        score = n + 2 * a.get("direct", 0) + a["completed"] + 0.5 * a["industry"] + (1 if a["last"] >= date.today().year - 5 else 0)
        inv = a["investigators"].most_common(1)
        out.append({"key": f"{fac}|{city}|{country}", "facility": fac, "city": city, "country": country, "studies": n, "direct": a.get("direct", 0),
                    "completed": a["completed"], "active": a["active"], "industry": a["industry"], "last": a["last"],
                    "investigator": inv[0][0] if inv else "", "score": score, "ncts": sorted(a["studies"])})
    out.sort(key=lambda r: -r["score"])
    return out


def _aff_match(aff, fac):
    a = set(re.findall(r"[a-z]{4,}", (aff or "").lower())) - {"hospital", "university", "universidade", "universidad", "federal", "national", "nacional", "instituto", "institute", "center", "centre", "hospital", "clinic", "clinica"}
    f = set(re.findall(r"[a-z]{4,}", (fac or "").lower()))
    return len(a & f) >= 1


def _clean_name(n):
    return re.split(r",\s*(md|phd|msc|rd|bsc|ms|bachelor|master|doctor|dr)\b", n, flags=re.I)[0].strip()


def survey_results(questions, invites):
    done = [i for i in invites if i["answers"]]
    by_c = defaultdict(lambda: {"contacted": 0, "completed": 0, "interested": 0, "rate": [], "volume": []})
    for i in invites:
        c = by_c[i["site"]["country"]]
        c["contacted"] += i["status"] != "draft"
        if i["answers"]:
            a = i["answers"]
            c["completed"] += 1
            if _num(a.get("int_level")) >= 4:
                c["interested"] += 1
            if _num(a.get("pt_rate")) > 0:
                c["rate"].append(_num(a.get("pt_rate")))
            if _num(a.get("pt_volume")) > 0:
                c["volume"].append(_num(a.get("pt_volume")))
    dist = {}
    for q in questions:
        if q["kind"] in ("single", "multi", "scale"):
            cnt = Counter()
            for i in done:
                v = i["answers"].get(q["id"])
                for x in (v if isinstance(v, list) else [v] if v else []):
                    cnt[x] += 1
            dist[q["id"]] = cnt
    rates = [r for c in by_c.values() for r in c["rate"]]
    site_rank = []
    for i in done:
        a = i["answers"]
        cap = sum(1 for k in ("ca_coord",) if a.get(k) == "Yes") + (a.get("ca_edc") == "Regularly") + (a.get("ca_prior") in ("3–5", "More than 5"))
        site_rank.append({"site": i["site"], "interest": _num(a.get("int_level")), "rate": _num(a.get("pt_rate")), "volume": _num(a.get("pt_volume")),
                          "cap": cap, "score": _num(a.get("int_level")) * 10 + min(_num(a.get("pt_rate")), 20) * 2 + cap * 5, "synthetic": i["synthetic"]})
    site_rank.sort(key=lambda r: -r["score"])
    return {"n_invited": len(invites), "n_sent": sum(i["status"] != "draft" for i in invites), "n_done": len(done),
            "by_country": dict(by_c), "dist": dist, "median_rate": statistics.median(rates) if rates else None,
            "site_rank": site_rank, "synthetic": any(i["synthetic"] for i in done)}


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


# ------------------------------------------------------------------ pillar 4

def sample_size(req, bench, ov):
    lit = [x["value"] for x in bench["literature"] if x.get("value")]
    p_default = round(statistics.median(lit), 2) if lit else 0.5
    p = _f(ov, "expected_p", _f(req, "expected_p", p_default * 100) / 100 if req.get("expected_p") else p_default)
    if p > 1:
        p /= 100
    d = _f(ov, "margin", _f(req, "margin", 3)) / 100
    deff = _f(ov, "deff", 1.5)
    level = ov.get("precision", "region")
    k = max(len(req["countries"]), 1)
    n_one = math.ceil(Z * Z * p * (1 - p) / (d * d) * deff)
    n_calc = n_one * (k if level == "country" else 1)
    n = int(_f(req, "target_n", 0)) or n_calc
    n = int(_f(ov, "target_n", n))
    per_c = n / k
    margin_c = Z * math.sqrt(p * (1 - p) * deff / per_c) if per_c > 0 else None
    return {"p": p, "p_src": "median of published figures" if lit and "expected_p" not in ov else "user", "margin": d, "deff": deff, "level": level,
            "n_calc": n_calc, "n": n, "per_country_margin": margin_c, "k": k}


def simulate(countries, n_target, rate, total_sites, ramp=3, startup_shift=0, max_m=60):
    """Month-by-month enrolment across countries. Sites per country ∝ score-weighted pool, min 2."""
    if not countries or not rate or rate <= 0:
        return None
    alloc = allocate_sites(countries, total_sites)
    cum, curve, done = 0.0, [(0, 0)], None
    per_c = {c["country"]: 0.0 for c in countries}
    for m in range(1, max_m + 1):
        for c in countries:
            open_m = m - (c["startup"] + startup_shift)
            if open_m <= 0:
                continue
            frac = min(open_m / ramp, 1.0)
            add = alloc[c["country"]] * frac * rate
            per_c[c["country"]] += add
            cum += add
        curve.append((m, min(cum, n_target)))
        if cum >= n_target:
            done = m
            break
    return {"months": done, "curve": curve, "alloc": alloc, "per_country": per_c}


def allocate_sites(countries, total):
    w = {c["country"]: max(c["reach"] or 0, 1) ** 0.5 * (0.5 + c["score"] / 100) for c in countries}
    s = sum(w.values()) or 1
    alloc = {k: max(2, round(total * v / s)) for k, v in w.items()}
    return alloc


def scenarios(req, cevals, bench, ss, ov, survey):
    rate_b = bench["rate"]
    reported = survey["median_rate"]
    if reported:
        realism = _f(ov, "realism", 0.5)
        base_rate = reported * realism
        rate_src = f"investigator survey median {reported:g}/month × {realism:.0%} realism factor (J)"
    elif rate_b["median"]:
        base_rate = rate_b["median"]
        rate_src = f"median of {rate_b['n']} {bench['pace_basis']} (ClinicalTrials.gov)"
    else:
        base_rate = 2.0
        rate_src = "default 2 patients/site/month (J)"
    base_rate = _f(ov, "rate", base_rate)
    lo = rate_b["p25"] if (rate_b["p25"] and not reported and "rate" not in ov) else base_rate * 0.6
    hi = rate_b["p75"] if (rate_b["p75"] and not reported and "rate" not in ov) else base_rate * 1.5
    total_sites = int(_f(ov, "sites", max(5 * len(cevals), 12)))
    use = [c for c in cevals if c["tier"] != "Backup"] if ov.get("drop_backup") == "1" else cevals
    runs = {
        "Conservative": simulate(use, ss["n"], lo, total_sites, startup_shift=2),
        "Base": simulate(use, ss["n"], base_rate, total_sites),
        "Optimistic": simulate(use, ss["n"], hi, total_sites, startup_shift=-1),
    }
    return {"runs": runs, "rates": {"Conservative": lo, "Base": base_rate, "Optimistic": hi}, "rate_src": rate_src,
            "sites": total_sites, "countries_used": [c["country"] for c in use]}


def risks(req, ind, cevals, bench, ss, sc, survey):
    out = []
    names = [c["country"] for c in cevals]
    obs = req.get("study_type", "").startswith("obs") or req.get("study_type") == "registry"

    def add(area, risk, lik, imp, mit, basis):
        out.append({"area": area, "risk": risk, "lik": lik, "imp": imp, "mit": mit, "basis": basis})
    slow = [c for c in cevals if c["startup"] >= 6]
    if slow:
        add("Start-up", "Ethics/regulatory approval slower in " + ", ".join(c["country"] for c in slow), "High", "High",
            "Submit there first; use a central ethics route where allowed; plan the timeline from the slowest country.", "J: typical review times")
    if "Brazil" in names:
        add("Start-up", "Brazil: CEP/CONEP review for multicentre studies can add months (new framework under Law 14,874/2024 still bedding in)", "Medium", "High",
            "Confirm with a local regulatory consultant; start submission early.", "J")
    small = [c for c in cevals if c["reach"] is not None and c["reach"] < ss["n"] / max(len(cevals), 1)]
    if small:
        add("Patients", "Small reachable pool for an equal share of the sample in " + ", ".join(c["country"] for c in small), "Medium", "Medium",
            "Allocate sample in proportion to patients, not equally; or drop to backup list.", "E: GLOBOCAN × judgment shares")
    if bench["rate"]["n"] < 6:
        add("Benchmark", f"Few completed comparable studies with usable dates ({bench['rate']['n']}); enrolment pace is uncertain", "High", "Medium",
            "Weight the investigator survey more; run a short pilot at 2–3 sites.", "F: registry count")
    if ind["globocan"] is None:
        add("Patients", "No curated patient numbers for this indication; country patient pool not estimated", "High", "Medium",
            "Enter a prevalence per 100,000 or add a licensed data source.", "—")
    if obs:
        add("Bias", "Selection bias if sites enrol convenient rather than consecutive patients", "Medium", "High",
            "Require consecutive enrolment and screening logs; monitor screening-to-enrolment ratios.", "J")
        if "nutrition" in (ind["label"] + req.get("description", "")).lower():
            add("Measurement", "Different malnutrition tools across sites (NRS-2002, SGA, GLIM) make prevalence hard to compare", "High", "High",
                "Fix GLIM as the reference definition and train sites; collect raw inputs (weight loss, BMI, muscle) centrally.", "S: tools vary in published LatAm studies")
    add("Data protection", "Personal-data laws differ by country (" + "; ".join(f"{c['country']}: {c['law']}" for c in cevals[:6]) + ")", "Medium", "Medium",
        "Pseudonymise at source; data-processing agreements per country; local legal review.", "J")
    base = sc["runs"]["Base"]
    want = _f(req, "months", 0)
    if base and base["months"] and want and base["months"] > want:
        add("Timeline", f"Base case {base['months']} months exceeds the {want:.0f} months requested", "High", "High",
            "Add sites in priority countries, extend window, or relax the precision target.", "E: scenario model")
    if survey["n_done"] and survey["n_done"] < 5:
        add("Evidence", f"Only {survey['n_done']} investigator responses so far", "Medium", "Medium", "Send reminders; aim for 3+ responses per country.", "F: survey")
    order = {"High": 0, "Medium": 1, "Low": 2}
    out.sort(key=lambda r: (order[r["lik"]] + order[r["imp"]]))
    return out


def verdict(req, cevals, sc):
    base = sc["runs"]["Base"]
    want = _f(req, "months", 0)
    pri = [c["country"] for c in cevals if c["tier"] == "Priority"]
    if not base or not base["months"]:
        return "Challenging", "bad", "At the modelled pace the sample is not reached within 5 years."
    if want and base["months"] > want * 1.3:
        return "Challenging", "bad", f"Base case {base['months']} months vs {want:.0f} requested."
    if want and base["months"] > want or len(pri) < 2:
        return "Feasible with conditions", "med", f"Base case {base['months']} months" + (f" vs {want:.0f} requested" if want else "") + f"; {len(pri)} priority countries."
    return "Feasible", "low", f"Base case {base['months']} months" + (f" within the {want:.0f} requested" if want else "") + f"; priority countries: {', '.join(pri) or 'none'}."


# ------------------------------------------------------------------ all together

def analyse(project, invites=None):
    req = project["req"]
    ov = dict(project.get("settings") or {})
    weights = {k: _f(ov, "w_" + k, v) for k, v in DEFAULT_WEIGHTS.items()}
    ind = catalog.INDICATIONS[req["indication"]]
    bench = benchmark(req, ind)
    cevals = countries_eval(req, ind, bench, ov, weights)
    sites = site_candidates(req, bench)
    surv = survey_results(project["questions"], invites or [])
    ss = sample_size(req, bench, ov)
    sc = scenarios(req, cevals, bench, ss, ov, surv)
    rk = risks(req, ind, cevals, bench, ss, sc, surv)
    v = verdict(req, cevals, sc)
    return {"req": req, "ind": ind, "ov": ov, "weights": weights, "bench": bench, "countries": cevals, "sites": sites,
            "survey": surv, "ss": ss, "sc": sc, "risks": rk, "verdict": v}
