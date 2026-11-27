"""Turn a free-text feasibility request (RFP) into structured fields.

Rules first (deterministic, explainable). If the optional `anthropic` package and an
ANTHROPIC_API_KEY are present, Claude reads the text too and fills gaps; rules still win
where they are confident, and every field records where it came from.
"""
import re

from . import ai, catalog

EXAMPLE_TEXT = ("A standalone feasibility assessment to be performed to see the prevalence of malnutrition and "
                "nutritional gaps in abdominal oncology surgery in patients from Latin America. This will be a "
                "prospective, multi-center, non-interventional observational study. The feasibility assessment will "
                "help decide on a full study in Latin America.")

EXAMPLE = {
    "title": "Malnutrition and nutritional gaps in abdominal oncology surgery, Latin America",
    "sponsor": "Mid-size pharma (nutrition franchise)",
    "description": EXAMPLE_TEXT,
    "ta": "Oncology",
    "indication": "abd_onc_surgery_nutrition",
    "keywords": "malnutrition, GLIM, NRS-2002, sarcopenia, perioperative nutrition, gastrectomy, colectomy, pancreatectomy",
    "study_type": "obs_prospective",
    "design": "Cross-sectional (point prevalence)",
    "phase": "Not applicable",
    "setting": "Hospital inpatient (surgical)",
    "population": "Adults (18+)",
    "region": "Latin America",
    "countries": ["Argentina", "Brazil", "Chile", "Colombia", "Mexico", "Peru"],
    "objective": "Estimate the prevalence of malnutrition (GLIM) and gaps in nutritional screening and support before and after abdominal cancer surgery.",
    "endpoints": "Prevalence of malnutrition by GLIM; share screened pre-operatively; share receiving nutritional support; 30-day complications by nutritional status",
    "target_n": "",
    "margin": "4",
    "expected_p": "",
    "months": "18",
    "decision": "Go / no-go and country selection for a full Latin America study",
    "services": ["benchmark", "countries", "investigators", "scenario"],
}

_TYPE_RULES = [
    (r"non[- ]?interventional|observational|real[- ]world|chart review|cohort study", "obs_prospective"),
    (r"retrospective|chart review|database|claims|ehr", "obs_retrospective"),
    (r"\bregistry\b", "registry"),
    (r"randomi[sz]ed|interventional|phase\s*(1|2|3|i{1,3})\b|placebo|investigational product", "interventional"),
]
_DESIGN_RULES = [
    (r"prevalence|cross[- ]sectional|point prevalence", "Cross-sectional (point prevalence)"),
    (r"case[- ]control", "Case-control"),
    (r"randomi[sz]ed", "Randomised controlled"),
    (r"single[- ]arm", "Single-arm"),
    (r"cohort|follow[- ]up|prospective", "Prospective cohort"),
]
_IND_RULES = [
    (r"malnutrition|nutrition|cachexia|sarcopenia", r"surg|resection|operat", r"abdominal|gastro|gastric|colorectal|pancrea|liver|hepat|oesophag|esophag|\bgi\b", "abd_onc_surgery_nutrition"),
    (r"malnutrition|nutrition|cachexia|sarcopenia", r"cancer|oncolog|tumou?r|neoplas", None, "cancer_cachexia"),
]
_COUNTRY_ALIASES = {"usa": "United States", "u.s.": "United States", "us ": "United States", "uk": "United Kingdom", "korea": "South Korea", "brasil": "Brazil", "méxico": "Mexico"}


def parse_rules(text):
    t = " " + (text or "").lower() + " "
    out, why = {}, {}
    for pat, val in _TYPE_RULES:
        if re.search(pat, t):
            out["study_type"] = val
            why["study_type"] = f"matched “{re.search(pat, t).group(0).strip()}”"
            if val == "obs_prospective" and re.search(r"retrospective|chart review", t):
                out["study_type"] = "obs_retrospective"
            break
    for pat, val in _DESIGN_RULES:
        if re.search(pat, t):
            out["design"] = val
            why["design"] = f"matched “{re.search(pat, t).group(0).strip()}”"
            break
    if "study_type" in out and out["study_type"] != "interventional":
        out["phase"] = "Not applicable"
    else:
        m = re.search(r"phase\s*(1|2|3|4|iv|iii|ii|i)\b", t)
        if m:
            out["phase"] = "Phase " + {"i": "1", "ii": "2", "iii": "3", "iv": "4"}.get(m.group(1), m.group(1))
    for a, b, c, ind in _IND_RULES:
        if re.search(a, t) and re.search(b, t) and (c is None or re.search(c, t)):
            out["indication"] = ind
            why["indication"] = "topic words: " + ", ".join(sorted({m.group(0) for p in (a, b, c) if p for m in [re.search(p, t)] if m}))
            break
    if "indication" not in out:
        best = None
        for ind in catalog.INDICATIONS.values():
            name = ind["label"].lower().split(" (")[0]
            if name in t and (best is None or len(name) > len(best[1])):
                best = (ind["id"], name)
        if best:
            out["indication"], why["indication"] = best[0], f"matched “{best[1]}”"
    if out.get("indication"):
        out["ta"] = catalog.INDICATIONS[out["indication"]]["ta"]
    countries = [c for c in catalog.COUNTRIES if c.lower() in t]
    countries += [v for k, v in _COUNTRY_ALIASES.items() if k in t and v not in countries]
    for region, cs in catalog.REGIONS.items():
        if region.lower() in t and "extended" not in region:
            out["region"] = region
            countries = list(dict.fromkeys(countries + cs))
            why["countries"] = f"region “{region}” → standard country set"
            break
    if countries:
        out["countries"] = sorted(countries)
        why.setdefault("countries", "country names in text")
    if re.search(r"surg|operat|resection", t):
        out["setting"] = "Hospital inpatient (surgical)"
        why["setting"] = "surgical patients"
    if re.search(r"older adults|elderly|65\+", t):
        out["population"] = "Older adults (65+)"
    elif re.search(r"paediatric|pediatric|children", t):
        out["population"] = "Children"
    m = re.search(r"(\d[\d,]{1,6})\s*(patients|participants|subjects)", t)
    if m:
        out["target_n"] = m.group(1).replace(",", "")
    if re.search(r"multi[- ]?cent(er|re)|multicent", t):
        why["multicentre"] = "multi-centre study"
    if re.search(r"prevalence", t):
        out["objective"] = "Estimate prevalence" + (" of malnutrition" if "malnutrition" in t else "") + " in the target population."
    return out, why


def parse(text):
    """Return (fields, provenance) merging rules and, when available, Claude."""
    fields, why = parse_rules(text)
    prov = {k: "rule: " + why.get(k, "pattern") for k in fields}
    aif = ai.extract_request(text) if ai.available() else None
    if aif:
        for k, v in aif.items():
            if v and k not in fields:
                fields[k] = v
                prov[k] = "AI (Claude) reading of the description"
    return fields, prov


def normalise(form):
    """Clean a submitted form (dict of str or list) into a request dict."""
    r = {k: (v if isinstance(v, list) else (v or "").strip()) for k, v in form.items()}
    r["countries"] = [c for c in (form.get("countries") or []) if c in catalog.COUNTRIES] if isinstance(form.get("countries"), list) else [c for c in (form.get("countries") or "").split(",") if c in catalog.COUNTRIES]
    if not r["countries"] and r.get("region") in catalog.REGIONS:
        r["countries"] = list(catalog.REGIONS[r["region"]])
    if r.get("indication") not in catalog.INDICATIONS:
        r["indication"] = "abd_onc_surgery_nutrition" if not r.get("indication") else r["indication"]
        if r["indication"] not in catalog.INDICATIONS:  # free text: try to match a known indication
            f, _ = parse_rules(r["indication"])
            r["indication"] = f.get("indication", "abd_onc_surgery_nutrition")
    r["services"] = r.get("services") if isinstance(r.get("services"), list) else [s for s, _, _ in catalog.SERVICES]
    r["title"] = r.get("title") or catalog.INDICATIONS[r["indication"]]["label"]
    return r
