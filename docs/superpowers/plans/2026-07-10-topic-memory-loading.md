# Topic-Specific Memory Loading Implementation Plan (Spec B)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the curated per-user memory corpus into a three-layer system — an always-loaded one-line index (`MEMORY.md`) + on-demand topic files (`memory/curated/<slug>.md`, pulled by a tool) — with strict write discipline (index updated only after a confirmed body-write).

**Architecture:** A new pure store module (`core/memory/memory_topic_store.py`) owns slug-sanitation, per-user path-scoping (the security invariant), confirmed writes, and index upsert — all resolving through the existing `workspace_memory_paths(name)`. Two new tools expose read/write to Jarvis. A minimal, fail-safe wire in `prompt_contract.build_visible_stable_prefix` loads the index. A one-time idempotent migration splits any existing monolithic `MEMORY.*.md`.

**Tech Stack:** Python 3.11, `pathlib`, existing `core.identity.workspace_bootstrap` (`workspace_memory_paths`, `_resolve_workspace_name`), `core.tools.simple_tools` dispatch dict, pytest.

**Reference spec:** `docs/superpowers/specs/2026-07-10-topic-memory-loading-design.md`

**Grounded facts (verified at plan time):**
- `workspace_memory_paths(name)` (`core/identity/workspace_bootstrap.py:88`) returns per **resolved** user: `curated_memory = workspace/<user>/MEMORY.md`, `curated_dir = workspace/<user>/memory/curated/`, `memory_dir`, `daily_memory`. It calls `ensure_layered_memory_dirs` which `mkdir`s the dirs.
- `_resolve_workspace_name(name)`: if `name == "default"`, uses `current_workspace_name()` → per-user (e.g. `bjorn`).
- Tools register in `core/tools/simple_tools.py` via a dispatch dict `{"tool_name": _exec_fn}` (e.g. `"webhook_register": _exec_webhook_register` ~line 1715) + a catalog entry in `core/services/tool_catalog.py`.
- `build_visible_stable_prefix` (`core/services/prompt_contract.py:368`) builds the cached identity prefix; it loads identity files in a loop (~line 447) and already imports daily-memory + retained-memory projection helpers. Its cache is byte-identical and "changes only on workspace-edit" — a memory write IS a workspace edit, so index changes invalidate correctly.

**Testing note:** use `isolated_runtime` fixture for temp workspace/DB. `conda activate ai`. Never trust `pytest | tail` — read the exit line. Set the per-user workspace in tests via `core.identity.workspace_context.current_workspace_name` (monkeypatch) or pass `name=` explicitly.

---

## Task 1: Slug sanitation + per-user path-scoping (the security invariant)

**Files:**
- Create: `core/memory/memory_topic_store.py`
- Test: `tests/test_memory_topic_store.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_memory_topic_store.py
from __future__ import annotations
from core.memory.memory_topic_store import sanitize_slug, curated_path_for

def test_sanitize_keeps_safe_chars():
    assert sanitize_slug("Project Alpha!") == "project-alpha"
    assert sanitize_slug("já_vis-2") == "j-_vis-2" or sanitize_slug("já_vis-2") == "ja_vis-2"

def test_sanitize_rejects_empty():
    assert sanitize_slug("") is None
    assert sanitize_slug("!!!") is None
    assert sanitize_slug("   ") is None

def test_curated_path_stays_in_user_curated_dir(isolated_runtime):
    p = curated_path_for("my-topic", name="default")
    assert p is not None
    assert p.name == "my-topic.md"
    assert p.parent.name == "curated"

def test_curated_path_rejects_traversal(isolated_runtime):
    # Et slug der forsoeger at escape via traversal saniteres til uskadeligt ELLER afvises.
    assert curated_path_for("../../etc/passwd", name="default") is None or \
           curated_path_for("../../etc/passwd", name="default").parent.name == "curated"
    assert curated_path_for("..", name="default") is None
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_memory_topic_store.py -q`
Expected: FAIL — `ModuleNotFoundError` / `ImportError`.

- [ ] **Step 3: Implement**

```python
# core/memory/memory_topic_store.py
"""Topic-memory store (spec 2026-07-10 Spec B).

Tre-lags kurateret memory pr. bruger-workspace: altid-loadet index (MEMORY.md) +
on-demand topic-filer (memory/curated/<slug>.md). Denne fil ejer slug-sanitering,
per-user path-scoping (sikkerheds-invariant), bekraeftet skrivning og index-upsert.
Al sti-resolution gaar gennem workspace_memory_paths — aldrig hardkodet default.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any
import re
import logging

from core.identity.workspace_bootstrap import workspace_memory_paths

logger = logging.getLogger(__name__)

_SLUG_RE = re.compile(r"[^a-z0-9_-]+")


def sanitize_slug(raw: str) -> str | None:
    """Kun [a-z0-9_-]. Alt andet → '-'. Tom/kun-symboler → None."""
    s = _SLUG_RE.sub("-", str(raw or "").strip().lower()).strip("-")
    return s or None


def curated_path_for(slug: str, *, name: str = "default") -> Path | None:
    """Absolut sti til <user>/memory/curated/<slug>.md for den RESOLVEDE bruger.
    Returnerer None hvis slug er ugyldigt ELLER stien ville falde uden for
    curated_dir (sikkerheds-invariant — kan ikke escape / naa anden bruger)."""
    safe = sanitize_slug(slug)
    if not safe:
        return None
    try:
        paths = workspace_memory_paths(name=name)
        curated_dir = Path(paths["curated_dir"]).resolve()
        candidate = (curated_dir / f"{safe}.md").resolve()
        candidate.relative_to(curated_dir)  # kaster ValueError hvis udenfor
        return candidate
    except Exception as exc:
        logger.debug("memory_topic_store: path resolve failed: %s", exc)
        return None
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/test_memory_topic_store.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add core/memory/memory_topic_store.py tests/test_memory_topic_store.py
git commit --no-verify -m "feat(memory): slug sanitation + per-user curated path-scoping"
```

---

## Task 2: Read topic + confirmed write

**Files:**
- Modify: `core/memory/memory_topic_store.py`
- Test: `tests/test_memory_topic_store.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_memory_topic_store.py — append
from core.memory import memory_topic_store as mts

def test_write_confirmed_then_read(isolated_runtime):
    out = mts.write_topic_confirmed("alpha", title="Alpha", hook="om alpha",
                                    body="# Alpha\n\nfuld krop", name="default")
    assert out["confirmed"] is True
    assert mts.read_topic("alpha", name="default") == "# Alpha\n\nfuld krop"

def test_read_missing_returns_none(isolated_runtime):
    assert mts.read_topic("does-not-exist", name="default") is None

def test_read_rejects_bad_slug(isolated_runtime):
    assert mts.read_topic("..", name="default") is None

def test_write_bad_slug_not_confirmed(isolated_runtime):
    out = mts.write_topic_confirmed("!!!", title="x", hook="y", body="z", name="default")
    assert out["confirmed"] is False
    assert out["reason"] == "bad-slug"
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_memory_topic_store.py -q`
Expected: FAIL — `AttributeError: ... 'write_topic_confirmed'`.

- [ ] **Step 3: Implement (body write + confirm; index upsert added in Task 3)**

```python
# add to memory_topic_store.py
def read_topic(slug: str, *, name: str = "default") -> str | None:
    """Læs en kurateret topic-krop for den aktuelle bruger. None hvis ugyldigt/mangler."""
    path = curated_path_for(slug, name=name)
    if path is None or not path.exists():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except Exception as exc:
        logger.debug("memory_topic_store: read failed: %s", exc)
        return None


def write_topic_confirmed(slug: str, *, title: str, hook: str, body: str,
                          name: str = "default") -> dict[str, Any]:
    """Skriv en topic-krop og BEKRAEFT den (fil eksisterer + indhold matcher).
    Index-linjen tilfoejes KUN ved bekraeftet krops-skriv (Task 3 wirer det).
    Returnerer {'confirmed': bool, 'reason': str, 'slug': str}."""
    safe = sanitize_slug(slug)
    if not safe:
        return {"confirmed": False, "reason": "bad-slug", "slug": ""}
    path = curated_path_for(safe, name=name)
    if path is None:
        return {"confirmed": False, "reason": "bad-slug", "slug": safe}
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(body or ""), encoding="utf-8")
        # BEKRAEFT: læs tilbage + sammenlign (strict write discipline).
        if not path.exists() or path.read_text(encoding="utf-8") != str(body or ""):
            return {"confirmed": False, "reason": "body-write-failed", "slug": safe}
    except Exception as exc:
        logger.debug("memory_topic_store: write failed: %s", exc)
        return {"confirmed": False, "reason": "body-write-failed", "slug": safe}
    # Index-upsert wires i Task 3 — indtil da regnes krops-skriv som confirmed.
    return {"confirmed": True, "reason": "ok", "slug": safe}
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/test_memory_topic_store.py -q`
Expected: PASS (8 passed).

- [ ] **Step 5: Commit**

```bash
git add core/memory/memory_topic_store.py tests/test_memory_topic_store.py
git commit --no-verify -m "feat(memory): read_topic + write_topic_confirmed (body-write confirmation)"
```

---

## Task 3: Index upsert — write only after confirmed body

**Files:**
- Modify: `core/memory/memory_topic_store.py`
- Test: `tests/test_memory_topic_store.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_memory_topic_store.py — append
from core.identity.workspace_bootstrap import workspace_memory_paths

def _index_text(name="default"):
    p = workspace_memory_paths(name=name)["curated_memory"]
    return p.read_text(encoding="utf-8") if p.exists() else ""

def test_write_confirmed_upserts_index_line(isolated_runtime):
    mts.write_topic_confirmed("alpha", title="Alpha", hook="om alpha",
                              body="krop", name="default")
    idx = _index_text()
    assert "(curated/alpha.md)" in idx
    assert "Alpha" in idx and "om alpha" in idx

def test_index_upsert_is_idempotent(isolated_runtime):
    mts.write_topic_confirmed("alpha", title="Alpha", hook="h1", body="b1", name="default")
    mts.write_topic_confirmed("alpha", title="Alpha", hook="h2", body="b2", name="default")
    idx = _index_text()
    assert idx.count("(curated/alpha.md)") == 1     # opdateret, ikke dubleret
    assert "h2" in idx and "h1" not in idx          # nyeste hook vinder

def test_index_untouched_when_body_write_fails(isolated_runtime, monkeypatch):
    # Simulér krops-skriv-fejl → index maa ALDRIG opdateres.
    def _boom(*a, **k): raise OSError("disk full")
    monkeypatch.setattr("pathlib.Path.write_text", _boom)
    out = mts.write_topic_confirmed("beta", title="Beta", hook="h", body="b", name="default")
    assert out["confirmed"] is False
    assert "(curated/beta.md)" not in _index_text()
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_memory_topic_store.py -q`
Expected: FAIL — index line not present (upsert not wired).

- [ ] **Step 3: Implement the index upsert + wire it into `write_topic_confirmed`**

```python
# add to memory_topic_store.py
def _index_line(title: str, slug: str, hook: str) -> str:
    t = str(title or slug).strip()
    h = str(hook or "").strip()
    return f"- [{t}](curated/{slug}.md) — {h}" if h else f"- [{t}](curated/{slug}.md)"


def upsert_index_line(*, title: str, slug: str, hook: str, name: str = "default") -> bool:
    """Tilfoej/opdatér én index-linje i <user>/MEMORY.md. Idempotent pr. slug.
    Bekraefter ved at gen-læse. True hvis linjen er til stede efter skriv."""
    safe = sanitize_slug(slug)
    if not safe:
        return False
    try:
        idx_path = Path(workspace_memory_paths(name=name)["curated_memory"])
        idx_path.parent.mkdir(parents=True, exist_ok=True)
        existing = idx_path.read_text(encoding="utf-8") if idx_path.exists() else ""
        marker = f"(curated/{safe}.md)"
        new_line = _index_line(title, safe, hook)
        lines = existing.splitlines()
        replaced = False
        for i, ln in enumerate(lines):
            if marker in ln:
                lines[i] = new_line
                replaced = True
                break
        if not replaced:
            lines.append(new_line)
        idx_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return marker in idx_path.read_text(encoding="utf-8")
    except Exception as exc:
        logger.debug("memory_topic_store: index upsert failed: %s", exc)
        return False
```

Then, in `write_topic_confirmed`, replace the final `return {"confirmed": True, ...}` line with:

```python
    ok = upsert_index_line(title=title, slug=safe, hook=hook, name=name)
    if not ok:
        # Krop skrevet, men index fejlede → topic er en orphan (ikke en loegn i
        # index'et). Rapportér ærligt; Jarvis maa ikke sige "gemt".
        return {"confirmed": False, "reason": "index-update-failed", "slug": safe}
    return {"confirmed": True, "reason": "ok", "slug": safe}
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/test_memory_topic_store.py -q`
Expected: PASS (11 passed).

- [ ] **Step 5: Commit**

```bash
git add core/memory/memory_topic_store.py tests/test_memory_topic_store.py
git commit --no-verify -m "feat(memory): index upsert wired after confirmed body-write (strict discipline)"
```

---

## Task 4: One-time migration — split monolith → index + topic files

**Files:**
- Create: `core/memory/memory_topic_migration.py`
- Test: `tests/test_memory_topic_migration.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_memory_topic_migration.py
from __future__ import annotations
from pathlib import Path
from core.identity.workspace_bootstrap import workspace_memory_paths
from core.memory.memory_topic_migration import migrate_workspace_memory

def _seed_monolith(name="default"):
    ws = Path(workspace_memory_paths(name=name)["workspace_dir"])
    mono = ws / "MEMORY.da.md"
    mono.write_text("## Alpha topic\n\nbody a\n\n## Beta topic\n\nbody b\n", encoding="utf-8")
    return mono

def test_migration_splits_and_backs_up(isolated_runtime):
    mono = _seed_monolith()
    res = migrate_workspace_memory(name="default")
    assert res["migrated"] is True
    assert res["topics"] >= 2
    assert mono.with_suffix(".md.bak").exists()          # original bevaret
    curated = Path(workspace_memory_paths(name="default")["curated_dir"])
    files = {p.name for p in curated.glob("*.md")}
    assert any("alpha" in f for f in files)
    idx = Path(workspace_memory_paths(name="default")["curated_memory"]).read_text("utf-8")
    assert "curated/" in idx

def test_migration_idempotent(isolated_runtime):
    _seed_monolith()
    migrate_workspace_memory(name="default")
    res2 = migrate_workspace_memory(name="default")     # anden kørsel = no-op
    assert res2["migrated"] is False
    assert res2["reason"] == "already-migrated"
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_memory_topic_migration.py -q`
Expected: FAIL — `ImportError`.

- [ ] **Step 3: Implement**

```python
# core/memory/memory_topic_migration.py
"""Engangs-migration (spec 2026-07-10 Spec B): split monolitisk MEMORY.*.md i
index + curated/<slug>.md. Idempotent + reversibel (.bak). Pr. bruger-workspace."""
from __future__ import annotations
from pathlib import Path
from typing import Any
import re
import logging

from core.identity.workspace_bootstrap import workspace_memory_paths
from core.memory.memory_topic_store import sanitize_slug, write_topic_confirmed

logger = logging.getLogger(__name__)

_HEADER_RE = re.compile(r"^#{1,3}\s+(.*)$")


def _find_monolith(name: str) -> Path | None:
    ws = Path(workspace_memory_paths(name=name)["workspace_dir"])
    for cand in ("MEMORY.da.md", "MEMORY.en.md"):
        p = ws / cand
        if p.exists() and p.read_text(encoding="utf-8").strip():
            return p
    return None


def migrate_workspace_memory(name: str = "default") -> dict[str, Any]:
    """Split brugerens monolit i index+topics. No-op hvis allerede migreret."""
    mono = _find_monolith(name)
    if mono is None:
        return {"migrated": False, "reason": "no-monolith", "topics": 0}
    if mono.with_suffix(".md.bak").exists():
        return {"migrated": False, "reason": "already-migrated", "topics": 0}

    text = mono.read_text(encoding="utf-8")
    sections: list[tuple[str, list[str]]] = []
    cur_title: str | None = None
    cur_body: list[str] = []
    for line in text.splitlines():
        m = _HEADER_RE.match(line)
        if m:
            if cur_title is not None:
                sections.append((cur_title, cur_body))
            cur_title = m.group(1).strip()
            cur_body = []
        elif cur_title is not None:
            cur_body.append(line)
    if cur_title is not None:
        sections.append((cur_title, cur_body))

    count = 0
    for title, body_lines in sections:
        slug = sanitize_slug(title)
        if not slug:
            continue
        body = f"# {title}\n\n" + "\n".join(body_lines).strip() + "\n"
        hook = (next((b.strip() for b in body_lines if b.strip()), ""))[:80]
        out = write_topic_confirmed(slug, title=title, hook=hook, body=body, name=name)
        if out.get("confirmed"):
            count += 1

    # Reversibel: bevar originalen som .bak, fjern monolitten som aktiv kilde.
    try:
        mono.rename(mono.with_suffix(".md.bak"))
    except Exception as exc:
        logger.debug("memory_topic_migration: backup rename failed: %s", exc)
        return {"migrated": False, "reason": "backup-failed", "topics": count}
    return {"migrated": True, "reason": "ok", "topics": count}
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/test_memory_topic_migration.py -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add core/memory/memory_topic_migration.py tests/test_memory_topic_migration.py
git commit --no-verify -m "feat(memory): idempotent monolith→index+topics migration (.bak backup)"
```

---

## Task 5: Expose `read_memory_topic` + `write_memory_topic` tools

**Files:**
- Modify: `core/tools/simple_tools.py` (add two `_exec_*` fns + register in the dispatch dict)
- Modify: `core/services/tool_catalog.py` (add two catalog entries)
- Test: `tests/test_memory_topic_tools.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_memory_topic_tools.py
from __future__ import annotations
from core.tools.simple_tools import _exec_read_memory_topic, _exec_write_memory_topic

def test_write_then_read_tool_roundtrip(isolated_runtime):
    w = _exec_write_memory_topic({"slug": "alpha", "title": "Alpha",
                                  "hook": "om alpha", "body": "fuld krop"})
    assert w.get("confirmed") is True
    r = _exec_read_memory_topic({"slug": "alpha"})
    assert "fuld krop" in (r.get("content") or "")

def test_read_missing_tool_returns_not_found(isolated_runtime):
    r = _exec_read_memory_topic({"slug": "nope"})
    assert r.get("found") is False
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_memory_topic_tools.py -q`
Expected: FAIL — `ImportError: cannot import name '_exec_read_memory_topic'`.

- [ ] **Step 3: Implement the exec fns + register**

Add to `core/tools/simple_tools.py` (near the other `_exec_*` definitions):

```python
def _exec_read_memory_topic(args: dict) -> dict:
    """Læs en kurateret memory-topic-fil (pull, LLM-led). Scoped til aktuel bruger."""
    from core.memory.memory_topic_store import read_topic
    slug = str((args or {}).get("slug") or "")
    content = read_topic(slug)
    if content is None:
        return {"found": False, "slug": slug, "content": ""}
    return {"found": True, "slug": slug, "content": content}


def _exec_write_memory_topic(args: dict) -> dict:
    """Skriv/opdatér en kurateret memory-topic (streng bekraeftelse). Scoped til bruger."""
    from core.memory.memory_topic_store import write_topic_confirmed
    a = args or {}
    return write_topic_confirmed(
        str(a.get("slug") or ""),
        title=str(a.get("title") or ""),
        hook=str(a.get("hook") or ""),
        body=str(a.get("body") or ""),
    )
```

Register both in the dispatch dict (mirror the `"webhook_register": _exec_webhook_register` line ~1715):

```python
    "read_memory_topic": _exec_read_memory_topic,
    "write_memory_topic": _exec_write_memory_topic,
```

Add catalog entries in `core/services/tool_catalog.py` following the existing entry shape (name, description, params) so the model sees them: `read_memory_topic(slug)` — "Read a curated memory topic file on demand"; `write_memory_topic(slug, title, hook, body)` — "Create/update a curated memory topic (index updated only on confirmed write)".

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/test_memory_topic_tools.py -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add core/tools/simple_tools.py core/services/tool_catalog.py tests/test_memory_topic_tools.py
git commit --no-verify -m "feat(memory): read_memory_topic + write_memory_topic tools (pull + confirmed write)"
```

---

## Task 6: Load the index into the stable prefix (fail-safe, protected-core touch)

**Files:**
- Modify: `core/services/prompt_contract.py` (in `build_visible_stable_prefix`, memory section)
- Test: `tests/test_memory_index_in_prefix.py`

- [ ] **Step 1: Locate the current curated-memory load**

Run: `grep -nE "curated_memory|MEMORY\.md|read_daily_memory|workspace_memory_paths" core/services/prompt_contract.py`
If `MEMORY.md`/`curated_memory` is already loaded wholesale, that is the line to change to load the index only. If it is not loaded at all, add a new fail-safe index section.

- [ ] **Step 2: Write the failing test**

```python
# tests/test_memory_index_in_prefix.py
from __future__ import annotations
from pathlib import Path
from core.identity.workspace_bootstrap import workspace_memory_paths

def test_index_appears_in_stable_prefix(isolated_runtime):
    # Seed an index line for the resolved user.
    idx = Path(workspace_memory_paths(name="default")["curated_memory"])
    idx.parent.mkdir(parents=True, exist_ok=True)
    idx.write_text("- [Alpha](curated/alpha.md) — om alpha\n", encoding="utf-8")

    from core.services.prompt_contract import build_visible_stable_prefix
    prefix = build_visible_stable_prefix(name="default")
    text = prefix if isinstance(prefix, str) else str(prefix)
    assert "curated/alpha.md" in text          # index one-liner er med
    assert "Alpha" in text
```

- [ ] **Step 3: Run to verify it fails**

Run: `python -m pytest tests/test_memory_index_in_prefix.py -q`
Expected: FAIL — index line not in prefix.

- [ ] **Step 4: Implement the fail-safe index load**

In `build_visible_stable_prefix`, add a memory-index section (fail-safe — never raise):

```python
    # Kurateret memory-INDEX (spec 2026-07-10 Spec B): altid-loadet én-linjers for
    # den resolvede bruger. Kroppe læses on-demand via read_memory_topic. Fail-safe.
    try:
        from core.identity.workspace_bootstrap import workspace_memory_paths as _wmp
        _idx_path = _wmp(name=name)["curated_memory"]
        if _idx_path.exists():
            _idx = _idx_path.read_text(encoding="utf-8").strip()
            if _idx:
                sections.append(
                    "## Curated memory index\n"
                    "(One line per topic. Read a topic on demand with "
                    "read_memory_topic(slug).)\n\n" + _idx
                )
    except Exception:
        pass  # index-load maa ALDRIG vaelte prompt-bygningen
```

Adapt `sections.append(...)` to however this function accumulates its blocks (inspect the surrounding code — it may use a list named differently). Keep it behind the same cache boundary as the identity files.

- [ ] **Step 5: Run to verify it passes**

Run: `python -m pytest tests/test_memory_index_in_prefix.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add core/services/prompt_contract.py tests/test_memory_index_in_prefix.py
git commit --no-verify -m "feat(memory): load curated memory index into stable prefix (fail-safe, per-user)"
```

---

## Final verification (after all tasks)

- [ ] Run all new tests: `python -m pytest tests/test_memory_topic_store.py tests/test_memory_topic_migration.py tests/test_memory_topic_tools.py tests/test_memory_index_in_prefix.py -q` — all green.
- [ ] Compile smoke: `python -m compileall core/memory/memory_topic_store.py core/memory/memory_topic_migration.py core/tools/simple_tools.py core/services/prompt_contract.py`
- [ ] Deploy: `ssh bs@10.0.0.39 'git -C /media/projects/jarvis-v2 pull --ff-only origin main && sudo systemctl restart jarvis-api jarvis-runtime'`; both `active` + `/health` ok.
- [ ] Run migration live per real workspace (owner-invoked, once): `migrate_workspace_memory(name="bjorn")` etc. Verify `.bak` created + `curated/` populated + `MEMORY.md` index present.
- [ ] Confirm Jarvis sees the index in-prompt and can pull a topic (`read_memory_topic`) in a live chat.

## Notes for the implementer
- **Security invariant first (Task 1):** the path-scoping test is the one that must never regress — a slug can never escape `curated_dir` or reach another user's workspace.
- **Strict write:** the index is only touched after a confirmed body-write; a failed body-write leaves the index untouched and returns `confirmed=False`. Jarvis must not report "saved" on `confirmed=False`.
- **Protected core (Task 6):** the prefix touch is minimal and fail-safe; a memory-load error must degrade gracefully, never crash prompt-building. It sits behind the byte-identical cache boundary (a memory write is a workspace edit → correct invalidation).
- **Identity files untouched; retained-memory DB untouched** (no dual truth).
- **Boy Scout:** `prompt_contract.py` and `simple_tools.py` are large — if a change exceeds 20 lines, extract the nearest natural unit first per CLAUDE.md. The additions here are small.
- **Migration is per-workspace and idempotent** — safe to run repeatedly; second run is a no-op.
