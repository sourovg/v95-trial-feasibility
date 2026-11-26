"""Curated public epidemiology for patient-population funnels.

Every step carries: base / low / high value, a label ([F] verified fact, [S] published
source read via a search snippet or secondary page, [E] estimate derived from sources,
[J] judgment) and a source link. Nothing here is patient-level data.

A "profile" ties an indication to a trial design. Only one profile is curated in this
demo (EGFR PACC first-line advanced NSCLC). Any other trial gets the generic funnel,
where the user types the starting numbers.
"""
import csv
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SRC = {
    "seer_lung": ("SEER Cancer Stat Facts: Lung and Bronchus Cancer (read 2026-11-26)",
                  "https://seer.cancer.gov/statfacts/html/lungb.html"),
    "acs_nsclc": ("American Cancer Society: What is lung cancer? (NSCLC is about 80-85% of lung cancers)",
                  "https://www.cancer.org/cancer/types/lung-cancer/about/what-is.html"),
    "mda_egfr": ("MD Anderson / Robichaux et al., Nature 2021: EGFR mutations in ~15% of NSCLC in North America, ~30-40% in Asia",
                 "https://www.mdanderson.org/newsroom/classifying-egfr-mutations-by-structure-and-function.h00-159464001.html"),
    "us_egfr19": ("US cohort table: EGFR mutation prevalence 19% (J Pers Med 2017)",
                  "https://pmc.ncbi.nlm.nih.gov/articles/PMC5618152/table/jpm-07-00005-t001"),
    "robichaux": ("Robichaux et al., Nature 2021: 30.8% of EGFR-mutant patients atypical (+2.2% both); PACC = 156/358 atypical in afatinib cohort",
                  "https://pmc.ncbi.nlm.nih.gov/articles/PMC8481125"),
    "unger": ("Unger et al., JNCI 2019: 8.1% of adult cancer patients enrol in trials (95% CI 6.3-10.0%)",
              "https://www.fredhutch.org/en/news/releases/2019/02/research-shows-structural-barriers-are-the-biggest-reason-for-low-participation-in-clinical-trials.html"),
    "globocan_cn": ("IARC GLOBOCAN 2022 China fact sheet: 1,060,584 new lung cancer cases",
                    "https://gco.iarc.who.int/media/globocan/factsheets/populations/160-china-fact-sheet.pdf"),
    "wcrf_jp": ("WCRF compilation of GLOBOCAN 2022: Japan 136,723 new lung cancer cases",
                "https://www.wcrf.org/cancer-trends/lung-cancer-statistics/"),
    "census": ("US Census Bureau, Vintage 2025 state population estimates (NST-EST2025-ALLDATA)",
               "https://www2.census.gov/programs-surveys/popest/datasets/2020-2025/state/totals/"),
    "judgment": ("Analyst judgment; replace with a sourced figure or a licensed claims/EHR count", ""),
}


def step(key, label, base, low, high, tag, src, note=""):
    return {"key": key, "label": label, "base": base, "low": low, "high": high,
            "tag": tag, "src": src, "note": note}


PROFILES = {
    "egfr_pacc_1l": {
        "name": "EGFR PACC-mutant, first-line, locally advanced or metastatic NSCLC",
        "search_cond": "EGFR non-small cell lung cancer",
        "core_terms": ["egfr"],
        # Rare subtypes of similar frequency used as enrolment-rate analogs [J]
        "analog_terms": ["exon 20", "exon20", "ex20ins", "ex20"],
        "focus_terms": ["pacc", "uncommon", "atypical", "g719", "s768i", "l861q", "e709", "l718", "non-classical"],
        "line_terms": ["first-line", "first line", "1l ", "treatment-naive", "treatment naive", "untreated",
                       "no prior systemic", "previously untreated"],
        "later_line_terms": ["previously treated", "after progression", "progressed on", "second-line",
                             "second line", "after osimertinib", "following osimertinib", "resistant to"],
        "setting_terms": ["advanced", "metastatic", "stage iv", "unresectable", "recurrent"],
        "early_terms": ["adjuvant", "resectable", "early stage", "early-stage", "neoadjuvant", "stage ib", "perioperative"],
        "countries": {
            "United States": [
                step("incidence", "New lung and bronchus cancer cases per year (2026 estimate)", 229410, 229410, 229410, "F", "seer_lung"),
                step("nsclc", "Share that are non-small cell (NSCLC)", 0.82, 0.80, 0.85, "S", "acs_nsclc"),
                step("advanced", "Share locally advanced/metastatic and not curable at diagnosis", 0.58, 0.51, 0.65, "E", "seer_lung",
                     "SEER: 51% distant at diagnosis; base adds ~1/3 of the 21% regional (unresectable). Excludes later recurrences, so may undercount."),
                step("egfr", "Share with an EGFR mutation", 0.15, 0.12, 0.19, "S", "mda_egfr", "High end from a US cohort reporting 19% (us_egfr19)."),
                step("pacc", "Share of EGFR-mutant tumours that are PACC", 0.135, 0.10, 0.16, "E", "robichaux",
                     "Derived: ~31% atypical x ~44% PACC among atypical = ~13.5%. The 44% comes from a treated subset, not a population sample."),
                step("tested", "Share tested with a result in time for first-line decision", 0.80, 0.65, 0.90, "J", "judgment"),
                step("criteria", "Share meeting other key criteria (ECOG 0-1, organ function, no prior systemic therapy)", 0.55, 0.40, 0.70, "J", "judgment"),
                step("enrol", "Share who enrol in any trial (all competing trials together)", 0.081, 0.063, 0.10, "S", "unger",
                     "All adult cancers; lung and targeted-therapy trials may differ."),
            ],
            "China": [
                step("incidence", "New lung cancer cases per year (2022)", 1060584, 1060584, 1060584, "S", "globocan_cn"),
                step("nsclc", "Share that are NSCLC", 0.82, 0.80, 0.85, "E", "acs_nsclc", "US/ACS share applied; not China-specific."),
                step("advanced", "Share advanced at diagnosis", 0.60, 0.50, 0.70, "J", "judgment"),
                step("egfr", "Share with an EGFR mutation", 0.35, 0.30, 0.40, "S", "mda_egfr"),
                step("pacc", "Share of EGFR-mutant that are PACC", 0.135, 0.10, 0.16, "E", "robichaux", "Assumes same mix as Western series."),
                step("tested", "Tested with result for first-line decision", 0.60, 0.45, 0.80, "J", "judgment"),
                step("criteria", "Meets other key criteria", 0.55, 0.40, 0.70, "J", "judgment"),
                step("enrol", "Share who enrol in any trial", 0.05, 0.02, 0.08, "J", "judgment"),
            ],
            "Japan": [
                step("incidence", "New lung cancer cases per year (2022)", 136723, 136723, 136723, "S", "wcrf_jp"),
                step("nsclc", "Share that are NSCLC", 0.82, 0.80, 0.85, "E", "acs_nsclc", "US/ACS share applied."),
                step("advanced", "Share advanced at diagnosis", 0.55, 0.45, 0.65, "J", "judgment"),
                step("egfr", "Share with an EGFR mutation", 0.35, 0.30, 0.40, "S", "mda_egfr"),
                step("pacc", "Share of EGFR-mutant that are PACC", 0.135, 0.10, 0.16, "E", "robichaux"),
                step("tested", "Tested with result for first-line decision", 0.85, 0.70, 0.95, "J", "judgment"),
                step("criteria", "Meets other key criteria", 0.55, 0.40, 0.70, "J", "judgment"),
                step("enrol", "Share who enrol in any trial", 0.05, 0.02, 0.08, "J", "judgment"),
            ],
        },
    },
}

# NCT id -> profile key. Other trials fall back to the generic funnel.
TRIAL_PROFILES = {"NCT07185997": "egfr_pacc_1l"}

GENERIC_STEPS = [
    step("incidence", "New cases per year in the country (type a sourced number)", 10000, 10000, 10000, "J", "judgment"),
    step("stage", "Share in the trial's disease stage/setting", 0.5, 0.3, 0.7, "J", "judgment"),
    step("biomarker", "Share with the required biomarker/subtype", 1.0, 1.0, 1.0, "J", "judgment"),
    step("criteria", "Share meeting other key criteria", 0.5, 0.35, 0.65, "J", "judgment"),
    step("enrol", "Share who enrol in any trial", 0.05, 0.02, 0.08, "J", "judgment"),
]


def run_funnel(steps, overrides=None):
    """Multiply steps. overrides: {step_key: base value}. Returns rows plus totals.

    'pool' = eligible patients per year (all steps except 'enrol').
    'enrollable' = pool x enrol share. Low/high multiply every low/high together, so the
    range is wider than the true uncertainty [J]."""
    overrides = overrides or {}
    rows, b, lo, hi = [], 1.0, 1.0, 1.0
    pool = None
    for s in steps:
        s = dict(s)
        if s["key"] in overrides:
            s["base"], s["overridden"] = overrides[s["key"]], True
            s["low"] = min(s["low"], s["base"])
            s["high"] = max(s["high"], s["base"])
        if s["key"] == "enrol":
            pool = (b, lo, hi)
        b, lo, hi = b * s["base"], lo * s["low"], hi * s["high"]
        s["running"] = (b, lo, hi)
        rows.append(s)
    if pool is None:
        pool = (b, lo, hi)
    return {"rows": rows, "pool": pool, "enrollable": (b, lo, hi)}


def state_split(us_pool):
    """Crude: allocate a US annual figure by state population share [E]."""
    path = os.path.join(ROOT, "data_snapshot", "us_state_population_2025.csv")
    with open(path) as f:
        rows = [(r["state"], int(r["population_2025"])) for r in csv.DictReader(f)]
    tot = sum(p for _, p in rows)
    return sorted(((s, p, us_pool * p / tot) for s, p in rows), key=lambda x: -x[1])
