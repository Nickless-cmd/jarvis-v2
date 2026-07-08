# Docs SP5 — Drift-sikring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A docs-drift watchdog — a hybrid pre-commit gate (blocks broken links + un-regenerated generated docs) plus a Central `docs:drift` nerve — so `docs/` cannot silently rot away from git+runtime truth.

**Architecture:** One stdlib engine `scripts/docs_drift_check.py` runs four check families (2 hard, 2 soft) by importing the existing generators and comparing their in-memory output to the committed files, plus a filesystem link-check. A pre-commit hook calls its `--check` gate. A self-safe nerve `core/services/docs_drift_watchdog.py` reads the committed `docs/drift_report.json` (never re-runs AST in the hot path) and publishes a `docs:drift` timeseries sample surfaced at `/central/docs-drift` and `jc docs-drift`.

**Tech Stack:** Python 3.11 stdlib (`ast`, `importlib`, `subprocess`, `json`), pytest, FastAPI, pre-commit.

**Execution note:** Stage 1 (repo-side, no container). Stage 2 (runtime → full suite + container deploy). Task 1 (engine + tests) and Task 3 (nerve + tests) → fresh **haiku** subagents (full code below). Tasks 2, 4, 5 (pre-commit/report wiring; route + app + cadence + CLI wiring; deploy) → **Claude inline**.

---

## STAGE 1 — repo-side (lands first, no container deploy)

### Task 1: `scripts/docs_drift_check.py` + tests

**Files:**
- Create: `scripts/docs_drift_check.py`
- Test: `tests/test_docs_drift_check.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_docs_drift_check.py
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "docs_drift_check", Path(__file__).resolve().parents[1] / "scripts" / "docs_drift_check.py")
d = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(d)


def test_broken_links_flags_missing_and_passes_valid(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "real.md").write_text("hello")
    good = docs / "a.md"
    good.write_text("[ok](real.md) and [ext](https://x.y) and [anchor](#top)")
    bad = docs / "b.md"
    bad.write_text("[gone](does_not_exist.md)")
    out = d.broken_links(docs)
    targets = {(o["doc"].split("/")[-1], o["target"]) for o in out}
    assert ("b.md", "does_not_exist.md") in targets
    assert not any(o["doc"].endswith("a.md") for o in out)


def test_norm_collapses_dates():
    assert d._norm("Generated 2026-07-08 x") == d._norm("Generated 2020-01-01 x")
    assert d._norm("Generated 2026-07-08 x") != d._norm("Generated 2026-07-08 y")


def test_real_repo_has_no_hard_drift():
    # Guards the committed tree: generated docs match their generators and no links dangle.
    rep = d.run_check()
    assert rep["counts"]["hard"] == 0, rep["hard"][:20]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `conda run -n ai python -m pytest tests/test_docs_drift_check.py -q`
Expected: FAIL — module attributes not defined. (`test_real_repo_has_no_hard_drift` also needs the generated docs to already be committed — they are, from SP4/SP2.)

- [ ] **Step 3: Write the implementation**

```python
# scripts/docs_drift_check.py
"""SP5 docs-drift checker — catch when docs/ diverges from git+runtime truth.

Hybrid: HARD checks gate a commit (broken markdown links; generated docs not regenerated
after their source changed); SOFT checks are advisory (bare code-path mentions that don't
resolve; requirements imports missing from requirements.txt). Stdlib only, self-safe per
family. `--check` = gate (hard families; staleness scoped to staged files) → exit 1 on hard
drift; default = full report → docs/drift_report.json."""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DOCS = REPO / "docs"
REPORT_OUT = DOCS / "drift_report.json"

_PATH_RE = re.compile(r"(?:core|apps|scripts)/[\w./-]+\.(?:py|ts|tsx|md|json)")
_MDLINK_RE = re.compile(r"\]\(([^)]+)\)")
_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
_SKIP_DOC_PARTS = {"_archive"}


def find_docs(root: Path = DOCS) -> list[Path]:
    return sorted(p for p in root.rglob("*.md") if not (_SKIP_DOC_PARTS & set(p.parts)))


def _norm(text: str) -> str:
    """Neutralize volatile 'Generated <date>' stamps so regeneration diffs are content-only."""
    return _DATE_RE.sub("DATE", text)


# ---- HARD: broken markdown links ----
def broken_links(docs_root: Path = DOCS) -> list[dict]:
    out: list[dict] = []
    for doc in find_docs(docs_root):
        text = doc.read_text(errors="ignore")
        rel_doc = str(doc.relative_to(docs_root.parent)) if docs_root.parent in doc.parents else doc.name
        for href in _MDLINK_RE.findall(text):
            href = href.split("#")[0].strip()
            if not href or href.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target = (doc.parent / href)
            if not target.exists():
                out.append({"doc": rel_doc, "kind": "link", "target": href})
    return out


# ---- HARD: stale generated docs (in-memory regenerate + compare) ----
def _load_script(name: str):
    spec = importlib.util.spec_from_file_location(name, REPO / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _expected_api_docs() -> dict[str, str]:
    g = _load_script("api_docs_gen")
    pages, cov = g.build()
    out = {str((g.API_DIR / f"{pid}.md").relative_to(REPO)): g.render_package_md(pid, es)
           for pid, es in pages.items()}
    out[str((g.API_DIR / "README.md").relative_to(REPO))] = g.render_index_md(pages, cov)
    out[str(g.COV_OUT.relative_to(REPO))] = g.render_coverage_md(cov)
    return out


def _expected_api_reference() -> dict[str, str]:
    g = _load_script("api_reference_gen")
    rows, source = g.collect_routes()
    return {str(g.OUT.relative_to(REPO)): g.render_md(rows, source)}


def _expected_capabilities() -> dict[str, str]:
    g = _load_script("capabilities_gen")
    rows = g.collect()
    return {str(g.OUT.relative_to(REPO)): g.render_md(rows)}


_GENERATORS = [
    {"name": "api_docs_gen", "source_dirs": ["core", "apps", "scripts"], "expected": _expected_api_docs},
    {"name": "api_reference_gen", "source_dirs": ["apps/api"], "expected": _expected_api_reference},
    {"name": "capabilities_gen", "source_dirs": ["core/tools", "core/services"], "expected": _expected_capabilities},
]


def _staged_under(source_dirs: list[str], staged: list[str]) -> bool:
    return any(sp == sd or sp.startswith(sd + "/") for sd in source_dirs for sp in staged)


def stale_generated(only_dirs: list[str] | None = None, repo: Path = REPO) -> list[dict]:
    out: list[dict] = []
    for gen in _GENERATORS:
        if only_dirs is not None and not _staged_under(gen["source_dirs"], only_dirs):
            continue
        try:
            expected = gen["expected"]()
        except Exception as exc:  # a broken checker must not wedge the repo → soft
            out.append({"generator": gen["name"], "kind": "checker_error", "error": str(exc)[:200]})
            continue
        for relpath, content in expected.items():
            f = repo / relpath
            actual = f.read_text(errors="ignore") if f.exists() else ""
            if _norm(actual) != _norm(content):
                out.append({"generator": gen["name"], "kind": "stale", "path": relpath})
    return out


# ---- SOFT: bare code-path mentions in prose that don't resolve ----
def prose_drift(docs_root: Path = DOCS, repo: Path = REPO) -> list[dict]:
    out: list[dict] = []
    skip = repo / "docs" / "reference" / "api"
    for doc in find_docs(docs_root):
        if skip in doc.parents:
            continue
        text = doc.read_text(errors="ignore")
        rel_doc = str(doc.relative_to(repo))
        for m in sorted(set(_PATH_RE.findall(text))):
            if not (repo / m).exists():
                out.append({"doc": rel_doc, "kind": "prose_path", "target": m})
    return out


# ---- SOFT: requirements drift ----
def requirements_drift(repo: Path = REPO) -> list[dict]:
    try:
        g = _load_script("requirements_gen")
        third = set(g.third_party(g.scan(repo)))
    except Exception as exc:
        return [{"kind": "checker_error", "checker": "requirements", "error": str(exc)[:200]}]
    req = repo / "requirements.txt"
    have: set[str] = set()
    if req.exists():
        for line in req.read_text(errors="ignore").splitlines():
            line = line.split("#")[0].strip()
            if line and not line.startswith("-"):
                have.add(re.split(r"[<>=~!\[ ]", line)[0].strip().lower())
    return [{"kind": "requirement_missing", "module": m}
            for m in sorted(third) if m.lower() not in have]


# ---- assembly ----
def staged_paths(repo: Path = REPO) -> list[str]:
    try:
        r = subprocess.run(["git", "-C", str(repo), "diff", "--cached", "--name-only"],
                           capture_output=True, text=True, timeout=15)
        return [ln.strip() for ln in r.stdout.splitlines() if ln.strip()]
    except Exception:
        return []


def hard_drift(staged: list[str] | None = None, repo: Path = REPO) -> list[dict]:
    gen = stale_generated(only_dirs=staged, repo=repo)
    return broken_links() + [x for x in gen if x.get("kind") == "stale"]


def run_check(repo: Path = REPO, staged: list[str] | None = None) -> dict:
    links = broken_links()
    gen = stale_generated(only_dirs=staged, repo=repo)
    hard = links + [x for x in gen if x.get("kind") == "stale"]
    soft = ([x for x in gen if x.get("kind") == "checker_error"]
            + prose_drift(repo=repo) + requirements_drift(repo))
    return {"generated_at": datetime.now(UTC).isoformat(),
            "hard": hard, "soft": soft,
            "counts": {"hard": len(hard), "soft": len(soft)}}


def main() -> int:
    ap = argparse.ArgumentParser(description="docs-drift checker")
    ap.add_argument("--check", action="store_true",
                    help="gate mode: hard families only, staleness scoped to staged files; exit 1 on hard drift")
    args = ap.parse_args()
    if args.check:
        hard = hard_drift(staged=staged_paths())
        if hard:
            print(f"docs-drift: {len(hard)} HARD drift item(s) — regenerate or fix links:")
            for h in hard[:50]:
                print("  -", json.dumps(h, ensure_ascii=False))
            print("Fix: run the relevant generator "
                  "(scripts/api_docs_gen.py / api_reference_gen.py / capabilities_gen.py) "
                  "or repair the broken link, then re-stage.")
            return 1
        print("docs-drift: clean (hard=0)")
        return 0
    rep = run_check()
    REPORT_OUT.write_text(json.dumps(rep, indent=2, ensure_ascii=False) + "\n")
    print(f"docs-drift report → {REPORT_OUT.relative_to(REPO)}: "
          f"hard={rep['counts']['hard']}, soft={rep['counts']['soft']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `conda run -n ai python -m pytest tests/test_docs_drift_check.py -q`
Expected: PASS (3 passed). If `test_real_repo_has_no_hard_drift` fails, the committed generated docs are out of date — run `python scripts/api_docs_gen.py && python scripts/api_reference_gen.py && python scripts/capabilities_gen.py`, commit those, and re-run. (Do NOT weaken the test.)

- [ ] **Step 5: Commit**

```bash
git add scripts/docs_drift_check.py tests/test_docs_drift_check.py
git commit -m "feat(docs): SP5 docs-drift checker engine (broken links + stale generated + soft advisories)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```
Pre-commit hooks must pass. If a hook fails, report the exact failure — do not bypass.

---

### Task 2 (Claude inline): pre-commit hook + report + CONTRIBUTING

- [ ] **Step 1: Add the pre-commit hook.** In `.pre-commit-config.yaml`, under the `repo: local` `hooks:` list, add (mirroring the existing `enforce-test-coverage` block shape):

```yaml
      - id: docs-drift-check
        name: Docs drift (broken links + un-regenerated generated docs)
        entry: /opt/conda/envs/ai/bin/python scripts/docs_drift_check.py --check
        language: system
        pass_filenames: false
        always_run: true
        stages: [pre-commit]
```

- [ ] **Step 2: Generate the first report.**

Run: `conda run -n ai python scripts/docs_drift_check.py`
Expected: writes `docs/drift_report.json`, prints `hard=0, soft=<n>`. If `hard>0`, fix (regenerate the flagged generator or repair the link) before continuing.

- [ ] **Step 3: Update `docs/CONTRIBUTING.md`.** Under the pre-commit gates list, add a fifth gate; and under "Regenerating derived docs", add the drift line. Concretely:
  - In the "Pre-commit gates" section, add: `5. **Docs drift** — blocks a commit whose staged source changes leave a generated doc un-regenerated, or whose docs contain a broken markdown link. Fix by running the relevant generator (see below) or repairing the link. Advisory (non-blocking) drift lands in \`docs/drift_report.json\` and the \`jc docs-drift\` nerve.`
  - In "Regenerating derived docs", append: `python scripts/docs_drift_check.py         # docs/drift_report.json (drift audit; --check gates commits)`

- [ ] **Step 4: Verify the gate works end-to-end.**

Run (temporarily break a link to prove the gate blocks, then restore):
```bash
conda run -n ai python scripts/docs_drift_check.py --check ; echo "exit=$?"
```
Expected: `docs-drift: clean (hard=0)` and `exit=0` on the clean tree.

- [ ] **Step 5: Commit.**

```bash
git add .pre-commit-config.yaml docs/drift_report.json docs/CONTRIBUTING.md
git commit -m "feat(docs): SP5 docs-drift pre-commit gate + first report + CONTRIBUTING

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

- [ ] **Step 6: Push Stage 1.**

```bash
git push
```
No container deploy (pure repo-side).

---

## STAGE 2 — runtime (Central nerve; full suite + container deploy)

### Task 3: `core/services/docs_drift_watchdog.py` + tests

**Files:**
- Create: `core/services/docs_drift_watchdog.py`
- Test: `tests/test_docs_drift_watchdog.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_docs_drift_watchdog.py
import json
from core.services import docs_drift_watchdog as w


def test_read_report_missing_is_empty(tmp_path):
    assert w.read_report(tmp_path / "nope.json") == {}


def test_check_docs_drift_reads_counts(tmp_path):
    rep = tmp_path / "drift_report.json"
    rep.write_text(json.dumps({"counts": {"hard": 2, "soft": 5}, "generated_at": "2026-07-08T00:00:00+00:00"}))
    state = w.check_docs_drift(report_path=rep, repo=tmp_path)
    assert state["hard_count"] == 2 and state["soft_count"] == 5
    assert state["report_present"] is True
    assert state["generated_at"].startswith("2026-07-08")


def test_check_docs_drift_missing_report_safe(tmp_path):
    state = w.check_docs_drift(report_path=tmp_path / "nope.json", repo=tmp_path)
    assert state["hard_count"] == 0 and state["report_present"] is False


def test_build_surface_never_throws():
    surf = w.build_docs_drift_surface()
    assert isinstance(surf, dict) and "hard_count" in surf
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `conda run -n ai python -m pytest tests/test_docs_drift_watchdog.py -q`
Expected: FAIL — module not found.

- [ ] **Step 3: Write the implementation**

```python
# core/services/docs_drift_watchdog.py
"""SP5 docs-drift watchdog — surface docs/drift_report.json to the Central as a docs:drift nerve.

Reads the committed report (never re-runs AST in the hot path), checks whether the report looks
stale relative to the generated docs, and emits a docs:drift timeseries sample + observe trace.
Self-safe: every function returns sensible defaults and never throws."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
REPORT = REPO / "docs" / "drift_report.json"


def read_report(report_path: Path = REPORT) -> dict[str, Any]:
    try:
        if not Path(report_path).exists():
            return {}
        data = json.loads(Path(report_path).read_text(errors="ignore"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _report_stale(report_path: Path = REPORT, repo: Path = REPO) -> bool:
    """Cheap proxy: True if any generated doc under docs/reference is newer than the report
    (i.e. regenerated but the report wasn't re-run). Stats only the small reference tree."""
    try:
        rp = Path(report_path)
        if not rp.exists():
            return True
        rt = rp.stat().st_mtime
        ref = repo / "docs" / "reference"
        if ref.exists():
            for p in ref.rglob("*.md"):
                if p.stat().st_mtime > rt:
                    return True
        return False
    except Exception:
        return False


def check_docs_drift(report_path: Path = REPORT, repo: Path = REPO) -> dict[str, Any]:
    rep = read_report(report_path)
    counts = rep.get("counts") or {}
    try:
        hard = int(counts.get("hard", 0) or 0)
    except Exception:
        hard = 0
    try:
        soft = int(counts.get("soft", 0) or 0)
    except Exception:
        soft = 0
    return {
        "hard_count": hard,
        "soft_count": soft,
        "report_present": bool(rep),
        "report_stale": _report_stale(report_path, repo),
        "generated_at": str(rep.get("generated_at", "")),
    }


def observe_docs_drift() -> dict[str, Any]:
    """Emit the docs:drift signal to Central (timeseries + observe trace). Self-safe."""
    state = check_docs_drift()
    try:
        from core.services.central_timeseries import record
        record("docs", "drift", value=float(state["hard_count"]),
               meta={"soft": state["soft_count"], "report_stale": state["report_stale"],
                     "present": state["report_present"]})
    except Exception:
        pass
    try:
        from core.services.central_core import central
        central().observe({"cluster": "docs", "nerve": "drift", "kind": "observe", **state})
    except Exception:
        pass
    return state


def build_docs_drift_surface() -> dict[str, Any]:
    """Read-only surface for /central/docs-drift. Never throws."""
    try:
        rep = read_report()
        state = check_docs_drift()
        state["status"] = "ok"
        state["top_hard"] = (rep.get("hard") or [])[:5]
        state["top_soft"] = (rep.get("soft") or [])[:5]
        return state
    except Exception:
        return {"status": "unavailable", "hard_count": 0, "soft_count": 0,
                "report_present": False, "report_stale": False, "generated_at": ""}


def _run_producer_tick(**_: Any) -> dict[str, object]:
    state = observe_docs_drift()
    return {"status": "ok", "hard": state["hard_count"], "soft": state["soft_count"]}


def register_docs_drift_producer() -> None:
    """Register the docs-drift observation as a ~5-min cadence producer."""
    from core.services.internal_cadence import ProducerSpec, register_producer
    register_producer(ProducerSpec(
        name="docs_drift_watchdog",
        cooldown_minutes=5,
        visible_grace_minutes=0,
        run_fn=_run_producer_tick,
        priority=10,
    ))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `conda run -n ai python -m pytest tests/test_docs_drift_watchdog.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add core/services/docs_drift_watchdog.py tests/test_docs_drift_watchdog.py
git commit -m "feat(central): SP5 docs-drift watchdog nerve (reads report → docs:drift signal)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4 (Claude inline): route + app registration + cadence wiring + CLI

- [ ] **Step 1: Create the route** `apps/api/jarvis_api/routes/central_docs_drift.py`:

```python
"""Central 'docs-drift' route — docs-drift watchdog surface (owner-view, read-only, self-safe).

SP5: surfaces docs/drift_report.json (hard/soft counts, report freshness, top items) so the
Central and `jc docs-drift` show whether docs have drifted from git+runtime truth."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter(prefix="/central", tags=["central-docs-drift"])


def _require_owner() -> None:
    from apps.api.jarvis_api.routes.central_auth import require_central_owner
    require_central_owner()


@router.get("/docs-drift")
async def get_docs_drift() -> dict:
    """Docs-drift surface: hard/soft counts, report freshness, top drift items. Owner-only."""
    _require_owner()
    try:
        from core.services.docs_drift_watchdog import build_docs_drift_surface
        surf = build_docs_drift_surface()
        if not isinstance(surf, dict):
            surf = {"status": "unavailable"}
    except Exception:
        surf = {"status": "unavailable"}
    surf["ts"] = datetime.now(timezone.utc).isoformat()
    return surf
```

- [ ] **Step 2: Register the router** in `apps/api/jarvis_api/app.py`. Find the block around line 591 where `central_connections` is imported and included, and add the same two lines for the new router:

```python
    from apps.api.jarvis_api.routes import central_docs_drift as _central_docs_drift
    app.include_router(_central_docs_drift.router)
```

- [ ] **Step 3: Wire the cadence producer.** In `core/services/internal_cadence_central_wiring.py`, inside `register_central_wiring_producers()`, add a new self-safe block matching the existing ones (e.g. after the `central_coverage` block):

```python
    try:
        from core.services.docs_drift_watchdog import register_docs_drift_producer
        register_docs_drift_producer()
    except Exception:
        pass
```

- [ ] **Step 4: Add the CLI subcommand.** In `apps/central_cli/central_cli/commands.py`, add to the `_GET_ENDPOINTS` dict:

```python
    "docs-drift": "/central/docs-drift",
```

- [ ] **Step 5: Compile-check + targeted tests.**

Run:
```bash
conda run -n ai python -m compileall core/services/docs_drift_watchdog.py apps/api/jarvis_api/routes/central_docs_drift.py core/services/internal_cadence_central_wiring.py -q
conda run -n ai python -m pytest tests/test_docs_drift_watchdog.py -q
```
Expected: compile OK, tests PASS.

- [ ] **Step 6: Verify the route registers + cadence producer is known (local, no restart).**

Run:
```bash
conda run -n ai python -c "from apps.api.jarvis_api.app import app; print([r.path for r in app.routes if 'docs-drift' in getattr(r,'path','')])"
conda run -n ai python -c "from core.services.docs_drift_watchdog import register_docs_drift_producer; register_docs_drift_producer(); print('producer registered ok')"
```
Expected: first prints `['/central/docs-drift']`; second prints `producer registered ok` (confirms the register call imports and runs cleanly).

- [ ] **Step 7: Commit.**

```bash
git add apps/api/jarvis_api/routes/central_docs_drift.py apps/api/jarvis_api/app.py core/services/internal_cadence_central_wiring.py apps/central_cli/central_cli/commands.py
git commit -m "feat(central): SP5 wire docs-drift route + cadence producer + jc docs-drift

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5 (Claude inline): full suite + deploy + live-verify

- [ ] **Step 1: Full test suite** (this touches runtime, so the ~20-min gate runs).

Run: `conda run -n ai python -m pytest -q -p no:cacheprovider --timeout=45 --timeout-method=signal`
Expected: PASS (known order-sensitive isolation flakes may need a re-run in isolation — see CONTRIBUTING).

- [ ] **Step 2: Push.**

```bash
git push
```

- [ ] **Step 3: Deploy to the container** (`bs@10.0.0.39`). On the container: pull (merge, never overwrite — Jarvis may have committed on container main; see the deploy gotcha memory), verify HEAD, restart BOTH services.

```bash
ssh bs@10.0.0.39 'cd /path/to/jarvis-v2 && git fetch origin && git log --oneline origin/main -1 && (git pull --ff-only origin main || git merge origin/main) && git rev-parse --short HEAD && sudo systemctl restart jarvis-runtime jarvis-api'
```
Expected: HEAD matches the pushed commit; both services restart. (Confirm the repo path on the container first with `ssh bs@10.0.0.39 'ls ~'` / known deploy path.)

- [ ] **Step 4: Live-verify the nerve.**

```bash
ssh bs@10.0.0.39 'systemctl is-active jarvis-runtime jarvis-api'
# Owner-gated surface via jc (runs on the container / owner context):
ssh bs@10.0.0.39 'cd /path/to/jarvis-v2 && conda run -n ai jc docs-drift || conda run -n ai jc raw /central/docs-drift'
```
Expected: both services `active`; the surface returns `{status: ok, hard_count, soft_count, report_stale, generated_at, ...}`. A `docs:drift` timeseries sample appears after the first cadence tick (`jc series` / `jc raw /central/timeseries`).

- [ ] **Step 5: Report** the drift numbers (hard/soft) and confirm the docs programme (SP1–SP5) is complete: the docs are now generated-where-possible, indexed, install-documented, per-function referenced, and drift-guarded.

---

## Self-Review

**Spec coverage:**
- Shared engine `docs_drift_check.py` with `broken_links` (hard), `stale_generated` (hard, in-memory regenerate + change-scoped), `prose_drift` (soft bare-path), `requirements_drift` (soft), `run_check`/`hard_drift`/`main` + `--check` gate + `drift_report.json` → Task 1 ✓.
- Change-scoped staleness via `git diff --cached --name-only` → `staged_paths` + `_staged_under`, used by `--check` (Task 1); full in default mode ✓.
- Date-header normalization (`_norm`) so regeneration diffs are content-only → Task 1, unit-tested ✓.
- Side 1 pre-commit gate → Task 2 hook ✓. CONTRIBUTING documents it → Task 2 Step 3 ✓.
- Side 2 nerve `docs_drift_watchdog.py` (`read_report`, `check_docs_drift`, `observe_docs_drift`, `build_docs_drift_surface`, `register_docs_drift_producer`) reading the report, never AST in hot path → Task 3 ✓.
- `central_timeseries.record("docs","drift",…)` + `central().observe` → Task 3 ✓.
- `/central/docs-drift` owner-gated route + app registration → Task 4 Steps 1–2 ✓.
- Cadence via `ProducerSpec` wired in `internal_cadence_central_wiring.py` → Task 4 Step 3 ✓.
- `jc docs-drift` via `_GET_ENDPOINTS` → Task 4 Step 4 ✓.
- Error handling: checker family that raises → soft `checker_error`, never blocks (`stale_generated`, `requirements_drift`); nerve fully self-safe; route returns `{"status":"unavailable"}` → Tasks 1, 3, 4 ✓.
- Testing: fixtures for `broken_links`, `_norm`, real-repo-no-hard-drift, watchdog counts/missing-report/surface → Tasks 1, 3 ✓.
- Two-stage deploy (Stage 1 repo-only; Stage 2 full suite + container restart both services) → Tasks 2/6, 5 ✓.

**Placeholder scan:** none — full code in Tasks 1 and 3; Tasks 2/4/5 are concrete wire/verify/deploy steps. The only intentional variable is the container repo path in Task 5 (`/path/to/jarvis-v2`) — resolve it live from the known deploy path before running.

**Type consistency:** `run_check → {generated_at, hard:[...], soft:[...], counts:{hard,soft}}`; `check_docs_drift → {hard_count, soft_count, report_present, report_stale, generated_at}`; `build_docs_drift_surface` extends that dict with `status`/`top_hard`/`top_soft`/`ts`. `stale_generated` items use `kind in {"stale","checker_error"}`; `broken_links` items `kind="link"`. `register_docs_drift_producer` uses `run_fn=_run_producer_tick(**_) -> dict`. Names identical across engine, nerve, route, tests.
