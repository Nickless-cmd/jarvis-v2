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

## Run experiment 001

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

## Run Investigation 2

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
