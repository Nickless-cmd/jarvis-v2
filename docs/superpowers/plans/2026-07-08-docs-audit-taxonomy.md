# Docs SP1 — Audit & Taxonomy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Classify all 423 docs vs git+runtime into færdig/forældet/droppet + a mangler gap-list, producing a manifest, frontmatter stamps, and an archive of dead weight.

**Architecture:** A regenerable static auditor (`scripts/docs_audit.py`, mirrors `capability_audit.py`) computes per-doc signals and auto-classifies the clear-cut; a multi-agent workflow triages only the ambiguous remainder; a synthesis step writes the manifest, stamps frontmatter, and archives. Pure logic is unit-tested; the workflow + mass-apply run inline.

**Tech Stack:** Python 3.11 (stdlib only — no yaml dep), git, pytest, `conda activate ai`.

**Execution note:** Task 1 (the auditor + tests) → fresh **haiku** subagent. Tasks 2–4 (run auditor, run workflow, apply manifest+stamps+archive) → **Claude inline**. Task 5 = gate + commit.

---

## File Structure

- **New** `scripts/docs_audit.py` — all pure functions (reference extraction, liveness, superseded detection, shipped-check, classify, frontmatter stamp, manifest render, gap-list) + `audit()`/`main()`.
- **New** `tests/test_docs_audit.py` — unit tests on fixtures.
- **Generated** `docs/docs_audit_raw.json` (Phase 1), `docs/DOCS_MANIFEST.json` + `docs/DOCS_MANIFEST.md` (Phase 3).
- **Moved** forældet/droppet docs → `docs/_archive/`.

---

## Task 1: `scripts/docs_audit.py` + tests

**Files:**
- Create: `scripts/docs_audit.py`
- Test: `tests/test_docs_audit.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_docs_audit.py
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "docs_audit", Path(__file__).resolve().parents[1] / "scripts" / "docs_audit.py")
da = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(da)


def test_extract_references_paths_and_symbols():
    text = "See `core/services/foo.py` and call `do_the_thing` in apps/api/x.py"
    refs = da.extract_references(text)
    assert "core/services/foo.py" in refs["paths"]
    assert "apps/api/x.py" in refs["paths"]
    assert "do_the_thing" in refs["symbols"]


def test_liveness_resolved_ratio(tmp_path):
    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "alive.py").write_text("x")
    refs = {"paths": ["core/alive.py", "core/dead.py"]}
    live = da.liveness(refs, repo_root=tmp_path)
    assert live["resolved"] == 1 and live["total"] == 2 and live["ratio"] == 0.5


def test_liveness_no_paths():
    assert da.liveness({"paths": []})["ratio"] is None


def test_detect_superseded_newer_wins():
    docs = [
        {"path": "old.md", "title": "arkitektur", "headings": {"a", "b", "c"}, "days": 200},
        {"path": "new.md", "title": "arkitektur", "headings": {"a", "b", "c"}, "days": 5},
    ]
    sup = da.detect_superseded(docs)
    assert sup.get("old.md") == "new.md" and "new.md" not in sup


def test_classify_all_refs_dead_old_is_foraeldet():
    cat, conf, basis = da.classify_heuristic(
        path="x.md", refs={"paths": ["core/gone.py"]}, live={"resolved": 0, "total": 1, "ratio": 0.0},
        days=200, superseded_by=None, is_superpowers=False, shipped=False)
    assert cat == "forældet"


def test_classify_recent_alive_is_faerdig():
    cat, _c, _b = da.classify_heuristic(
        path="x.md", refs={"paths": ["core/a.py"]}, live={"resolved": 1, "total": 1, "ratio": 1.0},
        days=3, superseded_by=None, is_superpowers=False, shipped=False)
    assert cat == "færdig"


def test_classify_superseded_is_droppet():
    cat, _c, _b = da.classify_heuristic(
        path="x.md", refs={"paths": []}, live={"ratio": None}, days=10,
        superseded_by="y.md", is_superpowers=False, shipped=False)
    assert cat == "droppet"


def test_classify_superpowers_shipped_is_faerdig():
    cat, _c, _b = da.classify_heuristic(
        path="p.md", refs={"paths": ["core/x.py"]}, live={"ratio": 1.0, "resolved": 1, "total": 1},
        days=2, superseded_by=None, is_superpowers=True, shipped=True)
    assert cat == "færdig"


def test_classify_ambiguous_is_needs_review():
    cat, _c, _b = da.classify_heuristic(
        path="x.md", refs={"paths": []}, live={"ratio": None}, days=3,
        superseded_by=None, is_superpowers=False, shipped=False)
    assert cat == "needs_review"


def test_stamp_frontmatter_prepends_when_absent():
    out = da.stamp_frontmatter("# Title\n\nbody", {"status": "færdig", "audited": "2026-07-08"})
    assert out.startswith("---\n") and "status: færdig" in out and "# Title" in out


def test_stamp_frontmatter_idempotent_and_preserves_other_keys():
    src = "---\nname: keepme\nstatus: old\n---\n# Title\n"
    once = da.stamp_frontmatter(src, {"status": "forældet"})
    twice = da.stamp_frontmatter(once, {"status": "forældet"})
    assert once == twice                 # idempotent
    assert "name: keepme" in once        # unrelated key preserved
    assert "status: forældet" in once and "status: old" not in once


def test_render_manifest_md_has_rows():
    entries = [{"path": "a.md", "category": "færdig", "basis": "b", "superseded_by": None}]
    md = da.render_manifest_md(entries)
    assert "a.md" in md and "færdig" in md
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `conda run -n ai python -m pytest tests/test_docs_audit.py -q`
Expected: FAIL — module/functions not defined.

- [ ] **Step 3: Write the implementation**

```python
# scripts/docs_audit.py
"""SP1 docs auditor — classify docs/*.md against git+runtime truth. Regenerable, static
(mirrors scripts/capability_audit.py). Stdlib only. Writes docs/docs_audit_raw.json."""
from __future__ import annotations

import json
import re
import subprocess
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_ROOT = REPO_ROOT / "docs"

_PATH_RE = re.compile(r"(?:core|apps|scripts)/[\w./-]+\.(?:py|ts|tsx|md|json)")
_SYMBOL_RE = re.compile(r"`([a-zA-Z_][a-zA-Z0-9_]{3,})`")
_STALE_DAYS = 120
_SUBSYSTEMS = ["core/services", "core/runtime", "core/tools", "core/context",
               "apps/api", "apps/ui", "scripts"]


def find_docs(root: Path = DOCS_ROOT) -> list[Path]:
    return sorted(p for p in root.rglob("*.md") if "_archive" not in p.parts)


def extract_references(text: str) -> dict:
    paths = sorted(set(_PATH_RE.findall(text)))
    symbols = sorted(set(_SYMBOL_RE.findall(text)))
    return {"paths": paths, "symbols": symbols}


def liveness(refs: dict, repo_root: Path = REPO_ROOT) -> dict:
    paths = refs.get("paths") or []
    if not paths:
        return {"resolved": 0, "total": 0, "ratio": None}
    resolved = sum(1 for p in paths if (repo_root / p).exists())
    return {"resolved": resolved, "total": len(paths), "ratio": round(resolved / len(paths), 3)}


def git_last_touch(path: Path, repo_root: Path = REPO_ROOT) -> tuple[int | None, str]:
    try:
        out = subprocess.run(["git", "log", "-1", "--format=%cI", "--", str(path)],
                             capture_output=True, text=True, cwd=repo_root, timeout=10)
        iso = out.stdout.strip()
        if not iso:
            return None, ""
        dt = datetime.fromisoformat(iso)
        return (datetime.now(dt.tzinfo) - dt).days, iso
    except Exception:
        return None, ""


def title_and_headings(text: str) -> tuple[str, set]:
    title, headings = "", set()
    for ln in text.splitlines():
        s = ln.strip()
        if s.startswith("#"):
            h = s.lstrip("#").strip().lower()
            if not title:
                title = h
            if h:
                headings.add(h)
    return title, headings


def detect_superseded(docs: list[dict]) -> dict:
    """docs: [{path,title,headings,days}]. Older doc is superseded by a NEWER doc that shares the
    same title or >0.6 heading Jaccard overlap."""
    result: dict = {}
    for a in docs:
        for b in docs:
            if a["path"] == b["path"] or not a["headings"] or not b["headings"]:
                continue
            same_title = bool(a["title"]) and a["title"] == b["title"]
            union = a["headings"] | b["headings"]
            overlap = len(a["headings"] & b["headings"]) / max(1, len(union))
            newer = (b["days"] is not None and a["days"] is not None and b["days"] < a["days"])
            if (same_title or overlap > 0.6) and newer:
                result[a["path"]] = b["path"]
                break
    return result


def feature_shipped(refs: dict, repo_root: Path = REPO_ROOT) -> bool:
    """A superpowers spec/plan 'shipped' if any referenced path exists, or a key symbol is in the tree."""
    if any((repo_root / p).exists() for p in refs.get("paths") or []):
        return True
    for sym in (refs.get("symbols") or [])[:8]:
        try:
            out = subprocess.run(["git", "grep", "-lE", re.escape(sym), "--", "core", "apps", "scripts"],
                                 capture_output=True, text=True, cwd=repo_root, timeout=10)
            if out.stdout.strip():
                return True
        except Exception:
            pass
    return False


def classify_heuristic(*, path: str, refs: dict, live: dict, days: int | None,
                       superseded_by: str | None, is_superpowers: bool,
                       shipped: bool) -> tuple[str, float, str]:
    ratio = live.get("ratio")
    old = days is not None and days > _STALE_DAYS
    if superseded_by:
        return "droppet", 0.8, f"superseded by {superseded_by}"
    if is_superpowers:
        if shipped:
            return "færdig", 0.75, "superpowers artifact shipped (refs/symbols present in tree)"
        if old:
            return "droppet", 0.6, "superpowers artifact, no trace in tree + old"
        return "needs_review", 0.0, "superpowers artifact, shipped-status unclear"
    if ratio is not None:
        if ratio == 0.0 and old:
            return "forældet", 0.8, f"all {live['total']} code refs dead + {days}d old"
        if ratio >= 0.9 and not old:
            return "færdig", 0.7, f"{live['resolved']}/{live['total']} refs alive, {days}d old"
    return "needs_review", 0.0, "ambiguous signals — needs read"


_FM_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def _yaml_val(v) -> str:
    s = str(v)
    return f'"{s}"' if (":" in s or "#" in s or s == "") else s


def stamp_frontmatter(text: str, fields: dict) -> str:
    """Idempotent, surgical YAML frontmatter merge: replaces only the given keys, preserves the rest
    verbatim (no lossy parse). Prepends a block when none exists. Stdlib only."""
    new_lines = [f"{k}: {_yaml_val(v)}" for k, v in fields.items()]
    m = _FM_RE.match(text)
    if m:
        keys = set(fields)
        kept = [ln for ln in m.group(1).splitlines()
                if ln.split(":", 1)[0].strip() not in keys]
        block = "\n".join(kept + new_lines)
        return f"---\n{block}\n---\n" + text[m.end():]
    return "---\n" + "\n".join(new_lines) + "\n---\n" + text


def render_manifest_md(entries: list[dict]) -> str:
    by_cat = Counter(e["category"] for e in entries)
    lines = ["# DOCS_MANIFEST", "",
             f"Generated {datetime.now(UTC).date().isoformat()} · {len(entries)} docs · {dict(by_cat)}",
             "", "| Path | Category | Basis | Superseded by |", "|---|---|---|---|"]
    for e in sorted(entries, key=lambda x: (x["category"], x["path"])):
        lines.append(f"| `{e['path']}` | {e['category']} | {e.get('basis','')} | {e.get('superseded_by') or ''} |")
    return "\n".join(lines) + "\n"


def build_gap_list(entries: list[dict]) -> list[dict]:
    """Coarse subsystem coverage: which _SUBSYSTEMS have NO færdig doc referencing them."""
    covered = set()
    for e in entries:
        if e["category"] != "færdig":
            continue
        for sub in _SUBSYSTEMS:
            if any(str(p).startswith(sub) for p in e.get("ref_paths") or []):
                covered.add(sub)
    return [{"subsystem": s, "covered": s in covered} for s in _SUBSYSTEMS]


def audit() -> dict:
    metas = []
    for p in find_docs():
        text = p.read_text(errors="ignore")
        title, headings = title_and_headings(text)
        days, iso = git_last_touch(p)
        refs = extract_references(text)
        metas.append({"path": str(p.relative_to(REPO_ROOT)), "title": title, "headings": headings,
                      "days": days, "iso": iso, "refs": refs,
                      "is_sp": "superpowers" in p.parts})
    superseded = detect_superseded([{"path": m["path"], "title": m["title"],
                                     "headings": m["headings"], "days": m["days"]} for m in metas])
    entries = []
    for m in metas:
        live = liveness(m["refs"])
        shipped = feature_shipped(m["refs"]) if m["is_sp"] else False
        cat, conf, basis = classify_heuristic(
            path=m["path"], refs=m["refs"], live=live, days=m["days"],
            superseded_by=superseded.get(m["path"]), is_superpowers=m["is_sp"], shipped=shipped)
        entries.append({"path": m["path"], "category": cat, "confidence": conf, "basis": basis,
                        "days": m["days"], "liveness": live, "superseded_by": superseded.get(m["path"]),
                        "ref_paths": m["refs"]["paths"]})
    return {"generated": datetime.now(UTC).isoformat(), "count": len(entries),
            "by_category": dict(Counter(e["category"] for e in entries)),
            "gap_list": build_gap_list(entries), "docs": entries}


def main() -> int:
    result = audit()
    out = DOCS_ROOT / "docs_audit_raw.json"
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"docs_audit: {result['count']} docs → {result['by_category']}")
    print(f"gaps: {[g['subsystem'] for g in result['gap_list'] if not g['covered']]}")
    print(f"written {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `conda run -n ai python -m pytest tests/test_docs_audit.py -q`
Expected: PASS (12 passed).

- [ ] **Step 5: Commit**

```bash
git add scripts/docs_audit.py tests/test_docs_audit.py
git commit -m "feat(docs): SP1 docs auditor — heuristic classification vs git+runtime"
```

---

## Task 2 (Claude inline): run Phase 1 auditor + review the split

- [ ] **Step 1: Run the auditor over all 423 docs**

Run: `conda run -n ai python scripts/docs_audit.py`
Expected: prints the category counts (e.g. `{'færdig': N, 'forældet': N, 'droppet': N, 'needs_review': N}`) + gap subsystems + writes `docs/docs_audit_raw.json`.

- [ ] **Step 2: Sanity-check the auto-classification**

Read `docs/docs_audit_raw.json`. Spot-check ~10 entries across categories: does each auto-classification's `basis` hold up (a `forældet` really has dead refs; a `droppet` superpowers plan really has no trace)? Note the `needs_review` count — that's the workflow's input for Task 3. If a whole category looks systematically wrong, fix `classify_heuristic` thresholds in `scripts/docs_audit.py`, re-run Task 1 tests + re-run the auditor before proceeding.

- [ ] **Step 3: Commit the raw audit (intermediate artifact)**

```bash
git add docs/docs_audit_raw.json
git commit -m "chore(docs): SP1 phase-1 raw audit output"
```

---

## Task 3 (Claude inline): Phase 2 workflow — triage the `needs_review` docs

- [ ] **Step 1: Extract the needs_review list**

Run: `conda run -n ai python -c "import json; d=json.load(open('docs/docs_audit_raw.json')); nr=[e['path'] for e in d['docs'] if e['category']=='needs_review']; print(len(nr)); import pathlib; pathlib.Path('docs/_needs_review.json').write_text(json.dumps(nr))"`
Note the count.

- [ ] **Step 2: Run the triage workflow (opt-in orchestration)**

Author and run a Workflow that pipelines over the `needs_review` paths (chunked if very many). Each agent receives ONE doc path + reads the doc + checks its concrete claims against the actual code/git (does referenced code exist? did the described feature ship? is it superseded by a newer doc?), and returns a structured verdict via schema:

```
{path, category: "færdig"|"forældet"|"droppet", summary: "<=20 words",
 ground_truth_basis: "<what was checked>", action: "keep"|"archive", superseded_by: string|null}
```

Collect verdicts → write `docs/_triage_verdicts.json`. (Workflow authored inline; if the needs_review count is small (<15), do it as a handful of Explore-agent reads instead of a full Workflow.)

- [ ] **Step 3: Commit the verdicts (intermediate artifact)**

```bash
git add docs/_triage_verdicts.json
git commit -m "chore(docs): SP1 phase-2 triage verdicts for needs_review docs"
```

---

## Task 4 (Claude inline): Phase 3 — manifest, frontmatter stamp, archive, gap-list

- [ ] **Step 1: Merge into the authoritative manifest**

Write a short inline merge: start from `docs_audit_raw.json`; for each `needs_review` entry, overwrite its category/basis/superseded_by with the Phase-2 verdict from `_triage_verdicts.json`. Produce the final entry list. Write `docs/DOCS_MANIFEST.json` (the merged list + `gap_list`) and `docs/DOCS_MANIFEST.md` via `docs_audit.render_manifest_md(entries)`.

- [ ] **Step 2: Stamp frontmatter on every classified doc (idempotent)**

For each entry, read the file, apply `docs_audit.stamp_frontmatter(text, {"status": category, "audited": "2026-07-08", "ground_truth": basis, ...("superseded_by": x if present)})`, write it back. This is a mechanical mass edit across ~423 files using the tested, surgical merge (existing keys preserved). Verify a couple by eye (one with prior frontmatter, one without).

- [ ] **Step 3: Archive forældet/droppet**

For each entry with category in (`forældet`, `droppet`) that is not already under `docs/_archive/`: `git mv <path> docs/_archive/<path-with-docs-prefix-stripped>` (preserve subpath, create dirs). Record old→new in the manifest. Re-render `DOCS_MANIFEST.md` with the post-move paths.

- [ ] **Step 4: Verify manifest ↔ filesystem consistency**

Run a check: every `færdig` path in the manifest exists at its stated location; every `forældet`/`droppet` path now lives under `docs/_archive/`; the `mangler` gap-list lists the uncovered subsystems. Fix any mismatch.

- [ ] **Step 5: Commit**

```bash
git add -A docs/
git commit -m "feat(docs): SP1 manifest + frontmatter stamps + archive dead docs

DOCS_MANIFEST.{md,json}: all 423 docs classified færdig/forældet/droppet vs git+runtime,
+ mangler gap-list. Frontmatter stamped on every doc; forældet/droppet moved to docs/_archive/."
```

---

## Task 5: gate + push

- [ ] **Step 1: Auditor tests**

Run: `conda run -n ai python -m pytest tests/test_docs_audit.py -q`
Expected: PASS.

- [ ] **Step 2: Full-suite gate (~20 min)**

Run: `conda run -n ai python -m pytest -q -p no:cacheprovider --timeout=45 --timeout-method=signal`
Expected: PASS. Known rotating isolation flakes (re-run alone to confirm): subagent_ecology, forgetting_engine, meta_learning, heartbeat_self_knowledge, workspace_bootstrap, causal_quality, db_user_temperature.

- [ ] **Step 3: Push**

```bash
git push
```
Expected: pre-push smoke passes.

- [ ] **Step 4: No container deploy** — this is a repo-docs change only (runtime code unaffected). The container will pick up docs on its next ordinary pull; no service restart needed.

- [ ] **Step 5: Report** the final split (færdig/forældet/droppet counts + gap-list) to Bjørn, and note SP2 (canonical structure + index) is the next sub-project.

---

## Self-Review

**Spec coverage:** heuristic auditor with ref-liveness/git-recency/superseded/shipped signals (Task 1) ✓; auto-classify clear-cut + needs_review (Task 1 `classify_heuristic`, run Task 2) ✓; workflow over doubtful only (Task 3) ✓; manifest md+json (Task 1 render + Task 4) ✓; idempotent frontmatter stamp preserving keys (Task 1 `stamp_frontmatter` + Task 4) ✓; archive forældet/droppet (Task 4) ✓; mangler gap-list (Task 1 `build_gap_list` + Task 4) ✓; ground-truth basis on every entry (carried in `basis`/`ground_truth_basis`) ✓; exactly four categories ✓.

**Placeholder scan:** none — the auditor is complete code; Tasks 2–4 inline steps describe concrete commands/merges (the workflow is authored at execution per the spec, which is an explicit process step not a code placeholder).

**Type consistency:** `extract_references→{paths,symbols}`, `liveness→{resolved,total,ratio}`, `classify_heuristic(*, path, refs, live, days, superseded_by, is_superpowers, shipped)→(cat,conf,basis)`, `stamp_frontmatter(text, fields)→str`, `render_manifest_md(entries)→str`, `build_gap_list(entries)→list` — signatures identical across the script, tests, and the Task-4 apply steps. Entry dict keys (`path`/`category`/`basis`/`superseded_by`/`ref_paths`) consistent between `audit()`, `render_manifest_md`, and `build_gap_list`.
```
