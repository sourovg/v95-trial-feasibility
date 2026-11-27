"""Pick-lists for the request form: therapeutic areas, indications, countries, study types.

Each indication knows how to search the registries (ClinicalTrials.gov condition and
extra terms) and, for cancers, which GLOBOCAN 2024 cancer sites make up its patient pool.
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

GLOBOCAN_URL = "https://gco.iarc.who.int/today/en/fact-sheets-populations"
GLOBOCAN_LABEL = "GLOBOCAN 2024, IARC/WHO country fact sheets (new cases 2024)"

# id, therapeutic area, label, ClinicalTrials.gov condition query, extra term query, GLOBOCAN sites
_IND = [
    # Oncology
    ("abd_onc_surgery_nutrition", "Oncology", "Malnutrition in abdominal cancer surgery (GI and HPB)",
     "malnutrition OR nutritional status OR nutritional risk OR cachexia OR sarcopenia",
     "(surgery OR surgical OR perioperative OR resection OR gastrectomy OR colectomy OR pancreatectomy OR hepatectomy OR esophagectomy) AND (cancer OR neoplasm OR tumor OR carcinoma OR oncology)",
     ["Colorectum", "Stomach", "Pancreas", "Liver", "Gallbladder", "Oesophagus"]),
    ("gi_cancer_surgery", "Oncology", "Gastrointestinal cancer surgery (outcomes, ERAS)",
     "gastric cancer OR colorectal cancer OR pancreatic cancer OR esophageal cancer OR liver cancer",
     "surgery OR resection OR ERAS OR perioperative", ["Colorectum", "Stomach", "Pancreas", "Liver", "Gallbladder", "Oesophagus"]),
    ("nsclc", "Oncology", "Non-small cell lung cancer", "non-small cell lung cancer", "", ["Lung"]),
    ("egfr_nsclc", "Oncology", "EGFR-mutant non-small cell lung cancer", "EGFR non-small cell lung cancer", "", ["Lung"]),
    ("breast", "Oncology", "Breast cancer", "breast cancer", "", ["Breast"]),
    ("crc", "Oncology", "Colorectal cancer", "colorectal cancer", "", ["Colorectum"]),
    ("gastric", "Oncology", "Gastric and gastro-oesophageal junction cancer", "gastric cancer OR gastroesophageal junction cancer", "", ["Stomach"]),
    ("pancreatic", "Oncology", "Pancreatic cancer", "pancreatic cancer", "", ["Pancreas"]),
    ("hcc", "Oncology", "Hepatocellular carcinoma", "hepatocellular carcinoma", "", ["Liver"]),
    ("prostate", "Oncology", "Prostate cancer", "prostate cancer", "", ["Prostate"]),
    ("ovarian", "Oncology", "Ovarian cancer", "ovarian cancer", "", ["Ovary"]),
    ("cervical", "Oncology", "Cervical cancer", "cervical cancer", "", ["Cervix uteri"]),
    ("bladder", "Oncology", "Bladder cancer", "bladder cancer OR urothelial carcinoma", "", ["Bladder"]),
    ("kidney", "Oncology", "Renal cell carcinoma", "renal cell carcinoma", "", ["Kidney"]),
    ("cancer_cachexia", "Oncology", "Cancer cachexia and nutrition (any tumour)", "cachexia OR malnutrition OR sarcopenia", "cancer OR neoplasm OR tumor", None),
    # Immunology & inflammation
    ("ad", "Immunology", "Atopic dermatitis", "atopic dermatitis", "", None),
    ("psoriasis", "Immunology", "Plaque psoriasis", "plaque psoriasis", "", None),
    ("ra", "Immunology", "Rheumatoid arthritis", "rheumatoid arthritis", "", None),
    ("uc", "Immunology", "Ulcerative colitis", "ulcerative colitis", "", None),
    ("crohn", "Immunology", "Crohn's disease", "Crohn disease", "", None),
    ("sle", "Immunology", "Systemic lupus erythematosus", "systemic lupus erythematosus", "", None),
    # Neuroscience
    ("mg", "Neuroscience", "Generalised myasthenia gravis", "myasthenia gravis", "", None),
    ("ms", "Neuroscience", "Multiple sclerosis", "multiple sclerosis", "", None),
    ("alz", "Neuroscience", "Alzheimer's disease (early)", "Alzheimer disease", "", None),
    ("migraine", "Neuroscience", "Migraine", "migraine", "", None),
    ("parkinson", "Neuroscience", "Parkinson's disease", "Parkinson disease", "", None),
    # Cardio-renal-metabolic
    ("t2d", "Cardio-metabolic", "Type 2 diabetes", "type 2 diabetes", "", None),
    ("obesity", "Cardio-metabolic", "Obesity", "obesity", "", None),
    ("hf", "Cardio-metabolic", "Heart failure", "heart failure", "", None),
    ("ckd", "Cardio-metabolic", "Chronic kidney disease", "chronic kidney disease", "", None),
    ("mash", "Cardio-metabolic", "MASH / NASH", "nonalcoholic steatohepatitis OR MASH", "", None),
    # Respiratory & infectious
    ("copd", "Respiratory", "COPD", "chronic obstructive pulmonary disease", "", None),
    ("asthma", "Respiratory", "Severe asthma", "severe asthma", "", None),
    ("rsv", "Infectious disease", "RSV", "respiratory syncytial virus", "", None),
    ("dengue", "Infectious disease", "Dengue", "dengue", "", None),
    # Rare
    ("dmd", "Rare disease", "Duchenne muscular dystrophy", "Duchenne muscular dystrophy", "", None),
    ("sma", "Rare disease", "Spinal muscular atrophy", "spinal muscular atrophy", "", None),
    ("hemophilia", "Rare disease", "Haemophilia A or B", "hemophilia", "", None),
]
INDICATIONS = {i[0]: {"id": i[0], "ta": i[1], "label": i[2], "cond": i[3], "term": i[4], "globocan": i[5]} for i in _IND}
AREAS = sorted({i[1] for i in _IND}, key=lambda a: (a != "Oncology", a))

REGIONS = {
    "Latin America": ["Argentina", "Brazil", "Chile", "Colombia", "Mexico", "Peru"],
    "Latin America (extended)": ["Argentina", "Brazil", "Chile", "Colombia", "Costa Rica", "Dominican Republic", "Ecuador", "Guatemala", "Mexico", "Panama", "Peru", "Uruguay"],
    "North America": ["United States", "Canada"],
    "Western Europe": ["Germany", "Italy", "Spain", "United Kingdom"],
    "Asia-Pacific": ["Australia", "China", "India", "Japan", "South Korea"],
    "Central & Eastern Europe": ["Poland"],
}
COUNTRIES = sorted({c for v in REGIONS.values() for c in v})

STUDY_TYPES = [
    ("obs_prospective", "Observational, prospective (non-interventional)"),
    ("obs_retrospective", "Observational, retrospective (chart review / RWD)"),
    ("registry", "Registry"),
    ("interventional", "Interventional (drug, device or nutrition)"),
]
DESIGNS = ["Cross-sectional (point prevalence)", "Prospective cohort", "Case-control", "Randomised controlled", "Single-arm", "Pragmatic / hybrid"]
PHASES = ["Not applicable", "Phase 1", "Phase 2", "Phase 3", "Phase 4"]
SETTINGS = ["Hospital inpatient (surgical)", "Hospital inpatient (medical)", "Outpatient / clinic", "Primary care", "Mixed"]
POPULATIONS = ["Adults (18+)", "Older adults (65+)", "Children", "All ages"]
SERVICES = [
    ("benchmark", "Benchmark analysis", "Similar studies, enrolment pace, published figures"),
    ("countries", "Country evaluation", "Patients, research activity, start-up time, competition"),
    ("investigators", "Investigator insights & site ID", "Candidate sites and an auto-designed investigator survey"),
    ("scenario", "Scenario & risk evaluation", "Sample size, timelines, risks and mitigations"),
]

# Start-up time to first patient (months) for the study type. Judgment, editable in the app.
# Ranges reflect typical ethics/regulatory review; verify with a local regulatory expert.
STARTUP = {  # country: (non-interventional, interventional)
    "Argentina": (4, 6), "Brazil": (6, 9), "Chile": (4, 7), "Colombia": (3, 5), "Mexico": (4, 7), "Peru": (4, 6),
    "Costa Rica": (4, 7), "Dominican Republic": (3, 5), "Ecuador": (4, 6), "Guatemala": (3, 5), "Panama": (3, 5), "Uruguay": (3, 5),
    "United States": (2, 4), "Canada": (3, 4), "Germany": (3, 5), "Italy": (4, 6), "Spain": (3, 5), "United Kingdom": (3, 5),
    "Australia": (2, 3), "China": (5, 8), "India": (4, 6), "Japan": (3, 5), "South Korea": (2, 4), "Poland": (3, 5),
}
DATA_LAW = {"Brazil": "LGPD", "Argentina": "Law 25.326", "Mexico": "LFPDPPP", "Colombia": "Law 1581", "Chile": "Law 19.628 (21.719 from Dec 2026)",
            "Peru": "Law 29733", "United States": "HIPAA (where applicable)", "Germany": "GDPR", "Italy": "GDPR", "Spain": "GDPR",
            "United Kingdom": "UK GDPR", "Poland": "GDPR", "China": "PIPL", "Japan": "APPI", "South Korea": "PIPA", "India": "DPDP Act",
            "Australia": "Privacy Act", "Canada": "PIPEDA / provincial"}

# Published figures for the worked example (verified against the PubMed abstracts).
LITERATURE = {
    "abd_onc_surgery_nutrition": [
        {"what": "Hospital malnutrition, 13 Latin American countries (ELAN, SGA, n=9,348)", "value": 0.502, "label": "50.2% malnourished; 11.2% severe",
         "cite": "Correia & Campos, Nutrition 2003", "url": "https://pubmed.ncbi.nlm.nih.gov/14559314/", "country": "Latin America"},
        {"what": "Hospital malnutrition, Brazil national survey (IBRANUTRI, SGA, n=4,000)", "value": 0.481, "label": "48.1% malnourished; 12.5% severe",
         "cite": "Waitzberg et al., Nutrition 2001", "url": "https://pubmed.ncbi.nlm.nih.gov/11448575/", "country": "Brazil"},
        {"what": "Pre-operative GI surgery candidates, Salvador, Brazil (GLIM; 64% cancer surgery)", "value": 0.323, "label": "32.3% malnourished (GLIM); 50.2% at risk (NRS-2002)",
         "cite": "Santos et al., Arq Bras Cir Dig 2022", "url": "https://pubmed.ncbi.nlm.nih.gov/35766608/", "country": "Brazil"},
        {"what": "Malnutrition risk in hospital wards, 10 Latin American countries (nutritionDay 2009–15, n=14,515)", "value": 0.396, "label": "39.6% at risk",
         "cite": "Correia et al., Clin Nutr 2021", "url": "https://pubmed.ncbi.nlm.nih.gov/34461585/", "country": "Latin America"},
    ],
}

_GLOBO = None


def globocan():
    global _GLOBO
    if _GLOBO is None:
        with open(os.path.join(ROOT, "data_snapshot", "globocan2024.json")) as f:
            _GLOBO = json.load(f)
    return _GLOBO


def options_json():
    """Pick-lists for the browser (indication search, region presets)."""
    return json.dumps({
        "indications": [{"id": v["id"], "ta": v["ta"], "label": v["label"]} for v in INDICATIONS.values()],
        "regions": REGIONS,
    })
