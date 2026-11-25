# Field Theory / Feltteori

This directory is an independent, exploratory research project. It is housed in
the Jarvis repository for now, but it does not import, modify, or define the
Jarvis runtime. Jarvis may later become one observation source among others.

The project begins from Bjørn's developing Feltteori: a set of philosophical
propositions about information, perspective, relations, continuity,
experience, expectation, and time. Those propositions are research prompts,
not established facts and not a destination built into the software.

## Start here

- [`research/conceptual-foundation.md`](research/conceptual-foundation.md) gives
  a neutral account of the propositions, ambiguities, observable consequences,
  alternatives, and currently untestable questions.
- [`research/initial-directions.md`](research/initial-directions.md) compares
  plausible first investigations and explains why experiment 001 was chosen.
- [`research/observation-model.md`](research/observation-model.md) defines the
  minimal provenance boundary without prescribing a database schema.
- [`research/notebook.md`](research/notebook.md) is the living research record.
- [`research/investigation-002-findings.md`](research/investigation-002-findings.md)
  separates the second investigation's measurements from its interpretations.
- [`research/live-investigations-001-002-findings.md`](research/live-investigations-001-002-findings.md)
  reports the first deployed, database-backed measurements and supersedes the
  simulations as evidence about Jarvis.
- [`research/investigation-003-findings.md`](research/investigation-003-findings.md)
  examines how the live model×weekday relationship changes across the preserved
  history, measurement perspectives, and adjacent-period transport.
- [`research/investigation-004-findings.md`](research/investigation-004-findings.md)
  separates state recurrence, transition continuity, chronology, and frozen
  prospective expectation.
- [`research/investigation-005-findings.md`](research/investigation-005-findings.md)
  distinguishes recorded error, consequence, adaptive response, and retention
  on an independent WDC-SILSO observational series.
- [`research/investigation-006-findings.md`](research/investigation-006-findings.md)
  tests whether Investigation 5's retention→adaptation relation transfers to a
  physically unrelated series (NOAA Mauna Loa CO₂) under the identical
  mechanism. It does not: the transfer is falsified, and the earlier lock-in
  result is narrowed to a joint configuration of rule, expert set and source.
- [`research/investigation-007-findings.md`](research/investigation-007-findings.md)
  asks whether the collapse to one expert is governed by the expert loss gap
  rather than by the source. It is inconclusive: the blend instrument's own
  independent variable is not monotone, so the experiment cannot reach its
  question, and it reports that instead of a falsification.
- [`research/investigation-008-findings.md`](research/investigation-008-findings.md)
  makes the gap an input by inverting the loss function, and asks Investigation
  6's open question directly. With a systematic advantage the two unrelated
  series collapse identically (median difference 0.0000, threshold near `1 − r`);
  with a rotating advantage they do not. The missing variable is the gap's
  **stability**, not its size — which is what CO₂'s trend actually changes.
- [`research/investigation-009-findings.md`](research/investigation-009-findings.md)
  asks whether Investigation 8's threshold survives a different expert set. It
  does — so completely that the experts never reach it. On a fine grid, four
  different sets of three or more experts give the *same* threshold on both
  sources, because in `fixed` assignment the threshold is analytic
  (`gap ≈ (x_threshold / learning_rate) · (1 − r)`) and the data never enters
  it. Investigation 8's agreement between sources in that mode was therefore a
  mathematical necessity, not an empirical finding. Only `roving` puts the data
  back, and there the threshold varies by a factor of eight. The two-expert set
  cannot be measured at all: its floor equals the minimum attainable effective
  count.
- [`research/investigation-010-findings.md`](research/investigation-010-findings.md) tests whether the roving collapse threshold is governed by the spread of the mean rank positions. It is not: the invariant holds to within the grid factor in `fixed` and fails by up to seven times in `roving`, because the threshold statistic asks about occupancy while being computed from a mean. Separating the two — duty cycle in `[0,1]`, mean-over-min in `[1,∞)` — shows the first report had used one name for both, and that occupancy separates the modes categorically while fluctuation does not.
- [`research/investigation-011-findings.md`](research/investigation-011-findings.md) replaces that statistic with four measures — occupancy, persistence, recovery, identity stability — and finds that three of them are algebraically dependent. `O·T = K·P` and `(1−O)·T = K'·R` force `P/(P+R) = O·K'/(O·K'+(1−O)·K)`, so occupancy, persistence and recovery span two degrees of freedom and not three; measured residual 1.1e-16. The fourth does carry an independent axis, but only when measured as dominance share: two cells from the same source, expert set and assignment, with occupancy 0.396 and 0.393, hold dominance shares of 0.453 and 0.921. The frozen definition, a switch count divided by the window length, read them as 0.738 and 0.937 — the opposite ordering. **Amendment 2 corrects a sign error that inverted the first report:** the protocol defined the dominant expert as `argmax` of accumulated loss, but the weight is `exp(−LR·(S−min S))`, so the governing expert is the `argmin`. Measured over 3198 months, `argmax` matched in 1 and `argmin` in 3198; 42 of 132 cells changed dominance share, and the original headline pair reversed. **Two further corrections.** Condition 3's pre-registered effect size (0.30) was not observed — the best pair reached 0.199 — which is recorded as a criterion not met inside the design, not as a demonstrated dependence; the verdict string was renamed to report that instead of interpreting it. And the headline pair moves `gap` and `retention` together, so it isolates neither: holding `gap` fixed at 0.05 and raising retention 0.9 → 0.99 leaves occupancy at 0.000 in both cells while dominance share goes 0.453 → 0.921, so retention shapes the dominance structure without moving occupancy. **A third blind spot, found last.** All four measures read *who* holds the top rank and none of them reads *how much* power it carries: two systems with constant weights 34/33/33 and 60/20/20 return identical values on every one of them. The per-month weights were computed and discarded. Carried alongside as `mean_top_weight` and `mean_top_margin`, the grid shows the gap is not a corner case — 896 pairs share occupancy, dominance share and identity stability to within 0.02 while differing in top weight by more than 0.05, and one cell holds the same expert at rank one for the entire window while that expert carries 38.5 % of the weight with 3.53 effective experts. **The two measures answer a question neither could alone.** On the 66 pairs that differ in retention alone, median change in dominance share is 0.000 against 0.220 in top weight, correlation 0.042, and no pair moves the rank order while the distribution stands still. But the asymmetry reverses with collapse: on the four pairs where occupancy is 0.000 in both cells, the rank order moves by +0.32 to +0.47 while the top weight moves by only +0.08 to +0.22. Retention sets the rank order while it is still contested, and sets the weight that rank carries once it is not. **The run count is not a third axis; the run shape is.** `persistence` is defined as `below/K`, so `K = O·T/P` is a rearrangement, not a regularity — 0 deviations on all 101 cells where persistence exists — and because runs alternate, `K − K'` is −1, 0 or +1 and never more, which is exactly the window-endpoint term. Adding `log K` to a regression on `O` and `P` raises R² from 0.4916 to 0.5095. What the identity leaves free is how the collapse time is partitioned: two constructed sequences with identical occupancy, persistence, recovery, `K` and `K'` differ in longest collapse by 10 against 37, and 27 of 101 real cells have `longest/persistence > 1.01` up to 8.49. The shape is a real degree of freedom but a weak one — R² reaches 0.5114 with it included.
- [`research/investigation-012-findings.md`](research/investigation-012-findings.md) asks how retention reaches the forecast when no structural measure predicts it, and finds that it barely does and that the forecast is not mostly structure. The path is closed by arithmetic: the ensemble error is `|Σ_e w_e·a_e|` with `a_e = real_e − outcome`, measured identity residual 0.0, and since the rank order does not depend on retention and `a` is data, `w` is the only channel. Where the error comes from, over 120 observations: the source explains η² = 0.798 of the total error variation, the expert set 0.114, and **retention 0.002**; as a continuous covariate the best single expert's error explains **93.4 %** and the top weight **2.6 %**. Within every expert set separately the oracle explains 86–99.8 % and the structure 0.1–13 %. The one path retention does take is concentration: `corr(Δ top weight, Δ error) = −0.414`, R² 0.171, surviving removal of the most reactive set (−0.382, R² 0.146), because a concentrated weight is closer to choosing the best expert than to averaging disagreeing ones — median `error/oracle` falls from 1.432 to 1.367 and concentration tracks that ratio at R² 0.214. But the effect has no reliable sign: median change **−0.005**, mean −0.690, and the error falls in **34 of 60** pairs. The corollary is the useful part: to predict whether a weighted ensemble forecasts well, measure the disagreement among its members and the error of its best member, not the shape of its weights. **Two faults in this investigation's own controls are recorded rather than smoothed over** — a monotonicity control that demanded exactly zero where a share was correct, and a verdict condition written as a fault among success conditions, which made `all()` unreachable and reported "a control failed" while all five were met.
- [`experiments/exp_001_perspective/PROTOCOL.md`](experiments/exp_001_perspective/PROTOCOL.md)
  documents the first method before its results.
- [`experiments/exp_002_discovery/PROTOCOL.md`](experiments/exp_002_discovery/PROTOCOL.md)
  records the discovery and confirmation boundary for Investigation 2.

## Minimal structure

```text
field_theory/
├── research/       conceptual documents and a chronological notebook
├── experiments/    protocols and small experiment entry points
├── src/            reusable, deliberately small research mechanics
├── tests/          integrity and reproducibility checks
└── artifacts/      versioned raw observations and derived run outputs
```

The distinction is more important than the directories: raw observations are
never rewritten by analysis; derived results identify their method and raw-data
digest; and notebook interpretation remains separate from measured output.

## Run synthetic method experiment 001

From this directory, using Python 3.11 or newer:

```bash
python experiments/exp_001_perspective/run.py \
  --output artifacts/exp_001/seed_20261030
```

The command refuses to overwrite an existing run. Parameters are adjustable
and are recorded in `manifest.json`; changing them creates a new run rather
than revising old evidence.

Run the focused tests from the repository root:

```bash
/opt/conda/envs/ai/bin/python -m pytest field_theory/tests
```

No database, service, network access, or Jarvis state is required. The first
implementation uses only the Python standard library.

## Run synthetic method Investigation 2

The three commands preserve generation, opaque analysis, and source reveal as
separate events:

```bash
python experiments/exp_002_discovery/generate.py \
  --output artifacts/exp_002/seed_202610302
python experiments/exp_002_discovery/analyze.py \
  --run artifacts/exp_002/seed_202610302
python experiments/exp_002_discovery/reveal.py \
  --run artifacts/exp_002/seed_202610302
```

The analyzer verifies the raw-data digest and never reads `source_key.json`.
Analysis and reveal refuse to replace prior outputs.

The two commands above preserve the original synthetic method-validation
history. Their measurements are not observations of Jarvis. Deployed
measurements use the protocols in `experiments/exp_001_live/` and
`experiments/exp_002_live/` and must be extracted on hostname `Jarvis` from the
live database in read-only mode.

## Run deployed measurements

These commands are intentionally host-gated and must run from the deployed
repository on CT105:

```bash
python field_theory/experiments/live_visible_runs/extract.py --output /tmp/<new-run>
python field_theory/experiments/exp_001_live/analyze.py --run /tmp/<new-run>
python field_theory/experiments/exp_002_live/analyze.py --run /tmp/<new-run>
```

The valid 2026-10-30 run is preserved under
`artifacts/live_visible_runs/ct105_20261030_96c1f6a49/`. Its manifest identifies
hostname `Jarvis`, deployed revision `96c1f6a49`, SQLite read-only mode, table
high-water ID 46095, and the observation digest.

Investigation 3 reuses that immutable snapshot and must also execute from the
deployed CT105 repository:

```bash
python field_theory/experiments/exp_003_change/collect_context.py \
  --run field_theory/artifacts/live_visible_runs/ct105_20261030_96c1f6a49 \
  --output /tmp/<exp003-run>
python field_theory/experiments/exp_003_change/analyze.py \
  --run field_theory/artifacts/live_visible_runs/ct105_20261030_96c1f6a49 \
  --output /tmp/<exp003-run>
```

The preserved deployed result is
`artifacts/exp_003_live/ct105_20261030_07906ebdd/`. Its post-hoc cell and
day×model audits are explicitly marked as following primary-result inspection.

Investigation 4's retrospective runner and prospective boundary are separate:

```bash
python field_theory/experiments/exp_004_continuity/analyze.py \
  --run field_theory/artifacts/live_visible_runs/ct105_20261030_96c1f6a49 \
  --output /tmp/<exp004-run>
python field_theory/experiments/exp_004_continuity/prepare_forecast.py \
  --run field_theory/artifacts/live_visible_runs/ct105_20261030_96c1f6a49 \
  --analysis /tmp/<exp004-run> \
  --output /tmp/<forecast.json>
```

The forecast must be committed and deployed before
`evaluate_prospective.py` queries availability above the frozen high-water ID.
The preserved run is `artifacts/exp_004_live/ct105_20261030_32092ec71/`.

## Run independent-source Investigation 5

Investigation 5 does not query Jarvis or CT105. Its protocol was committed
before the WDC-SILSO source file was downloaded or inspected. A new run fetches
and preserves the exact source response, excludes provisional values, and
compares fixed and adaptive expectation mechanisms:

```bash
python field_theory/experiments/exp_005_learning/run.py \
  --output /tmp/<exp005-run>
```

The preserved run is
`artifacts/exp_005_independent/silso_20261030_e9a732ca9/`. The declared post-hoc
audit can be reproduced once for a new primary run with:

```bash
python field_theory/experiments/exp_005_learning/audit.py \
  --run /tmp/<exp005-run>
```

## Run transfer Investigation 6

Investigation 6 applies the Investigation 5 mechanism unchanged to NOAA Mauna
Loa CO₂. The run refuses to overwrite an existing directory. Fetch the source
anew, or replay offline from a preserved copy of the exact bytes:

```bash
python field_theory/experiments/exp_006_order/run.py \
  --output /tmp/<exp006-run>
python field_theory/experiments/exp_006_order/run.py \
  --output /tmp/<exp006-run> \
  --source field_theory/artifacts/exp_006_order/noaa_20261030_v2/noaa_co2_mm_mlo.csv
```

Preserved runs are `artifacts/exp_006_order/noaa_20261030/` (superseded: its
reset branch was faulty) and `noaa_20261030_v2/`. A fresh fetch may differ,
since NOAA revises its record.

WDC-SILSO data are credited to the Royal Observatory of Belgium, Brussels,
DOI `10.24414/qnza-ac80`, and distributed under CC BY-NC 4.0. The source bytes,
license, retrieval time, and digest are recorded in the run manifest.
