# Docs SP2 — Canonical Structure + Index Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give docs/ real navigation + fresh code-grounded canonical docs (README, thin architecture map, generated API_REFERENCE + CAPABILITIES), and de-clutter the stale snapshots.

**Architecture:** Two new generators (import/AST route-walker + tool-registry-walker) produce breadth reference that can't re-stale; two hand-written anchors (README index + thin OVERVIEW) provide navigation and the architecture map; 4 stale snapshots move to design-history/. No runtime code touched; generated docs stay in place (runtime reads one of them).

**Tech Stack:** Python 3.11 (stdlib + FastAPI introspection), pytest, `conda activate ai`.

**Execution note:** Tasks 1–2 (generators + tests) → fresh **haiku** subagent each. Tasks 3–6 (run generators, write anchors, move snapshots, gate) → **Claude inline**.

---

## File Structure

- **New** `scripts/api_reference_gen.py` (+ test) — routes → `docs/reference/API_REFERENCE.md`.
- **New** `scripts/capabilities_gen.py` (+ test) — tool registry → `docs/reference/CAPABILITIES.md`.
- **New** `docs/README.md`, `docs/architecture/OVERVIEW.md` (hand-written anchors).
- **Move** 4 stale snapshots → `docs/design-history/`.

---

## Task 1: `scripts/api_reference_gen.py` + tests

**Files:**
- Create: `scripts/api_reference_gen.py`
- Test: `tests/test_api_reference_gen.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_api_reference_gen.py
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "api_reference_gen", Path(__file__).resolve().parents[1] / "scripts" / "api_reference_gen.py")
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)


def test_routes_from_app_extracts_method_path():
    from fastapi import FastAPI
    app = FastAPI()

    @app.get("/health")
    def health():
        return {}

    @app.post("/chat/send")
    def send():
        return {}

    rows = gen.routes_from_app(app)
    paths = {(r["method"], r["path"]) for r in rows}
    assert ("GET", "/health") in paths
    assert ("POST", "/chat/send") in paths


def test_routes_from_app_empty():
    from fastapi import FastAPI
    assert gen.routes_from_app(FastAPI()) == []


def test_routes_from_ast_reads_decorators(tmp_path):
    f = tmp_path / "routes_x.py"
    f.write_text(
        'from fastapi import APIRouter\n'
        'router = APIRouter()\n'
        '@router.get("/a")\n'
        'def a(): ...\n'
        '@router.post("/b/{id}")\n'
        'def b(id): ...\n')
    rows = gen.routes_from_ast(tmp_path)
    paths = {(r["method"], r["path"]) for r in rows}
    assert ("GET", "/a") in paths and ("POST", "/b/{id}") in paths


def test_render_md_groups_and_lists():
    rows = [{"method": "GET", "path": "/health", "name": "health", "module": "health.py"}]
    md = gen.render_md(rows)
    assert "/health" in md and "GET" in md and "API_REFERENCE" in md
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `conda run -n ai python -m pytest tests/test_api_reference_gen.py -q`
Expected: FAIL — module not defined.

- [ ] **Step 3: Write the implementation**

```python
# scripts/api_reference_gen.py
"""Generate docs/reference/API_REFERENCE.md from the FastAPI app (ground truth).
Primary: import the app and read app.routes. Fallback: AST-walk routes/*.py decorators.
Regenerable — can't re-stale. Stdlib + FastAPI."""
from __future__ import annotations

import ast
import re
from datetime import UTC, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ROUTES_DIR = REPO / "apps" / "api" / "jarvis_api" / "routes"
OUT = REPO / "docs" / "reference" / "API_REFERENCE.md"


def routes_from_app(app) -> list[dict]:
    """Read real mounted routes from a FastAPI app. Pure over the app object."""
    from fastapi.routing import APIRoute
    rows = []
    for r in getattr(app, "routes", []):
        if not isinstance(r, APIRoute):
            continue
        methods = sorted(m for m in (r.methods or set()) if m not in ("HEAD", "OPTIONS"))
        model = getattr(getattr(r, "response_model", None), "__name__", "") or ""
        mod = getattr(getattr(r, "endpoint", None), "__module__", "") or ""
        for m in methods:
            rows.append({"method": m, "path": r.path, "name": r.name or "",
                         "model": model, "module": mod.split(".")[-1]})
    return rows


_DEC_RE = re.compile(r'@(?:router|app)\.(get|post|put|patch|delete)\(\s*["\']([^"\']+)["\']')


def routes_from_ast(routes_dir: Path = ROUTES_DIR) -> list[dict]:
    """Fallback: scan route files for @router.<method>("path") decorators (no import)."""
    rows = []
    for p in sorted(Path(routes_dir).rglob("*.py")):
        try:
            for m, path in _DEC_RE.findall(p.read_text(errors="ignore")):
                rows.append({"method": m.upper(), "path": path, "name": "",
                             "model": "", "module": p.stem})
        except Exception:
            pass
    return rows


def collect_routes() -> tuple[list[dict], str]:
    """Try the live app first; fall back to AST. Returns (rows, source)."""
    try:
        from apps.api.jarvis_api.app import app  # type: ignore
        rows = routes_from_app(app)
        if rows:
            return rows, "app.routes (live)"
    except Exception:
        pass
    return routes_from_ast(), "AST fallback"


def render_md(rows: list[dict], source: str = "") -> str:
    rows = sorted(rows, key=lambda r: (r["path"], r["method"]))
    lines = ["# API_REFERENCE", "",
             f"> Generated {datetime.now(UTC).date().isoformat()} from {source or 'code'} — "
             f"{len(rows)} routes. Regenerate: `python scripts/api_reference_gen.py`. DO NOT hand-edit.",
             "", "| Method | Path | Response model | Source |", "|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['method']} | `{r['path']}` | {r.get('model','')} | {r.get('module','')} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    rows, source = collect_routes()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render_md(rows, source))
    print(f"api_reference_gen: {len(rows)} routes from {source} → {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `conda run -n ai python -m pytest tests/test_api_reference_gen.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add scripts/api_reference_gen.py tests/test_api_reference_gen.py
git commit -m "feat(docs): SP2 API reference generator (app.routes + AST fallback)"
```

---

## Task 2: `scripts/capabilities_gen.py` + tests

**Files:**
- Create: `scripts/capabilities_gen.py`
- Test: `tests/test_capabilities_gen.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_capabilities_gen.py
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "capabilities_gen", Path(__file__).resolve().parents[1] / "scripts" / "capabilities_gen.py")
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)


def test_tools_from_registry_categorizes():
    handlers = {"read_file": lambda a: None, "operator_bash": lambda a: None,
                "write_file": lambda a: None, "search_memory": lambda a: None}
    mutating = {"write_file", "operator_bash"}
    rows = gen.tools_from_registry(handlers, mutating)
    by = {r["name"]: r for r in rows}
    assert by["read_file"]["mutating"] is False and by["read_file"]["kind"] == "native"
    assert by["operator_bash"]["mutating"] is True and by["operator_bash"]["kind"] == "operator"
    assert by["write_file"]["mutating"] is True


def test_tools_from_registry_skips_bad():
    rows = gen.tools_from_registry({"": None, "ok_tool": lambda a: None}, set())
    assert [r["name"] for r in rows] == ["ok_tool"]


def test_render_md_has_counts_and_rows():
    rows = [{"name": "read_file", "kind": "native", "mutating": False}]
    md = gen.render_md(rows)
    assert "read_file" in md and "CAPABILITIES" in md and "1" in md
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `conda run -n ai python -m pytest tests/test_capabilities_gen.py -q`
Expected: FAIL.

- [ ] **Step 3: Write the implementation**

```python
# scripts/capabilities_gen.py
"""Generate docs/reference/CAPABILITIES.md from the live tool registry. Regenerable.
Reuses permission_classifier._MUTATING_TOOLS for the mutating flag. Stdlib only."""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "docs" / "reference" / "CAPABILITIES.md"


def tools_from_registry(handlers: dict, mutating: set) -> list[dict]:
    """Pure: map the name→handler registry to rows with kind + mutating flag."""
    rows = []
    for name in sorted(k for k in handlers if k):
        kind = "operator" if str(name).startswith("operator_") else "native"
        rows.append({"name": name, "kind": kind, "mutating": name in mutating})
    return rows


def render_md(rows: list[dict]) -> str:
    n_mut = sum(1 for r in rows if r["mutating"])
    lines = ["# CAPABILITIES", "",
             f"> Generated {datetime.now(UTC).date().isoformat()} — {len(rows)} tools "
             f"({n_mut} mutating). Regenerate: `python scripts/capabilities_gen.py`. DO NOT hand-edit.",
             "", "| Tool | Kind | Mutating |", "|---|---|---|"]
    for r in sorted(rows, key=lambda r: (r["kind"], r["name"])):
        lines.append(f"| `{r['name']}` | {r['kind']} | {'yes' if r['mutating'] else 'no'} |")
    return "\n".join(lines) + "\n"


def collect() -> list[dict]:
    from core.tools.simple_tools import _TOOL_HANDLERS
    try:
        from core.services.permission_classifier import _MUTATING_TOOLS as mut
    except Exception:
        mut = set()
    return tools_from_registry(dict(_TOOL_HANDLERS), set(mut))


def main() -> int:
    rows = collect()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render_md(rows))
    print(f"capabilities_gen: {len(rows)} tools → {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `conda run -n ai python -m pytest tests/test_capabilities_gen.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add scripts/capabilities_gen.py tests/test_capabilities_gen.py
git commit -m "feat(docs): SP2 capabilities generator (tool registry → reference)"
```

---

## Task 3 (Claude inline): run the generators

- [ ] **Step 1: Generate the reference docs**

Run: `conda run -n ai python scripts/api_reference_gen.py && conda run -n ai python scripts/capabilities_gen.py`
Expected: prints route/tool counts; writes `docs/reference/API_REFERENCE.md` + `docs/reference/CAPABILITIES.md`. Sanity-check: API_REFERENCE has a realistic route count (hundreds), CAPABILITIES lists the mutating tools with `yes`. If the app-import path failed and it fell back to AST, note that in the doc's source line (already handled).

- [ ] **Step 2: Commit**

```bash
git add docs/reference/API_REFERENCE.md docs/reference/CAPABILITIES.md
git commit -m "docs(docs): SP2 generated API_REFERENCE + CAPABILITIES (fresh from code)"
```

---

## Task 4 (Claude inline): hand-written anchors — README + OVERVIEW

- [ ] **Step 1: Write `docs/README.md`** — the entry point. Ground the "what is Jarvis" in `JARVIS_MANIFESTO.md`/`CENTRAL.md` (not aspiration). Then the doc map by category with working relative links:
  - **Getting started** → `USER_GUIDE.md` (install guide: SP3, note "coming")
  - **Architecture** → `architecture/OVERVIEW.md`, `CENTRAL.md`, `BACKEND_OVERVIEW.md`
  - **Reference** → `reference/API_REFERENCE.md`, `reference/CAPABILITIES.md`, `capability_matrix.md`
  - **Operations** → `MODEL_STRATEGY.md`, `TRANSPORTS.md`, `CHANNELS.md`, `CLI_SPEC.md`
  - **Generated (regenerable, in place)** → `capability_matrix.md`, `central_connectivity_matrix.md`, `god_file_map.md`, `DOCS_MANIFEST.md`
  - **Design history** → `superpowers/`, `design-history/`

- [ ] **Step 2: Write `docs/architecture/OVERVIEW.md`** — thin, code-grounded map (verify each claim against the tree/CLAUDE.md as you write):
  - Directory structure (`core/runtime`, `core/services`, `core/tools`, `core/context`, `apps/api`, `apps/ui`, `scripts`, `state/`, `workspace/`) with one-paragraph responsibility each.
  - Request flow (chat → `visible_runs` → tools/Central → response), the agentic loop, the Central nervous system (→ `CENTRAL.md`).
  - The four sources of truth (config / DB / workspace files / Central) per `CLAUDE.md`.
  - Explicit note: this is a MAP; per-file/function depth is the reference docs + SP4.

- [ ] **Step 3: Commit**

```bash
git add docs/README.md docs/architecture/OVERVIEW.md
git commit -m "docs(docs): SP2 README index + thin architecture OVERVIEW (code-grounded)"
```

---

## Task 5 (Claude inline): move stale snapshots + link-check

- [ ] **Step 1: Move the 4 stale snapshots to design-history/**

```bash
mkdir -p docs/design-history
for f in DOCS_AUDIT_2026-04-21.md TASK_daemon_fix_DIAGNOSIS_2026-04-21.md PREDECESSOR_COGNITION_AUDIT_2026-04-22.md CURRENT_STATUS.md; do
  git mv "docs/$f" "docs/design-history/$f" 2>/dev/null || echo "skip $f (already moved/absent)"
done
```

- [ ] **Step 2: Link-check README + OVERVIEW**

Verify every relative link in `docs/README.md` and `docs/architecture/OVERVIEW.md` resolves to an existing file. Run an inline check (extract `](...)` targets, resolve relative to the doc's dir, assert exists). Fix any dangling link (e.g. a moved snapshot, or a file that turned out archived).

- [ ] **Step 3: Regenerate the manifest to reflect the new reference docs + moves**

Run: `conda run -n ai python scripts/docs_audit.py` — refreshes `docs/docs_audit_raw.json` counts (the new README/OVERVIEW/reference docs classify as færdig; snapshots now under design-history). (The authoritative `DOCS_MANIFEST.json` from SP1 can be re-synthesized later; for SP2 just confirm the auditor still runs clean.)

- [ ] **Step 4: Commit**

```bash
git add -A docs/
git commit -m "docs(docs): SP2 move stale snapshots to design-history + link-checked anchors"
```

---

## Task 6: gate + push

- [ ] **Step 1: Generator tests**

Run: `conda run -n ai python -m pytest tests/test_api_reference_gen.py tests/test_capabilities_gen.py tests/test_docs_audit.py -q`
Expected: PASS.

- [ ] **Step 2: Full-suite gate (~20 min)**

Run: `conda run -n ai python -m pytest -q -p no:cacheprovider --timeout=45 --timeout-method=signal`
Expected: PASS. Known rotating isolation flakes (re-run alone): subagent_ecology, forgetting_engine, meta_learning, heartbeat_self_knowledge, workspace_bootstrap, causal_quality, db_user_temperature.

- [ ] **Step 3: Push**

```bash
git push
```

- [ ] **Step 4: No container deploy** — repo-docs + two `scripts/` generators (no runtime import at runtime). Container picks up docs on next ordinary pull.

- [ ] **Step 5: Report** the result to Bjørn (route/tool counts, new structure) and note SP3 (install guide) is next — DEPLOYMENT/SECURITY/CONTRIBUTING (archived stale in SP1) are its rewrite targets.

---

## Self-Review

**Spec coverage:** hybrid reorg — snapshots→design-history only, generated docs stay (safety correction) (Task 5) ✓; api_reference_gen import+AST fallback (Task 1) ✓; capabilities_gen registry walk + mutating flag reuse (Task 2) ✓; generated reference docs (Task 3) ✓; README index by category (Task 4) ✓; thin architecture OVERVIEW, SP4 boundary noted (Task 4) ✓; link-check (Task 5) ✓; generator tests on fixtures (Tasks 1–2) ✓.

**Placeholder scan:** none — generators are complete code; README/OVERVIEW are hand-written-at-execution content items with a concrete section spec (not code placeholders); the install-guide link is a labeled SP3 forward-reference.

**Type consistency:** `routes_from_app(app)`/`routes_from_ast(dir)`/`render_md(rows[,source])` in api gen match tests; `tools_from_registry(handlers, mutating)`/`render_md(rows)` in capabilities gen match tests; row dict keys (`method`/`path`/`model`/`module`; `name`/`kind`/`mutating`) consistent between builder, renderer, and tests.
