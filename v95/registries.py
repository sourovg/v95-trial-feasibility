"""Registries and literature beyond a single ClinicalTrials.gov record.

Queried live (cached 7 days, bundled snapshot offline):
  * ClinicalTrials.gov v2 — interventional and observational studies, by country
  * ISRCTN (UK-based, international, includes observational studies) — search API
  * PubMed E-utilities — count of published papers per country (evidence base)
Linked, not queried (no open API or bulk-download only):
  * WHO ICTRP (pulls 17+ registries, incl. ReBEC Brazil, REPEC Peru, RPCEC Cuba), EU CTIS,
    HMA-EMA Catalogue of RWD sources and studies, ISPOR/ISPE Real-World Evidence Registry.
"""
import hashlib
import json
import os
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from . import ctgov

FIELDS = ",".join([
    "NCTId", "BriefTitle", "OverallStatus", "Phase", "StudyType", "LeadSponsorName", "LeadSponsorClass",
    "EnrollmentCount", "EnrollmentType", "StartDate", "StartDateType", "PrimaryCompletionDate", "PrimaryCompletionDateType",
    "Condition", "Keyword", "DesignObservationalModel", "DesignTimePerspective",
    "OverallOfficialName", "OverallOfficialAffiliation", "OverallOfficialRole",
    "LocationFacility", "LocationCity", "LocationCountry", "LocationStatus",
])

LINKS = [
    ("WHO ICTRP", "https://trialsearch.who.int/", "Searches 17+ national registries at once, including ReBEC (Brazil), REPEC (Peru), RPCEC (Cuba), ChiCTR, CTRI, JRCT, EU CTR. No open API; weekly bulk download."),
    ("ReBEC (Brazil)", "https://ensaiosclinicos.gov.br/", "Brazilian Clinical Trials Registry; observational studies may register. Searchable through ICTRP."),
    ("EU CTIS", "https://euclinicaltrials.eu/", "EU Clinical Trials Information System (interventional trials in the EU/EEA since 2023)."),
    ("HMA-EMA Catalogues of RWD", "https://catalogues.ema.europa.eu/", "Real-world data sources and non-interventional studies in Europe (successor of the EU PAS Register)."),
    ("ISPOR/ISPE RWE Registry", "https://osf.io/registries/rwe/discover", "Pre-registration of hypothesis-evaluating real-world evidence studies (on OSF)."),
    ("PAHO / national cancer registries", "https://gco.iarc.who.int/", "GLOBOCAN country estimates (IARC/WHO) used for patient numbers."),
]


def _cached(url, kind="json", max_age_days=7):
    os.makedirs(ctgov.CACHE, exist_ok=True)
    k = hashlib.sha1(url.encode()).hexdigest()[:16] + (".json" if kind == "json" else ".txt")
    p = os.path.join(ctgov.CACHE, k)
    if os.path.exists(p) and time.time() - os.path.getmtime(p) < max_age_days * 86400:
        with open(p, encoding="utf-8") as f:
            return (json.load(f) if kind == "json" else f.read()), "cache"
    if not ctgov.OFFLINE:
        for attempt in range(3):
            try:
                if "eutils.ncbi" in url:  # NCBI allows ~3 requests/second without a key
                    time.sleep(0.4 + attempt)
                req = urllib.request.Request(url, headers={"User-Agent": "cohortia-feasibility-demo/0.2"})
                with urllib.request.urlopen(req, timeout=60) as r:
                    raw = r.read().decode("utf-8")
                data = json.loads(raw) if kind == "json" else raw
                with open(p, "w", encoding="utf-8") as f:
                    f.write(raw)
                return data, "live"
            except Exception:
                continue
    for folder in (ctgov.CACHE, ctgov.SNAPSHOT):
        q = os.path.join(folder, k)
        if os.path.exists(q):
            with open(q, encoding="utf-8") as f:
                return (json.load(f) if kind == "json" else f.read()), "snapshot (offline)"
    return None, "unavailable"


# ---------------------------------------------------------------- ClinicalTrials.gov

def ctgov_search(cond, term="", countries=None, study_type=None, max_pages=3):
    params = {"query.cond": cond, "pageSize": "1000", "fields": FIELDS, "countTotal": "true"}
    if term:
        params["query.term"] = term
    if countries:
        params["query.locn"] = " OR ".join(countries)
    if study_type:
        params["filter.advanced"] = f"AREA[StudyType]{study_type}"
    out, src, token, first = [], "live", None, None
    for _ in range(max_pages):
        p = dict(params)
        if token:
            p["pageToken"] = token
        url = ctgov.BASE + "?" + urllib.parse.urlencode(p)
        first = first or url
        data, s = _cached(url)
        if data is None:
            return out, s, first
        src = s if s != "live" else src
        out.extend(data.get("studies", []))
        token = data.get("nextPageToken")
        if not token:
            break
    return [flat(s) for s in out], src, first


def flat(s):
    f = ctgov.flat(s)
    p = s.get("protocolSection", s)
    d = p.get("designModule", {}).get("designInfo", {})
    f["obs_model"] = d.get("observationalModel", "")
    f["time_persp"] = d.get("timePerspective", "")
    f["officials"] = [{"name": o.get("name", ""), "aff": o.get("affiliation", ""), "role": o.get("role", "")}
                      for o in p.get("contactsLocationsModule", {}).get("overallOfficials", []) or []]
    return f


def ctgov_web_url(cond, term="", countries=None):
    q = {"cond": cond}
    if term:
        q["term"] = term
    if countries:
        q["locStr"] = ", ".join(countries[:1])
    return "https://clinicaltrials.gov/search?" + urllib.parse.urlencode(q)


# ---------------------------------------------------------------- ISRCTN

def isrctn_search(query, limit=50):
    url = "https://www.isrctn.com/api/query/format/default?" + urllib.parse.urlencode({"q": query, "limit": limit})
    raw, src = _cached(url, kind="text")
    if not raw:
        return {"total": None, "trials": [], "src": src, "url": url}
    ns = {"i": "http://www.67bricks.com/isrctn"}
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return {"total": None, "trials": [], "src": src, "url": url}
    trials = []
    for t in root.findall("i:fullTrial", ns):
        tr = t.find("i:trial", ns)
        idn = (tr.findtext("i:isrctn", "", ns) or "").strip()
        title = (tr.findtext("i:trialDescription/i:title", "", ns) or "").strip()
        countries = sorted({(c.text or "").strip() for c in tr.findall(".//i:recruitmentCountries/i:country", ns) if c.text})
        design = (tr.findtext(".//i:primaryStudyDesign", "", ns) or "").strip()
        status = (tr.findtext(".//i:overallStatusOverride", "", ns) or tr.findtext(".//i:recruitmentStatusOverride", "", ns) or "").strip()
        n = (tr.findtext(".//i:targetEnrolment", "", ns) or "").strip()
        trials.append({"id": "ISRCTN" + idn, "title": title, "countries": countries, "design": design, "status": status, "target": n})
    return {"total": int(root.get("totalCount", 0)), "trials": trials, "src": src,
            "url": "https://www.isrctn.com/search?" + urllib.parse.urlencode({"q": query})}


# ---------------------------------------------------------------- PubMed

def pubmed_count(term):
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?" + urllib.parse.urlencode({"db": "pubmed", "retmode": "json", "retmax": 0, "term": term})
    data, src = _cached(url, max_age_days=30)
    try:
        n = int(data["esearchresult"]["count"])
    except Exception:
        n = None
    return n, src, "https://pubmed.ncbi.nlm.nih.gov/?" + urllib.parse.urlencode({"term": term})


def pubmed_term(ind):
    """A PubMed query for the indication's topic (kept short and readable)."""
    if ind["id"] == "abd_onc_surgery_nutrition":
        return "(malnutrition OR nutritional status OR nutritional risk) AND (surgery OR surgical) AND (gastric OR colorectal OR pancreatic OR liver OR esophageal OR gastrointestinal) AND (cancer OR neoplasm)"
    t = re.sub(r"\s+OR\s+", " OR ", ind["cond"])
    return f"({t})" + (f" AND ({ind['term']})" if ind.get("term") and len(ind["term"]) < 120 else "")
