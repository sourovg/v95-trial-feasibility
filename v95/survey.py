"""Investigator feasibility questionnaire, designed from the request by rules (+ optional AI).

Five pillars, as used in CRO feasibility questionnaires:
  1 Interest  2 Medical practice  3 Study design acceptance  4 Patient pool & enrolment  5 Site capabilities
Each question records the rule that added it, so the sponsor can see why it is there.
"""
from . import ai, catalog

PILLARS = [
    ("interest", "Interest", "Is the investigator interested and available?"),
    ("practice", "Medical practice", "How are these patients managed today?"),
    ("design", "Study design acceptance", "Would the proposed design work at this site?"),
    ("patients", "Patient pool & enrolment potential", "How many patients, how fast?"),
    ("capabilities", "Site capabilities & resources", "Can the site run the study?"),
]
YN = ["Yes", "No", "Not sure"]


def _q(pillar, qid, text, kind, options=None, rule="always asked", unit=""):
    return {"pillar": pillar, "id": qid, "text": text, "kind": kind, "options": options or [], "rule": rule, "unit": unit}


def design(req):
    ind = catalog.INDICATIONS[req["indication"]]
    t = " ".join([req.get("description", ""), req.get("objective", ""), req.get("endpoints", ""), req.get("keywords", ""), ind["label"]]).lower()
    obs = req.get("study_type", "").startswith("obs") or req.get("study_type") == "registry"
    nutrition = any(w in t for w in ("nutrition", "malnutrition", "cachexia", "sarcopenia"))
    surgery = any(w in t for w in ("surg", "resection", "operat")) or "surgical" in req.get("setting", "").lower()
    onc = ind["ta"] == "Oncology"
    prevalence = "prevalence" in t or "cross-sectional" in req.get("design", "").lower()
    lab = ind["label"].split(" (")[0].lower()
    qs = []
    # 1 Interest
    qs += [
        _q("interest", "int_level", f"How interested are you in taking part in a study on {lab}?", "scale", ["1", "2", "3", "4", "5"]),
        _q("interest", "int_full", "If this feasibility leads to a full study, would you want to be considered as a site?", "single", YN),
        _q("interest", "int_conflict", "Are you running studies that would compete for the same patients in the next 12 months?", "single", YN),
    ]
    # 2 Medical practice
    if nutrition:
        qs += [
            _q("practice", "pr_screen", "Which nutritional screening or assessment tools are used routinely before surgery?", "multi",
               ["NRS-2002", "MUST", "MNA", "SGA / PG-SGA", "GLIM criteria", "None routinely", "Other"], "topic: nutrition"),
            _q("practice", "pr_screen_pct", "Roughly what share of these patients are screened for malnutrition before surgery?", "single",
               ["Under 25%", "25–50%", "50–75%", "Over 75%"], "topic: nutrition"),
            _q("practice", "pr_support", "Which nutritional support is part of standard care?", "multi",
               ["Dietitian consultation", "Oral nutritional supplements", "Immunonutrition", "Enteral nutrition", "Parenteral nutrition", "Prehabilitation programme", "None"], "topic: nutrition"),
            _q("practice", "pr_dietitian", "Is a dietitian part of the surgical team?", "single", ["Yes, dedicated", "Yes, shared / on request", "No"], "topic: nutrition"),
        ]
    if surgery:
        qs += [_q("practice", "pr_eras", "Is an enhanced recovery (ERAS) pathway used for these operations?", "single", ["Yes, for most", "For some", "No"], "setting: surgery")]
    if onc:
        qs += [_q("practice", "pr_mdt", "Are these patients discussed in a multidisciplinary tumour board?", "single", ["Always", "Usually", "Rarely"], "area: oncology")]
    if not (nutrition or surgery or onc):
        qs += [_q("practice", "pr_soc", "Briefly describe standard of care for these patients at your site.", "text")]
    # 3 Design acceptance
    if obs:
        qs += [
            _q("design", "de_consent", "Would your ethics committee require written informed consent for this non-interventional study?", "single", ["Yes", "No, waiver likely", "Not sure"], "type: observational"),
            _q("design", "de_consecutive", "Could you enrol consecutive eligible patients (to avoid selection bias)?", "single", YN, "type: observational"),
            _q("design", "de_burden", "Acceptable data-collection time per patient", "single", ["Under 15 min", "15–30 min", "30–60 min", "Over 60 min"], "type: observational"),
        ]
        if not prevalence:
            qs += [_q("design", "de_fu", "Is follow-up to 30 days after surgery feasible from routine records?", "single", YN, "design: cohort follow-up")]
        else:
            qs += [_q("design", "de_fu", "Could 30-day post-operative outcomes be collected from routine records?", "single", YN, "endpoint: complications")]
    else:
        qs += [
            _q("design", "de_random", "Would patients and physicians accept randomisation?", "single", YN, "type: interventional"),
            _q("design", "de_criteria", "Do the key inclusion and exclusion criteria exclude many of your patients?", "single", ["Few", "About half", "Most"], "type: interventional"),
            _q("design", "de_visits", "Is the visit schedule acceptable for your patients?", "single", YN, "type: interventional"),
        ]
    # 4 Patient pool
    pool_label = "abdominal cancer operations (gastric, colorectal, pancreatic, liver, oesophageal)" if (surgery and onc) else f"patients with {lab}"
    qs += [
        _q("patients", "pt_volume", f"How many {pool_label} does your site see per year?", "number", unit="per year", rule="always asked"),
        _q("patients", "pt_rate", "How many eligible patients could you realistically enrol per month?", "number", unit="per month", rule="always asked"),
    ]
    if nutrition:
        qs += [_q("patients", "pt_malnut", "In your estimate, what share of these patients are malnourished before surgery?", "single", ["Under 20%", "20–40%", "40–60%", "Over 60%"], "topic: nutrition")]
    if surgery and onc:
        qs += [_q("patients", "pt_mix", "Main operations at your site (select all with 20+ per year)", "multi",
                  ["Gastrectomy", "Colectomy / rectal resection", "Pancreatoduodenectomy", "Hepatectomy", "Oesophagectomy"], "setting: oncology surgery")]
    # 5 Capabilities
    qs += [
        _q("capabilities", "ca_coord", "Do you have a study coordinator or research nurse available?", "single", YN),
        _q("capabilities", "ca_edc", "Experience with electronic data capture (EDC) systems", "single", ["Regularly", "Occasionally", "Never"]),
        _q("capabilities", "ca_ethics", "Typical time from submission to ethics approval at your site", "single", ["Under 2 months", "2–4 months", "4–6 months", "Over 6 months"]),
        _q("capabilities", "ca_prior", "Studies of this kind your site has done in the last 5 years", "single", ["None", "1–2", "3–5", "More than 5"]),
    ]
    if nutrition:
        qs += [_q("capabilities", "ca_bodycomp", "Body-composition and function measures available", "multi",
                  ["Bioimpedance (BIA)", "CT muscle analysis (L3)", "Hand-grip dynamometer", "Albumin / prealbumin", "None"], "topic: nutrition")]
    qs += [_q("capabilities", "ca_comment", "Anything that would make this study hard or easy at your site?", "text")]

    ai_qs = []
    if ai.available():
        for i, q in enumerate(ai.extra_questions(req, [x["text"] for x in qs])):
            ai_qs.append(_q(q["pillar"], f"ai_{i}", q["text"], q["kind"], q.get("options") or (["1", "2", "3", "4", "5"] if q["kind"] == "scale" else []), "AI: tailored to this request"))
    return qs + ai_qs


def by_pillar(qs):
    return [(pid, name, desc, [q for q in qs if q["pillar"] == pid]) for pid, name, desc in PILLARS]
