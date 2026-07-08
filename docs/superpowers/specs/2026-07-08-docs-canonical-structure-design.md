# Docs Programme SP2 — Canonical Structure + Index

**Date:** 2026-07-08
**Status:** Approved (design)
**Programme:** Prod-ready docs/. SP1 (audit/taxonomy) LANDED `7c1e85f6`. This is SP2. Then SP3 install → SP4 per-file/function reference → SP5 drift-sikring.

## Goal

Give `docs/` a prod-ready information architecture with real navigation and **fresh, code-grounded** top-level canonical docs — because SP1 archived the stale flagships (ARCHITECTURE, API_REFERENCE, CAPABILITIES, CONSCIOUSNESS_ROADMAP). Make a newcomer able to find their way, and make the reference docs **impossible to re-stale** by generating them from code.

## Ground truth (post-SP1)

- `docs/DOCS_MANIFEST.json`: 283 færdig / 28 forældet / 7 droppet. færdig split: 211 `superpowers/` (design history), 29 top-level (mixed), 15 `specs/`, 13 `notes/`, rest scattered.
- Fresh anchors that survived: `CENTRAL.md` (2026-07-04, nervous-system truth), `BACKEND_OVERVIEW.md`, `USER_GUIDE.md`, `MODEL_STRATEGY.md`, `TRANSPORTS.md`, `CHANNELS.md`, `CLI_SPEC.md`, `streaming-production-grade-spec.md`.
- Generated tool-outputs currently at top-level: `capability_matrix.md`, `capability_partial_triage.md`, `central_connectivity_matrix.md`, `god_file_map.md`, `DOCS_MANIFEST.md`.
- Stale auto-færdig snapshots (SP1 caveat — refs-alive but historical): `DOCS_AUDIT_2026-04-21.md`, `TASK_daemon_fix_DIAGNOSIS_2026-04-21.md`, `PREDECESSOR_COGNITION_AUDIT_2026-04-22.md`, `CURRENT_STATUS.md`.
- Existing generator pattern: `scripts/capability_audit.py` → `docs/capability_matrix.md`.

## Architecture

Three parts: (A) hybrid reorganization, (B) two new code-grounded generators, (C) hand-written anchors + INDEX.

### A. Hybrid reorganization (git mv — reversible)

- **`docs/generated/`** ← move the machine-generated outputs (`capability_matrix.md`, `capability_partial_triage.md`, `central_connectivity_matrix.md`, `central_connectivity_matrix.json`, `god_file_map.md`, `DOCS_MANIFEST.md` + `.json`, `docs_audit_raw.json`). **Update each generator's output path** so re-runs write to the new location: `scripts/capability_audit.py`, `scripts/central_connectivity_audit.py` (or wherever god_file_map/connectivity write), `scripts/docs_audit.py`. A grep confirms no code/test reads the old paths before moving.
- **`docs/design-history/`** ← move the stale dated snapshots listed above. Valid history, out of the main nav; keep their SP1 frontmatter.
- **`docs/superpowers/` stays put** — it is already a contained design-history subdir, and the brainstorming/writing-plans skills write there; moving it would break them. INDEX labels it "design history" and links it.
- Everything else (the surviving canonical top-level docs, `specs/`, `notes/`, `guides`) stays flat for now; the INDEX groups them logically.

### B. Two new generators (breadth reference, auto — can't re-stale)

- **`scripts/api_reference_gen.py`** → `docs/reference/API_REFERENCE.md`. **Imports the FastAPI app and reads `app.routes`** (the ground truth — real mounted paths/methods, no startup events fired by plain import): for each `APIRoute` emit methods + path + name/summary + response-model name + the endpoint's source module. Grouped by router prefix. Regenerable. Self-safe: if importing the app fails (heavy deps), fall back to an AST walk of `apps/api/jarvis_api/routes/*.py` collecting `@router.<method>("...")` decorators — degraded but never crashes. `main()` writes the md.
- **`scripts/capabilities_gen.py`** → `docs/reference/CAPABILITIES.md`. Walks the tool registry (`core/tools/simple_tools.py` `_TOOL_HANDLERS` + the tool definitions) → tool name, one-line purpose (from the definition/docstring), category (native/operator/read-write), and whether it is approval-gated/mutating. Regenerable.

Generating (not hand-writing) these is the core trust move: they were stale precisely because they were hand-maintained. SP5 will wire a freshness check.

### C. Hand-written anchors + INDEX

- **`docs/README.md`** — the entry point. What Jarvis V2 is (2–3 sentences, grounded in JARVIS_MANIFESTO/CENTRAL, not aspiration), then the doc map by category with links:
  - Getting started → `USER_GUIDE.md`, (SP3 install guide placeholder link)
  - Architecture → `architecture/OVERVIEW.md`, `CENTRAL.md`, `BACKEND_OVERVIEW.md`
  - Reference → `reference/API_REFERENCE.md`, `reference/CAPABILITIES.md`, `generated/capability_matrix.md`
  - Operations → `DEPLOYMENT` (SP3), `MODEL_STRATEGY.md`, `TRANSPORTS.md`, `CHANNELS.md`, `CLI_SPEC.md`
  - Design history → `superpowers/`, `design-history/`
  - Generated (regenerable) → `generated/`
- **`docs/architecture/OVERVIEW.md`** — a **thin** top-level map (grounded in code + capability_matrix + CLAUDE.md): the directory structure and each subsystem's one-paragraph responsibility (`core/runtime`, `core/services`, `core/tools`, `core/context`, `apps/api`, `apps/ui`, `scripts`), how requests flow (chat → visible_runs → tools/Central), the Central nervous-system (→ CENTRAL.md), and the four sources of truth (config / DB / workspace files / Central, per CLAUDE.md). **Not exhaustive** — it points to reference/generated for depth. This is the SP2/SP4 boundary: SP2 = the map, SP4 = the territory (per-file/function).

## Scope boundary SP2 ↔ SP4

SP2 = structure + navigation + a thin architecture map + **generated breadth reference** (endpoints, tools — automatic, shallow). SP4 = per-file/per-function narrative depth with bidirectional code↔docs refs. No per-function prose in SP2.

## Testing

- `tests/test_api_reference_gen.py` — the route-walker on a fixture router (a small FastAPI app with 2 routes) yields the expected method/path/model rows; empty app → empty section, no crash.
- `tests/test_capabilities_gen.py` — the registry-walker on a fixture handler dict yields tool rows with category + mutating flag; unknown/malformed entry skipped.
- README + OVERVIEW are hand-written prose — verified by spot-check against code (not unit-tested), and every link they contain is checked to resolve (a small link-check step at apply time).

## Files

- **New:** `scripts/api_reference_gen.py` + `tests/test_api_reference_gen.py`; `scripts/capabilities_gen.py` + `tests/test_capabilities_gen.py`.
- **New (generated):** `docs/reference/API_REFERENCE.md`, `docs/reference/CAPABILITIES.md`.
- **New (hand-written):** `docs/README.md`, `docs/architecture/OVERVIEW.md`.
- **Move (git mv):** generated outputs → `docs/generated/`; stale snapshots → `docs/design-history/`.
- **Modify:** generator scripts' output paths (`capability_audit.py`, `docs_audit.py`, connectivity/god-file generators) to the new `docs/generated/` location; `docs/DOCS_MANIFEST.*` regenerated/relocated accordingly.

## Deploy / scope

Repo-docs + two scripts under `scripts/` (with tests). No runtime code change, no container deploy. Full-suite gate runs (scripts have tests); the doc moves are verified to break no test (grep old paths first). Lands on `main`.
