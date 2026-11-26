"""ClinicalTrials.gov API v2 client (public, no key). Live fetch with a local cache.

Every response is cached in data/cache/. If the network is unavailable, the bundled
snapshot in data_snapshot/ctgov/ is used instead, so the demo runs offline.
"""
import hashlib
import json
import os
import time
import urllib.parse
import urllib.request

BASE = "https://clinicaltrials.gov/api/v2/studies"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "data", "cache")
SNAPSHOT = os.path.join(ROOT, "data_snapshot", "ctgov")

LIST_FIELDS = ",".join([
    "NCTId", "BriefTitle", "OfficialTitle", "OverallStatus", "Phase", "StudyType",
    "LeadSponsorName", "LeadSponsorClass", "EnrollmentCount", "EnrollmentType",
    "StartDate", "StartDateType", "PrimaryCompletionDate", "PrimaryCompletionDateType", "Condition", "Keyword", "EligibilityCriteria",
    "LocationFacility", "LocationCity", "LocationState", "LocationCountry", "LocationStatus",
])

OFFLINE = os.environ.get("V95_OFFLINE") == "1"


def _key(url):
    return hashlib.sha1(url.encode()).hexdigest()[:16] + ".json"


def _get(url, max_age_days=7):
    os.makedirs(CACHE, exist_ok=True)
    k = _key(url)
    p = os.path.join(CACHE, k)
    if os.path.exists(p) and time.time() - os.path.getmtime(p) < max_age_days * 86400:
        with open(p) as f:
            return json.load(f), "cache"
    if not OFFLINE:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "v95-feasibility-demo/0.1"})
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.load(r)
            with open(os.path.join(CACHE, k), "w") as f:
                json.dump(data, f)
            return data, "live"
        except Exception:
            pass
    for folder in (CACHE, SNAPSHOT):  # stale copy is better than nothing
        p = os.path.join(folder, k)
        if os.path.exists(p):
            with open(p) as f:
                return json.load(f), "snapshot (offline)"
    raise RuntimeError("ClinicalTrials.gov unreachable and no cached copy for " + url)


def study(nct):
    data, src = _get(f"{BASE}/{nct}")
    return data, src


def search(cond, statuses=None, advanced=None, max_pages=5):
    """Return (list of studies, source, query_url). Pages through up to max_pages x 1000."""
    params = {"query.cond": cond, "pageSize": "1000", "fields": LIST_FIELDS, "countTotal": "true"}
    if statuses:
        params["filter.overallStatus"] = ",".join(statuses)
    if advanced:
        params["filter.advanced"] = advanced
    out, src, token, first_url = [], "live", None, None
    for _ in range(max_pages):
        p = dict(params)
        if token:
            p["pageToken"] = token
        url = BASE + "?" + urllib.parse.urlencode(p)
        first_url = first_url or url
        data, s = _get(url)
        src = s if s != "live" else src
        out.extend(data.get("studies", []))
        token = data.get("nextPageToken")
        if not token:
            break
    return out, src, first_url



# ---------- flatten helpers ----------

def flat(s):
    """Flatten an API study record into a simple dict."""
    p = s.get("protocolSection", s)
    idm = p.get("identificationModule", {})
    st = p.get("statusModule", {})
    sp = p.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {})
    de = p.get("designModule", {})
    en = de.get("enrollmentInfo", {})
    locs = p.get("contactsLocationsModule", {}).get("locations", [])
    return {
        "nct": idm.get("nctId"),
        "title": idm.get("briefTitle", ""),
        "official": idm.get("officialTitle", ""),
        "status": st.get("overallStatus", ""),
        "phase": "/".join(x.replace("PHASE", "Ph ").replace("EARLY_Ph ", "Early Ph ") for x in de.get("phases", []) or []) or "n/a",
        "phases": de.get("phases", []) or [],
        "type": de.get("studyType", ""),
        "sponsor": sp.get("name", ""),
        "sponsor_class": sp.get("class", ""),
        "enroll": en.get("count"),
        "enroll_type": en.get("type", ""),
        "start": st.get("startDateStruct", {}).get("date"),
        "start_type": st.get("startDateStruct", {}).get("type", ""),
        "pcd": st.get("primaryCompletionDateStruct", {}).get("date"),
        "pcd_type": st.get("primaryCompletionDateStruct", {}).get("type", ""),
        "conditions": p.get("conditionsModule", {}).get("conditions", []),
        "keywords": p.get("conditionsModule", {}).get("keywords", []),
        "criteria": p.get("eligibilityModule", {}).get("eligibilityCriteria", ""),
        "min_age": p.get("eligibilityModule", {}).get("minimumAge", ""),
        "locations": [{
            "facility": (l.get("facility") or "").strip(),
            "city": l.get("city", ""), "state": l.get("state", ""),
            "country": l.get("country", ""), "status": l.get("status", ""),
        } for l in locs],
    }
