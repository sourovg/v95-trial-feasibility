"""Feasibility analytics on public ClinicalTrials.gov records: criteria, competing trials,
site track record and enrolment benchmarks/scenarios. Deterministic; no AI calls yet."""
import re
import statistics
from collections import defaultdict
from datetime import date

ACTIVE = {"RECRUITING", "NOT_YET_RECRUITING", "ENROLLING_BY_INVITATION"}


def parse_date(s):
    if not s:
        return None
    parts = [int(x) for x in s.split("-")]
    return date(parts[0], parts[1] if len(parts) > 1 else 6, parts[2] if len(parts) > 2 else 15)


def months_between(a, b):
    return (b - a).days / 30.44


# ---------- criteria ----------

TAGS = [
    ("Biomarker", r"egfr|mutation|pacc|alk|ros1|kras|her2|pd-l1|biomarker|g719"),
    ("Stage / setting", r"metastatic|advanced|stage|resect|curative|recurrent"),
    ("Line of therapy", r"prior|first-line|treatment-naive|untreated|previous(ly)? treated|regimen"),
    ("Performance status", r"ecog|karnofsky|performance status"),
    ("CNS", r"cns|brain|leptomening"),
    ("Organ function / labs", r"hepatic|renal|creatinine|bilirubin|neutrophil|platelet|hemoglobin|organ function"),
    ("Cardiac", r"qtc|cardiac|ejection|heart"),
    ("Lung toxicity", r"interstitial|pneumonitis|ild"),
]


def split_criteria(text):
    """Split the free-text eligibility block into inclusion/exclusion bullet lists."""
    inc, exc, cur = [], [], None
    for raw in (text or "").splitlines():
        line = raw.strip()
        low = line.lower()
        if not line:
            continue
        if "exclusion" in low and len(line) < 60:
            cur = exc
            continue
        if ("inclusion" in low or "eligibility criteria" in low) and len(line) < 60:
            cur = inc
            continue
        if line.startswith(("*", "-", "•")) or re.match(r"^\d+[.)]", line):
            item = re.sub(r"^(\*|-|•|\d+[.)])\s*", "", line).replace("\\_", "_").replace("\\>", ">").replace("\\<", "<")
            (cur if cur is not None else inc).append(item)
    tagged = []
    for kind, items in (("Include", inc), ("Exclude", exc)):
        for it in items:
            tags = [t for t, rx in TAGS if re.search(rx, it.lower())]
            tagged.append({"kind": kind, "text": it, "tags": tags})
    return tagged


# ---------- competing trials ----------

def inclusion_text(criteria):
    """Inclusion part only: exclusion lists often name other mutations, which would
    otherwise look like overlap."""
    low = (criteria or "").lower()
    i = low.find("exclusion criteria")
    return low[:i] if i > 0 else low[:6000]


def score_overlap(t, profile):
    """Score how directly a trial competes for the same patients. Returns (score, reasons).
    Uses title, conditions, keywords and inclusion criteria; exclusion text is ignored."""
    title = (t["title"] + " " + t["official"]).lower()
    meta = " ".join([title, " ".join(t["conditions"]), " ".join(t["keywords"])]).lower()
    txt = meta + " " + inclusion_text(t["criteria"])
    score, why = 0, []
    core = profile.get("core_terms", [])
    inc = inclusion_text(t["criteria"])
    if core and not any(w in meta or w in inc[:3000] for w in core):
        return -1, ["required biomarker not in inclusion"]
    for w in core:
        neg = r"(no |without |negative for |absence of |lack\w* |wild[- ]type)[^.\n]{0,80}" + re.escape(w)
        if re.search(neg, inc) and w not in title:
            return -1, ["requires " + w.upper() + "-negative patients"]
    if any(w in txt for w in profile.get("setting_terms", [])):
        score += 1; why.append("advanced/metastatic")
    if any(w in title for w in profile.get("early_terms", [])) and not any(w in title for w in profile.get("setting_terms", [])):
        score -= 2; why.append("early-stage setting")
    if any(w in txt for w in profile.get("line_terms", [])):
        score += 1; why.append("first-line / untreated")
    if any(w in title for w in profile.get("later_line_terms", [])):
        score -= 1; why.append("later line")
    hits = [w for w in profile.get("focus_terms", []) if w in txt]
    if hits:
        score += 2; why.append("same subtype (" + ", ".join(sorted(set(h.strip() for h in hits))[:3]) + ")")
    return score, why


def tier(score):
    return "Direct" if score >= 3 else "Partial" if score >= 1 else "Low"


def site_key(l):
    f = re.sub(r"[^a-z0-9]+", " ", l["facility"].lower())
    f = re.sub(r"\b(the|inc|llc|research site|site)\b", "", f)
    return (re.sub(r"\s+", " ", f).strip(), (l["city"] or "").lower(), l["country"])


def competing(target, studies, profile):
    tkeys = {site_key(l) for l in target["locations"]}
    out = []
    for t in studies:
        if t["nct"] == target["nct"] or t["status"] not in ACTIVE or t["type"] != "INTERVENTIONAL":
            continue
        sc, why = score_overlap(t, profile)
        keys = {site_key(l) for l in t["locations"]}
        countries = defaultdict(int)
        for l in t["locations"]:
            countries[l["country"]] += 1
        out.append({**t, "score": sc, "why": why, "tier": tier(sc), "n_sites": len(t["locations"]),
                    "shared_sites": len(keys & tkeys), "countries": dict(countries)})
    out.sort(key=lambda x: (-x["score"], -x["shared_sites"], -(x["enroll"] or 0)))
    return out


# ---------- sites ----------

def site_track_record(target, studies, comp, since_year=2016):
    """Rank facilities by how many similar trials they ran since since_year (public listing
    only: ClinicalTrials.gov does not publish per-site enrolment)."""
    tkeys = {site_key(l) for l in target["locations"]}
    load = defaultdict(int)  # active Direct/Partial competing trials at the site
    for c in comp:
        if c["tier"] in ("Direct", "Partial"):
            for l in c["locations"]:
                load[site_key(l)] += 1
    sites = {}
    for t in studies:
        sd = parse_date(t["start"])
        if not sd or sd.year < since_year or t["type"] != "INTERVENTIONAL":
            continue
        for l in t["locations"]:
            if not l["facility"] or l["facility"].lower().strip() in ("research site", "local institution", "site"):
                continue  # anonymised listings (e.g. "Research Site") can't be told apart
            k = site_key(l)
            s = sites.setdefault(k, {"facility": l["facility"], "city": l["city"], "state": l["state"],
                                     "country": l["country"], "trials": set(), "industry": 0,
                                     "completed": 0, "terminated": 0})
            if t["nct"] in s["trials"]:
                continue
            s["trials"].add(t["nct"])
            s["industry"] += t["sponsor_class"] == "INDUSTRY"
            s["completed"] += t["status"] == "COMPLETED"
            s["terminated"] += t["status"] in ("TERMINATED", "WITHDRAWN")
    out = []
    for k, s in sites.items():
        n = len(s["trials"])
        out.append({**s, "n": n, "trials": sorted(s["trials"]), "load": load.get(k, 0), "in_target": k in tkeys})
    out.sort(key=lambda x: (-x["n"], -x["industry"], x["load"]))
    return out


# ---------- enrolment benchmarks ----------

def benchmarks(studies, enrol_fraction=0.6, profile=None, since_year=2012):
    """Patients per site per month from finished industry phase 2/3 trials with actual
    enrolment, actual start and primary-completion dates, and >=5 listed sites.
    Start->primary completion includes treatment and follow-up, so we assume enrolment ran
    for enrol_fraction of that window [J]."""
    rows = []
    for t in studies:
        if t["sponsor_class"] != "INDUSTRY" or t["enroll_type"] != "ACTUAL" or not t["enroll"]:
            continue
        if not ({"PHASE2", "PHASE3"} & set(t["phases"])):
            continue
        if t["status"] not in ("COMPLETED", "ACTIVE_NOT_RECRUITING") or t["pcd_type"] != "ACTUAL":
            continue
        a, b, n = parse_date(t["start"]), parse_date(t["pcd"]), len(t["locations"])
        if not a or not b or n < 5 or t["enroll"] < 30 or a.year < since_year:
            continue
        sc, _ = score_overlap(t, profile or {})
        if sc < 0:
            continue
        m = months_between(a, b)
        if m < 6:
            continue
        rate = t["enroll"] / (n * m * enrol_fraction)
        rows.append({**t, "n_sites": n, "months": m, "rate": rate, "tier": tier(sc),
                     "subtype": _subtype_in_meta(t, profile or {})})
    rows.sort(key=lambda r: r["rate"])
    sub = [r for r in rows if r["subtype"]]
    basis = sub if len(sub) >= 4 else rows
    summary = _summ([r["rate"] for r in basis])
    summary["basis"] = "same or analogous rare-subtype trials" if basis is sub else "all similar trials"
    summary["all"] = _summ([r["rate"] for r in rows])
    summary["sub"] = _summ([r["rate"] for r in sub])
    return rows, summary


def _subtype_in_meta(t, profile):
    meta = " ".join([t["title"], t["official"], " ".join(t["conditions"]), " ".join(t["keywords"])]).lower()
    return any(w in meta for w in profile.get("focus_terms", []) + profile.get("analog_terms", []))


def _summ(rates):
    if len(rates) >= 4:
        q = statistics.quantiles(rates, n=4)
        summary = {"n": len(rates), "p25": q[0], "median": q[1], "p75": q[2]}
    elif rates:
        summary = {"n": len(rates), "p25": min(rates), "median": statistics.median(rates), "p75": max(rates)}
    else:
        summary = {"n": 0, "p25": 0.05, "median": 0.1, "p75": 0.2}
    return summary


def enrolment_curve(target_n, sites, rate, ramp_months=6, max_months=96):
    """Sites switch on evenly over ramp_months; each enrols `rate` patients/month."""
    cum, curve, done = 0.0, [(0, 0.0)], None
    for m in range(1, max_months + 1):
        active = sites * min(1.0, m / ramp_months) if ramp_months else sites
        cum += active * rate
        curve.append((m, min(cum, target_n)))
        if done is None and cum >= target_n:
            done = m
            break
    return curve, done
