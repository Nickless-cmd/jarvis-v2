# CONTRIBUTING

How to work in this codebase. Setup: [`INSTALL.md`](INSTALL.md). Security rules: [`SECURITY.md`](SECURITY.md).

## Dev setup
```bash
conda activate ai
pip install -e . && pip install -r requirements.txt
pre-commit install
```

## Running tests
```bash
conda run -n ai python -m pytest -q                       # quick
# full suite (the gate CI runs, ~20 min):
conda run -n ai python -m pytest -q -p no:cacheprovider --timeout=45 --timeout-method=signal
```
A handful of tests are order-sensitive isolation flakes (they pass when run alone) — re-run a failure in isolation before assuming a regression.

## Pre-commit gates (all five must pass)
1. **detect-secrets** — blocks new hardcoded secrets. False positive → `detect-secrets scan --baseline .secrets.baseline` (see [`SECURITY.md`](SECURITY.md)).
2. **Enforce test coverage** — every new `core/…` file needs a matching `tests/test_<stem>.py` (exact stem). Write the test first.
3. **Block kitchen-sink commits** — keep commits focused.
4. **Block jvs-\* API keys** — no Jarvis-issued keys in the tree.
5. **Docs drift** — blocks a commit whose staged source changes leave a generated doc un-regenerated, or whose docs contain a broken markdown link. Fix by running the relevant generator (see below) or repairing the link. Advisory (non-blocking) drift lands in [`drift_report.json`](drift_report.json) and the `jc docs-drift` nerve. (Historical trees — `superpowers/`, `design-history/`, `_archive/` — are exempt per the freshness policy.)

## Code rules (from `CLAUDE.md`)
- No file over **1500 lines** without explicit exception; split at 1200. No core runtime file over **2000** lines.
- One primary responsibility per file. No hidden side effects.
- **No dual truth** between config and DB. Risky actions require an explicit policy/approval path.
- Sources of truth: `config` = runtime/governance settings · `DB` = operational state/events/runs/costs · `workspace files` = identity/memory/skills text · `Central` = the control plane over truth.

## The Boy-Scout rule
When you touch a file **over 2000 lines** (adding >20 lines or changing logic), first extract the nearest natural cohesive unit (a class, a daemon, a state machine) into a new file — **re-export the moved symbols** so imports don't break — *before* making your actual change. No exceptions. File sizes fall over time without a dedicated refactor.

## TDD workflow
Write the failing test → run it (confirm it fails) → minimal implementation → run it (confirm it passes) → commit. Small, frequent commits.

## Commits & PRs
- Branch off `main`; commit/push only when the work is ready and requested.
- End commit messages with the trailer:
  ```
  Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
  ```
- Use `git pull --ff-only`; if the target host has diverged, **merge, never overwrite/rebase**.
- Design docs live in `docs/superpowers/specs/`, plans in `docs/superpowers/plans/` (spec → plan → build).

## Regenerating derived docs
The reference docs are generated — never hand-edit them; regenerate:
```bash
python scripts/api_docs_gen.py         # reference/api/ + reference/DOCSTRING_COVERAGE.md
python scripts/api_reference_gen.py    # reference/API_REFERENCE.md
python scripts/capabilities_gen.py     # reference/CAPABILITIES.md
python scripts/capability_audit.py     # capability_matrix.md
python scripts/docs_audit.py           # doc classification (DOCS_MANIFEST source)
python scripts/requirements_gen.py     # candidate imports for requirements.txt
python scripts/docs_drift_check.py     # docs/drift_report.json (drift audit; --check gates commits)
```

## Code ↔ docs convention
The per-package reference under [`reference/api/`](reference/api/README.md) is derived from the source, so the mapping is by rule, not by hand:
- A module `<pkg>/<mod>.py` is documented on the page for its package — `docs/reference/api/<dotted pkg>.md` (large flat directories like `core/services` are split into numbered chunk pages `<dotted pkg>.NN.md`; the index shows each chunk's module range). Its section is `## \`<pkg>/<mod>.py\``, and every entry links back to the source at `file#Lline`.
- **To document a function, add/improve its docstring in the source and regenerate** — do not hand-edit the reference pages. Undocumented public functions are tracked in [`reference/DOCSTRING_COVERAGE.md`](reference/DOCSTRING_COVERAGE.md).
