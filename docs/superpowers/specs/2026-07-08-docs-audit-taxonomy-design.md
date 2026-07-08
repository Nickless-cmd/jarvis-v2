# Docs Programme SP1 — Audit & Taxonomy

**Date:** 2026-07-08
**Status:** Approved (design)
**Programme:** Production-ready docs/ for the whole codebase. Sub-projects: **SP1 audit/taxonomy (this)** → SP2 canonical structure+index → SP3 install guide → SP4 codebase reference docs (workflow-scale) → SP5 drift-sikring. Each gets its own spec→plan cycle.

## Goal

Make `docs/` legible. Classify all **423** existing docs against **git-log + runtime truth** (never the doc's own claims) into **færdig / forældet / droppet**, plus a **mangler** gap-list of undocumented subsystems. Produce a manifest, stamp a status frontmatter on every doc, and archive the dead weight. This is the foundation the rest of the programme builds on.

**Explicitly NOT in SP1:** rewriting/consolidating doc *content* (SP2), writing per-file/per-function reference docs (SP4), or building the ongoing drift checker (SP5). SP1 only *classifies, stamps, archives, and maps gaps*.

## Ground truth (verified 2026-07-08)

- **Code:** 1,417 Python files, ~467k LOC, ~13,870 functions (across `core/`, `apps/`, `scripts/`).
- **Docs:** 423 `.md` files — incl. 131 `docs/superpowers/specs/`, 77 `docs/superpowers/plans/`, 22 `docs/notes/`, overlapping top-level (`ARCHITECTURE.md`/`ARCHITECTURE_DEEP_DIVE.md`/`BACKEND_OVERVIEW.md`), a stale `DOCS_AUDIT_2026-04-21.md`, `INDEX.md`, `_archive/`.
- **Existing generator pattern to mirror:** `scripts/capability_audit.py` → `docs/capability_matrix.md` (static analysis, regenerable). SP1's auditor follows this shape.

## Method — hybrid (three phases)

### Phase 1 — heuristic auditor (deterministic, cheap)

New `scripts/docs_audit.py` (regenerable, static). For each `.md` under `docs/` it computes signals:

- **Code-reference liveness:** extract referenced file paths (regex for `core/...`, `apps/...`, `scripts/...`, backtick paths) and symbol names; check each against the working tree — % of references that still resolve.
- **Git recency:** the doc's last-commit date; and for docs citing a git-sha, whether that sha is far behind HEAD.
- **Superseded/duplicate:** title + heading-shingle similarity to detect overlapping docs (e.g. the three ARCHITECTURE files); a newer doc covering the same subject supersedes an older one.
- **Superpowers specs/plans:** check whether the described feature shipped — grep git-log + the working tree for the plan/spec's key symbols/paths. A plan whose artifacts exist = **færdig(done)**; a spec/plan with no trace = **droppet**; superseded = **forældet**.

**Auto-classify only the clear-cut** (with a `confidence`): all-refs-dead + old → forældet; superseded duplicate → droppet; recent + refs-alive + (for plans) shipped → færdig-candidate. Everything else → **needs_review**. Output a preliminary `docs_audit_raw.json`.

### Phase 2 — workflow triage (the doubtful remainder only)

A multi-agent workflow (opt-in) over the `needs_review` docs. Each agent reads one doc + checks its concrete claims against the actual code/git and returns a structured verdict `{path, category, summary, ground_truth_basis, action, superseded_by?}`. Fan-out; only the ambiguous subset (not all 423) reaches the LLM.

### Phase 3 — synthesis + apply

- Merge Phase-1 auto-classified + Phase-2 verdicts → `docs/DOCS_MANIFEST.json` (authoritative) and `docs/DOCS_MANIFEST.md` (human table: path · category · summary · basis · action).
- **Stamp frontmatter** on every classified doc (idempotent): prepend/merge YAML
  ```yaml
  ---
  status: færdig | forældet | droppet
  audited: 2026-07-08
  ground_truth: "<why — e.g. 'refs core/services/foo.py alive; plan commit abc1234 shipped'>"
  superseded_by: <path or omitted>
  ---
  ```
  If a doc already has frontmatter, merge these keys without clobbering others.
- **Archive:** `git mv` every `forældet`/`droppet` doc into `docs/_archive/<original-subpath>` (git history preserved). `færdig` docs stay in place. The manifest records old→new paths.
- **Mangler gap-list:** a coarse subsystem→doc-coverage map (top-level code areas: `core/services`, `core/runtime`, `core/tools`, `apps/api`, `apps/ui`, `scripts`, each major subsystem) × "does any current doc cover it?" → list the gaps. Written into the manifest as the `mangler` section. This *feeds SP4*; SP1 does not fill it.

## Categories (exactly the four Bjørn asked for)

| Category | Meaning | Action |
|---|---|---|
| **færdig** | Valid + kept. Two senses: a *reference/architecture* doc that is accurate & current, OR a *spec/plan* whose work **shipped** (done history — still a true record). | keep in place, stamp |
| **forældet** | Was real, but code moved / claims now stale / superseded by a newer doc | archive + `superseded_by`, stamp |
| **droppet** | Describes something never built / abandoned (no trace in code or git) | archive, stamp |
| **mangler** | (not a doc) a documentation gap — a subsystem with no coverage | manifest entry → SP4 |

**Note on volume:** stamping frontmatter touches all ~423 docs — a large but purely mechanical, generated diff (the auditor writes it; humans don't hand-edit). A shipped plan is **færdig**, not forældet — "the plan is done" ≠ "the doc is stale". The manifest's `summary` distinguishes accurate-reference from done-history.

## Ground-truth discipline

Every classification cites *why* in `ground_truth` (a checked ref / git-sha / superseding doc) — evidence, not opinion. This is the whole point: docs earn their category from git+runtime, not self-claim.

## Files

- **New:** `scripts/docs_audit.py` (heuristic auditor) + `tests/test_docs_audit.py`.
- **New:** `docs/DOCS_MANIFEST.md` + `docs/DOCS_MANIFEST.json` (generated).
- **Modify:** every classified doc — frontmatter stamp (mechanical, via the synthesis step).
- **Move:** `forældet`/`droppet` docs → `docs/_archive/` (git mv).
- The Phase-2 workflow is authored inline at execution (not a committed file) unless saved for reuse.

## Testing

`tests/test_docs_audit.py` — unit tests for the auditor's pure logic on fixtures:
- reference extraction (paths + symbols from markdown);
- liveness check (existing vs deleted path → resolved/unresolved);
- superseded detection (two overlapping fixture docs → newer supersedes older);
- classification thresholds (all-dead+old → forældet; recent+alive → færdig-candidate; no-trace spec → droppet; ambiguous → needs_review);
- frontmatter merge (idempotent; existing keys preserved).
Workflow output + archive moves are spot-checked live, not unit-tested.

## Deploy / scope

This is a repo-docs change (no runtime code). Full-suite gate still runs (the auditor is under `scripts/`, its test under `tests/`). No container deploy needed for docs themselves, but the auditor script + manifest land on `main` like any change. `docs_audit.py` is re-runnable so the manifest can be refreshed anytime (basis for SP5).
