"""Tiny stdlib web server for the feasibility pack."""
import html
import re
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import pack as packmod

NAME = "FeasiblePack"  # placeholder working name
DEFAULT_NCT = "NCT07185997"
e = html.escape

CSS = """
:root{--ink:#1d2433;--mute:#5b6577;--line:#e3e6ec;--bg:#f7f8fa;--card:#fff;--acc:#2456a6;--warn:#a15c00;--ok:#1f7a4d;--bad:#b42318}
*{box-sizing:border-box}body{margin:0;font:14px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--ink);background:var(--bg)}
header{background:#14213d;color:#fff;padding:14px 24px;display:flex;gap:16px;align-items:baseline;flex-wrap:wrap}
header b{font-size:18px}header span{opacity:.75;font-size:12px}
main{max-width:1180px;margin:0 auto;padding:20px 16px 60px}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:16px 18px;margin:0 0 16px}
h1{font-size:20px;margin:0 0 4px}h2{font-size:16px;margin:0 0 10px;color:#14213d}h3{font-size:14px;margin:14px 0 6px}
.mute{color:var(--mute)}.small{font-size:12px}
table{border-collapse:collapse;width:100%;font-size:13px}th,td{border-bottom:1px solid var(--line);padding:5px 6px;text-align:left;vertical-align:top}
th{background:#f1f3f7;font-weight:600;font-size:12px}td.n,th.n{text-align:right;font-variant-numeric:tabular-nums}
.tag{display:inline-block;font-size:11px;font-weight:600;border-radius:4px;padding:0 5px;margin-right:3px}
.F{background:#e3f4ea;color:var(--ok)}.S{background:#e6eefb;color:var(--acc)}.E{background:#fff1dc;color:var(--warn)}.J{background:#fde8e7;color:var(--bad)}
.Direct{background:#fde8e7;color:var(--bad)}.Partial{background:#fff1dc;color:var(--warn)}.Low{background:#eef0f3;color:var(--mute)}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px}
.kpi{border:1px solid var(--line);border-radius:8px;padding:10px 12px;background:#fbfcfe}.kpi .v{font-size:22px;font-weight:700}.kpi .l{font-size:12px;color:var(--mute)}
input[type=text],input[type=number]{width:90px;padding:3px 5px;border:1px solid #c9ced8;border-radius:4px;font:inherit}
button,.btn{background:var(--acc);color:#fff;border:0;border-radius:5px;padding:6px 12px;font:inherit;cursor:pointer;text-decoration:none;display:inline-block}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px}@media(max-width:800px){.grid2{grid-template-columns:1fr}}
a{color:var(--acc)}.yes{color:var(--ok);font-weight:600}.note{background:#fffbea;border:1px solid #f1e3a6;border-radius:6px;padding:8px 10px;font-size:12px}
nav a{margin-right:12px;font-size:13px}
@media print{header,nav,form button,.noprint{display:none}body{background:#fff}.card{border:0;padding:0}}
"""


def fmt(x, d=0):
    if x is None:
        return "n/a"
    return f"{x:,.{d}f}"


def pct(x):
    return f"{x*100:.1f}%" if x < 0.1 else f"{x*100:.0f}%"


def tag(t):
    return f'<span class="tag {t}">{t}</span>'


def link_nct(n):
    return f'<a href="https://clinicaltrials.gov/study/{n}" target="_blank">{n}</a>'


def src_link(p, key):
    label, url = p["sources"][key]
    return f'<a href="{e(url)}" target="_blank" title="{e(label)}">source</a>' if url else '<span class="mute">judgment</span>'


def page(title, body):
    return f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title><style>{CSS}</style></head><body>
<header><b>{NAME}</b><span>Clinical-trial feasibility pack from public data · demo · every number is an estimate unless tagged F</span></header>
<main>{body}</main></body></html>"""


def home():
    return page(NAME, f"""<div class="card"><h1>Feasibility pack from public data</h1>
<p class="mute">Enter a ClinicalTrials.gov ID. The demo has curated epidemiology for one trial
(<b>{DEFAULT_NCT}</b>, ArriVent's ALPACCA phase 3 in EGFR PACC-mutant NSCLC). Any other trial still gets competing trials,
site track record and enrolment benchmarks, with a blank funnel you fill in.</p>
<form action="/pack"><input type="text" name="nct" value="{DEFAULT_NCT}" style="width:160px"> <button>Build pack</button></form>
<p class="small mute">Public, aggregate data only: ClinicalTrials.gov API, SEER, GLOBOCAN, US Census. No patient-level data.
Not affiliated with any sponsor. Not medical or regulatory advice.</p></div>""")


def svg_curves(runs, n_target, window):
    W, H, pad = 640, 240, 36
    maxm = max([r["months"] or 96 for r in runs.values()] + [window or 0]) + 2
    def X(m): return pad + (W - 2 * pad) * m / maxm
    def Y(v): return H - pad - (H - 2 * pad) * v / n_target
    colors = ["#b42318", "#2456a6", "#1f7a4d"]
    out = [f'<svg viewBox="0 0 {W} {H}" width="100%" style="max-width:{W}px">',
           f'<line x1="{pad}" y1="{H-pad}" x2="{W-pad}" y2="{H-pad}" stroke="#999"/><line x1="{pad}" y1="{pad}" x2="{pad}" y2="{H-pad}" stroke="#999"/>',
           f'<line x1="{pad}" y1="{Y(n_target)}" x2="{W-pad}" y2="{Y(n_target)}" stroke="#ccc" stroke-dasharray="4"/>',
           f'<text x="{pad+4}" y="{Y(n_target)-4}" font-size="11" fill="#5b6577">target {n_target}</text>']
    for m in range(0, int(maxm) + 1, 12):
        out.append(f'<text x="{X(m)}" y="{H-pad+14}" font-size="10" text-anchor="middle" fill="#5b6577">{m}</text>')
    out.append(f'<text x="{W/2}" y="{H-4}" font-size="11" text-anchor="middle" fill="#5b6577">months from first site open</text>')
    if window:
        out.append(f'<line x1="{X(window)}" y1="{pad}" x2="{X(window)}" y2="{H-pad}" stroke="#a15c00" stroke-dasharray="3"/>'
                   f'<text x="{X(window)+4}" y="{pad+10}" font-size="10" fill="#a15c00">sponsor start to primary completion ({window:.0f} mo)</text>')
    for (label, r), c in zip(runs.items(), colors):
        pts = " ".join(f"{X(m):.1f},{Y(v):.1f}" for m, v in r["curve"])
        out.append(f'<polyline fill="none" stroke="{c}" stroke-width="2" points="{pts}"/>')
    out.append("</svg>")
    leg = " ".join(f'<span style="color:{c};font-weight:600">■ {e(l)}</span>' for l, c in zip(runs, colors))
    return "".join(out) + f'<div class="small">{leg}</div>'


def render(p, q):
    t = p["target"]
    nct = p["nct"]
    comp = p["competing"]
    direct = [c for c in comp if c["tier"] == "Direct"]
    partial = [c for c in comp if c["tier"] == "Partial"]
    us = p["funnels"].get("United States")
    sc = p["scenario"]
    typical = sc["runs"]["Typical (median)"]
    win = p["posted_window_months"]

    # --- takeaways
    k = []
    if us:
        k.append((f'{fmt(us["enrollable"][0])} <span class="small mute">({fmt(us["enrollable"][1])}–{fmt(us["enrollable"][2])})</span>',
                  "US patients/year likely to enrol in any trial for this population [E]"))
        k.append((f'{fmt(us["fair_share"][0])}', f'US patients/year left for this trial if shared with {us["direct_competitors"]} direct competitors active in the US [E]'))
    k.append((str(len(direct)), f"Direct competing trials active now ({len(partial)} partial) [F count, J tiering]"))
    k.append((f'{typical["months"] or ">96"} mo', f'Typical time to {sc["n"]} patients with {sc["sites"]} sites (benchmark median) [E]'
              + (f"; sponsor posts {win:.0f} mo start to primary completion" if win else "")))

    takeaways = []
    if us and p["profile_key"]:
        cn = p["funnels"].get("China")
        takeaways.append(f'The US can supply only a small part of {sc["n"]} patients: about {fmt(us["enrollable"][0])} US patients a year enrol in <i>any</i> trial for this population, '
                         f'before splitting them with {us["direct_competitors"]} direct competitors. '
                         + (f'China\'s pool is roughly {cn["pool"][0]/us["pool"][0]:.0f}x larger (EGFR mutations are 2-3x more common in Asian patients), which explains the site footprint ({cn["target_sites"]} of {len(t["locations"])} sites in China).' if cn else ""))
    if win and typical["months"]:
        verdict = "tight" if typical["months"] > win * 0.7 else "achievable"
        takeaways.append(f'Benchmarks from {p["bench"]["n"]} finished {e(p["bench"]["basis"])} put enrolment at about {typical["rate"]:.3f} patients per site per month. '
                         f'At that pace {sc["sites"]} sites need ~{typical["months"]} months to enrol {sc["n"]}; the sponsor posts {win:.0f} months from first patient to primary completion, '
                         f'which must also cover treatment and follow-up. Plan looks <b>{verdict}</b> [J].')
    top_free = [s for s in p["sites"] if s["country"] == "United States" and not s["in_target"]][:3]
    if top_free:
        takeaways.append("Experienced US sites not yet listed for this trial include " + "; ".join(e(s["facility"]) for s in top_free)
                         + " (ranked by number of similar trials since 2016; they also carry competing trials).")

    kp = "".join(f'<div class="kpi"><div class="v">{v}</div><div class="l">{l}</div></div>' for v, l in k)
    out = [f"""<nav class="noprint"><a href="/">← New pack</a><a href="#pop">Population</a><a href="#comp">Competing trials</a><a href="#sites">Sites</a><a href="#enrol">Enrolment</a><a href="#src">Sources</a> <a href="javascript:print()">Print / save PDF</a></nav>
<div class="card"><div class="small mute">Feasibility pack · generated {p['generated']} · trial data: {e(p['src_trial'])} · similar trials: {e(p['src_all'])} ({p['n_similar']:,} records)</div>
<h1>{e(t['title'])}</h1><div class="mute">{link_nct(nct)} · {e(t['sponsor'])} · {e(t['phase'])} · {e(t['status'].replace('_',' ').title())} · target {fmt(t['enroll'])} ({e(t['enroll_type'].lower())}) · {len(t['locations'])} sites in {len({l['country'] for l in t['locations']})} countries · start {e(t['start'] or '')} · primary completion {e(t['pcd'] or '')} ({e(t['pcd_type'].lower())})</div>
<p class="small">Population profile: <b>{e(p['profile']['name'])}</b>. Similar-trial search: “{e(p['cond'])}”.</p>
<div class="kpis">{kp}</div>
<h3>What this pack says</h3><ul>{''.join(f'<li>{x}</li>' for x in takeaways) or '<li class="mute">Fill in the funnel to get population takeaways.</li>'}</ul>
<div class="note">Labels: {tag('F')} verified fact from a primary source · {tag('S')} published figure read from a secondary page · {tag('E')} estimate derived from sources · {tag('J')} analyst judgment. Ranges multiply all lows or all highs together, so they are wider than the true uncertainty.</div></div>"""]

    # --- criteria
    rows = "".join(f'<tr><td>{c["kind"]}</td><td>{e(c["text"][:300])}</td><td class="small">{", ".join(c["tags"])}</td></tr>' for c in p["criteria"][:24])
    out.append(f'<div class="card"><h2>1. Key eligibility criteria (parsed from the public record)</h2><table><tr><th>Type</th><th>Criterion</th><th>Drives funnel step</th></tr>{rows}</table>'
               f'<p class="small mute">Parsed with simple rules. The product would use AI to read a full protocol and map each criterion to a funnel step.</p></div>')

    # --- funnels
    blocks = []
    for country, f in p["funnels"].items():
        trs = []
        for s in f["rows"]:
            is_count = s["key"] == "incidence"
            val = fmt(s["base"]) if is_count else pct(s["base"])
            rng = "" if is_count or s["low"] == s["high"] else f'{pct(s["low"])}–{pct(s["high"])}'
            ov = f' <span class="tag E">edited</span>' if s.get("overridden") else ""
            cur = q.get("o_" + country + "_" + s["key"], "")
            trs.append(f'<tr><td>{e(s["label"])}{ov}<div class="small mute">{e(s["note"])}</div></td><td class="n">{val}<br><span class="small mute">{rng}</span></td>'
                       f'<td>{tag(s["tag"])} {src_link(p, s["src"])}</td><td class="n">{fmt(s["running"][0])}</td>'
                       f'<td class="noprint"><input type="text" name="o_{e(country)}_{s["key"]}" value="{e(cur)}" placeholder="{s["base"]}"></td></tr>')
        blocks.append(f"""<h3>{e(country)} <span class="small mute">· this trial lists {f['target_sites']} sites here · {f['direct_competitors']} direct competitors active here</span></h3>
<table><tr><th>Step</th><th class="n">Base (range)</th><th>Label</th><th class="n">Running total / yr</th><th class="noprint">Your value</th></tr>{''.join(trs)}
<tr><th>Eligible patients per year (pool)</th><th class="n">{fmt(f['pool'][0])}</th><th colspan="3" class="small">range {fmt(f['pool'][1])}–{fmt(f['pool'][2])} {tag('E')}</th></tr>
<tr><th>Likely to enrol in any trial per year</th><th class="n">{fmt(f['enrollable'][0])}</th><th colspan="3" class="small">range {fmt(f['enrollable'][1])}–{fmt(f['enrollable'][2])} {tag('E')}</th></tr>
<tr><th>Fair share for this trial (÷ 1 + direct competitors here)</th><th class="n">{fmt(f['fair_share'][0])}</th><th colspan="3" class="small">crude: assumes equal split {tag('J')}</th></tr></table>""")
    hidden = "".join(f'<input type="hidden" name="{k_}" value="{e(v)}">' for k_, v in q.items() if not k_.startswith("o_"))
    states = "".join(f'<tr><td>{e(s)}</td><td class="n">{fmt(pop)}</td><td class="n">{fmt(n, 1)}</td></tr>' for s, pop, n in p["state_split"][:12])
    out.append(f"""<div class="card" id="pop"><h2>2. Patient population (annual, incident) {tag('E')}</h2>
<p class="small mute">Incident-case funnel: newly diagnosed patients per year who would meet the key criteria. Prevalent and recurrent patients are not added, which may undercount. Type your own values (shares as decimals, e.g. 0.12) and rebuild.</p>
<form action="/pack">{hidden}{''.join(blocks)}<p><button>Rebuild with my values</button> <a class="small" href="/pack?nct={nct}">reset</a></p></form>
<h3>Where in the US (crude split by population)</h3><p class="small mute">US eligible pool allocated by 2025 state population ({src_link(p,'census')}). Ignores state differences in smoking, lung-cancer rates and Asian-American population share, all of which matter here. Product version: state cancer rates (CDC USCS) and county demographics.</p>
<table style="max-width:520px"><tr><th>State</th><th class="n">Population 2025</th><th class="n">Eligible / yr {tag('E')}</th></tr>{states}</table></div>""")

    # --- competing
    def comp_rows(lst, limit):
        r = []
        for c in lst[:limit]:
            top = ", ".join(f"{k_} {v}" for k_, v in sorted(c["countries"].items(), key=lambda x: -x[1])[:3])
            r.append(f'<tr><td>{link_nct(c["nct"])}</td><td><span class="tag {c["tier"]}">{c["tier"]}</span></td><td>{e(c["title"][:110])}<div class="small mute">{e("; ".join(c["why"]))}</div></td>'
                     f'<td>{e(c["sponsor"][:32])}<div class="small mute">{e(c["sponsor_class"].lower())}</div></td><td>{e(c["phase"])}</td><td class="small">{e(c["status"].replace("_"," ").lower())}</td>'
                     f'<td class="n">{fmt(c["enroll"])}</td><td class="n">{c["n_sites"]}</td><td class="n">{c["shared_sites"] or ""}</td><td class="small">{e(top)}</td></tr>')
        return "".join(r)
    head = '<tr><th>Trial</th><th>Overlap</th><th>Title / why</th><th>Sponsor</th><th>Phase</th><th>Status</th><th class="n">Target n</th><th class="n">Sites</th><th class="n">Shared sites</th><th>Top countries</th></tr>'
    ind_direct = sum(1 for c in direct if c["sponsor_class"] == "INDUSTRY")
    out.append(f"""<div class="card" id="comp"><h2>3. Competing trials recruiting now {tag('F')} list · {tag('J')} overlap tier</h2>
<p class="small mute">Active interventional trials on ClinicalTrials.gov matching “{e(p['cond'])}” ({len(comp)} found). Overlap tier from title, conditions, keywords and inclusion criteria: Direct = same subtype and setting/line; Partial = same biomarker, different setting or line. “Shared sites” = facilities also listed for {nct}, where the two trials compete for the same patients at the same desk.
<a href="https://clinicaltrials.gov/search?cond={urllib.parse.quote(p['cond'])}&aggFilters=status:rec%20not" target="_blank">Open the live search</a>.</p>
<h3>Direct ({len(direct)}, of which {ind_direct} industry-sponsored)</h3><table>{head}{comp_rows(direct, 60)}</table>
<h3>Partial (top 15 of {len(partial)})</h3><table>{head}{comp_rows(partial, 15)}</table></div>""")

    # --- sites
    countries = sorted({s["country"] for s in p["sites"]}, key=lambda c: -sum(1 for s in p["sites"] if s["country"] == c))
    sel = q.get("site_country", "United States")
    opts = "".join(f'<option {"selected" if c == sel else ""}>{e(c)}</option>' for c in ["All"] + countries[:25])
    lst = [s for s in p["sites"] if sel == "All" or s["country"] == sel][:30]
    srows = "".join(f'<tr><td>{e(s["facility"][:70])}</td><td class="small">{e(", ".join(x for x in (s["city"], s["state"], s["country"]) if x))}</td><td class="n">{s["n"]}</td><td class="n">{s["industry"]}</td><td class="n">{s["completed"]}</td><td class="n">{s["terminated"] or ""}</td><td class="n">{s["load"] or ""}</td><td>{"<span class=yes>listed</span>" if s["in_target"] else ""}</td></tr>' for s in lst)
    hidden2 = "".join(f'<input type="hidden" name="{k_}" value="{e(v)}">' for k_, v in q.items() if k_ != "site_country")
    out.append(f"""<div class="card" id="sites"><h2>4. Candidate sites: track record on similar trials {tag('F')} counts · {tag('J')} ranking</h2>
<form action="/pack#sites" class="noprint">{hidden2}Country <select name="site_country" onchange="this.form.submit()">{opts}</select></form>
<p class="small mute">Facilities listed on similar interventional trials started since 2016, ranked by count. ClinicalTrials.gov does not publish per-site enrolment, so this is experience, not performance. “Competing load” = Direct or Partial trials recruiting at the site now. Facility names are only lightly cleaned; anonymised listings such as “Research Site” are left out.</p>
<table><tr><th>Facility</th><th>Location</th><th class="n">Similar trials</th><th class="n">Industry</th><th class="n">Completed</th><th class="n">Terminated / withdrawn</th><th class="n">Competing load now</th><th>In {nct}</th></tr>{srows}</table></div>""")

    # --- enrolment
    b = p["bench"]
    brows = "".join(f'<tr><td>{link_nct(r["nct"])}</td><td>{e(r["title"][:90])}</td><td>{e(r["sponsor"][:28])}</td><td class="n">{r["enroll"]}</td><td class="n">{r["n_sites"]}</td><td class="n">{r["months"]:.0f}</td><td class="n">{r["rate"]:.3f}</td></tr>'
                    for r in p["bench_rows"] if (r["subtype"] or b["basis"] == "all similar trials"))
    srun = "".join(f'<tr><td>{e(l)}</td><td class="n">{r["rate"]:.3f}</td><td class="n">{r["months"] or ">96"}</td></tr>' for l, r in sc["runs"].items())
    hidden3 = "".join(f'<input type="hidden" name="{k_}" value="{e(v)}">' for k_, v in q.items() if k_ not in ("target_n", "sites", "ramp", "enrol_fraction"))
    out.append(f"""<div class="card" id="enrol"><h2>5. Enrolment estimate {tag('E')}</h2>
<p class="small mute">Benchmark = patients per site per month in finished industry phase 2/3 trials (started 2012+, actual enrolment, ≥5 sites). Basis: <b>{e(b['basis'])}</b> (n={b['n']}). For comparison, all similar EGFR trials: median {b['all']['median']:.3f} (n={b['all']['n']}).
Assumes enrolment ran for {p['enrol_fraction']:.0%} of the start-to-primary-completion window {tag('J')}; listed sites may not all have enrolled.</p>
<div class="grid2"><div>{svg_curves(sc['runs'], sc['n'], win)}</div><div>
<form action="/pack#enrol">{hidden3}<table>
<tr><td>Target patients</td><td><input type="number" name="target_n" value="{sc['n']}"></td></tr>
<tr><td>Sites</td><td><input type="number" name="sites" value="{sc['sites']}"></td></tr>
<tr><td>Months to open all sites</td><td><input type="number" name="ramp" value="{sc['ramp']}"></td></tr>
<tr><td>Enrolment share of window</td><td><input type="text" name="enrol_fraction" value="{p['enrol_fraction']}"></td></tr></table>
<p><button>Recalculate</button></p></form>
<table><tr><th>Scenario</th><th class="n">Pts/site/month</th><th class="n">Months to target</th></tr>{srun}</table></div></div>
<h3>Benchmark trials</h3><table><tr><th>Trial</th><th>Title</th><th>Sponsor</th><th class="n">Enrolled</th><th class="n">Sites</th><th class="n">Months</th><th class="n">Pts/site/mo</th></tr>{brows}</table></div>""")

    # --- sources
    srcs = "".join("<li>" + e(l) + (f' — <a href="{e(u)}" target="_blank">{e(u)}</a>' if u else "") + "</li>" for l, u in p["sources"].values())
    out.append(f"""<div class="card" id="src"><h2>6. Sources and method</h2><ul class="small">
<li>ClinicalTrials.gov API v2, fetched {p['generated']} — <a href="{e(p['q_all'])}" target="_blank">similar-trials query</a>; <a href="https://clinicaltrials.gov/api/v2/studies/{nct}" target="_blank">this trial</a></li>{srcs}</ul>
<h3>Not built yet</h3><ul class="small"><li>AI protocol reader (criteria are rule-parsed from the public summary)</li><li>Curated epidemiology for more indications; rare-disease registries</li>
<li>Licensed claims/EHR counts to check public estimates (kill test: within ±30% for 3 indications)</li><li>Facility-name cleaning, investigator names, per-site enrolment (needs paid data)</li>
<li>Race/ethnicity mix of the eligible pool vs trial sites; ex-US epidemiology beyond China and Japan</li><li>Expert review step and report export</li></ul></div>""")
    return page(f"{nct} feasibility pack", "".join(out))


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

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = {k: v[-1] for k, v in urllib.parse.parse_qs(u.query).items()}
        if u.path == "/":
            return self._send(home())
        if u.path == "/pack":
            nct = (q.get("nct") or DEFAULT_NCT).strip().upper()
            if not re.fullmatch(r"NCT\d{8}", nct):
                return self._send(page("Bad ID", "<div class=card>Use an ID like NCT07185997. <a href='/'>Back</a></div>"), 400)
            q["nct"] = nct
            try:
                return self._send(render(packmod.build(nct, q), q))
            except Exception as ex:  # show the problem instead of a blank page
                return self._send(page("Error", f"<div class=card><h2>Could not build the pack</h2><pre>{e(repr(ex))}</pre><a href='/'>Back</a></div>"), 500)
        self._send(page("Not found", "<div class=card>Not found. <a href='/'>Home</a></div>"), 404)


def serve(port=8095):
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"{NAME} demo running at http://localhost:{port}  (Ctrl+C to stop)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
