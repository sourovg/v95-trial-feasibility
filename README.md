# V95 trial feasibility: half-day demo

Working name **FeasiblePack** (placeholder). Builds a feasibility pack for one public clinical trial from
public, aggregate data only. Independent tool; not affiliated with any sponsor; not medical or regulatory advice.
Separate from Symelix: no shared code, accounts or database. No patient-level data.

## Run it (Mac, nothing to install)
```
python3 app.py serve                 # http://localhost:8095 (pack for NCT07185997 opens from the home page)
python3 app.py pack NCT07185997      # key numbers in the terminal
python3 -m unittest discover -s tests   # 8 tests
V95_OFFLINE=1 python3 app.py serve   # use only the bundled snapshot (no internet)
python3 app.py snapshot NCT07185997  # refresh the bundled ClinicalTrials.gov snapshot
```
Python 3.10+ standard library only. Live calls go to the public ClinicalTrials.gov API v2 and are cached
in `data/cache/` for 7 days (git-ignored). `data_snapshot/` holds a copy fetched 2026-11-26 so the demo works offline.

## Demo trial
**NCT07185997, ALPACCA** (ArriVent BioPharma, a small/mid sponsor): phase 3, firmonertinib vs osimertinib/afatinib,
first-line, EGFR PACC-mutant advanced NSCLC, target 480, 141 sites in 17 countries.

## What the pack shows
| Section | Data | Labels |
|---|---|---|
| Key criteria | Rule-parsed from the public record | F |
| Patient population | Incident-case funnel for US, China, Japan; every step has base/low/high, source link and label; editable | F/S/E/J per step |
| US by state | National pool split by 2025 Census state population (crude) | E |
| Competing trials | Active interventional trials, tiered Direct/Partial/Low by title, conditions, keywords and *inclusion* criteria; shared sites with the target | F list, J tier |
| Candidate sites | Facilities on similar trials since 2016, with industry/completed/terminated counts and current competing load | F counts, J ranking |
| Enrolment | Patients/site/month from finished same-or-analogous rare-subtype trials (exon 20 used as analog), ramp-up curves vs the sponsor's posted window; editable | E |

## Results for the demo trial (2026-11-26) [E unless marked]
- US: ~970 newly eligible patients/year (range 290–2,400); ~80/year enrol in *any* trial; 11 direct competitors active in the US.
- China pool ~8x the US (EGFR mutations 2–3x more common), which fits the sponsor's 48 China sites.
- 27 direct competing trials active (13 industry) [F count, J tier]; 189 partial.
- Benchmarks (5 finished rare-subtype trials, incl. ArriVent's own exon 20 phase 3): ~0.08 patients/site/month -> ~47 months to 480 with 141 sites, against 38 months posted from start to primary completion (which also covers follow-up). Plan looks tight [J].

## Known limits
- Only one curated epidemiology profile; other NCT IDs get a generic funnel you fill in.
- Competition tiering is keyword-based and over-inclusive (e.g. broad EGFR trials whose inclusion lists uncommon mutations show as Direct).
- PACC share (~13.5% of EGFR-mutant) is derived from a treated subset in Robichaux 2021, not a population sample.
- Enrolment window assumption (60% of start->primary completion) is judgment; per-site enrolment is not public.
- Not built: AI protocol reader, more indications, licensed claims/EHR check (kill test: within ±30%), race/ethnicity mix, facility-name cleaning, investigators, expert review, export.
