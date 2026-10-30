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

WDC-SILSO data are credited to the Royal Observatory of Belgium, Brussels,
DOI `10.24414/qnza-ac80`, and distributed under CC BY-NC 4.0. The source bytes,
license, retrieval time, and digest are recorded in the run manifest.
