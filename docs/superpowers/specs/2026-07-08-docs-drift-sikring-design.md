# Docs Programme SP5 — Drift-sikring (docs-drift watchdog)

**Date:** 2026-07-08
**Status:** Approved (design)
**Programme:** Prod-ready docs/. SP1 (audit) + SP2 (structure+generators) + SP3 (install) + SP4 (codebase reference) LANDED. This is SP5 — the final sub-project.

## Goal

A watchdog that catches when `docs/` diverges from git+runtime truth, so the docs cannot rot again. Bjørn's hard truth: **git + runtime are the only real sources of truth** — docs are only trustworthy if something continuously proves they still match. SP5 makes that proof automatic and gives it two sides: a **repo-side hybrid gate** (blocks the drift that actually rots docs) and a **Central nerve** (surfaces drift status live in `jc`/Central as part of Jarvis' self-observation).

## Decisions (from brainstorm)

- **Enforcement = hybrid.** The pre-commit gate BLOCKS on the cheap, deterministic, high-value drift (dangling refs; generated docs not regenerated after their source changed). Fuzzy prose-vs-code checks are **advisory only** — too noisy to gate, so people never learn to `--no-verify`.
- **Also a Central nerve.** A `docs:drift` signal so the Central (and `jc`) shows drift status live. Fits the "Central absorbs everything" strategy.
- **Requirements drift = soft/advisory** (a missing optional dep must not block a commit).
- **Staleness gate is change-scoped** — the pre-commit hook only regenerates a generator when the commit stages files under that generator's source tree, keeping the hook fast. A full regenerate-and-diff runs in the default/CI mode.
- **The nerve reads the committed report, never re-runs AST in the hot path.**

## Ground truth (verified 2026-07-08)

- Building blocks exist: `scripts/api_docs_gen.py`, `api_reference_gen.py`, `capabilities_gen.py`, `docs_audit.py`, `requirements_gen.py`, `capability_audit.py`.
- `scripts/docs_audit.py` already extracts path refs (`_PATH_RE`) and symbol refs (`_SYMBOL_RE`) from docs and checks path liveness — SP5 reuses these patterns.
- Central nerve pattern (verified against `core/services/central_llm_egress.py`, `central_timeseries.py`, `internal_cadence.py`):
  - `central_timeseries.record(cluster, nerve, value=..., meta={...})` — self-safe, bounded deque, persists ~180s. (`core/services/central_timeseries.py:77`)
  - A nerve module provides `observe_*()` (emit) + `build_*_surface()` (read-only) + `register_*_producer()` (cadence via `ProducerSpec`). (`core/services/central_llm_egress.py:46`)
  - Cadence bootstrap wiring lives in `core/services/internal_cadence_central_wiring.py`.
  - Owner-gated read route pattern: `apps/api/jarvis_api/routes/central_connections.py:14`.
  - `jc` maps a subcommand → `/central/*` via `_GET_ENDPOINTS` in `apps/central_cli/central_cli/commands.py:15`.
- No existing `docs` cluster / `drift` nerve — `central_drift.py` is a rate-change monitor for *other* nerves, not a signal carrier; do not reuse it.

## Architecture

Two sides over one shared engine.

### Shared engine — `scripts/docs_drift_check.py`

Stdlib only, static, mirrors `docs_audit.py`. Pure, unit-tested functions. Three check families, each result tagged `hard` or `soft`:

- **`dangling_refs(docs_root) -> list[dict]`** (🔴 hard). For every non-archived doc, collect two kinds of target and resolve each correctly: (a) bare code paths like `core/services/foo.py` (matched by `docs_audit`'s `_PATH_RE`) resolve **relative to the repo root**; (b) markdown link targets `](rel#Lnn)` (e.g. the `[src](../../../core/…)` links the SP4 pages emit) resolve **relative to the doc's own directory**, stripping any `#…` fragment. A target that does not resolve on disk is drift. External links (`http(s)://`, `mailto:`) are ignored. Deterministic, filesystem-only. (Symbol references are handled by the soft family, not here.)
- **`stale_generated(repo_root, only_dirs=None) -> list[dict]`** (🔴 hard). For each generator with a known (source-tree → output-file) mapping, regenerate its output into a temp location and byte-compare to the committed file; a mismatch means "you forgot to regenerate." When `only_dirs` is given (the staged source trees), only generators whose source tree intersects are checked — this is the fast pre-commit path. When `only_dirs is None`, all generators are checked (CI/report path).
- **`prose_drift(docs_root, repo_root) -> list[dict]`** (🟡 soft). Symbols in hand-written (non-generated) docs that don't appear anywhere in the code — reuse `docs_audit`'s symbol extraction + a code-symbol index. Advisory only.
- **`requirements_drift(repo_root) -> list[dict]`** (🟡 soft). Re-run the `requirements_gen` import scan; imports present in code but absent from `requirements.txt` are advisory drift.

Assembly + modes:
- **`run_check(repo_root, staged=None) -> dict`** — builds the full report `{hard: [...], soft: [...], generated_at, counts}`. If `staged` (list of staged paths) is provided, `stale_generated` is scoped to those source trees; otherwise full.
- **`main()`** — CLI. `--check` mode: compute the two hard families (staleness scoped to staged files via `git diff --cached --name-only`), print any hard drift, exit 1 if non-empty, else 0. Default mode: full report (all families, unscoped) → write `docs/drift_report.json` and print a summary; exit 0.

Generator→output map (explicit, in the script):

| Generator | Source trees | Output(s) |
|---|---|---|
| `api_docs_gen` | `core`, `apps`, `scripts` | `docs/reference/api/*.md`, `docs/reference/DOCSTRING_COVERAGE.md` |
| `api_reference_gen` | `apps/api` | `docs/reference/API_REFERENCE.md` |
| `capabilities_gen` | `core/tools`, `core/services` | `docs/reference/CAPABILITIES.md` |

`capability_audit` and `docs_audit` are audits whose output is inherently a snapshot (not a claim about current code the same way), so they are **not** in the hard staleness set; `requirements_gen` is covered by the soft `requirements_drift` family. This keeps the hard gate to genuinely deterministic, regenerate-or-block outputs.

Staleness is checked by comparing generated bytes **excluding a volatile "Generated <date>" header line** (the generators stamp today's date, which would otherwise always differ). The comparison normalizes that one line before diffing.

### Side 1 — repo gate

A `docs-drift-check` hook in `.pre-commit-config.yaml` runs `python scripts/docs_drift_check.py --check`. It blocks the commit on dangling refs or (change-scoped) stale generated docs. Fast: dangling scan is filesystem-only; staleness only regenerates generators whose source tree is staged.

### Side 2 — Central nerve — `core/services/docs_drift_watchdog.py`

Self-safe (never throws). Reads the committed `docs/drift_report.json` and checks whether it is stale relative to the working tree (report older than the newest `docs/` or source mtime → "report itself is stale, drift unknown"). Functions:
- `read_report(repo_root) -> dict` — load `docs/drift_report.json`; `{}` if missing.
- `check_docs_drift(repo_root) -> dict` — `{hard_count, soft_count, report_stale, generated_at}` from the report + freshness check.
- `observe_docs_drift()` — `central_timeseries.record("docs", "drift", value=<hard_count>, meta={soft, report_stale})` + `central().observe({...})`. Both wrapped, never throws.
- `build_docs_drift_surface() -> dict` — read-only surface (status, hard/soft counts, report_stale, generated_at, top few drift items).
- `register_docs_drift_producer()` — `ProducerSpec(name="docs_drift_watchdog", cooldown_minutes=5, run_fn=…)`, wired in `internal_cadence_central_wiring.py`.

### Side 2 surface — route + CLI

- `apps/api/jarvis_api/routes/central_docs_drift.py` — owner-gated `GET /central/docs-drift` → `build_docs_drift_surface()`. Registered in the API app alongside the other central routes.
- `apps/central_cli/central_cli/commands.py` — add `"docs-drift": "/central/docs-drift"` to `_GET_ENDPOINTS` → `jc docs-drift`.

## Data flow

```
commit → pre-commit `--check` → (dangling + scoped staleness) → block or pass
CI / manual → default mode → full report → docs/drift_report.json (committed)
runtime cadence (~5m) → docs_drift_watchdog reads report → central_timeseries + observe
                                                          → /central/docs-drift → jc docs-drift
```

## Error handling

- The engine is best-effort per check family: a family that raises is caught and recorded as a `soft` "checker_error" entry rather than crashing the run (a broken checker must not block all commits). Dangling-ref and staleness families, being simple, should not raise; if they do, the `--check` gate treats a checker_error as **soft** (does not block) and surfaces it, so a bug in the checker can't wedge the repo.
- The nerve is fully self-safe: any error → sensible defaults, never throws, never blocks the cadence.
- Route returns `{"status": "unavailable"}` on any failure.

## Testing

- `tests/test_docs_drift_check.py` — on fixtures: `dangling_refs` flags a doc linking a non-existent path and passes a valid one; `stale_generated` detects a hand-mutated generated file and passes a freshly-generated one (header-line normalization verified); `run_check` on the real repo returns **no hard drift** (guards the current tree is clean); the volatile-header normalization is unit-tested.
- `tests/test_docs_drift_watchdog.py` — `check_docs_drift` reads a fixture report and computes counts + freshness; missing report → self-safe defaults; `build_docs_drift_surface` never throws.

## Files

- **New:** `scripts/docs_drift_check.py` + `tests/test_docs_drift_check.py`; `core/services/docs_drift_watchdog.py` + `tests/test_docs_drift_watchdog.py`; `apps/api/jarvis_api/routes/central_docs_drift.py`.
- **Modify:** `.pre-commit-config.yaml` (hook); the API app router registration; `apps/central_cli/central_cli/commands.py` (`_GET_ENDPOINTS`); `docs/CONTRIBUTING.md` (document the gate + `jc docs-drift`).
- **Generated:** `docs/drift_report.json` (committed).

## Scope boundary

SP5 = the drift watchdog (repo gate + Central nerve) built on the existing generators. It does **not** rewrite any generator, does not fill the SP4 docstring gap, and does not add fuzzy AI-judged "is this doc's prose accurate?" checks beyond the deterministic symbol-existence advisory. It closes the docs programme: after SP5, docs that drift from git+runtime are caught mechanically.

## Deploy

Two-stage. **Stage 1 (repo-side, lands first):** `scripts/docs_drift_check.py` + tests + the pre-commit hook + CONTRIBUTING — pure repo, no runtime, no container deploy; the generator test + a run of `--check` on the clean tree is the gate. **Stage 2 (runtime):** the nerve + route + CLI + cadence wiring — touches runtime, so the full suite (~20 min) gates it and it deploys to the container (`git pull` ff/merge + `sudo systemctl restart jarvis-runtime jarvis-api` on `bs@10.0.0.39`, restart BOTH). Lands on `main`.
