"""Tiny stdlib web server for the feasibility pack."""
import html
import math
import re
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import pack as packmod

from .ui import CSS, NAME, LEGEND, e, fmt, link_nct, page, pct, tag  # noqa: F401
DEFAULT_NCT = "NCT07185997"
EXAMPLES = [
    ("NCT07185997", "ArriVent · Phase 3 · lung cancer", "First-line EGFR PACC-mutant NSCLC (ALPACCA). Full pack with curated patient numbers.", "Full demo", True),
    ("NCT06452277", "Bayer · Phase 3 · lung cancer", "Sevabertinib vs standard care in HER2-mutant NSCLC. Competitors, sites and pace; you fill in patient numbers.", "Partial", False),
    ("NCT06463587", "Merck KGaA · Phase 3 · rare disease", "Oral cladribine in generalised myasthenia gravis. Competitors, sites and pace; you fill in patient numbers.", "Partial", False),
]
IN_TRIAL = "<span class='pill ok'>in trial</span>"












def src_link(p, key):
    label, url = p["sources"][key]
    return f'<a href="{e(url)}" target="_blank" title="{e(label)}">source ↗</a>' if url else '<span class="mute xs">judgment</span>'




# ------------------------------------------------------------------ home

def trial_home():
    ex = "".join(f"""<a class="ex" href="/pack?nct={n}"><div class="id">{n} <span class="tag {'F' if full else 'S'}">{badge}</span></div>
<div class="small mute" style="margin:4px 0 6px">{e(who)}</div><div class="small">{e(desc)}</div></a>""" for n, who, desc, badge, full in EXAMPLES)
    return page("Trial lookup · " + NAME, active="trial", body=f"""<div class="wrap">
<div class="homehero"><span class="eyebrow">Trial lookup</span><h1>Check a registered trial in seconds</h1>
<p>Type a trial's ClinicalTrials.gov number. In seconds you get a feasibility pack: how many patients exist,
who else is recruiting them, which sites have done this before, and how long enrolment is likely to take.</p>
<form class="search" action="/pack"><input type="text" name="nct" value="{DEFAULT_NCT}" aria-label="NCT number"><button>Build feasibility pack</button></form>
<p class="small mute" style="margin-top:14px">The NCT number is the ID every trial gets on <a href="https://clinicaltrials.gov" target="_blank">ClinicalTrials.gov</a> (e.g. NCT07185997).
A sponsor would use the number of its own planned trial, or of a competitor's or similar trial.</p></div>

<div class="card"><h2>How to use it</h2><p class="sub">Built for clinical operations and feasibility leads at small and mid-size biotechs.</p>
<div class="steps">
<div class="step"><b class="n">1</b><h3 style="margin-top:0">Enter a trial</h3><div class="small">Your registered trial, or a close comparator if yours isn't registered yet. The pack reads its criteria, countries and sites.</div></div>
<div class="step"><b class="n">2</b><h3 style="margin-top:0">Read the verdict</h3><div class="small">The top of the pack says whether enrolment looks tight, the four numbers that matter, and why. Every number shows its source and whether it is a fact or an estimate.</div></div>
<div class="step"><b class="n">3</b><h3 style="margin-top:0">Test your plan</h3><div class="small">Change any assumption (testing rate, sites, ramp-up) and rebuild. Print to PDF and take it into CRO bids or a board meeting.</div></div>
</div></div>

<div class="card"><h2>Try an example</h2><p class="sub">The first one has hand-checked patient numbers; the others show what you get for any trial today.</p>
<div class="grid3">{ex}</div></div>

<div class="card"><h2>What's in a pack</h2><div class="what" style="margin-top:12px">
<div><b>Verdict and key numbers</b><span class="small mute">Enrolment risk, patients per year, competitors, months to target.</span></div>
<div><b>Patient population</b><span class="small mute">Step-by-step from new cases to eligible patients, by country and US state.</span></div>
<div><b>Competing trials</b><span class="small mute">Who is recruiting the same patients now, and at which of your sites.</span></div>
<div><b>Candidate sites</b><span class="small mute">Hospitals with the most similar trials, and how busy they are now.</span></div>
<div><b>Enrolment forecast</b><span class="small mute">Pace from finished similar trials, three scenarios, back-tested accuracy.</span></div>
<div><b>Sources</b><span class="small mute">Every figure links to SEER, GLOBOCAN, Census or the trial registry.</span></div>
</div></div>
<footer>Public, aggregate data only: ClinicalTrials.gov, SEER, GLOBOCAN, US Census. No patient-level data. Not affiliated with any sponsor. Not medical or regulatory advice.</footer>
</div>""")


# ------------------------------------------------------------------ charts

def svg_curves(runs, n_target, window):
    W, H, L, B, T, R = 680, 280, 46, 34, 16, 16
    maxm = max([r["months"] or 96 for r in runs.values()] + [window or 0]) + 3
    def X(m): return L + (W - L - R) * m / maxm
    def Y(v): return H - B - (H - B - T) * v / n_target
    colors = ["#ef4444", "#0f766e", "#3b82f6"]
    o = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="Enrolment curves">']
    for frac in (0, .25, .5, .75, 1):
        y = Y(n_target * frac)
        o.append(f'<line x1="{L}" y1="{y}" x2="{W-R}" y2="{y}" stroke="#e2e8f0"/><text x="{L-6}" y="{y+4}" font-size="11" text-anchor="end" fill="#64748b">{int(n_target*frac)}</text>')
    for m in range(0, int(maxm) + 1, 12):
        o.append(f'<text x="{X(m)}" y="{H-B+16}" font-size="11" text-anchor="middle" fill="#64748b">{m}</text>')
    o.append(f'<text x="{(W+L)/2}" y="{H-2}" font-size="11" text-anchor="middle" fill="#64748b">months from first site opening</text>')
    if window:
        o.append(f'<rect x="{X(window)}" y="{T}" width="{X(maxm)-X(window)}" height="{H-B-T}" fill="#fef3c7" opacity=".55"/>'
                 f'<line x1="{X(window)}" y1="{T}" x2="{X(window)}" y2="{H-B}" stroke="#b45309" stroke-dasharray="4 3"/>'
                 f'<text x="{X(window)+6}" y="{T+14}" font-size="11" fill="#b45309">sponsor’s posted window ({window:.0f} mo)</text>')
    for (label, r), c in zip(runs.items(), colors):
        pts = " ".join(f"{X(m):.1f},{Y(v):.1f}" for m, v in r["curve"])
        o.append(f'<polyline fill="none" stroke="{c}" stroke-width="3" stroke-linejoin="round" points="{pts}"/>')
        if r["months"]:
            o.append(f'<circle cx="{X(r["months"])}" cy="{Y(n_target)}" r="4.5" fill="{c}"/>')
    o.append("</svg>")
    return "".join(o)


def html_funnel(rows):
    """Funnel as bars on a log scale so the small final numbers stay visible."""
    vals = [r["running"][0] for r in rows]
    top = math.log10(max(vals[0], 10))
    out = []
    for i, (r, v) in enumerate(zip(rows, vals)):
        w = max(3, 100 * max(math.log10(max(v, 1)), 0) / top)
        last = i == len(rows) - 1
        col = "var(--acc)" if last else f"rgba(20,184,166,{0.35 + 0.6 * i / len(rows):.2f})"
        out.append(f'<div class="frow"><span title="{e(r["label"])}">{e(r["label"])}</span>'
                   f'<div class="t"><div style="width:{w:.0f}%;background:{col}"></div></div><b>{fmt(v)}</b></div>')
    return '<div class="funnel">' + "".join(out) + "</div>"


def bars(items, maxv=None, fmtv=lambda v: fmt(v)):
    maxv = maxv or max([v for _, v in items] + [1])
    return "".join(f'<div class="barrow"><span title="{e(k)}">{e(k if len(k) < 22 else k[:20] + "…")}</span><div class="t"><div class="bar" style="width:{100*v/maxv:.1f}%"></div></div><span class="n" style="text-align:right">{fmtv(v)}</span></div>' for k, v in items)


# ------------------------------------------------------------------ report

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
    curated = bool(p["profile_key"])

    # verdict
    vm = typical["months"] or 999
    if win:
        ratio = vm / win
        vclass, vtext = (("v-high", "Enrolment risk: high") if ratio > 1 else ("v-med", "Enrolment risk: medium") if ratio > 0.7 else ("v-low", "Enrolment risk: low"))
        vwhy = f"Typical pace needs ~{typical['months'] or '96+'} months to enrol {sc['n']}; the sponsor's posted start-to-primary-completion window is {win:.0f} months and must also cover treatment and follow-up."
    else:
        vclass, vtext, vwhy = "v-med", "Enrolment risk: not rated", "No posted completion date to compare with."

    chips = [t["sponsor"], t["phase"], t["status"].replace("_", " ").title(), f"Target {fmt(t['enroll'])} patients",
             f"{len(t['locations'])} sites · {len({l['country'] for l in t['locations']})} countries", f"Start {t['start'] or 'n/a'}"]
    out = [f"""<div class="hero"><span class="verdict {vclass}">● {vtext} {tag('J')}</span>
<h1>{e(t['title'])}</h1><div class="small" style="color:#cbd5e1">{link_nct(nct)} · {e(p['profile']['name'])}</div>
<div class="chips">{''.join(f'<span class="chip">{e(c)}</span>' for c in chips)}</div>
<p class="small" style="color:#e2e8f0;margin:14px 0 0;max-width:820px">{e(vwhy)}</p></div>"""]

    # KPIs
    k = []
    if us and curated:
        k.append(("", f'{fmt(us["enrollable"][0])}', f'{fmt(us["enrollable"][1])}–{fmt(us["enrollable"][2])}', "US patients a year who join <i>any</i> trial for this population"))
        k.append(("bad" if us["fair_share"][0] < 20 else "warn", f'{fmt(us["fair_share"][0])}', "per year", f'left for this trial after {us["direct_competitors"]} direct US competitors'))
    else:
        k.append(("warn", "—", "", "Patient numbers: fill in the funnel below (no curated profile for this trial yet)"))
    k.append(("bad" if len(direct) > 10 else "warn" if direct else "", str(len(direct)), f"+{len(partial)} partial", "trials recruiting the same patients right now"))
    k.append(("bad" if vclass == "v-high" else "warn", f'{typical["months"] or "96+"} mo', f'range {sc["runs"]["Fast (P75)"]["months"] or "96+"}–{sc["runs"]["Slow (P25)"]["months"] or "96+"}', f'to enrol {sc["n"]} with {sc["sites"]} sites (typical pace)'))
    out.append('<div class="kpis">' + "".join(f'<div class="kpi {c}"><div class="v">{v} <span class="r">{r}</span></div><div class="l">{l}</div></div>' for c, v, r, l in k) + "</div>")

    # insights
    ins = []
    if us and curated:
        cn = p["funnels"].get("China")
        ins.append(f'<b>The US can&rsquo;t fill this trial.</b> About {fmt(us["enrollable"][0])} US patients a year join any trial for this population, shared with {us["direct_competitors"]} direct competitors. '
                   + (f'China&rsquo;s pool is ~{cn["pool"][0]/us["pool"][0]:.0f}× larger, which fits the sponsor putting {cn["target_sites"]} of {len(t["locations"])} sites there.' if cn else ""))
    if win and typical["months"]:
        ins.append(f'<b>The timeline looks {"tight" if vclass != "v-low" else "achievable"}.</b> {p["bench"]["n"]} finished {e(p["bench"]["basis"].replace("all similar trials", "similar trials"))} enrolled about {typical["rate"]:.3f} patients per site per month; at that pace this trial needs ~{typical["months"]} months vs {win:.0f} posted.')
    free = [s for s in p["sites"] if s["country"] == "United States" and not s["in_target"]][:3]
    if free:
        busy = sum(1 for s in free if s["load"])
        ins.append("<b>Experienced US sites not yet in this trial:</b> " + ", ".join(e(s["facility"]) for s in free) + f". {busy} of {len(free)} are running competing trials now.")
    out.append(f'<div class="card" id="summary"><h2>What this pack says</h2><p class="sub">Three things a clinical-operations lead would take into a CRO conversation.</p><div class="insights">'
               + "".join(f'<div class="ins"><b class="n">{i+1}</b><div>{x}</div></div>' for i, x in enumerate(ins))
               + f'</div><div class="legend"><span>{tag("F")} verified fact</span><span>{tag("S")} published figure</span><span>{tag("E")} estimate</span><span>{tag("J")} judgment</span><span>Ranges multiply all lows or all highs, so they are wider than the real uncertainty.</span></div></div>')

    # population
    countries = list(p["funnels"].items())
    cmp_items = [(c, f["pool"][0]) for c, f in countries]
    funnels_html = "".join(f'<div class="panel"><h3 style="margin-top:0">{e(c)} <span class="mute xs">· {f["target_sites"]} trial sites · {f["direct_competitors"]} direct competitors here</span></h3>{html_funnel(f["rows"])}'
                           f'<div class="small">Eligible pool <b>{fmt(f["pool"][0])}</b>/yr <span class="mute">({fmt(f["pool"][1])}–{fmt(f["pool"][2])})</span> · join any trial <b>{fmt(f["enrollable"][0])}</b>/yr · fair share for this trial <b>{fmt(f["fair_share"][0])}</b>/yr {tag("E")}</div></div>'
                           for c, f in countries)
    blocks = []
    for country, f in countries:
        trs = []
        for s in f["rows"]:
            is_count = s["key"] == "incidence"
            val = fmt(s["base"]) if is_count else pct(s["base"])
            rng = "" if is_count or s["low"] == s["high"] else f'{pct(s["low"])}–{pct(s["high"])}'
            ov = ' <span class="tag E">edited</span>' if s.get("overridden") else ""
            cur = q.get("o_" + country + "_" + s["key"], "")
            trs.append(f'<tr><td>{e(s["label"])}{ov}<div class="xs mute">{e(s["note"])}</div></td><td class="n">{val}<div class="xs mute">{rng}</div></td>'
                       f'<td>{tag(s["tag"])} {src_link(p, s["src"])}</td><td class="n">{fmt(s["running"][0])}</td>'
                       f'<td class="noprint"><input class="sm" type="text" name="o_{e(country)}_{s["key"]}" value="{e(cur)}" placeholder="{s["base"]}"></td></tr>')
        blocks.append(f'<h3>{e(country)}</h3><div class="tw"><table><tr><th>Step</th><th class="n">Base (range)</th><th>Label · source</th><th class="n">Running total / yr</th><th class="noprint">Your value</th></tr>{"".join(trs)}</table></div>')
    hidden = "".join(f'<input type="hidden" name="{k_}" value="{e(v)}">' for k_, v in q.items() if not k_.startswith("o_"))
    st = p["state_split"][:12]
    out.append(f"""<div class="card" id="pop"><h2>Patient population</h2><p class="sub">Newly diagnosed patients per year who would meet the key criteria, built step by step from public statistics. {tag('E')}</p>
<div class="grid2" style="margin-bottom:6px"><div><h3 style="margin-top:0">Eligible patients per year, by country</h3>{bars(cmp_items)}</div>
<div><h3 style="margin-top:0">Where in the US <span class="mute xs">(crude: split by state population)</span></h3>{bars([(s, n) for s, _, n in st], fmtv=lambda v: fmt(v))}</div></div>
<div class="grid2" style="margin-top:14px">{funnels_html}</div>
<details {'open' if any(k_.startswith('o_') for k_ in q) or not curated else ''}><summary>See every assumption and its source · change any value</summary><div>
<p class="small mute">Shares as decimals (e.g. 0.12). Leave blank to keep the base value. The US state split ignores state differences in smoking, lung-cancer rates and Asian-American population share ({src_link(p,'census')}).</p>
<form action="/pack#pop">{hidden}{''.join(blocks)}<p><button>Rebuild with my values</button> <a class="btn ghost" href="/pack?nct={nct}">Reset</a></p></form></div></details></div>""")

    # competing
    by_country = {}
    for c in direct:
        for ct in c["countries"]:
            by_country[ct] = by_country.get(ct, 0) + 1
    by_phase = {}
    for c in direct:
        by_phase[c["phase"]] = by_phase.get(c["phase"], 0) + 1
    ind_direct = sum(1 for c in direct if c["sponsor_class"] == "INDUSTRY")
    shared = sorted([c for c in direct + partial if c["shared_sites"]], key=lambda c: -c["shared_sites"])[:6]

    def comp_rows(lst, limit):
        r = []
        for c in lst[:limit]:
            top = ", ".join(f"{k_} {v}" for k_, v in sorted(c["countries"].items(), key=lambda x: -x[1])[:3])
            r.append(f'<tr><td>{link_nct(c["nct"])}<div><span class="tag {c["tier"]}">{c["tier"]}</span></div></td><td><b style="font-weight:600">{e(c["sponsor"][:40])}</b><div class="small">{e(c["title"][:120])}</div><div class="xs mute">{e("; ".join(c["why"]))}</div></td>'
                     f'<td>{e(c["phase"])}<div class="xs mute">{e(c["status"].replace("_"," ").lower())}</div></td><td class="n">{fmt(c["enroll"])}</td><td class="n">{c["n_sites"]}</td><td class="n">{c["shared_sites"] or "–"}</td><td class="xs">{e(top)}</td></tr>')
        return "".join(r)
    head = '<tr><th>Trial</th><th>Sponsor · title · why it competes</th><th>Phase</th><th class="n">Target</th><th class="n">Sites</th><th class="n">Shared sites</th><th>Top countries</th></tr>'
    shared_html = "".join(f'<div class="barrow"><span>{link_nct(c["nct"])}</span><div class="t"><div class="bar" style="width:{100*c["shared_sites"]/max(1, shared[0]["shared_sites"]):.0f}%;background:#ef4444"></div></div><span style="text-align:right">{c["shared_sites"]}</span></div><div class="xs mute" style="margin:-4px 0 6px">{e(c["sponsor"][:50])}</div>' for c in shared) or '<p class="small mute">None.</p>'
    out.append(f"""<div class="card" id="comp"><h2>Competing trials</h2><p class="sub">{len(direct)} direct competitors ({ind_direct} company-sponsored) and {len(partial)} partial, recruiting now on ClinicalTrials.gov. {tag('F')} list · {tag('J')} tiering</p>
<div class="grid3"><div><h3 style="margin-top:0">Direct competitors by country</h3>{bars(sorted(by_country.items(), key=lambda x: -x[1])[:8])}</div>
<div><h3 style="margin-top:0">By phase</h3>{bars(sorted(by_phase.items(), key=lambda x: -x[1]))}</div>
<div><h3 style="margin-top:0">Most shared sites with {nct}</h3>{shared_html}</div></div>
<h3>Direct competitors</h3><p class="small mute">Same subtype and same setting or line of therapy. Keyword-based, so some are broader than this trial.</p><div class="tw"><table>{head}{comp_rows(direct, 12)}</table></div>
<details><summary>All {len(direct)} direct and top 25 partial competitors</summary><div><div class="tw"><table>{head}{comp_rows(direct[12:], 100)}{comp_rows(partial, 25)}</table></div>
<p class="small"><a href="https://clinicaltrials.gov/search?cond={urllib.parse.quote(p['cond'])}" target="_blank">Open the live search on ClinicalTrials.gov ↗</a></p></div></details></div>""")

    # sites
    cts = sorted({s["country"] for s in p["sites"]}, key=lambda c: -sum(1 for s in p["sites"] if s["country"] == c))
    sel = q.get("site_country", "United States")
    opts = "".join(f'<option {"selected" if c == sel else ""}>{e(c)}</option>' for c in ["All"] + cts[:25])
    lst = [s for s in p["sites"] if sel == "All" or s["country"] == sel]
    new = [s for s in lst if not s["in_target"]][:6]
    cards = "".join(f'<div class="site"><b>{e(s["facility"][:60])}</b><span class="xs mute">{e(", ".join(x for x in (s["city"], s["state"], s["country"]) if x))}</span><div>'
                    f'<span class="pill ok">{s["n"]} similar trials</span><span class="pill">{s["industry"]} industry</span>'
                    f'<span class="pill {"warn" if s["load"] >= 4 else ""}">{s["load"]} competing now</span></div></div>' for s in new)
    mx = max([s["n"] for s in lst[:30]] + [1])
    srows = "".join(f'<tr><td><b style="font-weight:600">{e(s["facility"][:60])}</b><div class="xs mute">{e(", ".join(x for x in (s["city"], s["state"], s["country"]) if x))}</div></td>'
                    f'<td style="width:180px"><div class="barrow" style="grid-template-columns:1fr 30px;margin:2px 0"><div class="t"><div class="bar" style="width:{100*s["n"]/mx:.0f}%"></div></div><span>{s["n"]}</span></div></td>'
                    f'<td class="n">{s["industry"]}</td><td class="n">{s["completed"]}</td><td class="n">{s["terminated"] or "–"}</td><td class="n">{s["load"] or "–"}</td><td>{IN_TRIAL if s["in_target"] else ""}</td></tr>' for s in lst[:30])
    hidden2 = "".join(f'<input type="hidden" name="{k_}" value="{e(v)}">' for k_, v in q.items() if k_ != "site_country")
    out.append(f"""<div class="card" id="sites"><div style="display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap"><div><h2>Candidate sites</h2>
<p class="sub">Hospitals that ran the most similar trials since 2016. Experience, not performance: per-site enrolment is not public. {tag('F')} counts · {tag('J')} ranking</p></div>
<form action="/pack#sites" class="noprint">{hidden2}<select name="site_country" onchange="this.form.submit()">{opts}</select></form></div>
<h3 style="margin-top:4px">Experienced sites not yet in this trial</h3><div class="grid3">{cards or '<p class="small mute">None found.</p>'}</div>
<details><summary>Top 30 sites in {e(sel)}</summary><div><div class="tw"><table><tr><th>Facility</th><th>Similar trials</th><th class="n">Industry</th><th class="n">Completed</th><th class="n">Stopped</th><th class="n">Competing now</th><th></th></tr>{srows}</table></div></div></details></div>""")

    # enrolment
    b = p["bench"]
    colors = {"Slow (P25)": "#ef4444", "Typical (median)": "#0f766e", "Fast (P75)": "#3b82f6"}
    scen = "".join(f'<div class="scen" style="border-top:4px solid {colors[l]}"><div class="xs mute">{e(l)}</div><div class="v">{r["months"] or "96+"} mo</div><div class="xs mute">{r["rate"]:.3f} patients / site / month</div></div>' for l, r in sc["runs"].items())
    brows = "".join(f'<tr><td>{link_nct(r["nct"])}</td><td>{e(r["sponsor"][:28])}<div class="xs mute">{e(r["title"][:90])}</div></td><td class="n">{r["enroll"]}</td><td class="n">{r["n_sites"]}</td><td class="n">{r["months"]:.0f}</td><td class="n">{r["rate"]:.3f}</td></tr>'
                    for r in p["bench_rows"] if (r["subtype"] or b["basis"] == "all similar trials"))
    hidden3 = "".join(f'<input type="hidden" name="{k_}" value="{e(v)}">' for k_, v in q.items() if k_ not in ("target_n", "sites", "ramp", "enrol_fraction"))
    out.append(f"""<div class="card" id="enrol"><h2>Enrolment forecast</h2><p class="sub">Pace taken from {b['n']} finished {e(b['basis'])}; sites open gradually over the ramp-up period. {tag('E')}</p>
<div class="grid2"><div>{svg_curves(sc['runs'], sc['n'], win)}</div><div><div class="grid3" style="gap:10px">{scen}</div>
<form action="/pack#enrol" class="noprint" style="margin-top:16px">{hidden3}<div class="grid2" style="gap:10px">
<label class="small">Target patients<br><input type="number" name="target_n" value="{sc['n']}" style="width:100%"></label>
<label class="small">Sites<br><input type="number" name="sites" value="{sc['sites']}" style="width:100%"></label>
<label class="small">Months to open all sites<br><input type="number" name="ramp" value="{sc['ramp']}" style="width:100%"></label>
<label class="small">Enrolment share of window {tag('J')}<br><input type="text" name="enrol_fraction" value="{p['enrol_fraction']}" style="width:100%"></label></div>
<p><button>Recalculate</button></p></form></div></div>
<div class="note"><b>How accurate is this?</b> Back-tested on 285 finished trials: within ±30% of the real pace for 20% of EGFR lung cancer trials, 48% of myasthenia gravis and 23% of atopic dermatitis trials; within 2× for 53–81%. Treat the months as a range, not a promise.</div>
<details><summary>Benchmark trials used</summary><div><div class="tw"><table><tr><th>Trial</th><th>Sponsor · title</th><th class="n">Enrolled</th><th class="n">Sites</th><th class="n">Months</th><th class="n">Pts/site/mo</th></tr>{brows}</table></div>
<p class="xs mute">All similar trials: median {b['all']['median']:.3f} (n={b['all']['n']}). Assumes enrolment ran for {p['enrol_fraction']:.0%} of the start-to-primary-completion window.</p></div></details></div>""")

    # criteria + sources
    rows = "".join(f'<tr><td><span class="tag {"F" if c["kind"]=="Include" else "J"}">{c["kind"]}</span></td><td>{e(c["text"][:700])}</td><td class="xs">{", ".join(c["tags"])}</td></tr>' for c in p["criteria"][:24])
    srcs = "".join("<li>" + e(l) + (f' — <a href="{e(u)}" target="_blank">link ↗</a>' if u else "") + "</li>" for l, u in p["sources"].values())
    out.append(f"""<div class="card" id="crit"><h2>Key eligibility criteria</h2><p class="sub">Parsed from the public trial record. The product version would read the full protocol with AI.</p>
<div class="tw"><table><tr><th>Type</th><th>Criterion</th><th>Drives</th></tr>{rows}</table></div></div>
<div class="card" id="src"><h2>Sources and method</h2><p class="sub">Generated {p['generated']} · trial data: {e(p['src_trial'])} · similar trials: {e(p['src_all'])} ({p['n_similar']:,} records)</p>
<ul class="small"><li>ClinicalTrials.gov API v2 — <a href="{e(p['q_all'])}" target="_blank">similar-trials query ↗</a> · <a href="https://clinicaltrials.gov/api/v2/studies/{nct}" target="_blank">this trial ↗</a></li>{srcs}</ul>
<h3>Not built yet</h3><ul class="small mute"><li>AI protocol reader</li><li>Curated epidemiology beyond this one indication</li><li>Licensed claims/EHR counts to check patient numbers</li><li>Investigator names, per-site enrolment (paid data)</li><li>Race/ethnicity mix vs sites</li><li>Expert review step and Word/PDF export</li></ul></div>""")

    side = """<nav class="side noprint"><a href="#summary">Summary</a><a href="#pop">Patients</a><a href="#comp">Competing trials</a><a href="#sites">Sites</a><a href="#enrol">Enrolment</a><a href="#crit">Criteria</a><a href="#src">Sources</a><a class="sbtn" href="javascript:print()">Save as PDF</a></nav>"""
    return page(f"{nct} feasibility pack", active="trial", body=f'<div class="wrap"><div class="layout">{side}<main>{"".join(out)}</main></div></div>')


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
                return self._send(page("Check the ID", "<div class='wrap'><div class=card><h2>That doesn't look like an NCT number</h2><p>Use the format NCT followed by 8 digits, e.g. NCT07185997. <a href='/'>Back</a></p></div></div>"), 400)
            q["nct"] = nct
            try:
                return self._send(render(packmod.build(nct, q), q))
            except Exception as ex:  # show the problem instead of a blank page
                return self._send(page("Error", f"<div class='wrap'><div class=card><h2>Could not build the pack</h2><p class=small>Check the number exists on ClinicalTrials.gov and that you're online (only the demo trials work offline).</p><pre class=xs>{e(repr(ex))}</pre><a href='/'>Back</a></div></div>"), 500)
        self._send(page("Not found", "<div class='wrap'><div class=card>Not found. <a href='/'>Home</a></div></div>"), 404)


def serve(port=8095):
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"{NAME} demo running at http://localhost:{port}  (Ctrl+C to stop)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
