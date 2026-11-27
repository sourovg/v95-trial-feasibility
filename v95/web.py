"""Cohortia web app: request intake → four pillars → investigator survey → proposal."""
import json
import random
import re
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import ai, catalog, intake, project, registries, store, survey
from . import pack as packmod
from . import server as trialview
from .ui import LEGEND, NAME, WORDMARK, e, fmt, link_nct, page, pct, tag

TABS = [("overview", "Overview", ""), ("benchmark", "Benchmark", "1"), ("countries", "Countries", "2"),
        ("investigators", "Investigators", "3"), ("scenario", "Scenario & risk", "4"), ("proposal", "Proposal", "")]
STUDY_TYPE = dict(catalog.STUDY_TYPES)
SCEN_COL = {"Conservative": "#c2410c", "Base": "#0d9488", "Optimistic": "#2563eb"}  # validated categorical trio


def _opts(values, sel):
    out = []
    for v in values:
        k, lab = (v if isinstance(v, tuple) else (v, v))
        out.append(f'<option value="{e(k)}"{" selected" if k == sel else ""}>{e(lab)}</option>')
    return "".join(out)


def _wrap(inner, cls="wrap"):
    return f'<div class="{cls}">{inner}</div>'


# ------------------------------------------------------------------ home

def home():
    projs = store.list_projects()
    rows = "".join(f'<a class="req" href="/p/{p["id"]}"><span class="id">{p["id"]}</span><span><b>{e(p["req"].get("title",""))}</b>'
                   f'<div class="xs mute">{e(STUDY_TYPE.get(p["req"].get("study_type"), ""))} · {e(", ".join(p["req"].get("countries", [])))}</div></span>'
                   f'<span class="xs mute">{e(p["created"])}</span></a>' for p in projs)
    ai_on, ai_txt = ai.status()
    pill = [("1", "Benchmark analysis", "Similar studies across ClinicalTrials.gov and ISRCTN, enrolment pace, published figures from PubMed.", "Automated"),
            ("2", "Country evaluation", "Patients from GLOBOCAN, research activity, start-up time and competition, scored with weights you control.", "Automated"),
            ("3", "Investigator insights", "Candidate sites and investigators from registries; a five-pillar survey designed from your request, sent and tracked here.", "Automated + investigators"),
            ("4", "Scenario & risk", "Sample size, timelines by scenario and country, risk register and a go / no-go view.", "Automated")]
    cards = "".join(f'<div class="pillar"><div class="ic">{n}</div><b>{t}</b><div class="small mute">{d}</div><span class="ai">{a}</span></div>' for n, t, d, a in pill)
    body = f"""<div class="wrap">
<div class="hhero"><div><span class="eyebrow">Study feasibility, automated</span>
<h1>From feasibility request to proposal in an afternoon</h1>
<p class="lead">Describe the study you are considering. Cohortia benchmarks similar studies, scores countries, designs and sends the investigator survey, and models timelines and risks, with every number traced to its source.</p>
<div class="ctas"><a class="btn lg" href="/new">Start a feasibility request</a><a class="btn lg ghost" href="/new?example=1">Open the worked example</a></div>
<p class="small mute" style="margin-top:14px">Have a registered trial? <a href="/trial">Look it up by NCT number</a>.</p></div>
<div class="mock" aria-hidden="true"><div class="xs" style="letter-spacing:.06em;text-transform:uppercase;color:#99f6e4;font-weight:700">Country evaluation · example</div>
<div style="font-weight:700;color:#fff;margin:6px 0 10px">Malnutrition in abdominal cancer surgery · Latin America</div>
<div class="row"><span><b>Brazil</b> · 14,052 reachable surgical patients/yr</span><span class="sc">74</span></div>
<div class="row"><span><b>Mexico</b> · 3,993</span><span class="sc">49</span></div>
<div class="row"><span><b>Argentina</b> · 3,190</span><span class="sc">41</span></div>
<div class="row"><span><b>Chile</b> · 1,994</span><span class="sc">39</span></div>
<div class="xs" style="margin-top:10px;color:#94a3b8">Snapshot of the worked example, 27 Nov 2026 · scores 0–100</div></div></div>
<div class="card"><h2>Four pillars, one workflow</h2><p class="sub">The same structure CRO feasibility teams use, with the desk work done by rules and AI and checked by you.</p><div class="pillars">{cards}</div></div>
<div class="grid2"><div class="card"><h2>Your requests</h2><div class="list">{rows or '<p class="small mute">No requests yet. Start one, or open the worked example.</p>'}</div></div>
<div class="card"><h2>Data sources</h2><ul class="small" style="padding-left:18px;margin:8px 0">
<li><b>ClinicalTrials.gov</b>: interventional and observational studies, sites, investigators (queried live)</li>
<li><b>ISRCTN</b>: international registry incl. observational studies (queried live)</li>
<li><b>PubMed</b>: published research per country (queried live)</li>
<li><b>GLOBOCAN 2024</b> (IARC/WHO): new cancer cases for 24 countries (bundled)</li>
<li>Linked: WHO ICTRP (ReBEC, REPEC and 15+ registries), EU CTIS, HMA-EMA RWD catalogue, ISPOR RWE registry</li></ul>
<div class="callout info">AI is <b>{ai_on}</b>. {e(ai_txt)}</div></div></div>
<footer>Public, aggregate data only. No patient-level data. Demo: survey invitations are simulated; nothing is emailed.</footer></div>"""
    return page(NAME + " · feasibility from request to proposal", body, active="home")


# ------------------------------------------------------------------ request form

def form_page(vals=None, prov=None, note=""):
    v = dict(vals or {})
    prov = prov or {}
    ind_sel = v.get("indication", "")
    ind_lab = catalog.INDICATIONS[ind_sel]["label"] if ind_sel in catalog.INDICATIONS else ""

    def p(k):
        return f'<span class="prov" title="{e(prov[k])}">auto-filled</span>' if k in prov else ""
    stype = "".join(f'<label><input type="radio" name="study_type" value="{k}"{" checked" if v.get("study_type", "obs_prospective") == k else ""}><span>{e(lab)}</span></label>' for k, lab in catalog.STUDY_TYPES)
    sel_c = set(v.get("countries") or [])
    chips = "".join(f'<label><input type="checkbox" name="countries" value="{e(c)}"{" checked" if c in sel_c else ""}>{e(c)}</label>' for c in catalog.COUNTRIES)
    svc = set(v.get("services") or [s for s, _, _ in catalog.SERVICES])
    services = "".join(f'<label><input type="checkbox" name="services" value="{k}"{" checked" if k in svc else ""}><span><b>{e(t)}</b><br><span class="xs mute">{e(d)}</span></span></label>' for k, t, d in catalog.SERVICES)
    areas = '<option value="">All areas</option>' + _opts(catalog.AREAS, v.get("ta", ""))
    ai_on, ai_txt = ai.status()
    body = f"""<div class="wrap"><div style="margin-bottom:18px"><span class="eyebrow">New feasibility request</span><h1>Describe the study you are assessing</h1>
<p class="sub" style="font-size:15px">Paste the request or RFP text and let Cohortia fill the fields, or pick from the lists. Everything can be changed later.</p>{note}</div>
<form method="post" action="/new" id="rfp"><div class="formgrid"><div>
<div class="fsec"><h2><span class="num">1</span>The request</h2>
<label class="field"><span>Request title</span><input type="text" name="title" value="{e(v.get('title',''))}" placeholder="e.g. Malnutrition in abdominal cancer surgery, Latin America"></label>
<div class="row2"><label class="field"><span>Sponsor (optional)</span><input type="text" name="sponsor" value="{e(v.get('sponsor',''))}" placeholder="Company or team"></label>
<label class="field"><span>Decision this feasibility supports</span><input type="text" name="decision" value="{e(v.get('decision',''))}" placeholder="e.g. Go / no-go for a full study"></label></div>
<label class="field"><span>Description or RFP text</span><textarea name="description" placeholder="What study is being considered, in which patients and where, and what the feasibility should answer.">{e(v.get('description',''))}</textarea>
<small>Tip: the more you say about population, design and countries, the more fields fill themselves.</small></label>
<div style="display:flex;gap:10px;align-items:center;margin-top:12px;flex-wrap:wrap"><button class="btn ghost" name="action" value="parse" formnovalidate>Auto-fill from description</button>
<span class="xs mute">Rules{' + Claude' if ai_on == 'on' else ''} read the text; filled fields are marked <span class="prov">auto-filled</span></span></div></div>

<div class="fsec"><h2><span class="num">2</span>Study</h2>
<div class="row2"><label class="field"><span>Therapeutic area {p('ta')}</span><select name="ta" id="ta">{areas}</select></label>
<div class="field indsearch"><span>Indication or topic {p('indication')}</span><input type="text" id="indq" placeholder="Search, e.g. nutrition, lung, psoriasis" value="{e(ind_lab)}" autocomplete="off">
<input type="hidden" name="indication" id="ind" value="{e(ind_sel)}"><div class="indlist" id="indlist"></div></div></div>
<label class="field"><span>Keywords (optional)</span><input type="text" name="keywords" value="{e(v.get('keywords',''))}" placeholder="e.g. GLIM, NRS-2002, gastrectomy"></label>
<div class="field"><span>Study type {p('study_type')}</span><div class="choice">{stype}</div></div>
<div class="row3"><label class="field"><span>Design {p('design')}</span><select name="design">{_opts(catalog.DESIGNS, v.get('design',''))}</select></label>
<label class="field"><span>Phase {p('phase')}</span><select name="phase">{_opts(catalog.PHASES, v.get('phase','Not applicable'))}</select></label>
<label class="field"><span>Setting {p('setting')}</span><select name="setting">{_opts(catalog.SETTINGS, v.get('setting',''))}</select></label></div>
<div class="row2"><label class="field"><span>Population {p('population')}</span><select name="population">{_opts(catalog.POPULATIONS, v.get('population','Adults (18+)'))}</select></label>
<label class="field"><span>Primary objective {p('objective')}</span><input type="text" name="objective" value="{e(v.get('objective',''))}"></label></div>
<label class="field"><span>Key endpoints / data to collect</span><input type="text" name="endpoints" value="{e(v.get('endpoints',''))}"></label></div>

<div class="fsec"><h2><span class="num">3</span>Geography {p('countries')}</h2>
<label class="field"><span>Region preset</span><select name="region" id="region"><option value="">Choose countries yourself</option>{_opts(list(catalog.REGIONS), v.get('region',''))}</select></label>
<div class="field"><span>Countries</span><div class="cchips" id="cchips">{chips}</div><small>Patient numbers are available for these 24 countries (GLOBOCAN 2024). Registries are searched for all.</small></div></div>

<div class="fsec"><h2><span class="num">4</span>Targets</h2>
<div class="row3"><label class="field"><span>Target sample size</span><input type="number" name="target_n" min="0" value="{e(str(v.get('target_n','')))}" placeholder="Leave blank to calculate"></label>
<label class="field"><span>Precision (± percentage points)</span><input type="number" step="0.5" min="0.5" name="margin" value="{e(str(v.get('margin','4')))}"><small>For prevalence-type objectives</small></label>
<label class="field"><span>Enrolment window (months)</span><input type="number" min="1" name="months" value="{e(str(v.get('months','18')))}"></label></div>
<label class="field"><span>Expected proportion, % (optional)</span><input type="number" step="1" min="1" max="99" name="expected_p" value="{e(str(v.get('expected_p','')))}" placeholder="Blank: use published figures"></label></div>

<div class="fsec"><h2><span class="num">5</span>Scope of the assessment</h2><div class="choice">{services}</div>
<div style="margin-top:20px;display:flex;gap:12px;flex-wrap:wrap"><button class="btn lg" name="action" value="create">Create feasibility project</button><a class="btn lg ghost" href="/new?example=1">Load worked example</a></div></div>
</div>
<aside class="aside"><div class="card"><h3 style="margin-top:0">What you will get</h3><ol class="small" style="padding-left:18px;margin:0">
<li><b>Benchmark</b> of similar registered studies and published figures</li><li><b>Country scorecard</b> with patients, activity, start-up time, competition</li>
<li><b>Investigator shortlist</b> and a survey designed from this request</li><li><b>Scenarios, risks</b> and a printable proposal</li></ol>
<div class="callout info" style="margin-top:14px">AI is <b>{ai_on}</b>. {e(ai_txt)}</div>
<p class="xs mute">Public, aggregate data only. Every figure is labelled fact, published figure, estimate or judgment.</p></div></aside>
</div></form></div>
<script>
const OPT={catalog.options_json()};
const ta=document.getElementById('ta'),q=document.getElementById('indq'),hid=document.getElementById('ind'),list=document.getElementById('indlist');
function draw(){{const s=q.value.toLowerCase(),a=ta.value;list.innerHTML='';
 OPT.indications.filter(i=>(!a||i.ta===a)&&(hid.value||!s||i.label.toLowerCase().includes(s)||i.ta.toLowerCase().includes(s))).forEach(i=>{{
  const d=document.createElement('div');d.innerHTML='<span>'+i.label+'</span><small>'+i.ta+'</small>';if(i.id===hid.value)d.className='sel';
  d.onclick=()=>{{hid.value=i.id;q.value=i.label;ta.value=i.ta;draw();}};list.appendChild(d);}});}}
q.addEventListener('input',()=>{{hid.value='';draw();}});ta.addEventListener('change',draw);draw();
document.getElementById('region').addEventListener('change',ev=>{{const cs=OPT.regions[ev.target.value];if(!cs)return;
 document.querySelectorAll('#cchips input').forEach(x=>x.checked=cs.includes(x.value));}});
</script>"""
    return page("New request · " + NAME, body)


def parse_form(body):
    q = urllib.parse.parse_qs(body, keep_blank_values=True)
    out = {}
    for k, v in q.items():
        out[k] = v if k in ("countries", "services", "site") else v[-1]
    return out


# ------------------------------------------------------------------ project pages

def _head(proj, a, tab):
    r = a["req"]
    vt, vc, vwhy = a["verdict"]
    tabs = "".join(f'<a class="{"on" if k == tab else ""}" href="/p/{proj["id"]}?tab={k}">' + (f'<span class="n">{n}</span>' if n else "") + f'{lab}</a>' for k, lab, n in TABS)
    return f"""<div class="phead"><div class="in"><div class="meta"><span>{proj['id']}</span><span>·</span><span>Created {e(proj['created'])}</span>{'<span>·</span><span>' + e(r.get('sponsor')) + '</span>' if r.get('sponsor') else ''}</div>
<h1>{e(r['title'])}</h1><div class="meta"><span class="chip">{e(a['ind']['label'])}</span><span class="chip">{e(STUDY_TYPE.get(r.get('study_type'), ''))}</span>
<span class="chip">{e(r.get('design',''))}</span><span class="chip">{e(', '.join(r['countries']))}</span><span class="verdict v-{vc}" style="margin:0" title="{e(vwhy)}">● {e(vt)}</span></div>
<nav class="tabs">{tabs}</nav></div></div>"""


def _kpi(v, label, sub="", cls=""):
    return f'<div class="kpi {cls}"><div class="v{" sm" if len(str(v)) > 7 else ""}">{v}</div><div class="l">{label}</div>{f"<div class=xs style=color:var(--mute)>{sub}</div>" if sub else ""}</div>'


def overview(proj, a):
    r, b, s, sc, sv = a["req"], a["bench"], a["ss"], a["sc"], a["survey"]
    base = sc["runs"]["Base"]
    pri = [c["country"] for c in a["countries"] if c["tier"] == "Priority"]
    vt, vc, vwhy = a["verdict"]
    facts = {"request": r["title"], "verdict": vt, "why": vwhy, "sample": s["n"], "base_months": base and base["months"],
             "countries": [(c["country"], round(c["score"]), c["tier"], round(c["reach"] or 0)) for c in a["countries"]],
             "similar_studies_region": len([t for t in b["region"] if t["rel"] != "Low"]), "survey_done": sv["n_done"]}
    summ = ai.summary(facts) if ai.available() else None
    if not summ:
        top = a["countries"][0] if a["countries"] else None
        summ = (f"{vt}. {vwhy} The sample of {s['n']:,} patients (± {s['margin']*100:.0f} points at 95% confidence, expected proportion {s['p']:.0%}) "
                f"is modelled with {sc['sites']} sites at {sc['rates']['Base']:.1f} patients per site per month. "
                + (f"{top['country']} scores highest ({top['score']:.0f}/100) on patients, research activity, start-up time and competition. " if top else "")
                + f"{len([t for t in b['region'] if t['rel'] == 'Direct'])} closely matching studies are registered in these countries. "
                + ("Investigator survey results are included." if sv["n_done"] else "Next step: send the investigator survey to confirm interest, practice and patient numbers."))
    kp = "".join([
        _kpi(fmt(s["n"]), "Patients needed", f"±{s['margin']*100:.0f} pts, {s['level']} level"),
        _kpi(f"{base['months']} mo" if base and base["months"] else "60+ mo", "Base-case timeline", f"incl. start-up; window {r.get('months') or 'n/a'} mo", "" if vc == "low" else "warn" if vc == "med" else "bad"),
        _kpi(len(pri), "Priority countries", ", ".join(pri) or "none"),
        _kpi(len([t for t in b["region"] if t["rel"] != "Low"]), "Similar studies in region", "ClinicalTrials.gov"),
        _kpi(f"{sv['n_done']}/{sv['n_invited']}", "Survey responses", "investigators"),
    ])
    steps = [("Benchmark", "benchmark", f"{len(b['region'])} registry studies screened, {b['rate']['n']} with usable pace"),
             ("Countries", "countries", f"{len(a['countries'])} countries scored"),
             ("Investigators", "investigators", f"{len(a['sites'])} candidate sites; {len(proj['questions'])}-question survey ready"),
             ("Scenario & risk", "scenario", f"{len(a['risks'])} risks logged"), ("Proposal", "proposal", "ready to print")]
    st = "".join(f'<a class="ex" href="/p/{proj["id"]}?tab={k}"><div class="id">{t} →</div><div class="small mute">{d}</div></a>' for t, k, d in steps)
    req_rows = "".join(f"<tr><th style='width:180px'>{e(k)}</th><td>{e(str(v_))}</td></tr>" for k, v_ in [
        ("Description", r.get("description", "")), ("Objective", r.get("objective", "")), ("Endpoints", r.get("endpoints", "")),
        ("Keywords", r.get("keywords", "")), ("Setting / population", f"{r.get('setting','')} · {r.get('population','')}"),
        ("Decision supported", r.get("decision", ""))] if v_)
    return f"""<div class="kpis k5">{kp}</div>
<div class="grid2"><div class="card"><h2>Summary</h2><p class="sub">{'Drafted by Claude from the computed facts' if ai.available() else 'Generated by rules from the computed facts'}; check before sharing.</p><p>{e(summ)}</p>
<a class="btn" href="/p/{proj['id']}?tab=proposal">Open proposal</a></div>
<div class="card"><h2>Workflow</h2><div style="display:grid;gap:10px;margin-top:10px">{st}</div></div></div>
<div class="card"><h2>Request</h2><div class="tw"><table>{req_rows}</table></div></div>"""


def benchmark_tab(proj, a):
    b = a["bench"]
    rel = [t for t in b["region"] if t["rel"] != "Low"]
    rows = "".join(f'<tr><td>{link_nct(t["nct"])}</td><td><span class="rel {t["rel"]}">{t["rel"]}</span></td><td>{e(t["title"][:110])}<div class="xs mute">{e(t["sponsor"][:50])}</div></td>'
                   f'<td class="xs">{"Observational" if t["type"] == "OBSERVATIONAL" else "Interventional"}</td><td class="xs">{e(t["status"].replace("_", " ").title())}</td>'
                   f'<td class="xs">{e(", ".join(sorted({l["country"] for l in t["locations"] if l["country"] in a["req"]["countries"]})))}</td>'
                   f'<td class="n">{fmt(t["enroll"])}</td><td class="n">{(t["start"] or "")[:4]}</td></tr>' for t in rel[:40])
    pr = "".join(f'<tr><td>{link_nct(t["nct"])}</td><td>{e(t["title"][:90])}</td><td class="n">{t["enroll"]:,}</td><td class="n">{t["n_sites"]}</td><td class="n">{t["months"]:.0f}</td><td class="n">{t["rate"]:.2f}</td></tr>' for t in b["paced"])
    lit = "".join(f'<tr><td>{e(x["what"])}</td><td><b>{e(x["label"])}</b></td><td><a href="{e(x["url"])}" target="_blank" rel="noopener">{e(x["cite"])} ↗</a></td><td>{tag("S")}</td></tr>' for x in b["literature"])
    isr = b["isrctn"]
    irows = "".join(f'<tr><td><a href="https://www.isrctn.com/{e(t["id"])}" target="_blank" rel="noopener">{e(t["id"])}</a></td><td><span class="rel {t["rel"]}">{t["rel"]}</span></td><td>{e(t["title"][:110])}</td><td class="xs">{e(t["design"])}</td><td class="xs">{e(", ".join([c for c in t["countries"] if c not in ("England", "Scotland", "Wales")][:4]))}</td></tr>' for t in isr["relevant"][:12])
    links = "".join(f'<li><a href="{e(u)}" target="_blank" rel="noopener">{e(n)} ↗</a> <span class="mute">{e(d)}</span></li>' for n, u, d in registries.LINKS)
    r_, sz, du, si = b["rate"], b["size"], b["duration"], b["sites"]
    def q3(x, d=0):
        return f"{fmt(x['median'], d)} <span class='r'>({fmt(x['p25'], d)}–{fmt(x['p75'], d)})</span>" if x["n"] else "n/a"
    yrs = b["years"]
    ymax = max(yrs.values()) if yrs else 1
    ybars = "".join(f'<div title="{y}: {n} studies" style="flex:1;display:flex;flex-direction:column;justify-content:flex-end;align-items:center;gap:3px"><div style="width:100%;max-width:18px;height:{max(3, 80 * n / ymax):.0f}px;background:var(--acc2);border-radius:4px 4px 0 0"></div><span class="xs mute" style="font-size:10px">{str(y)[2:]}</span></div>' for y, n in list(yrs.items())[-16:])
    lit_block = f"""<div class="card"><h2>Published figures</h2><p class="sub">Curated from peer-reviewed studies and checked against the PubMed abstracts. Used as the expected proportion for sample size.</p>
<div class="tw"><table><tr><th>Study</th><th>Finding</th><th>Source</th><th></th></tr>{lit}</table></div></div>""" if lit else ""
    return f"""<div class="kpis">{_kpi(len(rel), "Similar studies in your countries", f"of {len(b['region'])} screened")}{_kpi(b['by_status'].get('Recruiting / not yet', 0), "Recruiting now (any relevance)")}
{_kpi(fmt(b['pubmed_total']), "Papers on PubMed", "topic, worldwide")}{_kpi(len(isr['relevant']), "Relevant ISRCTN records", f"of {fmt(isr['total'])} found")}</div>
<div class="card"><h2>Enrolment benchmarks</h2><p class="sub">From {r_['n']} {e(b['pace_basis'])} worldwide with actual enrolment and dates (ClinicalTrials.gov). Median (P25–P75). {tag('F')} inputs, {tag('E')} rate</p>
<div class="kpis" style="margin:0">{_kpi(q3(r_, 2), "Patients / site / month")}{_kpi(q3(sz), "Sample size")}{_kpi(q3(si), "Sites")}{_kpi(q3(du), "Months, start → primary completion")}</div>
<details><summary>Studies used for the pace benchmark ({len(b['paced'])})</summary><div><div class="tw"><table><tr><th>Study</th><th>Title</th><th class="n">Enrolled</th><th class="n">Sites</th><th class="n">Months</th><th class="n">Pts/site/mo</th></tr>{pr}</table></div></div></details></div>
{lit_block}
<div class="card"><h2>Registered studies in {e(', '.join(a['req']['countries']))}</h2><p class="sub">Relevance from title, conditions and keywords: <span class="rel Direct">Direct</span> same topic, <span class="rel Partial">Partial</span> related. {len(b['region']) - len(rel)} low-relevance hits hidden. <a href="{e(b['region_url'])}" target="_blank" rel="noopener">API query ↗</a> · data: {e(b['region_src'])}</p>
<div style="display:flex;gap:4px;align-items:flex-end;height:110px;margin:6px 0 14px" role="img" aria-label="Studies by start year">{ybars}</div>
<div class="tw"><table><tr><th>Study</th><th>Fit</th><th>Title · sponsor</th><th>Type</th><th>Status</th><th>Countries</th><th class="n">N</th><th class="n">Start</th></tr>{rows}</table></div></div>
<div class="card"><h2>Other registries</h2><p class="sub">ISRCTN, queried for “{e(project.isrctn_query(a['ind']))}”: {fmt(isr['total'])} records, {len(isr['relevant'])} relevant by title · <a href="{e(isr['url'])}" target="_blank" rel="noopener">open search ↗</a></p>
<div class="tw"><table><tr><th>ID</th><th>Fit</th><th>Title</th><th>Design</th><th>Countries</th></tr>{irows or '<tr><td colspan=5 class=mute>No records or registry unreachable.</td></tr>'}</table></div>
<h3>Also check (no open API)</h3><ul class="small">{links}</ul></div>"""


def countries_tab(proj, a):
    pid, ov, w = proj["id"], a["ov"], a["weights"]
    def sc(v):
        return f'<span class="score {"hi" if v >= 65 else "md" if v >= 40 else "lo"}">{v:.0f}</span>'
    rows = ""
    for c in a["countries"]:
        m = c["metrics"]
        bars_ = "".join(f'<td><div class="mbar" title="{project.WEIGHT_LABELS[k]}: {m[k]:.0f}/100"><div style="width:{m[k]:.0f}%"></div></div></td>' for k in project.DEFAULT_WEIGHTS)
        rows += (f'<tr><td><b>{e(c["country"])}</b></td><td>{sc(c["score"])}</td><td><span class="tier {c["tier"]}">{c["tier"]}</span></td>'
                 f'<td class="n">{fmt(c["reach"])}</td><td class="n">{c["studies"]}</td><td class="n">{c["sites"]}</td><td class="n">{c["active"]}</td><td class="n">{fmt(c["pubmed"])}</td><td class="n">{c["startup"]:g}</td>{bars_}</tr>')
    wf = "".join(f'<label>{project.WEIGHT_LABELS[k]}<input type="number" name="w_{k}" value="{w[k]:g}" min="0" max="100"></label>' for k in project.DEFAULT_WEIGHTS)
    cards = ""
    for c in a["countries"]:
        fun = "".join(f'<tr><td>{e(l)}<div class="xs mute">{e(n)}</div></td><td class="n">{fmt(v)}</td><td>{tag(t)}</td></tr>' for l, v, t, n in c["funnel"])
        act = "".join(f'<li>{link_nct(t["nct"])} {e(t["title"][:70])}</li>' for t in c["active_list"])
        cards += f"""<div class="panel"><div style="display:flex;justify-content:space-between;align-items:center"><h3 style="margin:0">{e(c['country'])}</h3>{sc(c['score'])}</div>
<div class="tw"><table style="margin-top:8px">{fun or '<tr><td class=mute>No curated patient numbers for this indication.</td></tr>'}</table></div>
<p class="xs" style="margin:10px 0 0"><b>Start-up:</b> {c['startup']:g} months {tag('J')} · <b>Data law:</b> {e(c['law'])} · <a href="{e(c['pubmed_url'])}" target="_blank" rel="noopener">{fmt(c['pubmed'])} papers ↗</a></p>
{f'<p class="xs" style="margin:6px 0 0"><b>Recruiting now:</b></p><ul class="xs" style="margin:2px 0;padding-left:18px">{act}</ul>' if act else ''}</div>"""
    ind = a["ind"]
    assum = ""
    if ind["globocan"]:
        if ind["id"] in ("abd_onc_surgery_nutrition", "gi_cancer_surgery"):
            assum += f'<label class="small">Share of new cases resected {tag("J")}<br><input type="text" name="resection" value="{e(str(ov.get("resection", "0.40")))}"></label>'
        else:
            assum += f'<label class="small">Share meeting key criteria {tag("J")}<br><input type="text" name="eligible" value="{e(str(ov.get("eligible", "0.30")))}"></label>'
    else:
        assum += f'<label class="small">Prevalence per 100,000 {tag("J")}<br><input type="text" name="prev100k" value="{e(str(ov.get("prev100k", "")))}" placeholder="enter to estimate"></label>'
    assum += f'<label class="small">Share at research-capable hospitals {tag("J")}<br><input type="text" name="reach" value="{e(str(ov.get("reach", "0.25")))}"></label>'
    su = "".join(f'<label class="small">{e(c["country"])} start-up (months)<br><input type="number" name="startup_{e(c["country"])}" value="{c["startup"]:g}"></label>' for c in a["countries"])
    return f"""<div class="card"><h2>Country scorecard</h2><p class="sub">Each factor is scaled 0–100 across the selected countries, then weighted. Priority ≥ 65, Include ≥ 40.</p>
<div class="tw"><table><tr><th>Country</th><th>Score</th><th>Tier</th><th class="n">Reachable patients / yr {tag('E')}</th><th class="n">Similar studies {tag('F')}</th><th class="n">Experienced sites {tag('F')}</th><th class="n">Competing now {tag('F')}</th><th class="n">Papers {tag('F')}</th><th class="n">Start-up mo {tag('J')}</th>
{''.join(f'<th>{project.WEIGHT_LABELS[k]}</th>' for k in project.DEFAULT_WEIGHTS)}</tr>{rows}</table></div>{LEGEND}
<form method="post" action="/p/{pid}/settings?tab=countries" class="noprint" style="margin-top:18px"><h3>Weights</h3><div class="wform">{wf}</div>
<h3>Assumptions</h3><div class="wform">{assum}</div><details><summary>Start-up time by country</summary><div><div class="wform">{su}</div></div></details>
<p><button>Recalculate</button></p></form></div>
<div class="card"><h2>Country detail</h2><p class="sub">Patients: {e(catalog.GLOBOCAN_LABEL)} <a href="{catalog.GLOBOCAN_URL}" target="_blank" rel="noopener">↗</a>, then editable shares.</p><div class="grid3">{cards}</div></div>"""


def investigators_tab(proj, a, invites):
    pid, sv = proj["id"], a["survey"]
    invited = {i["site"]["key"] for i in invites}
    srows = "".join(f'<tr><td><input type="checkbox" name="site" value="{e(s["key"])}"{" checked" if i < 12 and s["key"] not in invited else ""}{" disabled" if s["key"] in invited else ""}></td>'
                    f'<td><b>{e(s["facility"][:70])}</b><div class="xs mute">{e(s["city"])}, {e(s["country"])}</div></td><td>{e(s["investigator"]) or "<span class=mute>—</span>"}</td>'
                    f'<td class="n">{s["studies"]}</td><td class="n">{s["direct"]}</td><td class="n">{s["completed"]}</td><td class="n">{s["active"]}</td><td class="n">{s["last"] or ""}</td>'
                    f'<td class="xs">{" ".join(link_nct(n) for n in s["ncts"][:3])}</td></tr>' for i, s in enumerate(a["sites"][:60]))
    qhtml = ""
    for pid_, name, desc, qs in survey.by_pillar(proj["questions"]):
        items = "".join(f'<li>{e(q["text"])} <span class="rule{" ai" if q["rule"].startswith("AI") else ""}">{e(q["rule"])}</span>'
                        + (f'<div class="opts">{e(" · ".join(q["options"]))}</div>' if q["options"] else f'<div class="opts">{e(q["kind"])} {e(q.get("unit", ""))}</div>') + '</li>' for q in qs)
        qhtml += f'<div class="qp"><h3>{e(name)} <span class="xs mute" style="font-weight:400">{len(qs)} questions · {e(desc)}</span></h3><ol>{items}</ol></div>'
    irows = "".join(f'<tr><td><b>{e(i["site"]["facility"][:60])}</b><div class="xs mute">{e(i["site"]["country"])}{" · " + e(i["site"]["investigator"]) if i["site"]["investigator"] else ""}</div></td>'
                    f'<td><span class="status {i["status"].split()[0]}">{e(i["status"])}</span>{" <span class=rule>demo data</span>" if i["synthetic"] else ""}</td>'
                    f'<td class="xs">{e(i["sent_at"] or "")}</td><td><a href="/s/{i["token"]}" target="_blank">survey link ↗</a></td></tr>' for i in invites)
    by_c = "".join(f'<tr><td>{e(c)}</td><td class="n">{d["contacted"]}</td><td class="n">{d["completed"]}</td><td class="n">{d["interested"]}</td><td class="n">{(sum(d["rate"]) / len(d["rate"])) if d["rate"] else 0:.1f}</td><td class="n">{fmt(sum(d["volume"]))}</td></tr>' for c, d in sorted(sv["by_country"].items()))
    dist = ""
    for q in proj["questions"]:
        cnt = sv["dist"].get(q["id"])
        if not cnt or q["id"] not in ("int_level", "pr_screen", "pr_screen_pct", "pr_support", "pt_malnut", "ca_ethics", "de_consent", "ca_bodycomp"):
            continue
        tot = max(sum(cnt.values()), 1)
        mx = max(cnt.values())
        bars_ = "".join(f'<div class="dist"><span>{e(k)}</span><div class="t"><div style="width:{100 * n / mx:.0f}%"></div></div><b class="n">{n}</b></div>' for k, n in cnt.most_common())
        dist += f'<div class="panel"><b class="small">{e(q["text"])}</b><div style="margin-top:8px">{bars_}</div></div>'
    rank = "".join(f'<tr><td>{e(r["site"]["facility"][:60])}<div class="xs mute">{e(r["site"]["country"])}</div></td><td class="n">{r["interest"]:.0f}/5</td><td class="n">{fmt(r["volume"])}</td><td class="n">{r["rate"]:g}</td><td class="n">{r["cap"]}/3</td><td class="n"><b>{r["score"]:.0f}</b></td></tr>' for r in sv["site_rank"][:15])
    results = ""
    if sv["n_done"]:
        results = f"""<div class="card" id="results"><h2>Survey results</h2>
{'<div class="callout warn">Includes <b>demo responses</b> generated to show the dashboard. They are not real investigator answers. <form method=post action=/p/' + pid + '/clear style=display:inline><button class="btn ghost" style="padding:4px 10px;margin-left:8px">Remove demo responses</button></form></div>' if sv['synthetic'] else ''}
<div class="kpis">{_kpi(sv['n_sent'], 'Invitations sent')}{_kpi(sv['n_done'], 'Completed')}{_kpi(f"{100 * sv['n_done'] / max(sv['n_sent'], 1):.0f}%", 'Response rate')}{_kpi(fmt(sv['median_rate'], 1), 'Median patients / month reported', 'before realism factor')}</div>
<div class="tw"><table><tr><th>Country</th><th class="n">Contacted</th><th class="n">Completed</th><th class="n">Interested (4–5)</th><th class="n">Avg pts / month</th><th class="n">Patients / yr (sum)</th></tr>{by_c}</table></div>
<h3>Answers to key questions</h3><div class="grid3">{dist}</div>
<h3>Site ranking from answers</h3><div class="tw"><table><tr><th>Site</th><th class="n">Interest</th><th class="n">Volume / yr</th><th class="n">Pts / month</th><th class="n">Capabilities</th><th class="n">Score</th></tr>{rank}</table></div></div>"""
    send = ""
    if invites:
        drafts = sum(i["status"] == "draft" for i in invites)
        send = f"""<div class="card" id="invites"><h2>Invitations</h2><p class="sub">{len(invites)} investigators on the list · {drafts} not yet sent</p>
<div class="callout warn"><b>Demo mode:</b> sending is simulated. Nothing is emailed. Real sending needs the sponsor's approval, a privacy notice and a contact channel that respects each country's rules (see compliance below).</div>
<div style="display:flex;gap:10px;flex-wrap:wrap;margin:10px 0">
<form method="post" action="/p/{pid}/send"><button{" disabled" if not drafts else ""}>Send {drafts} invitations (simulated)</button></form>
<form method="post" action="/p/{pid}/simulate"><button class="btn ghost">Fill demo responses</button></form></div>
<div class="tw"><table><tr><th>Investigator / site</th><th>Status</th><th>Sent</th><th></th></tr>{irows}</table></div></div>"""
    return f"""<div class="kpis">{_kpi(len(a['sites']), 'Candidate sites', 'from registry studies')}{_kpi(len(proj['questions']), 'Survey questions', '5 pillars')}{_kpi(len(invites), 'On invitation list')}{_kpi(sv['n_done'], 'Responses')}</div>
<div class="card"><h2>Candidate sites and investigators</h2><p class="sub">Hospitals that ran similar studies in your countries, ranked by relevant, completed and recent studies. Investigator names are the public study officials on ClinicalTrials.gov. {tag('F')}</p>
<form method="post" action="/p/{pid}/invite"><div class="tw"><table><tr><th></th><th>Site</th><th>Investigator (registry)</th><th class="n">Similar</th><th class="n">Direct</th><th class="n">Completed</th><th class="n">Active</th><th class="n">Latest</th><th>Studies</th></tr>{srows or '<tr><td colspan=9 class=mute>No sites found in registry studies for these countries.</td></tr>'}</table></div>
<p class="xs mute">Registries list few sites for observational studies; in a real project add the sponsor's own site list, KOL lists and national society members.</p>
<p><button>Add selected to survey list</button></p></form></div>
<div class="card"><h2>Investigator survey</h2><p class="sub">Designed from the request: each question shows the rule that added it{' (Claude added tailored questions)' if any(q['rule'].startswith('AI') for q in proj['questions']) else ''}. Preview it as an investigator would see it from any invitation link.</p>{qhtml}</div>
{send}{results}
<div class="card"><h2>Compliance checklist for real sending</h2><p class="sub">Judgment, not legal advice; confirm with counsel in each country.</p><ul class="small">
<li><b>Who contacts:</b> sponsors may contact investigators for feasibility. Many prefer a third party (CRO or platform) and a blinded sponsor name until a site is selected.</li>
<li><b>Payment:</b> if investigators are paid for completing the survey, pay fair market value and record it; US manufacturers report such payments under Open Payments; similar transparency codes exist elsewhere.</li>
<li><b>Personal data:</b> investigator names and emails are personal data (GDPR, LGPD and others). Use a lawful basis, a privacy notice, opt-out, and keep only business contact details.</li>
<li><b>Confidentiality:</b> share a synopsis, not the protocol; use a CDA before sharing more.</li>
<li><b>No promotion:</b> feasibility questions must not promote a product.</li></ul></div>"""


def scenario_tab(proj, a):
    pid, s, sc, ov = proj["id"], a["ss"], a["sc"], a["ov"]
    runs = sc["runs"]
    tiles = "".join(f'<div class="scen" style="border-top:4px solid {SCEN_COL[k]}"><div class="xs mute">{k}</div><div class="v">{(r["months"] if r and r["months"] else "60+")} mo</div><div class="xs mute">{sc["rates"][k]:.2f} pts / site / month</div></div>' for k, r in runs.items())
    base = runs["Base"] or {"alloc": {}, "per_country": {}}
    gmax = max([r["months"] or 60 for r in runs.values() if r] + [float(a["req"].get("months") or 0) + 6, 12])
    gantt = ""
    for c in a["countries"]:
        if c["country"] not in sc["countries_used"]:
            continue
        su = c["startup"]
        end = (runs["Base"]["months"] if runs["Base"] and runs["Base"]["months"] else 60)
        gantt += (f'<div class="g"><span>{e(c["country"])} <span class="xs mute">{base["alloc"].get(c["country"], 0)} sites</span></span><div class="t">'
                  f'<span class="su" style="left:0;width:{100 * su / gmax:.1f}%" title="Start-up {su:g} months"></span>'
                  f'<span class="en" style="left:{100 * su / gmax:.1f}%;width:{max(0, 100 * (end - su) / gmax):.1f}%" title="Enrolling, about {base["per_country"].get(c["country"], 0):.0f} patients"></span></div></div>')
    win = float(a["req"].get("months") or 0)
    chart = _curves(runs, s["n"], win)
    risks = "".join(f'<tr><td class="xs"><b>{e(r["area"])}</b></td><td>{e(r["risk"])}</td><td><span class="lik {r["lik"]}">{r["lik"]}</span></td><td><span class="lik {r["imp"]}">{r["imp"]}</span></td><td class="small">{e(r["mit"])}</td><td class="xs mute">{e(r["basis"])}</td></tr>' for r in a["risks"])
    lvl = _opts([("region", "Whole region"), ("country", "Each country")], s["level"])
    return f"""<div class="card"><h2>Sample size</h2><p class="sub">n = 1.96² × p(1−p) / d² × design effect{' × countries' if s['level'] == 'country' else ''}. Expected proportion: {e(s['p_src'])}.</p>
<div class="kpis" style="margin:0">{_kpi(fmt(s['n']), 'Patients needed' + (' (your target)' if a['req'].get('target_n') else ''))}{_kpi(pct(s['p']), 'Expected proportion')}{_kpi(f"±{s['margin']*100:.1f}", 'Precision, points')}{_kpi(f"±{(s['per_country_margin'] or 0)*100:.1f}", 'Precision per country', f"if split evenly over {s['k']}")}</div>
<form method="post" action="/p/{pid}/settings?tab=scenario" class="noprint" style="margin-top:14px"><div class="wform">
<label>Expected proportion (0–1)<input type="text" name="expected_p" value="{s['p']:.2f}"></label><label>Precision ± points<input type="text" name="margin" value="{s['margin']*100:g}"></label>
<label>Design effect {tag('J')}<input type="text" name="deff" value="{s['deff']:g}"></label><label>Precision for<select name="precision">{lvl}</select></label>
<label>Override sample size<input type="number" name="target_n" value="{e(str(ov.get('target_n', '')))}"></label></div>
<h3>Enrolment</h3><div class="wform"><label>Total sites<input type="number" name="sites" value="{sc['sites']}"></label><label>Base pts / site / month<input type="text" name="rate" value="{e(str(ov.get('rate', '')))}" placeholder="{sc['rates']['Base']:.2f}"></label>
<label>Survey realism factor {tag('J')}<input type="text" name="realism" value="{e(str(ov.get('realism', '0.5')))}"></label><label>Drop backup countries<select name="drop_backup">{_opts([('0', 'No'), ('1', 'Yes')], ov.get('drop_backup', '0'))}</select></label></div>
<p><button>Recalculate</button></p></form></div>
<div class="card"><h2>Timeline scenarios</h2><p class="sub">Month by month: each country opens after its start-up time, sites ramp up over 3 months. Base pace: {e(sc['rate_src'])}. {tag('E')}</p>
<div class="grid2"><div>{chart}</div><div><div class="grid3" style="gap:10px">{tiles}</div><h3>By country (base case)</h3><div class="gantt">{gantt}</div>
<div class="legendrow"><span><i style="background:#fbbf24;height:8px"></i>start-up</span><span><i style="background:var(--acc2);height:8px"></i>enrolling</span></div></div></div></div>
<div class="card"><h2>Risk register</h2><p class="sub">Raised by rules from the request, country data, benchmarks and survey answers.</p>
<div class="tw"><table><tr><th>Area</th><th>Risk</th><th>Likelihood</th><th>Impact</th><th>Mitigation</th><th>Basis</th></tr>{risks}</table></div></div>"""


def _curves(runs, n, window):
    W, H, L, B, T, R = 660, 280, 50, 34, 16, 150
    maxm = max([r["months"] or 60 for r in runs.values() if r] + [window or 0]) + 2
    def X(m): return L + (W - L - R) * m / maxm
    def Y(v): return H - B - (H - B - T) * v / max(n, 1)
    o = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="Cumulative enrolment by scenario">']
    for f in (0, .25, .5, .75, 1):
        o.append(f'<line x1="{L}" y1="{Y(n*f):.1f}" x2="{W-R}" y2="{Y(n*f):.1f}" stroke="#eef2f7"/><text x="{L-6}" y="{Y(n*f)+4:.1f}" font-size="11" text-anchor="end" fill="#64748b">{int(n*f):,}</text>')
    step = 6 if maxm <= 40 else 12
    for m in range(0, int(maxm) + 1, step):
        o.append(f'<text x="{X(m):.1f}" y="{H-B+16}" font-size="11" text-anchor="middle" fill="#64748b">{m}</text>')
    o.append(f'<text x="{(W+L-R)/2:.0f}" y="{H-2}" font-size="11" text-anchor="middle" fill="#64748b">months from project start</text>')
    if window:
        o.append(f'<line x1="{X(window):.1f}" y1="{T}" x2="{X(window):.1f}" y2="{H-B}" stroke="#94a3b8" stroke-dasharray="4 3"/><text x="{X(window)+4:.1f}" y="{H-B-6}" font-size="11" fill="#475569">requested {window:.0f} mo</text>')
    for k, r in runs.items():
        if not r:
            continue
        pts = " ".join(f"{X(m):.1f},{Y(v):.1f}" for m, v in r["curve"])
        o.append(f'<polyline fill="none" stroke="{SCEN_COL[k]}" stroke-width="2" stroke-linejoin="round" points="{pts}"><title>{k}: {r["months"] or "60+"} months</title></polyline>')
        m_end, v_end = r["curve"][-1]
        o.append(f'<circle cx="{X(m_end):.1f}" cy="{Y(v_end):.1f}" r="4" fill="{SCEN_COL[k]}" stroke="#fff" stroke-width="2"/>')
        ly = T + 6 + {"Optimistic": 0, "Base": 18, "Conservative": 36}[k]
        o.append(f'<line x1="{W-R+8}" y1="{ly-4}" x2="{W-R+20}" y2="{ly-4}" stroke="{SCEN_COL[k]}" stroke-width="2"/>'
                 f'<text x="{W-R+25}" y="{ly:.1f}" font-size="11.5" fill="#334155">{k} {r["months"] or "60+"} mo</text>')
    o.append("</svg>")
    return "".join(o)


def proposal_tab(proj, a):
    r, b, s, sc, sv = a["req"], a["bench"], a["ss"], a["sc"], a["survey"]
    vt, vc, vwhy = a["verdict"]
    base = sc["runs"]["Base"]
    ctry = "".join(f'<tr><td>{e(c["country"])}</td><td>{c["score"]:.0f}</td><td>{c["tier"]}</td><td class="n">{fmt(c["reach"])}</td><td class="n">{c["studies"]}</td><td class="n">{c["startup"]:g}</td><td class="n">{(base or {}).get("alloc", {}).get(c["country"], "")}</td></tr>' for c in a["countries"])
    sites = "".join(f'<li>{e(x["facility"][:70])} ({e(x["city"])}, {e(x["country"])}){" · " + e(x["investigator"]) if x["investigator"] else ""}</li>' for x in a["sites"][:10])
    risks = "".join(f'<li><b>{e(x["risk"])}</b> ({x["lik"].lower()} likelihood, {x["imp"].lower()} impact). {e(x["mit"])}</li>' for x in a["risks"][:6])
    lit = "".join(f'<li>{e(x["label"])}: {e(x["what"])}. <a href="{e(x["url"])}">{e(x["cite"])}</a></li>' for x in b["literature"])
    runs = " · ".join(f'{k}: {(v["months"] if v and v["months"] else "60+")} months' for k, v in sc["runs"].items())
    survey_line = (f"{sv['n_done']} of {sv['n_sent']} invited investigators responded" + (" (includes demo responses: replace with real answers before use)" if sv["synthetic"] else "") + "."
                   if sv["n_done"] else "The investigator survey is designed and ready to send; results will refine patient numbers and pace.")
    return f"""<div class="doc"><div class="cover"><div style="display:flex;align-items:center;gap:10px" class="logo">{WORDMARK}</div>
<p class="xs mute" style="margin:18px 0 4px;text-transform:uppercase;letter-spacing:.08em">Feasibility assessment · draft for review</p><h1>{e(r['title'])}</h1>
<p class="small mute">{e(r.get('sponsor') or 'Sponsor not named')} · {proj['id']} · {e(proj['created'])}</p>
<span class="verdict v-{vc}">● {e(vt)}</span> <span class="small">{e(vwhy)}</span></div>
<h2>1. Request and scope</h2><p class="small">{e(r.get('description',''))}</p><p class="small"><b>Study:</b> {e(STUDY_TYPE.get(r.get('study_type'), ''))}, {e(r.get('design',''))}; {e(r.get('setting',''))}; {e(r.get('population',''))}. <b>Countries:</b> {e(', '.join(r['countries']))}. <b>Decision supported:</b> {e(r.get('decision','') or 'not stated')}.</p>
<h2>2. Benchmark analysis</h2><p class="small">{len([t for t in b['region'] if t['rel'] != 'Low'])} related studies are registered in these countries ({len([t for t in b['region'] if t['rel'] == 'Direct'])} closely matching); {b['by_status'].get('Recruiting / not yet', 0)} are recruiting now. Across {b['rate']['n']} comparable completed studies worldwide, median pace was {fmt(b['rate']['median'], 2)} patients per site per month (P25–P75 {fmt(b['rate']['p25'], 2)}–{fmt(b['rate']['p75'], 2)}), median size {fmt(b['size']['median'])} and {fmt(b['sites']['median'])} sites. ISRCTN holds {fmt(b['isrctn']['total'])} related records; PubMed {fmt(b['pubmed_total'])} papers.</p>{f'<p class="small"><b>Published figures:</b></p><ul class="small">{lit}</ul>' if lit else ''}
<h2>3. Country evaluation</h2><div class="tw"><table><tr><th>Country</th><th>Score</th><th>Tier</th><th class="n">Reachable pts/yr</th><th class="n">Similar studies</th><th class="n">Start-up mo</th><th class="n">Sites (base)</th></tr>{ctry}</table></div>
<p class="xs mute">Weights: {', '.join(f"{project.WEIGHT_LABELS[k]} {v:g}" for k, v in a['weights'].items())}. Patient numbers: GLOBOCAN 2024 × judgment shares.</p>
<h2>4. Investigator insights and site identification</h2><p class="small">{survey_line} Top candidate sites from registry experience:</p><ol class="small">{sites}</ol>
<h2>5. Scenario and risk evaluation</h2><p class="small">Target {fmt(s['n'])} patients (expected proportion {pct(s['p'])}, ±{s['margin']*100:.0f} points, design effect {s['deff']:g}) with {sc['sites']} sites. {runs} (base pace: {e(sc['rate_src'])}).</p><ul class="small">{risks}</ul>
<h2>6. Recommendation and next steps</h2><ol class="small"><li>{e(vt)}: {e(vwhy)}</li><li>Confirm interest and patient numbers through the investigator survey (target 3+ responses per country).</li>
<li>Validate start-up times and data-protection requirements with local regulatory experts.</li><li>Fix the case definition and data dictionary before site selection.</li></ol>
<h2>Method and sources</h2><p class="xs mute">ClinicalTrials.gov API v2 (queried {e(b['region_src'])}), ISRCTN API, PubMed E-utilities, GLOBOCAN 2024 (IARC/WHO). Labels in the app: F fact, S published figure, E estimate, J judgment. Public, aggregate data only. Draft generated by {NAME}; requires expert review.</p>
<p class="noprint" style="margin-top:24px"><a class="btn" href="javascript:print()">Save as PDF</a></p></div>"""


def project_page(pid, tab):
    proj = store.get_project(pid)
    if not proj:
        return None
    invites = store.invites(pid)
    a = project.analyse(proj, invites)
    tab = tab if tab in dict((k, 1) for k, _, _ in TABS) else "overview"
    fn = {"overview": overview, "benchmark": benchmark_tab, "countries": countries_tab, "scenario": scenario_tab, "proposal": proposal_tab}
    inner = investigators_tab(proj, a, invites) if tab == "investigators" else fn[tab](proj, a)
    return page(f"{proj['req']['title']} · {NAME}", _head(proj, a, tab) + _wrap(inner))


# ------------------------------------------------------------------ investigator survey

def survey_page(token, done=False):
    inv = store.invite(token)
    if not inv:
        return None
    proj = store.get_project(inv["project_id"])
    r = proj["req"]
    if done:
        body = f'<div class="wrap survey"><div class="card" style="text-align:center;padding:40px"><h1>Thank you</h1><p>Your answers were recorded. The study team may contact you if your site is shortlisted.</p></div></div>'
        return _survey_shell(body)
    qs = ""
    for pid_, name, desc, items in survey.by_pillar(proj["questions"]):
        block = ""
        for q in items:
            if q["kind"] in ("single", "scale"):
                ctl = "".join(f'<label><input type="radio" name="{q["id"]}" value="{e(o)}">{e(o)}</label>' for o in q["options"])
            elif q["kind"] == "multi":
                ctl = "".join(f'<label><input type="checkbox" name="{q["id"]}" value="{e(o)}">{e(o)}</label>' for o in q["options"])
            elif q["kind"] == "number":
                ctl = f'<input type="number" min="0" name="{q["id"]}"> <span class="xs mute">{e(q.get("unit", ""))}</span>'
            else:
                ctl = f'<textarea name="{q["id"]}"></textarea>'
            block += f'<div class="q"><p>{e(q["text"])}</p>{ctl}</div>'
        qs += f'<h2 style="margin-top:26px">{e(name)}</h2><p class="sub">{e(desc)}</p>{block}'
    site = inv["site"]
    body = f"""<div class="wrap survey"><div class="card"><span class="eyebrow">Feasibility questionnaire</span><h1>{e(r['title'])}</h1>
<p class="small">Dear {e(site.get('investigator') or 'Investigator')}, {e(site['facility'])}: we are assessing whether a {e(STUDY_TYPE.get(r.get('study_type'), 'study').lower())} is feasible. About 10 minutes. Please answer for your site; no patient-identifiable information.</p>
<p class="small"><b>Synopsis:</b> {e(r.get('objective') or r.get('description', ''))}</p>
<p class="xs mute">Sent on behalf of {e(r.get('sponsor') or 'a study sponsor')} (sponsor may be blinded until site selection). Your answers are used only for this feasibility assessment. You can decline or ask for your contact details to be removed at any time.</p></div>
<form method="post" action="/s/{token}">{qs}<p style="margin:22px 0"><button class="btn lg">Submit answers</button></p></form></div>"""
    return _survey_shell(body)


def _survey_shell(body):
    return page("Feasibility questionnaire", body).replace('<a class="l cta" href="/new">New request</a>', "")


def synthetic_answers(q, site, rnd):
    if q["kind"] == "scale":
        return rnd.choice(["3", "4", "4", "5", "5"])
    if q["kind"] == "single":
        return rnd.choice(q["options"][:3] if len(q["options"]) > 3 and rnd.random() < 0.7 else q["options"])
    if q["kind"] == "multi":
        return rnd.sample(q["options"], k=min(len(q["options"]), rnd.randint(1, 3)))
    if q["kind"] == "number":
        big = 1 + site.get("studies", 1) * 0.4
        return str(int(rnd.uniform(60, 260) * big)) if q["id"] == "pt_volume" else str(rnd.randint(2, 10))
    return ""


# ------------------------------------------------------------------ HTTP

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, body, code=200):
        b = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _redirect(self, to):
        self.send_response(303)
        self.send_header("Location", to)
        self.end_headers()

    def _err(self, ex):
        return self._send(page("Error", f"<div class='wrap'><div class=card><h2>Something went wrong</h2><p class=small>If you are offline, only the worked example and demo trials work.</p><pre class=xs>{e(repr(ex))}</pre><a href='/'>Home</a></div></div>"), 500)

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = {k: v[-1] for k, v in urllib.parse.parse_qs(u.query).items()}
        try:
            if u.path == "/":
                return self._send(home())
            if u.path == "/new":
                if q.get("example"):
                    return self._send(form_page(intake.EXAMPLE, note='<div class="callout info">Worked example loaded: the Latin America malnutrition request. Press <b>Create feasibility project</b> at the bottom.</div>'))
                return self._send(form_page({"countries": [], "services": [s for s, _, _ in catalog.SERVICES]}))
            if u.path == "/trial":
                return self._send(trialview.trial_home())
            if u.path == "/pack":
                return trialview.Handler.do_GET(self)
            m = re.fullmatch(r"/p/(FR-[0-9A-F]{6})", u.path)
            if m:
                out = project_page(m.group(1), q.get("tab", "overview"))
                return self._send(out) if out else self._send(page("Not found", "<div class=wrap><div class=card>Project not found. <a href='/'>Home</a></div></div>"), 404)
            m = re.fullmatch(r"/s/([A-Za-z0-9_-]{6,20})", u.path)
            if m:
                out = survey_page(m.group(1), q.get("done") == "1")
                return self._send(out) if out else self._send(page("Not found", "<div class=wrap><div class=card>This survey link is not valid.</div></div>"), 404)
        except Exception as ex:
            return self._err(ex)
        self._send(page("Not found", "<div class='wrap'><div class=card>Not found. <a href='/'>Home</a></div></div>"), 404)

    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        n = int(self.headers.get("Content-Length") or 0)
        raw_body = self.rfile.read(n).decode("utf-8") if n else ""
        f = parse_form(raw_body)
        try:
            if u.path == "/new":
                if f.get("action") == "parse":
                    fields, prov = intake.parse(f.get("description", ""))
                    merged = {**f, **{k: v for k, v in fields.items() if not f.get(k) or k in ("countries", "indication", "study_type", "design")}}
                    if not f.get("countries"):
                        merged["countries"] = fields.get("countries", [])
                    note = f'<div class="callout ok">Filled {len(prov)} fields from the description. Check them, then create the project.</div>' if prov else '<div class="callout warn">Nothing recognisable in the description; fill the fields below.</div>'
                    return self._send(form_page(merged, prov, note))
                req = intake.normalise(f)
                if not req["countries"]:
                    return self._send(form_page(f, note='<div class="callout warn">Pick at least one country or a region.</div>'))
                pid = store.create_project(req, survey.design(req))
                return self._redirect(f"/p/{pid}")
            m = re.fullmatch(r"/p/(FR-[0-9A-F]{6})/(settings|invite|send|simulate|clear)", u.path)
            if m:
                pid, act = m.groups()
                proj = store.get_project(pid)
                if not proj:
                    return self._send(page("Not found", "<div class=wrap><div class=card>Not found.</div></div>"), 404)
                tab = urllib.parse.parse_qs(u.query).get("tab", ["overview"])[-1]
                if act == "settings":
                    st = dict(proj["settings"])
                    for k, v in f.items():
                        if isinstance(v, str) and re.fullmatch(r"[A-Za-z_ ]{1,40}", k):
                            if v.strip() == "":
                                st.pop(k, None)
                            else:
                                st[k] = v.strip()[:20]
                    store.update_settings(pid, st)
                    return self._redirect(f"/p/{pid}?tab={tab}")
                if act == "invite":
                    keys = f.get("site")
                    keys = keys if isinstance(keys, list) else [keys] if keys else []
                    a = project.analyse(proj, [])
                    chosen = [s for s in a["sites"] if s["key"] in set(keys)]
                    store.add_invites(pid, [{k: s[k] for k in ("key", "facility", "city", "country", "investigator", "studies")} for s in chosen])
                    return self._redirect(f"/p/{pid}?tab=investigators#invites")
                if act == "send":
                    store.mark_sent(pid)
                    return self._redirect(f"/p/{pid}?tab=investigators#invites")
                if act == "simulate":
                    store.mark_sent(pid)
                    for i in store.invites(pid):
                        if i["answers"]:
                            continue
                        rnd = random.Random(i["token"])
                        if rnd.random() < 0.25:  # some never answer
                            continue
                        ans = {q["id"]: synthetic_answers(q, i["site"], rnd) for q in proj["questions"]}
                        store.save_response(i["token"], pid, ans, synthetic=True)
                    return self._redirect(f"/p/{pid}?tab=investigators#results")
                if act == "clear":
                    store.clear_synthetic(pid)
                    return self._redirect(f"/p/{pid}?tab=investigators#invites")
            m = re.fullmatch(r"/s/([A-Za-z0-9_-]{6,20})", u.path)
            if m:
                inv = store.invite(m.group(1))
                if not inv:
                    return self._send(page("Not found", "<div class=wrap><div class=card>Invalid link.</div></div>"), 404)
                qid = {q["id"]: q for q in store.get_project(inv["project_id"])["questions"]}
                raw = urllib.parse.parse_qs(raw_body)
                ans = {k: (v[:20] if qid[k]["kind"] == "multi" else v[-1][:2000]) for k, v in raw.items() if k in qid}
                store.save_response(inv["token"], inv["project_id"], ans)
                return self._redirect(f"/s/{inv['token']}?done=1")
        except Exception as ex:
            return self._err(ex)
        self._send(page("Not found", "<div class=wrap><div class=card>Not found.</div></div>"), 404)


def serve(port=8095):
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"{NAME} running at http://localhost:{port}  (Ctrl+C to stop)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
