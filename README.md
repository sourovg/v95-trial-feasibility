# Cohortia (V95): study feasibility from request to proposal

Working name **Cohortia** (not trademark-checked). A feasibility workflow for pharma and CRO teams:
describe a study (RFP-style form or free text), and the app runs the four feasibility pillars
(benchmark analysis, country evaluation, investigator insights with an auto-designed survey, scenario and risk)
and drafts a proposal. Public, aggregate data only. Independent tool; separate from Symelix; not medical or regulatory advice.

## Run it (Mac, nothing to install)
```
python3 app.py serve                    # http://localhost:8095
python3 -m unittest discover -s tests   # 14 tests (offline)
V95_OFFLINE=1 python3 app.py serve      # bundled snapshot only (worked example + 3 demo trials)
python3 app.py snapshot-all             # refresh the bundled snapshot
python3 app.py pack NCT07185997         # trial lookup numbers in the terminal
python3 scripts/backtest.py             # enrolment back-test (needs internet)
```
Python 3.10+ standard library only. Optional AI: `pip install anthropic` and set `ANTHROPIC_API_KEY`; Claude then
helps read the request, adds up to 4 tailored survey questions and drafts the summary. Without it, rules do everything
(set `COHORTIA_AI=0` to force rules). Projects, invitations and survey answers are kept in `data/cohortia.db` (git-ignored).

## How to use it
1. Open http://localhost:8095 and click **Open the worked example** (Latin America malnutrition study), or **Start a feasibility request**.
2. Paste the request text and press **Auto-fill from description**; check the fields (area, searchable indication, study type, design, countries, targets) and **Create feasibility project**.
3. Work through the tabs: **Benchmark**, **Countries** (change weights and assumptions), **Investigators** (pick sites, add them to the survey list, send (simulated), open a survey link to answer as an investigator, or fill demo responses), **Scenario & risk** (sample size, sites, pace), **Proposal** (Save as PDF).
4. **Trial lookup** (top bar) keeps the original NCT-number pack.

Sending is simulated: nothing is emailed. See [docs/round2-notes.md](docs/round2-notes.md) for data sources, what is automated, and the legal points for real sending.

## Data sources
| Source | Use | How |
|---|---|---|
| ClinicalTrials.gov API v2 | Similar interventional and observational studies by country, sites, public study officials, enrolment pace | live, cached 7 days |
| ISRCTN API | International registry incl. observational studies | live |
| PubMed E-utilities | Published papers on the topic, per country (affiliation) | live |
| GLOBOCAN 2024 (IARC/WHO) | New cancer cases by site, 24 countries | bundled (`data_snapshot/globocan2024.json`) |
| Curated literature | ELAN, IBRANUTRI, Santos 2022 (GLIM), nutritionDay LatAm; checked against PubMed abstracts | bundled |
| Linked only | WHO ICTRP (ReBEC, REPEC, 15+ registries), EU CTIS, HMA-EMA RWD catalogues, ISPOR/ISPE RWE registry | links |

---

# Trial lookup (round 1)
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

## Accuracy check
`python3 scripts/backtest.py` back-tests the enrolment pace on finished trials in 3 indications (no look-ahead). Result 2026-11-26: within ±30% for 20–48% of trials, within 2x for 53–81%; leans optimistic in oncology and atopic dermatitis. Details: [docs/accuracy-check.md](docs/accuracy-check.md).

## Expert review
A clinical-development or epidemiology expert checks each pack before it is trusted. Sheet: [docs/expert-review-sheet.md](docs/expert-review-sheet.md).

## Known limits
- Only one curated epidemiology profile; other NCT IDs get a generic funnel you fill in.
- Competition tiering is keyword-based and over-inclusive (e.g. broad EGFR trials whose inclusion lists uncommon mutations show as Direct).
- PACC share (~13.5% of EGFR-mutant) is derived from a treated subset in Robichaux 2021, not a population sample.
- Enrolment window assumption (60% of start->primary completion) is judgment; per-site enrolment is not public.
- Not built: AI protocol reader, more indications, licensed claims/EHR check (kill test: within ±30%), race/ethnicity mix, facility-name cleaning, investigators, expert review, export.
