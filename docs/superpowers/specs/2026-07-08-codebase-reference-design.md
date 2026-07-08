# Docs Programme SP4 — Codebase Reference (generated breadth)

**Date:** 2026-07-08
**Status:** Approved (design)
**Programme:** Prod-ready docs/. SP1 (audit) + SP2 (structure+generators) + SP3 (install) LANDED. This is SP4. Then SP5 drift-sikring.

## Goal

Document **every file and function** with a code reference — feasibly. SP4 ships a **generator** that turns the codebase into per-package reference pages (signatures + existing docstrings + source links), plus a **docstring-coverage audit** listing the undocumented functions. It does **not** hand-write the 8,815 missing docstrings (that is a separate, budgeted gap-fill effort) — but it makes the whole surface navigable and drift-proof now.

## Ground truth (verified 2026-07-08)

- **1,421** Python files across `core/`+`apps/`+`scripts/`; **15,204** functions/methods.
- **78%** of files have a module docstring; **42%** of functions have a docstring (6,389); **57% don't** (8,815).
- So a generator captures everything by *signature* immediately, plus 42% richly by docstring — the real gap is the 8,815 undocumented functions.
- Existing generator pattern: `capability_audit.py`, `api_reference_gen.py`, `capabilities_gen.py` (SP2). Reference docs live under `docs/reference/`.

## Decisions (from brainstorm)

- **Deliverable:** generator + coverage audit (breadth now). Docstring gap-fill deferred to a separate budgeted effort.
- **Granularity:** one page **per package/directory** (~dozens of pages), not per-module (1,421 files) or per-subsystem (~20 giant files).
- **Bidirectional refs:** doc→code via `file:line` links (auto). code→doc via a **derivable-path convention** (`core/services/foo.py` → `docs/reference/api/core.services.md#foo`), documented in the api index + CONTRIBUTING — **no invasive comment injected into the 1,421 source files**.

## Architecture

### `scripts/api_docs_gen.py` — the reference generator

AST-walks `core/`+`apps/`+`scripts/` (skipping `tests/`, `__pycache__`, dot-dirs). Pure, static, stdlib only. Core functions (each unit-tested on fixtures):
- `iter_py(root)` — the source files to document.
- `module_entry(text, relpath)` — parse one file → `{module, docstring_summary, members: [{kind, name, signature, doc_summary, lineno}]}` where members are top-level classes + functions/methods (one nesting level for class methods), `signature` reconstructed from the AST args, `doc_summary` = first line of the docstring or `""`.
- `package_of(relpath)` — the dotted package/dir key (e.g. `core/services/foo.py` → `core.services`).
- **Pagination for oversized packages:** `core/services/` is a flat directory of ~800 modules, so a single `core.services.md` would be unusable. `page_key(pkg, module_name, n_in_pkg, chunk=40)` splits a package with more than `chunk` modules into alphabetical chunks (`core.services.a-c`, `core.services.d-f`, …), so no page exceeds ~40 modules. Small packages stay a single page. Result: dozens-to-~100 manageable pages, all listed in the index.
- `render_package_md(pkg, entries)` — the markdown for one package page: a heading, then per module its docstring + a table/list of members with `signature` · summary · `[src](../../core/services/foo.py#Lnn)` link.
- `coverage(entries)` — counts documented vs undocumented functions per package + a prioritized undocumented list (public = non-`_`, non-test).
- `render_index_md(pkgs, cov)` — `docs/reference/api/README.md` linking every package page + a coverage summary.
- `render_coverage_md(cov)` — `docs/reference/DOCSTRING_COVERAGE.md`: per-package %, the prioritized undocumented public functions (the "mangler" for functions).
- `main()` — writes `docs/reference/api/<pkg>.md` for each package, the index, and the coverage report; prints totals.

### Output

- `docs/reference/api/<dotted.package>[.<chunk>].md` — dozens-to-~100 pages; big flat dirs chunked (e.g. `core.services.a-c.md` … `core.runtime.md`, `apps.api.jarvis_api.routes.md`, `scripts.md`).
- `docs/reference/api/README.md` — index + how to read + the code↔doc convention.
- `docs/reference/DOCSTRING_COVERAGE.md` — the gap report (feeds a future gap-fill + SP5).

### Bidirectional convention (non-invasive)

- **doc → code:** every member links `[src](<relative path to file>#L<lineno>)`.
- **code → doc:** deterministic by rule — module `<pkg>/<mod>.py` is documented in `docs/reference/api/<dotted pkg>.md`, anchor `#<mod>`. Stated once in `api/README.md` and referenced from `CONTRIBUTING.md`. No source-file edits.

## Testing

`tests/test_api_docs_gen.py` — the pure functions on fixtures:
- `module_entry` extracts a function's name + reconstructed signature + first-line doc-summary; a no-docstring function → empty summary; a class with methods → members incl. the methods.
- `package_of` maps paths to dotted package keys; `page_key` returns a single page for a small package and an alphabetical chunk suffix for an oversized one.
- `coverage` counts documented/undocumented correctly and lists only public (non-`_`, non-test) undocumented functions.
- `render_package_md` / `render_index_md` / `render_coverage_md` produce markdown containing the expected names, signatures, and `#L` source links.

## Files

- **New:** `scripts/api_docs_gen.py` + `tests/test_api_docs_gen.py`.
- **Generated:** `docs/reference/api/*.md` (dozens), `docs/reference/api/README.md`, `docs/reference/DOCSTRING_COVERAGE.md`.
- **Update:** `docs/README.md` (link the api reference + coverage), `docs/CONTRIBUTING.md` (the code↔doc convention + "regenerate" line).

## Scope boundary

SP4 = generated breadth reference + coverage gap-list + convention. It does **not** write the 8,815 missing docstrings (a separate budgeted gap-fill, workflow-scale) and does not build the drift checker (SP5 — though this generator + coverage report are its building blocks).

## Deploy

Repo-docs + one `scripts/` generator (with tests). No runtime change, no container deploy. The generator test + a link/anchor sanity check gate correctness; the full runtime suite is not required (no runtime code). Lands on `main`.
