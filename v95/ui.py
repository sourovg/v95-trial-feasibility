"""Shared look and feel: design tokens, page shell, Cohortia logo, small formatters."""
import html
import urllib.parse

NAME = "Cohortia"
e = html.escape

CSS = """
:root{--ink:#0f1b2d;--ink2:#334155;--mute:#64748b;--line:#e2e8f0;--bg:#f4f6fa;--card:#fff;
--navy:#0b1f3a;--acc:#0f766e;--acc2:#14b8a6;--accbg:#e6f6f4;--blue:#2563eb;--amber:#b45309;--amberbg:#fef3c7;--red:#b91c1c;--redbg:#fee2e2;--green:#15803d;--greenbg:#dcfce7;
--shadow:0 1px 2px rgba(15,27,45,.06),0 4px 16px rgba(15,27,45,.06);--r:14px}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;font:15px/1.5 Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--ink);background:var(--bg)}
a{color:var(--acc);text-decoration:none}a:hover{text-decoration:underline}
.top{background:var(--navy);color:#fff;padding:0 28px;height:60px;display:flex;align-items:center;gap:14px;position:sticky;top:0;z-index:10}
.logo{display:flex;align-items:center;gap:10px;font-weight:700;font-size:18px;color:#fff}.logo:hover{text-decoration:none}
.logo i{width:28px;height:28px;border-radius:8px;background:linear-gradient(135deg,var(--acc2),#3b82f6);display:inline-block}
.top .tag2{font-size:12px;color:#cbd5e1;border:1px solid #334155;border-radius:20px;padding:2px 10px}
.top .sp{flex:1}.top a.l{color:#e2e8f0;font-size:14px}
.wrap{max-width:1200px;margin:0 auto;padding:28px 20px 80px}
.layout{display:grid;grid-template-columns:200px 1fr;gap:28px}
.side{position:sticky;top:84px;align-self:start;display:flex;flex-direction:column;gap:2px}
.side a{color:var(--ink2);padding:7px 12px;border-radius:8px;font-size:14px}.side a:hover{background:#e9eef5;text-decoration:none}
.side .sbtn{margin-top:12px;background:var(--acc);color:#fff;text-align:center}.side .sbtn:hover{background:#0d5f59}
.layout>main{min-width:0}@media(max-width:900px){.layout{grid-template-columns:1fr}.side{display:none}.wrap{padding:16px 14px 60px}.hero{padding:20px}.card{padding:18px 16px}.homehero h1{font-size:28px}}
.card{background:var(--card);border-radius:var(--r);box-shadow:var(--shadow);padding:24px 26px;margin:0 0 22px}
h1{font-size:26px;line-height:1.25;margin:0 0 8px;letter-spacing:-.01em}h2{font-size:19px;margin:0 0 4px;letter-spacing:-.01em}
h3{font-size:15px;margin:20px 0 8px}.sub{color:var(--mute);font-size:14px;margin:0 0 16px}
.mute{color:var(--mute)}.small{font-size:13px}.xs{font-size:12px}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0 0}.chip{background:#eef2f7;color:var(--ink2);border-radius:20px;padding:3px 11px;font-size:13px}
.hero{background:linear-gradient(135deg,#0b1f3a 0%,#123a5c 60%,#0f766e 140%);color:#fff;border-radius:var(--r);padding:28px 30px;margin-bottom:22px;box-shadow:var(--shadow)}
.hero h1{color:#fff;font-size:22px}.hero .chip{background:rgba(255,255,255,.12);color:#e2e8f0}.hero a{color:#99f6e4}
.verdict{display:inline-flex;align-items:center;gap:8px;font-weight:600;border-radius:22px;padding:5px 14px;font-size:14px;margin-bottom:12px}
.v-high{background:#fecaca;color:#7f1d1d}.v-med{background:#fde68a;color:#78350f}.v-low{background:#bbf7d0;color:#14532d}
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:22px}@media(max-width:900px){.kpis{grid-template-columns:1fr 1fr}}
.kpi{background:var(--card);border-radius:var(--r);box-shadow:var(--shadow);padding:18px 18px 16px;border-top:4px solid var(--acc2)}
.kpi .v{font-size:30px;font-weight:700;letter-spacing:-.02em}.kpi .r{font-size:13px;color:var(--mute);font-weight:500}
.kpi .l{font-size:13px;color:var(--ink2);margin-top:4px}.kpi.warn{border-top-color:#f59e0b}.kpi.bad{border-top-color:#ef4444}
.insights{display:grid;gap:10px}.ins{display:flex;gap:12px;align-items:flex-start;background:#f8fafc;border-radius:10px;padding:12px 14px}
.ins b.n{flex:none;width:26px;height:26px;border-radius:50%;background:var(--acc);color:#fff;display:flex;align-items:center;justify-content:center;font-size:13px}
table{border-collapse:collapse;width:100%;font-size:13.5px}th,td{border-bottom:1px solid var(--line);padding:9px 10px;text-align:left;vertical-align:top}
th{color:var(--mute);font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.03em;background:#f8fafc}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums}tr:hover td{background:#fafcff}
.tag{display:inline-block;font-size:11px;font-weight:700;border-radius:5px;padding:1px 6px;vertical-align:1px}
.F{background:var(--greenbg);color:var(--green)}.S{background:#dbeafe;color:#1d4ed8}.E{background:var(--amberbg);color:var(--amber)}.J{background:var(--redbg);color:var(--red)}
.Direct{background:var(--redbg);color:var(--red)}.Partial{background:var(--amberbg);color:var(--amber)}.Low{background:#f1f5f9;color:var(--mute)}
.legend{display:flex;flex-wrap:wrap;gap:14px;font-size:12px;color:var(--mute);margin-top:14px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:22px}.grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}
@media(max-width:800px){.grid2,.grid3{grid-template-columns:1fr}}
.panel{border:1px solid var(--line);border-radius:12px;padding:16px}
.funnel{margin:6px 0 12px}.frow{display:grid;grid-template-columns:minmax(0,1.2fr) 1fr 70px;gap:10px;align-items:center;font-size:12.5px;margin:5px 0;color:var(--ink2)}
.frow span{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.frow .t{height:16px;background:#f1f5f9;border-radius:5px;overflow:hidden}.frow .t div{height:100%;border-radius:5px}
.frow b{text-align:right;font-variant-numeric:tabular-nums;color:var(--ink)}
.card{scroll-margin-top:80px}.tw{overflow-x:auto}
.bar{height:10px;border-radius:5px;background:linear-gradient(90deg,var(--acc2),var(--acc))}
.barrow{display:grid;grid-template-columns:150px 1fr 60px;gap:10px;align-items:center;font-size:13px;margin:6px 0}
.barrow .t{height:10px;background:#eef2f7;border-radius:5px;overflow:hidden}
details{border:1px solid var(--line);border-radius:12px;margin-top:16px}summary{cursor:pointer;padding:12px 16px;font-weight:600;font-size:14px;list-style:none}
summary::before{content:"▸ ";color:var(--acc)}details[open] summary::before{content:"▾ "}details>div{padding:0 16px 16px}
input[type=text],input[type=number],select{padding:7px 10px;border:1px solid #cbd5e1;border-radius:8px;font:inherit;font-size:14px;background:#fff}
input.sm{width:96px;padding:4px 8px;font-size:13px}
button,.btn{background:var(--acc);color:#fff;border:0;border-radius:9px;padding:9px 18px;font:inherit;font-weight:600;cursor:pointer;display:inline-block}
button:hover,.btn:hover{background:#0d5f59;text-decoration:none}.btn.ghost{background:#fff;color:var(--acc);border:1px solid #99d5cf}
.site{border:1px solid var(--line);border-radius:12px;padding:14px}.site b{display:block;font-size:14px}
.pill{display:inline-block;font-size:12px;border-radius:12px;padding:1px 8px;background:#f1f5f9;color:var(--ink2);margin:6px 4px 0 0}
.pill.ok{background:var(--greenbg);color:var(--green)}.pill.warn{background:var(--amberbg);color:var(--amber)}
.scen{border-radius:12px;padding:14px;text-align:center;border:1px solid var(--line)}.scen .v{font-size:26px;font-weight:700}
.note{background:#f8fafc;border-left:3px solid var(--acc2);border-radius:6px;padding:10px 14px;font-size:13px;color:var(--ink2)}
/* home */
.homehero{text-align:center;padding:56px 20px 40px}.homehero h1{font-size:38px;max-width:760px;margin:0 auto 14px}
.homehero p{font-size:18px;color:var(--ink2);max-width:680px;margin:0 auto 26px}
.search{display:flex;gap:10px;justify-content:center;flex-wrap:wrap}.search input{width:260px;font-size:17px;padding:11px 14px}.search button{font-size:16px;padding:11px 22px}
.steps{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}@media(max-width:800px){.steps{grid-template-columns:1fr}}
.step b.n{display:inline-flex;width:30px;height:30px;border-radius:50%;background:var(--accbg);color:var(--acc);align-items:center;justify-content:center;margin-bottom:8px}
.ex{display:block;border:1px solid var(--line);border-radius:12px;padding:16px;color:var(--ink);transition:.15s}.ex:hover{border-color:var(--acc2);box-shadow:var(--shadow);text-decoration:none}
.ex .id{font-weight:700;color:var(--acc)}
.what{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}@media(max-width:800px){.what{grid-template-columns:1fr}}
.what div{background:#f8fafc;border-radius:12px;padding:14px}.what b{display:block;margin-bottom:4px}
footer{color:var(--mute);font-size:12px;text-align:center;margin-top:30px}
@media print{.top,.side,.noprint,details summary{display:none}.layout{display:block}body{background:#fff}.card,.kpi{box-shadow:none;border:1px solid var(--line)}
details{border:0}details>div{display:block!important}.hero{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
"""

EXTRA_CSS = """
/* ---- Cohortia shell ---- */
.top{background:#fff;color:var(--ink);border-bottom:1px solid var(--line);box-shadow:0 1px 0 rgba(15,27,45,.02)}
.logo{color:var(--navy)}.logo svg{flex:none}.logo .wm{font-weight:750;letter-spacing:-.02em;font-size:19px}.logo .wm em{font-style:normal;color:var(--acc)}
.top .tag2{color:var(--mute);border-color:var(--line);background:#f8fafc}
.top a.l{color:var(--ink2);font-size:14px;padding:6px 10px;border-radius:8px}.top a.l:hover{background:#f1f5f9;text-decoration:none}
.top a.l.on{color:var(--acc);font-weight:600}.top a.cta{background:var(--acc);color:#fff;font-weight:600}.top a.cta:hover{background:#0d5f59}
@media(max-width:700px){.top{padding:0 12px;gap:6px}.top .tag2,.top a.l.hide-s{display:none}.logo .wm{font-size:17px}}
/* home */
.hhero{display:grid;grid-template-columns:1.15fr 1fr;gap:36px;align-items:center;padding:40px 0 30px}
@media(max-width:900px){.hhero{grid-template-columns:1fr;padding:18px 0}}
.eyebrow{display:inline-block;font-size:12px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--acc);background:var(--accbg);border-radius:20px;padding:4px 12px;margin-bottom:14px}
.hhero h1{font-size:42px;line-height:1.1;letter-spacing:-.03em;margin:0 0 16px}.hhero p.lead{font-size:18px;color:var(--ink2);margin:0 0 24px}
@media(max-width:700px){.hhero h1{font-size:30px}}
.ctas{display:flex;gap:12px;flex-wrap:wrap}.btn.lg{padding:13px 22px;font-size:16px;border-radius:11px}
.mock{background:linear-gradient(160deg,#0b1f3a,#123a5c 65%,#0f766e);border-radius:20px;padding:22px;color:#e2e8f0;box-shadow:0 20px 50px rgba(11,31,58,.25)}
.mock .row{display:flex;justify-content:space-between;align-items:center;background:rgba(255,255,255,.07);border-radius:10px;padding:10px 12px;margin:8px 0;font-size:13.5px}
.mock .row b{color:#fff}.mock .sc{font-weight:700;color:#5eead4}
.pillars{display:grid;grid-template-columns:repeat(4,1fr);gap:16px}@media(max-width:900px){.pillars{grid-template-columns:1fr 1fr}}@media(max-width:560px){.pillars{grid-template-columns:1fr}}
.pillar{background:#fff;border:1px solid var(--line);border-radius:14px;padding:18px}.pillar .ic{width:36px;height:36px;border-radius:10px;background:var(--accbg);color:var(--acc);display:flex;align-items:center;justify-content:center;font-weight:700;margin-bottom:10px}
.pillar b{display:block;margin-bottom:4px}.pillar .ai{display:inline-block;margin-top:8px;font-size:11.5px;font-weight:600;color:var(--blue);background:#eff6ff;border-radius:6px;padding:2px 7px}
.list a.req{display:grid;grid-template-columns:110px 1fr auto;gap:14px;align-items:center;padding:12px 4px;border-bottom:1px solid var(--line);color:var(--ink)}
.list a.req:hover{background:#fafcff;text-decoration:none}.list a.req .id{font-weight:700;color:var(--acc);font-size:13px}
@media(max-width:600px){.list a.req{grid-template-columns:1fr}}
/* form */
.formgrid{display:grid;grid-template-columns:1fr 320px;gap:26px}@media(max-width:980px){.formgrid{grid-template-columns:1fr}}
.fsec{background:#fff;border-radius:var(--r);box-shadow:var(--shadow);padding:24px 26px;margin-bottom:20px}
@media(max-width:700px){.fsec{padding:18px 16px}}
.fsec h2{display:flex;align-items:center;gap:10px}.fsec h2 .num{width:26px;height:26px;border-radius:50%;background:var(--navy);color:#fff;font-size:13px;display:inline-flex;align-items:center;justify-content:center}
.field{display:flex;flex-direction:column;gap:6px;margin:14px 0 0}.field>span{font-size:13px;font-weight:600;color:var(--ink2)}.field small{color:var(--mute);font-size:12px}
.field input[type=text],.field input[type=number],.field select,.field textarea{width:100%;padding:10px 12px;border:1px solid #cbd5e1;border-radius:10px;font:inherit;font-size:14.5px;background:#fff;transition:.15s}
.field textarea{min-height:120px;resize:vertical;line-height:1.5}
.field input:focus,.field select:focus,.field textarea:focus{outline:none;border-color:var(--acc2);box-shadow:0 0 0 3px rgba(20,184,166,.18)}
.row2{display:grid;grid-template-columns:1fr 1fr;gap:14px}.row3{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
@media(max-width:700px){.row2,.row3{grid-template-columns:1fr}}
.choice{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin-top:8px}@media(max-width:700px){.choice{grid-template-columns:1fr}}
.choice label{border:1px solid #cbd5e1;border-radius:11px;padding:11px 13px;cursor:pointer;font-size:14px;display:flex;gap:9px;align-items:flex-start;background:#fff}
.choice label:has(input:checked){border-color:var(--acc);background:var(--accbg);box-shadow:0 0 0 1px var(--acc) inset}
.choice input{accent-color:var(--acc);margin-top:3px}
.cchips{display:flex;flex-wrap:wrap;gap:8px;margin-top:8px}.cchips label{border:1px solid #cbd5e1;border-radius:20px;padding:6px 13px;font-size:13.5px;cursor:pointer;background:#fff;user-select:none}
.cchips label:has(input:checked){background:var(--navy);border-color:var(--navy);color:#fff}.cchips input{display:none}
.prov{display:inline-block;font-size:11px;font-weight:600;color:var(--blue);background:#eff6ff;border-radius:6px;padding:1px 7px;margin-left:6px}
.aside{position:sticky;top:84px;align-self:start}.aside .card{padding:20px}
.indsearch{position:relative}.indlist{max-height:230px;overflow:auto;border:1px solid var(--line);border-radius:10px;margin-top:6px;background:#fff}
.indlist div{padding:8px 12px;font-size:14px;cursor:pointer;display:flex;justify-content:space-between;gap:10px}.indlist div:hover,.indlist div.sel{background:var(--accbg)}
.indlist div small{color:var(--mute)}
/* project */
.phead{background:#fff;border-bottom:1px solid var(--line)}.phead .in{max-width:1200px;margin:0 auto;padding:22px 20px 0}
.phead h1{font-size:24px;margin:4px 0 6px}.phead .meta{display:flex;flex-wrap:wrap;gap:8px;align-items:center;font-size:13px;color:var(--mute)}
.tabs{display:flex;gap:4px;margin-top:16px;overflow-x:auto;scrollbar-width:none}.tabs a{white-space:nowrap;padding:11px 14px;font-size:14px;color:var(--ink2);border-bottom:2px solid transparent;font-weight:500}
.tabs a:hover{text-decoration:none;color:var(--ink)}.tabs a.on{color:var(--acc);border-bottom-color:var(--acc);font-weight:600}
.tabs a .n{display:inline-flex;width:20px;height:20px;border-radius:50%;background:#eef2f7;color:var(--ink2);font-size:11px;align-items:center;justify-content:center;margin-right:6px}
.tabs a.on .n{background:var(--acc);color:#fff}
.kpis.k5{grid-template-columns:repeat(5,1fr)}@media(max-width:900px){.kpis.k5{grid-template-columns:1fr 1fr}}
.kpi .v.sm{font-size:22px}
.score{display:inline-flex;align-items:center;justify-content:center;min-width:44px;height:28px;border-radius:8px;font-weight:700;font-variant-numeric:tabular-nums;padding:0 8px}
.score.hi{background:var(--greenbg);color:var(--green)}.score.md{background:var(--amberbg);color:var(--amber)}.score.lo{background:#f1f5f9;color:var(--mute)}
.mbar{height:7px;border-radius:4px;background:#eef2f7;overflow:hidden;min-width:60px}.mbar div{height:100%;background:var(--acc2);border-radius:4px}
.tier{font-size:12px;font-weight:700;border-radius:6px;padding:2px 8px}.tier.Priority{background:var(--greenbg);color:var(--green)}.tier.Include{background:#dbeafe;color:#1d4ed8}.tier.Backup{background:#f1f5f9;color:var(--mute)}
.wform{display:grid;grid-template-columns:repeat(5,1fr);gap:10px}@media(max-width:800px){.wform{grid-template-columns:1fr 1fr}}
.wform label{font-size:12.5px;color:var(--ink2)}.wform input,.wform select{width:100%;display:block;margin-top:4px}
.qp{border:1px solid var(--line);border-radius:12px;padding:16px;margin-bottom:12px}.qp h3{margin:0 0 2px;display:flex;align-items:center;gap:8px}
.qp ol{margin:10px 0 0;padding-left:20px}.qp li{margin:7px 0;font-size:14px}.qp .opts{color:var(--mute);font-size:12.5px}
.rule{font-size:11px;color:var(--mute);background:#f1f5f9;border-radius:5px;padding:1px 6px;margin-left:4px;white-space:nowrap}.rule.ai{color:var(--blue);background:#eff6ff}
.status{font-size:12px;font-weight:600;border-radius:12px;padding:2px 9px;white-space:nowrap}.status.draft{background:#f1f5f9;color:var(--mute)}.status.sent{background:#dbeafe;color:#1d4ed8}.status.completed{background:var(--greenbg);color:var(--green)}
.callout{border-radius:12px;padding:14px 16px;font-size:13.5px;margin:12px 0}.callout.warn{background:var(--amberbg);color:#78350f}.callout.info{background:#eff6ff;color:#1e3a8a}.callout.ok{background:var(--greenbg);color:#14532d}
.gantt .g{display:grid;grid-template-columns:110px 1fr;gap:10px;align-items:center;font-size:13px;margin:7px 0}
.gantt .t{position:relative;height:18px;background:#f8fafc;border-radius:5px}.gantt .t span{position:absolute;top:0;height:18px;border-radius:5px}
.gantt .su{background:repeating-linear-gradient(45deg,#fde68a,#fde68a 4px,#fef3c7 4px,#fef3c7 8px)}.gantt .en{background:var(--acc2)}
.lik{font-size:12px;font-weight:700;border-radius:6px;padding:1px 7px}.lik.High{background:var(--redbg);color:var(--red)}.lik.Medium{background:var(--amberbg);color:var(--amber)}.lik.Low{background:#f1f5f9;color:var(--mute)}
.rel{font-size:11px;font-weight:700;border-radius:5px;padding:1px 6px}.rel.Direct{background:var(--redbg);color:var(--red)}.rel.Partial{background:var(--amberbg);color:var(--amber)}.rel.Low{background:#f1f5f9;color:var(--mute)}
.doc{max-width:860px;margin:0 auto;background:#fff;border-radius:var(--r);box-shadow:var(--shadow);padding:48px 56px}
@media(max-width:700px){.doc{padding:24px 18px}}
.doc h1{font-size:28px}.doc h2{font-size:18px;margin:28px 0 8px;padding-top:14px;border-top:1px solid var(--line)}
.doc .cover{border-bottom:3px solid var(--acc);padding-bottom:18px;margin-bottom:10px}
.survey{max-width:760px;margin:0 auto}.survey .q{background:#fff;border-radius:12px;border:1px solid var(--line);padding:16px 18px;margin:10px 0}
.survey .q p{margin:0 0 10px;font-weight:600;font-size:14.5px}.survey .q label{display:inline-flex;align-items:center;gap:6px;margin:4px 14px 4px 0;font-size:14px}
.survey .q input[type=number],.survey .q textarea{padding:9px 11px;border:1px solid #cbd5e1;border-radius:9px;font:inherit;width:100%;max-width:240px}.survey .q textarea{max-width:100%;min-height:70px}
.dist{display:grid;grid-template-columns:minmax(0,1fr) 120px 34px;gap:8px;align-items:center;font-size:12.5px;margin:4px 0}
.dist .t{height:8px;background:#eef2f7;border-radius:4px;overflow:hidden}.dist .t div{height:100%;background:var(--acc2);border-radius:4px}
.legendrow{display:flex;gap:16px;flex-wrap:wrap;font-size:12.5px;color:var(--ink2);margin:6px 0 4px}.legendrow i{display:inline-block;width:14px;height:3px;border-radius:2px;vertical-align:middle;margin-right:6px}
@media print{.phead .tabs,.noprint,.top{display:none!important}.doc{box-shadow:none;padding:0}}
"""


def _logo_svg(size=30):
    import math
    dots = []
    for i, ang in enumerate((60, 100, 140, 180, 220, 260, 300)):
        a = math.radians(ang)
        x, y = 16 + 9 * math.cos(a), 16 - 9 * math.sin(a)
        r = 2.0 if i in (0, 6) else 2.4
        dots.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{r}" fill="#fff" opacity="{0.55 + 0.45 * (1 - abs(i - 3) / 3):.2f}"/>')
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 32 32" aria-hidden="true"><defs><linearGradient id="cg" x1="0" y1="0" x2="1" y2="1">'
            '<stop offset="0" stop-color="#0b1f3a"/><stop offset="1" stop-color="#0f766e"/></linearGradient></defs>'
            '<rect width="32" height="32" rx="9" fill="url(#cg)"/>' + "".join(dots) +
            '<circle cx="21.5" cy="16" r="3.1" fill="#5eead4"/></svg>')


LOGO = _logo_svg()
WORDMARK = f'{LOGO}<span class="wm">Cohort<em>ia</em></span>'
FAVICON = "data:image/svg+xml," + urllib.parse.quote(_logo_svg(32))


def page(title, body, nav="", active=""):
    links = [("/", "Requests", "home"), ("/trial", "Trial lookup", "trial")]
    nl = "".join(f'<a class="l hide-s{" on" if k == active else ""}" href="{h}">{t}</a>' for h, t, k in links)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title><link rel="icon" href="{FAVICON}">
<link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>{CSS}{EXTRA_CSS}</style></head><body>
<div class="top"><a class="logo" href="/">{WORDMARK}</a><span class="tag2">Demo · public data</span><span class="sp"></span>{nav}{nl}<a class="l cta" href="/new">New request</a></div>
{body}</body></html>"""


def fmt(x, d=0):
    return "n/a" if x is None else f"{x:,.{d}f}"


def pct(x):
    return "n/a" if x is None else f"{x*100:.1f}%" if x < 0.1 else f"{x*100:.0f}%"


def tag(t):
    return f'<span class="tag {t}" title="{ {"F":"verified fact","S":"published figure","E":"estimate","J":"judgment"}[t] }">{t}</span>'


def link_nct(n):
    return f'<a href="https://clinicaltrials.gov/study/{n}" target="_blank" rel="noopener">{n}</a>'


LEGEND = ('<div class="legend"><span>' + tag("F") + ' verified fact</span><span>' + tag("S") + ' published figure</span><span>' +
          tag("E") + ' estimate</span><span>' + tag("J") + ' judgment (editable)</span></div>')
