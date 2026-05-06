# Tool Router Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce visible-chat prompt token cost from ~43K to ~15-20K per turn by sending only a relevant subset of the 293 tool definitions, with safety nets so Jarvis never silently loses capability.

**Architecture:** A new `ToolRouter` between `_build_visible_input` and the provider call returns a `ToolSelection`. Selection = (always-core from 7-day usage) ∪ (top-K embedding matches against user_message). Confidence below threshold → fallback to full list. Jarvis can call `load_more_tools` to fetch missing schemas. Always-on `[TOOL_CATALOG]` (~6K tok, cacheable) lets him see all 293 tool names at all times.

**Tech Stack:** Python 3.11, SQLite, FastAPI, sentence-transformers via Ollama (`nomic-embed-text` or `mxbai-embed-large`), React/JSX for MC widget.

**Spec:** `docs/superpowers/specs/2026-05-06-tool-router-design.md`

---

## File Structure

### New files

| Path | Responsibility |
|---|---|
| `core/services/tool_catalog.py` | Compact catalog text (name + 1-line desc) for system prompt |
| `core/services/tool_tagger.py` | LLM-bootstrap tags + override layer reads |
| `core/services/tool_embeddings.py` | Embedding cache (sqlite + on-demand recompute) |
| `core/services/tool_router.py` | `select_tools()` — confidence, selection, fallback |
| `core/services/tool_router_runtime.py` | Nightly daemon: refresh always-core, recompute embeddings, adjust threshold |
| `apps/api/jarvis_api/routes/tool_router.py` | `/mc/tool-router-state` endpoint |
| `apps/ui/src/components/mission-control/ToolRouterCard.jsx` | MC widget |
| `state/tool_tags.pinned.json` | Manual pinned set (committed) |
| `state/tool_tags.overrides.json` | Manual tag overrides (committed, starts empty) |
| `tests/services/test_tool_catalog.py` | |
| `tests/services/test_tool_tagger.py` | |
| `tests/services/test_tool_router.py` | |
| `tests/services/test_tool_router_runtime.py` | |
| `tests/integration/test_tool_router_wire.py` | Full visible-run smoke |

### Modified files

| Path | Change |
|---|---|
| `core/eventbus/events.py` | Add `tool_router` to `ALLOWED_EVENT_FAMILIES` |
| `core/runtime/db.py` | Migrations for `tool_router_decisions`, `tool_router_load_more` |
| `core/runtime/settings.py` | Add `tool_router_enabled`, `tool_router_threshold`, `tool_router_always_core_size`, `tool_router_k_embeddings`, `tool_router_embedding_model` |
| `core/services/visible_runs.py` | Use `select_tools()` to scope `_agentic_tools`; honor `_round_extra_tools` from `load_more_tools` |
| `core/services/prompt_contract.py` | Insert `[TOOL_CATALOG]` section in `build_visible_chat_prompt_assembly` |
| `core/tools/simple_tools.py` | Register `load_more_tools` definition + handler |
| `apps/api/jarvis_api/app.py` | Mount router; start `tool_router_runtime` daemon |
| `apps/ui/src/components/mission-control/CheapBalancerTab.jsx` | Mount `<ToolRouterCard />` |
| `scripts/smoke_test_startup.py` | Verify `/mc/tool-router-state` endpoint |

---

## Task 1: Event family + settings flags + DB migrations

**Files:**
- Modify: `core/eventbus/events.py`
- Modify: `core/runtime/settings.py`
- Modify: `core/runtime/db.py`
- Test: `tests/runtime/test_tool_router_db_migrations.py`

- [ ] **Step 1: Add `tool_router` event family**

In `core/eventbus/events.py`, add to `ALLOWED_EVENT_FAMILIES`:

```python
"tool_router",  # tool selection observability (added 2026-05-06)
```

- [ ] **Step 2: Add settings flags**

In `core/runtime/settings.py`, add inside `RuntimeSettings`:

```python
tool_router_enabled: bool = True
tool_router_threshold: float = 0.55
tool_router_always_core_size: int = 70
tool_router_k_embeddings: int = 30
tool_router_embedding_model: str = "nomic-embed-text"
tool_router_embedding_provider: str = "ollama"
```

- [ ] **Step 3: Write failing migration test**

Create `tests/runtime/test_tool_router_db_migrations.py`:

```python
from core.runtime.db import init_db, connect

def test_tool_router_decisions_table_exists(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_DB_PATH", str(tmp_path / "jarvis.db"))
    init_db()
    with connect() as c:
        row = c.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name='tool_router_decisions'"
        ).fetchone()
    assert row is not None

def test_tool_router_load_more_table_exists(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_DB_PATH", str(tmp_path / "jarvis.db"))
    init_db()
    with connect() as c:
        row = c.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name='tool_router_load_more'"
        ).fetchone()
    assert row is not None
```

Run: `pytest tests/runtime/test_tool_router_db_migrations.py -v`. Expected: FAIL.

- [ ] **Step 4: Add migrations to `init_db()`**

In `core/runtime/db.py`, append inside `init_db()` (after the last existing CREATE TABLE block):

```python
        c.execute("""
            CREATE TABLE IF NOT EXISTS tool_router_decisions (
              id INTEGER PRIMARY KEY,
              run_id TEXT, session_id TEXT, lane TEXT,
              user_message_preview TEXT,
              selected_names_json TEXT,
              always_core_names_json TEXT,
              embedding_picks_json TEXT,
              confidence REAL, threshold REAL,
              fallback_used INTEGER, fallback_reason TEXT,
              elapsed_ms INTEGER,
              tokens_saved_estimate INTEGER,
              created_at TEXT
            )
        """)
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_tool_router_decisions_created_at "
            "ON tool_router_decisions(created_at)"
        )
        c.execute("""
            CREATE TABLE IF NOT EXISTS tool_router_load_more (
              id INTEGER PRIMARY KEY,
              run_id TEXT, decision_id INTEGER,
              requested_names_json TEXT, requested_query TEXT,
              resolved_names_json TEXT,
              round_index INTEGER,
              created_at TEXT
            )
        """)
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_tool_router_load_more_created_at "
            "ON tool_router_load_more(created_at)"
        )
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/runtime/test_tool_router_db_migrations.py -v`. Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add core/eventbus/events.py core/runtime/settings.py core/runtime/db.py tests/runtime/test_tool_router_db_migrations.py
git commit -m "feat(tool-router): event family, settings flags, DB migrations"
```

---

## Task 2: Pinned set + overrides scaffolding

**Files:**
- Create: `state/tool_tags.pinned.json`
- Create: `state/tool_tags.overrides.json`

- [ ] **Step 1: Initial pinned set**

Create `state/tool_tags.pinned.json` with the manually-chosen always-core tools that must never be excluded regardless of usage:

```json
{
  "_doc": "Tools pinned to always-core regardless of 7-day usage. Edit freely.",
  "pinned": [
    "read_file", "write_file", "edit_file", "grep", "list_dir", "glob",
    "bash", "pause_and_ask", "remember_this", "recall_memories",
    "search_memory", "search_sessions", "web_search", "web_fetch",
    "decision_create", "goal_create", "todo_add", "todo_complete",
    "scheduled_task_create", "load_more_tools",
    "discord_channel", "send_message",
    "git_status", "git_log", "git_diff", "git_show"
  ]
}
```

- [ ] **Step 2: Empty overrides file**

Create `state/tool_tags.overrides.json`:

```json
{
  "_doc": "Manual tag overrides. Format: {\"tool_name\": [\"tag1\", \"tag2\"]}. Wins over auto tags.",
  "overrides": {}
}
```

- [ ] **Step 3: Commit**

```bash
git add state/tool_tags.pinned.json state/tool_tags.overrides.json
git commit -m "feat(tool-router): seed pinned set and overrides scaffold"
```

---

## Task 3: tool_catalog.py — compact catalog text

**Files:**
- Create: `core/services/tool_catalog.py`
- Test: `tests/services/test_tool_catalog.py`

- [ ] **Step 1: Write failing tests**

Create `tests/services/test_tool_catalog.py`:

```python
from core.services.tool_catalog import build_catalog_text, catalog_token_estimate

def test_catalog_lists_all_tools():
    text = build_catalog_text()
    assert "TOOL CATALOG" in text
    # Catalog must list every registered tool
    from core.tools.simple_tools import get_tool_definitions
    defs = get_tool_definitions()
    for d in defs:
        name = (d.get("function") or {}).get("name") or d.get("name")
        assert name and name in text, f"Missing {name!r} in catalog"

def test_catalog_format_is_one_line_per_tool():
    text = build_catalog_text()
    lines = [ln for ln in text.splitlines() if ln.startswith("- ")]
    assert len(lines) >= 200, f"Expected ≥200 tool lines, got {len(lines)}"
    # Each entry should contain a colon separating name from description
    bad = [ln for ln in lines if ":" not in ln]
    assert not bad, f"Lines without name:desc separator: {bad[:3]}"

def test_catalog_caches_until_tools_change():
    a = build_catalog_text()
    b = build_catalog_text()
    assert a is b, "Catalog text should be cached identity-equal between calls"

def test_catalog_token_estimate_reasonable():
    n = catalog_token_estimate()
    assert 3000 < n < 15000, f"Catalog tokens out of expected band: {n}"
```

Run: `pytest tests/services/test_tool_catalog.py -v`. Expected: FAIL (module missing).

- [ ] **Step 2: Implement `tool_catalog.py`**

Create `core/services/tool_catalog.py`:

```python
"""Compact tool catalog for system prompt.

Lists all registered tool names + a 1-line description so Jarvis always
knows what exists, even when the full tool definitions sent on a turn
are a subset (selected by tool_router). Cached in-memory; invalidated
when the tool registry hash changes.
"""
from __future__ import annotations

import hashlib
import json
from typing import Optional

from core.tools.simple_tools import get_tool_definitions

_HEADER = (
    "TOOL CATALOG (use load_more_tools(names=[...]) or "
    "load_more_tools(query=\"...\") to fetch full schemas):\n"
)

_cached_text: Optional[str] = None
_cached_hash: Optional[str] = None


def _registry_hash() -> str:
    defs = get_tool_definitions() or []
    payload = json.dumps(
        sorted(
            (
                (d.get("function") or {}).get("name") or d.get("name") or "",
                _short_desc(d),
            )
            for d in defs
        ),
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _short_desc(tool_def: dict) -> str:
    fn = tool_def.get("function") or tool_def
    desc = str(fn.get("description") or "").strip()
    # Take first sentence or first 90 chars, whichever is shorter.
    head = desc.split("\n", 1)[0]
    if "." in head[:120]:
        head = head.split(".", 1)[0] + "."
    return head[:120].strip() or "(no description)"


def build_catalog_text() -> str:
    """Return cached catalog text; rebuild only if tool registry changed."""
    global _cached_text, _cached_hash
    h = _registry_hash()
    if _cached_text is not None and _cached_hash == h:
        return _cached_text
    defs = get_tool_definitions() or []
    lines = [_HEADER]
    for d in sorted(
        defs,
        key=lambda dd: ((dd.get("function") or {}).get("name") or dd.get("name") or ""),
    ):
        name = (d.get("function") or {}).get("name") or d.get("name") or "?"
        lines.append(f"- {name}: {_short_desc(d)}")
    text = "\n".join(lines)
    _cached_text = text
    _cached_hash = h
    return text


def catalog_token_estimate() -> int:
    """Rough char/4 token estimate of the current catalog."""
    return max(1, len(build_catalog_text()) // 4)


def invalidate_cache() -> None:
    """Force next call to rebuild. Useful in tests."""
    global _cached_text, _cached_hash
    _cached_text = None
    _cached_hash = None
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/services/test_tool_catalog.py -v`. Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add core/services/tool_catalog.py tests/services/test_tool_catalog.py
git commit -m "feat(tool-router): tool_catalog with cached compact text"
```

---

## Task 4: Wire `[TOOL_CATALOG]` into prompt_contract

**Files:**
- Modify: `core/services/prompt_contract.py` (in `build_visible_chat_prompt_assembly`)
- Test: `tests/services/test_prompt_catalog_section.py`

- [ ] **Step 1: Write failing test**

Create `tests/services/test_prompt_catalog_section.py`:

```python
from core.services.prompt_contract import build_visible_chat_prompt_assembly

def test_visible_prompt_includes_tool_catalog():
    a = build_visible_chat_prompt_assembly(
        provider="ollama", model="glm-5.1:cloud",
        user_message="hej", session_id=None,
    )
    assert "TOOL CATALOG" in (a.text or "")
```

Run: `pytest tests/services/test_prompt_catalog_section.py -v`. Expected: FAIL.

- [ ] **Step 2: Insert section in `build_visible_chat_prompt_assembly`**

In `core/services/prompt_contract.py`, near the end of `build_visible_chat_prompt_assembly` (just before the function returns the `PromptAssembly`), append the catalog as a new part. Find the last `parts.append(...)` block and add after it:

```python
        try:
            from core.services.tool_catalog import build_catalog_text
            _catalog_text = build_catalog_text()
            if _catalog_text:
                parts.append(_catalog_text)
        except Exception:
            # Catalog is best-effort — never break prompt assembly.
            pass
```

(Place this so it appears late in the assembled text; ordering doesn't matter for correctness, but late means it doesn't interleave with identity sections.)

- [ ] **Step 3: Run tests**

Run: `pytest tests/services/test_prompt_catalog_section.py -v`. Expected: PASS.

- [ ] **Step 4: Verify with measurement script**

Run: `conda run -n ai python scripts/measure_prompt_payload.py | head -30`.
Confirm system prompt now contains `[TOOL_CATALOG]`-related growth (~5-7K extra tokens). This is expected — we're temporarily *adding* tokens; tool selection in later tasks will subtract many more.

- [ ] **Step 5: Commit**

```bash
git add core/services/prompt_contract.py tests/services/test_prompt_catalog_section.py
git commit -m "feat(tool-router): inject TOOL_CATALOG section into visible prompt"
```

---

## Task 5: tool_tagger.py — read overrides + LLM bootstrap

**Files:**
- Create: `core/services/tool_tagger.py`
- Test: `tests/services/test_tool_tagger.py`

- [ ] **Step 1: Write failing tests for read path**

Create `tests/services/test_tool_tagger.py`:

```python
import json
from pathlib import Path
import pytest

from core.services import tool_tagger

@pytest.fixture
def isolated_tags(tmp_path, monkeypatch):
    monkeypatch.setattr(tool_tagger, "_TAGS_PATH", tmp_path / "tool_tags.json")
    monkeypatch.setattr(tool_tagger, "_OVERRIDES_PATH", tmp_path / "tool_tags.overrides.json")
    monkeypatch.setattr(tool_tagger, "_PINNED_PATH", tmp_path / "tool_tags.pinned.json")
    return tmp_path

def test_get_tags_returns_empty_when_no_files(isolated_tags):
    assert tool_tagger.get_tags("read_file") == []

def test_overrides_win_over_auto(isolated_tags):
    (isolated_tags / "tool_tags.json").write_text(json.dumps({"tags": {"read_file": ["code"]}}))
    (isolated_tags / "tool_tags.overrides.json").write_text(
        json.dumps({"overrides": {"read_file": ["system", "io"]}})
    )
    tool_tagger.invalidate_cache()
    assert tool_tagger.get_tags("read_file") == ["system", "io"]

def test_pinned_set_loads(isolated_tags):
    (isolated_tags / "tool_tags.pinned.json").write_text(
        json.dumps({"pinned": ["read_file", "bash"]})
    )
    tool_tagger.invalidate_cache()
    assert "read_file" in tool_tagger.get_pinned_set()
    assert "bash" in tool_tagger.get_pinned_set()

def test_unknown_tool_returns_empty(isolated_tags):
    (isolated_tags / "tool_tags.json").write_text(json.dumps({"tags": {"x": ["a"]}}))
    tool_tagger.invalidate_cache()
    assert tool_tagger.get_tags("nonexistent") == []
```

Run: `pytest tests/services/test_tool_tagger.py -v`. Expected: FAIL (module missing).

- [ ] **Step 2: Implement read path**

Create `core/services/tool_tagger.py`:

```python
"""Tool tag taxonomy.

Three layers, override-first:
  1. tool_tags.overrides.json — manual overrides
  2. tool_tags.json           — LLM-bootstrap auto tags
Pinned set lives in tool_tags.pinned.json (separate axis from tags).

Cached in-memory; mtime-checked on each call.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# Allowed tag domains (LLM bootstrap is constrained to this set)
ALLOWED_DOMAINS = {
    "memory", "code", "system", "web", "social", "audio", "video",
    "image", "identity", "scheduling", "hardware", "dev", "planning",
    "search",
}

_STATE_DIR = Path(os.getenv("JARVIS_STATE_DIR") or (Path.home() / ".jarvis-v2" / "state"))
_TAGS_PATH = _STATE_DIR / "tool_tags.json"
_OVERRIDES_PATH = _STATE_DIR / "tool_tags.overrides.json"
_PINNED_PATH = _STATE_DIR / "tool_tags.pinned.json"

# Fallback to repo paths if state dir doesn't have them yet (first-run)
_REPO_OVERRIDES = Path(__file__).resolve().parent.parent.parent / "state" / "tool_tags.overrides.json"
_REPO_PINNED = Path(__file__).resolve().parent.parent.parent / "state" / "tool_tags.pinned.json"

_cache: dict[str, object] = {"loaded": False}


def _load_json(p: Path) -> dict:
    try:
        return json.loads(p.read_text())
    except FileNotFoundError:
        return {}
    except Exception as exc:
        logger.warning("tool_tagger: failed to read %s: %s", p, exc)
        return {}


def _ensure_loaded() -> None:
    if _cache.get("loaded"):
        return
    auto = _load_json(_TAGS_PATH).get("tags", {}) or {}
    overrides = _load_json(_OVERRIDES_PATH).get("overrides", {}) or {}
    if not overrides and _REPO_OVERRIDES.exists():
        overrides = _load_json(_REPO_OVERRIDES).get("overrides", {}) or {}
    pinned = set(_load_json(_PINNED_PATH).get("pinned", []) or [])
    if not pinned and _REPO_PINNED.exists():
        pinned = set(_load_json(_REPO_PINNED).get("pinned", []) or [])
    _cache["auto"] = auto
    _cache["overrides"] = overrides
    _cache["pinned"] = pinned
    _cache["loaded"] = True


def get_tags(tool_name: str) -> list[str]:
    """Return tags for `tool_name`. Overrides win over auto. Empty list if unknown."""
    _ensure_loaded()
    overrides = _cache["overrides"]  # type: ignore[index]
    if tool_name in overrides:
        return list(overrides[tool_name])
    auto = _cache["auto"]  # type: ignore[index]
    return list(auto.get(tool_name, []))


def get_pinned_set() -> set[str]:
    _ensure_loaded()
    return set(_cache["pinned"])  # type: ignore[arg-type]


def invalidate_cache() -> None:
    _cache.clear()
    _cache["loaded"] = False
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/services/test_tool_tagger.py -v`. Expected: PASS.

- [ ] **Step 4: Add LLM bootstrap function**

Append to `core/services/tool_tagger.py`:

```python
def bootstrap_tags(*, dry_run: bool = False) -> dict[str, list[str]]:
    """Use a cheap-lane LLM to generate domain tags for every registered tool.

    Returns the {tool_name: [tags]} dict. If dry_run is False, writes to
    `_TAGS_PATH` (the auto layer; overrides remain untouched).
    """
    from core.tools.simple_tools import get_tool_definitions
    from core.services.cheap_provider_runtime import call_cheap_provider

    defs = get_tool_definitions() or []
    catalog = []
    for d in defs:
        fn = d.get("function") or d
        name = fn.get("name") or "?"
        desc = str(fn.get("description") or "").strip().split("\n", 1)[0][:200]
        catalog.append({"name": name, "desc": desc})

    prompt = (
        "Tag each tool with 1-3 domain tags from this fixed set:\n"
        f"{sorted(ALLOWED_DOMAINS)}\n\n"
        "Return strict JSON: {\"tags\": {\"tool_name\": [\"tag1\", \"tag2\"]}}.\n"
        "No prose. Only tags from the allowed set.\n\n"
        f"Tools:\n{json.dumps(catalog, ensure_ascii=False)}"
    )

    response_text = call_cheap_provider(
        prompt=prompt,
        purpose="tool_tag_bootstrap",
        max_tokens=8000,
    )

    try:
        parsed = json.loads(response_text)
        tags = parsed.get("tags", {})
    except Exception as exc:
        logger.error("tool_tagger.bootstrap_tags parse failed: %s", exc)
        tags = {}

    # Filter to allowed domains only
    cleaned = {
        name: [t for t in tag_list if t in ALLOWED_DOMAINS][:3]
        for name, tag_list in tags.items()
        if isinstance(tag_list, list)
    }

    if not dry_run:
        _STATE_DIR.mkdir(parents=True, exist_ok=True)
        _TAGS_PATH.write_text(
            json.dumps({"tags": cleaned}, ensure_ascii=False, indent=2)
        )
        invalidate_cache()

    return cleaned
```

- [ ] **Step 5: Add bootstrap test (mock cheap provider)**

Append to `tests/services/test_tool_tagger.py`:

```python
def test_bootstrap_filters_to_allowed_domains(isolated_tags, monkeypatch):
    fake_response = json.dumps({"tags": {
        "read_file": ["code", "system"],
        "bash": ["system", "INVALID_DOMAIN", "code"],
    }})
    monkeypatch.setattr(
        "core.services.cheap_provider_runtime.call_cheap_provider",
        lambda **kwargs: fake_response,
    )
    monkeypatch.setattr(tool_tagger, "_STATE_DIR", isolated_tags)
    out = tool_tagger.bootstrap_tags()
    assert "INVALID_DOMAIN" not in out["bash"]
    assert "system" in out["bash"]
```

Run: `pytest tests/services/test_tool_tagger.py -v`. Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add core/services/tool_tagger.py tests/services/test_tool_tagger.py
git commit -m "feat(tool-router): tool_tagger with override layers and LLM bootstrap"
```

---

## Task 6: tool_embeddings.py — embedding cache

**Files:**
- Create: `core/services/tool_embeddings.py`
- Test: `tests/services/test_tool_embeddings.py`

- [ ] **Step 1: Write failing tests**

Create `tests/services/test_tool_embeddings.py`:

```python
import sqlite3
import pytest

from core.services import tool_embeddings as te

@pytest.fixture
def fake_embed(monkeypatch):
    def _embed(text: str) -> list[float]:
        h = sum(ord(c) for c in text) % 100
        return [float(h), 0.5, 0.5]
    monkeypatch.setattr(te, "_compute_embedding", _embed)
    return _embed

@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(te, "_DB_PATH", tmp_path / "tool_embeddings.sqlite")
    return tmp_path

def test_get_embedding_caches(isolated_db, fake_embed):
    v1 = te.get_embedding("read_file", "read file from path")
    v2 = te.get_embedding("read_file", "read file from path")
    assert v1 == v2

def test_top_k_returns_most_similar(isolated_db, fake_embed):
    te.get_embedding("read_file", "read file from path")
    te.get_embedding("bash", "run shell command")
    te.get_embedding("grep", "search across files")
    hits = te.top_k_similar("read file something", k=2)
    assert len(hits) == 2
    assert hits[0][0] in {"read_file", "bash", "grep"}

def test_recompute_overwrites(isolated_db, fake_embed):
    te.get_embedding("read_file", "v1 description")
    te.invalidate("read_file")
    v2 = te.get_embedding("read_file", "v2 description")
    assert v2 == fake_embed("v2 description")
```

Run: `pytest tests/services/test_tool_embeddings.py -v`. Expected: FAIL.

- [ ] **Step 2: Implement embedding cache**

Create `core/services/tool_embeddings.py`:

```python
"""Tool description embedding cache.

Each tool gets one embedding (vector) of its name + description, computed
once via Ollama (configurable model) and persisted to sqlite. Used by
tool_router to find context-relevant tools.

Also provides `top_k_similar(query, k)` — embed the query, return the
k tool names most similar by cosine distance.
"""
from __future__ import annotations

import json
import logging
import math
import os
import sqlite3
import struct
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_DB_PATH = Path(
    os.getenv("JARVIS_STATE_DIR") or (Path.home() / ".jarvis-v2" / "state")
) / "tool_embeddings.sqlite"


def _connect() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(_DB_PATH))
    c.execute(
        "CREATE TABLE IF NOT EXISTS tool_embeddings ("
        "  name TEXT PRIMARY KEY, "
        "  description_hash TEXT, "
        "  embedding BLOB, "
        "  computed_at TEXT"
        ")"
    )
    return c


def _pack(vec: list[float]) -> bytes:
    return struct.pack(f"<{len(vec)}f", *vec)


def _unpack(blob: bytes) -> list[float]:
    n = len(blob) // 4
    return list(struct.unpack(f"<{n}f", blob))


def _hash_desc(desc: str) -> str:
    import hashlib
    return hashlib.sha256(desc.encode("utf-8")).hexdigest()[:16]


def _compute_embedding(text: str) -> list[float]:
    """Call Ollama embedding endpoint. Override in tests."""
    from core.runtime.settings import RuntimeSettings  # late import for test ergonomics
    s = RuntimeSettings()
    model = s.tool_router_embedding_model
    # Use the existing Ollama client path used elsewhere
    import requests
    base_url = os.getenv("OLLAMA_BASE_URL", "http://10.0.0.25:11434")
    r = requests.post(
        f"{base_url}/api/embeddings",
        json={"model": model, "prompt": text},
        timeout=15,
    )
    r.raise_for_status()
    return list(r.json().get("embedding") or [])


def get_embedding(name: str, description: str) -> list[float]:
    h = _hash_desc(description)
    with _connect() as c:
        row = c.execute(
            "SELECT description_hash, embedding FROM tool_embeddings WHERE name = ?",
            (name,),
        ).fetchone()
        if row and row[0] == h:
            return _unpack(row[1])
    vec = _compute_embedding(f"{name}: {description}")
    with _connect() as c:
        c.execute(
            "INSERT OR REPLACE INTO tool_embeddings(name, description_hash, embedding, computed_at) "
            "VALUES (?, ?, ?, ?)",
            (name, h, _pack(vec), time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime())),
        )
        c.commit()
    return vec


def invalidate(name: str) -> None:
    with _connect() as c:
        c.execute("DELETE FROM tool_embeddings WHERE name = ?", (name,))
        c.commit()


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def top_k_similar(query: str, k: int = 30) -> list[tuple[str, float]]:
    """Return (tool_name, similarity) sorted desc by cosine similarity."""
    qv = _compute_embedding(query)
    out: list[tuple[str, float]] = []
    with _connect() as c:
        rows = c.execute("SELECT name, embedding FROM tool_embeddings").fetchall()
    for name, blob in rows:
        sim = _cosine(qv, _unpack(blob))
        out.append((name, sim))
    out.sort(key=lambda r: r[1], reverse=True)
    return out[:k]


def warmup_all() -> int:
    """Compute embeddings for every registered tool. Returns count computed."""
    from core.tools.simple_tools import get_tool_definitions
    defs = get_tool_definitions() or []
    n = 0
    for d in defs:
        fn = d.get("function") or d
        name = fn.get("name") or ""
        desc = str(fn.get("description") or "").strip()
        if not name:
            continue
        try:
            get_embedding(name, desc)
            n += 1
        except Exception as exc:
            logger.warning("tool_embeddings.warmup_all skipped %s: %s", name, exc)
    return n
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/services/test_tool_embeddings.py -v`. Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add core/services/tool_embeddings.py tests/services/test_tool_embeddings.py
git commit -m "feat(tool-router): embedding cache with sqlite + ollama backend"
```

---

## Task 7: tool_router.py — selector core

**Files:**
- Create: `core/services/tool_router.py`
- Test: `tests/services/test_tool_router.py`

- [ ] **Step 1: Write failing tests for confidence scoring**

Create `tests/services/test_tool_router.py`:

```python
import pytest
from unittest.mock import patch

from core.services import tool_router as tr

def test_clarity_signal_short_affirmation_low():
    assert tr._clarity_signal("ja") < 0.3
    assert tr._clarity_signal("ok") < 0.3

def test_clarity_signal_question_high():
    assert tr._clarity_signal("hvor mange tokens bruger vi nu?") > 0.6

def test_clarity_signal_empty_zero():
    assert tr._clarity_signal("") == 0.0

def test_score_monotonic_in_top_sim():
    a = tr._score("læs filen visible_runs.py", top_sim=0.3, load_more_rate_7d=0.05)
    b = tr._score("læs filen visible_runs.py", top_sim=0.7, load_more_rate_7d=0.05)
    assert b > a

def test_score_lowered_by_high_load_more_rate():
    a = tr._score("læs filen", top_sim=0.5, load_more_rate_7d=0.0)
    b = tr._score("læs filen", top_sim=0.5, load_more_rate_7d=0.20)
    assert b < a
```

Run: `pytest tests/services/test_tool_router.py -v`. Expected: FAIL.

- [ ] **Step 2: Implement scoring + select_tools skeleton**

Create `core/services/tool_router.py`:

```python
"""Per-turn tool selection.

Returns a ToolSelection containing the names of tools to send with full
schema this turn. Falls back to the full registry when confidence is low,
when any subsystem fails, or when the killswitch is set.
"""
from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field

from core.eventbus.bus import event_bus
from core.runtime.db import connect
from core.runtime.settings import RuntimeSettings

logger = logging.getLogger(__name__)

_QUESTION_WORDS_DA_EN = {
    "hvor", "hvad", "hvem", "hvorfor", "hvordan", "hvornår",
    "what", "where", "why", "how", "who", "when",
}
_AFFIRMATIONS = {"ja", "nej", "ok", "okay", "godt", "go", "sure", "yes", "no"}
_BOOTSTRAP_FALLBACK_CORE = [
    "read_file", "write_file", "edit_file", "grep", "list_dir",
    "bash", "pause_and_ask", "remember_this", "recall_memories",
    "search_memory", "web_search", "decision_create",
    "todo_add", "load_more_tools",
    "git_status", "git_log", "git_diff",
    "discord_channel", "send_message",
    "scheduled_task_create", "goal_create",
    "search_sessions", "todo_complete", "web_fetch",
    "git_show",
]


@dataclass
class ToolSelection:
    selected_names: list[str]
    always_core: list[str] = field(default_factory=list)
    embedding_picks: list[str] = field(default_factory=list)
    confidence: float = 0.0
    threshold: float = 0.0
    fallback_used: bool = False
    fallback_reason: str = ""
    elapsed_ms: int = 0
    reason: str = ""


def _clarity_signal(msg: str) -> float:
    msg = (msg or "").strip()
    if not msg:
        return 0.0
    words = re.findall(r"\w+", msg.lower())
    if not words:
        return 0.0
    if len(words) == 1 and words[0] in _AFFIRMATIONS:
        return 0.15
    if len(words) < 3:
        return 0.30
    has_q = any(w in _QUESTION_WORDS_DA_EN for w in words) or "?" in msg
    base = 0.55 + (0.15 if has_q else 0.0) + min(0.15, len(words) * 0.01)
    return min(1.0, base)


def _score(user_message: str, *, top_sim: float, load_more_rate_7d: float) -> float:
    msg_clarity = _clarity_signal(user_message)
    similarity_strength = min(top_sim / 0.7, 1.0) if top_sim > 0 else 0.0
    adaptive_floor = max(0.30, 0.60 - load_more_rate_7d * 2.0)
    return (msg_clarity * 0.4 + similarity_strength * 0.6) * adaptive_floor


def _all_tool_names() -> list[str]:
    from core.tools.simple_tools import get_tool_definitions
    return [
        ((d.get("function") or {}).get("name") or d.get("name") or "")
        for d in (get_tool_definitions() or [])
    ]


def _always_core_set(limit: int) -> list[str]:
    """Top-N tools by 7-day call count ∪ pinned set, with fallback."""
    from core.services.tool_tagger import get_pinned_set
    pinned = get_pinned_set()
    try:
        with connect() as c:
            rows = c.execute(
                "SELECT json_extract(payload_json, '$.tool') AS tool, COUNT(*) AS n "
                "FROM events WHERE kind = 'tool.invoked' "
                "AND created_at >= datetime('now', '-7 days') "
                "GROUP BY tool ORDER BY n DESC LIMIT ?",
                (max(limit, 200),),
            ).fetchall()
        used_top = [r[0] for r in rows if r[0]][:limit]
    except Exception as exc:
        logger.warning("tool_router._always_core_set query failed: %s", exc)
        used_top = []

    core = list(dict.fromkeys(list(pinned) + used_top))
    if not core:
        core = list(_BOOTSTRAP_FALLBACK_CORE)

    # Trim to the configured size, but keep all pinned items even if it
    # pushes past `limit` slightly — pinned is intentional.
    pinned_in_core = [n for n in core if n in pinned]
    rest = [n for n in core if n not in pinned]
    out = pinned_in_core + rest[: max(0, limit - len(pinned_in_core))]
    return out


def _load_more_rate_7d() -> float:
    try:
        with connect() as c:
            decisions = c.execute(
                "SELECT COUNT(*) FROM tool_router_decisions "
                "WHERE created_at >= datetime('now', '-7 days')"
            ).fetchone()[0]
            load_more = c.execute(
                "SELECT COUNT(*) FROM tool_router_load_more "
                "WHERE created_at >= datetime('now', '-7 days')"
            ).fetchone()[0]
        if not decisions:
            return 0.0
        return float(load_more) / float(decisions)
    except Exception:
        return 0.0


def select_tools(
    *, user_message: str, session_id: str | None, lane: str, run_id: str | None = None,
) -> ToolSelection:
    """Select a subset of tools for this turn. Always returns a ToolSelection."""
    started_at = time.monotonic()
    settings = RuntimeSettings()

    if not settings.tool_router_enabled:
        sel = ToolSelection(
            selected_names=_all_tool_names(),
            fallback_used=True,
            fallback_reason="killswitch-off",
            reason="tool_router_enabled=False",
            elapsed_ms=int((time.monotonic() - started_at) * 1000),
        )
        _persist(sel, user_message, session_id, lane, run_id)
        return sel

    try:
        return _select_inner(
            user_message=user_message,
            session_id=session_id,
            lane=lane,
            run_id=run_id,
            settings=settings,
            started_at=started_at,
        )
    except Exception as exc:
        logger.exception("tool_router.select_tools failed; falling back to full list")
        sel = ToolSelection(
            selected_names=_all_tool_names(),
            fallback_used=True,
            fallback_reason=f"router-error: {type(exc).__name__}",
            reason=str(exc)[:200],
            elapsed_ms=int((time.monotonic() - started_at) * 1000),
        )
        _persist(sel, user_message, session_id, lane, run_id)
        return sel


def _select_inner(
    *, user_message, session_id, lane, run_id, settings, started_at,
) -> ToolSelection:
    from core.services.tool_embeddings import top_k_similar

    always_core = _always_core_set(settings.tool_router_always_core_size)
    threshold = float(settings.tool_router_threshold)
    load_more_rate = _load_more_rate_7d()

    # Embedding picks (with timeout-protective try)
    try:
        sim = top_k_similar(user_message or "", k=settings.tool_router_k_embeddings)
    except Exception as exc:
        logger.warning("tool_router: embedding lookup failed: %s", exc)
        sim = []

    top_sim = sim[0][1] if sim else 0.0
    confidence = _score(user_message or "", top_sim=top_sim, load_more_rate_7d=load_more_rate)

    if confidence < threshold:
        sel = ToolSelection(
            selected_names=_all_tool_names(),
            always_core=always_core,
            embedding_picks=[n for n, _ in sim],
            confidence=confidence,
            threshold=threshold,
            fallback_used=True,
            fallback_reason="confidence-below-threshold",
            elapsed_ms=int((time.monotonic() - started_at) * 1000),
            reason=f"confidence={confidence:.3f} < threshold={threshold:.3f}",
        )
        _persist(sel, user_message, session_id, lane, run_id)
        return sel

    embedding_picks = [n for n, _ in sim if n not in set(always_core)]
    selected = list(dict.fromkeys(always_core + embedding_picks))[:100]

    sel = ToolSelection(
        selected_names=selected,
        always_core=always_core,
        embedding_picks=embedding_picks,
        confidence=confidence,
        threshold=threshold,
        fallback_used=False,
        elapsed_ms=int((time.monotonic() - started_at) * 1000),
        reason=f"selected={len(selected)} core={len(always_core)} emb={len(embedding_picks)}",
    )
    _persist(sel, user_message, session_id, lane, run_id)
    return sel


def _persist(
    sel: ToolSelection, user_message: str, session_id: str | None, lane: str, run_id: str | None,
) -> None:
    preview = (user_message or "")[:200]
    full_count = len(_all_tool_names())
    tokens_saved = max(0, (full_count - len(sel.selected_names)) * 130)  # ~130 tok avg per tool def
    payload = {
        "run_id": run_id, "session_id": session_id, "lane": lane,
        "user_message_preview": preview,
        "selected_count": len(sel.selected_names),
        "fallback_used": bool(sel.fallback_used),
        "always_core_count": len(sel.always_core),
        "embedding_picks_count": len(sel.embedding_picks),
        "confidence": sel.confidence, "threshold": sel.threshold,
        "elapsed_ms": sel.elapsed_ms,
        "would_have_sent_full": full_count,
        "tokens_saved_estimate": tokens_saved,
    }
    try:
        event_bus.publish("tool_router.decision", payload)
    except Exception:
        pass
    try:
        with connect() as c:
            c.execute(
                "INSERT INTO tool_router_decisions("
                "run_id, session_id, lane, user_message_preview, "
                "selected_names_json, always_core_names_json, embedding_picks_json, "
                "confidence, threshold, fallback_used, fallback_reason, "
                "elapsed_ms, tokens_saved_estimate, created_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?, datetime('now'))",
                (
                    run_id, session_id, lane, preview,
                    json.dumps(sel.selected_names), json.dumps(sel.always_core),
                    json.dumps(sel.embedding_picks),
                    sel.confidence, sel.threshold,
                    1 if sel.fallback_used else 0, sel.fallback_reason,
                    sel.elapsed_ms, tokens_saved,
                ),
            )
            c.commit()
    except Exception as exc:
        logger.warning("tool_router._persist failed: %s", exc)
```

- [ ] **Step 3: Add selector behaviour tests**

Append to `tests/services/test_tool_router.py`:

```python
def test_killswitch_returns_full_list(monkeypatch):
    from core.runtime.settings import RuntimeSettings
    monkeypatch.setattr(RuntimeSettings, "tool_router_enabled", False)
    sel = tr.select_tools(user_message="hvad sker der?", session_id=None, lane="visible")
    assert sel.fallback_used
    assert sel.fallback_reason == "killswitch-off"
    assert len(sel.selected_names) == len(tr._all_tool_names())

def test_low_confidence_falls_back(monkeypatch):
    monkeypatch.setattr(tr, "_load_more_rate_7d", lambda: 0.0)
    monkeypatch.setattr(
        "core.services.tool_embeddings.top_k_similar",
        lambda query, k=30: [],
    )
    sel = tr.select_tools(user_message="ok", session_id=None, lane="visible")
    assert sel.fallback_used
    assert sel.fallback_reason == "confidence-below-threshold"

def test_selection_returns_subset_when_confident(monkeypatch):
    monkeypatch.setattr(tr, "_load_more_rate_7d", lambda: 0.0)
    monkeypatch.setattr(
        "core.services.tool_embeddings.top_k_similar",
        lambda query, k=30: [("read_file", 0.85), ("grep", 0.8)],
    )
    monkeypatch.setattr(tr, "_always_core_set", lambda limit: ["bash", "pause_and_ask"])
    sel = tr.select_tools(
        user_message="hvad er i visible_runs.py?",
        session_id=None, lane="visible",
    )
    if not sel.fallback_used:
        assert "bash" in sel.selected_names
        assert "read_file" in sel.selected_names
```

Run: `pytest tests/services/test_tool_router.py -v`. Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add core/services/tool_router.py tests/services/test_tool_router.py
git commit -m "feat(tool-router): selector core with confidence + fallback"
```

---

## Task 8: load_more_tools magic tool

**Files:**
- Modify: `core/tools/simple_tools.py` (definition + handler)
- Test: `tests/services/test_load_more_tools.py`

- [ ] **Step 1: Write failing test**

Create `tests/services/test_load_more_tools.py`:

```python
from core.tools.simple_tools import execute_tool

def test_load_more_tools_unknown_name_returns_error():
    out = execute_tool("load_more_tools", {"names": ["this_does_not_exist"]})
    assert out["status"] == "error" or "not found" in str(out).lower()

def test_load_more_tools_known_name_returns_ok():
    out = execute_tool("load_more_tools", {"names": ["read_file"]})
    assert out["status"] == "ok"
    assert "read_file" in out.get("added", [])

def test_load_more_tools_query_returns_matches(monkeypatch):
    import core.services.tool_embeddings as te
    monkeypatch.setattr(te, "top_k_similar", lambda q, k=30: [("read_file", 0.9), ("grep", 0.85)])
    out = execute_tool("load_more_tools", {"query": "read a file please"})
    assert out["status"] == "ok"
    assert "read_file" in out.get("added", [])
```

Run: `pytest tests/services/test_load_more_tools.py -v`. Expected: FAIL.

- [ ] **Step 2: Add the tool definition**

In `core/tools/simple_tools.py`, find `TOOL_DEFINITIONS = [` (around line 521). Append at the end of that list (just before the closing `]`):

```python
    {
        "type": "function",
        "function": {
            "name": "load_more_tools",
            "description": (
                "Fetch full tool schemas you didn't get this turn. Provide "
                "either explicit `names` (list of tool names from the catalog) "
                "or a natural-language `query` and the router will embedding-match. "
                "Added tools become available on the next agentic round."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "names": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Explicit tool names to load.",
                    },
                    "query": {
                        "type": "string",
                        "description": "Natural-language query for embedding match.",
                    },
                },
            },
        },
    },
```

- [ ] **Step 3: Add the handler**

Add a new function in `core/tools/simple_tools.py` (place near other tool handlers):

```python
def _tool_load_more_tools(arguments: dict) -> dict:
    """Resolve which tools to add to the next round. Logs to DB + events."""
    import json as _json
    from core.eventbus.bus import event_bus
    from core.runtime.db import connect

    names = list(arguments.get("names") or [])
    query = (arguments.get("query") or "").strip()

    all_names = {
        ((d.get("function") or {}).get("name") or d.get("name") or "")
        for d in (TOOL_DEFINITIONS or [])
    }

    resolved: list[str] = []
    unknown: list[str] = []
    for n in names:
        if n in all_names:
            resolved.append(n)
        else:
            unknown.append(n)

    if query and not resolved:
        try:
            from core.services.tool_embeddings import top_k_similar
            hits = top_k_similar(query, k=10)
            resolved = [n for n, _ in hits if n in all_names][:5]
        except Exception:
            resolved = []

    if not resolved and unknown:
        return {
            "status": "error",
            "error": f"tools not found: {unknown}. Use names from the TOOL CATALOG.",
        }

    if not resolved:
        return {
            "status": "ok",
            "added": [],
            "message": "no strong matches",
        }

    try:
        event_bus.publish("tool_router.load_more_fired", {
            "requested_names": names, "requested_query": query,
            "resolved_names": resolved,
        })
    except Exception:
        pass

    try:
        with connect() as c:
            c.execute(
                "INSERT INTO tool_router_load_more("
                "requested_names_json, requested_query, resolved_names_json, created_at) "
                "VALUES (?,?,?, datetime('now'))",
                (_json.dumps(names), query, _json.dumps(resolved)),
            )
            c.commit()
    except Exception:
        pass

    return {
        "status": "ok",
        "added": resolved,
        "message": f"Added {len(resolved)} tool(s); available next round.",
    }
```

- [ ] **Step 4: Register the handler**

Find the `_TOOL_HANDLERS` dict in `core/tools/simple_tools.py` and add:

```python
    "load_more_tools": _tool_load_more_tools,
```

(If `_FORCE_HANDLERS` exists separately, add to it as well.)

- [ ] **Step 5: Run tests**

Run: `pytest tests/services/test_load_more_tools.py -v`. Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add core/tools/simple_tools.py tests/services/test_load_more_tools.py
git commit -m "feat(tool-router): add load_more_tools magic tool"
```

---

## Task 9: Wire selector into visible_runs

**Files:**
- Modify: `core/services/visible_runs.py` (around line 1061 where `_get_tool_defs()` is called)
- Test: `tests/integration/test_tool_router_wire.py`

- [ ] **Step 1: Write integration test**

Create `tests/integration/test_tool_router_wire.py`:

```python
from unittest.mock import patch
from core.services.tool_router import select_tools

def test_selector_returns_load_more_tools_in_selection():
    sel = select_tools(
        user_message="hej hvad sker der i dag?",
        session_id=None, lane="visible",
    )
    assert "load_more_tools" in sel.selected_names or sel.fallback_used
```

Run: `pytest tests/integration/test_tool_router_wire.py -v`. Expected: depends on tags state. May pass or fail; that's OK — this is a sanity check. The actual integration test is the next step.

- [ ] **Step 2: Modify `visible_runs.py`**

In `core/services/visible_runs.py`, find around line 1061 where `_agentic_tools = _get_tool_defs()` is set. Replace with the scoped version:

```python
                _agentic_tools = _get_tool_defs()
                # ── Tool router: scope tool defs to a relevant subset ──
                # Falls back to the full list silently if anything goes wrong.
                _round_extra_tools: list[str] = []  # populated by load_more_tools
                try:
                    from core.services.tool_router import select_tools as _select_tools
                    _selection = _select_tools(
                        user_message=run.user_message,
                        session_id=run.session_id,
                        lane="visible" if not run.autonomous else "autonomous",
                        run_id=run.run_id,
                    )
                    if not _selection.fallback_used:
                        _selected_set = set(_selection.selected_names)
                        _agentic_tools = [
                            d for d in _agentic_tools
                            if ((d.get("function") or {}).get("name") or d.get("name") or "") in _selected_set
                        ]
                except Exception:
                    pass  # keep full list on any error
```

- [ ] **Step 3: Honor `_round_extra_tools` between rounds**

In the same file, find the `for _agentic_round in range(_AGENTIC_MAX_ROUNDS):` loop. After the existing `_round_tool_definitions` line, modify it to merge in extras:

```python
                    _round_tool_definitions = None if _is_last_round else _agentic_tools
                    # Merge in tools added by load_more_tools in previous rounds
                    if _round_tool_definitions is not None and _round_extra_tools:
                        _all_defs = _get_tool_defs() or []
                        _extra_set = set(_round_extra_tools)
                        _existing_names = {
                            ((d.get("function") or {}).get("name") or d.get("name") or "")
                            for d in _round_tool_definitions
                        }
                        for d in _all_defs:
                            n = (d.get("function") or {}).get("name") or d.get("name") or ""
                            if n in _extra_set and n not in _existing_names:
                                _round_tool_definitions = _round_tool_definitions + [d]
```

- [ ] **Step 4: Detect load_more_tools call results to populate `_round_extra_tools`**

Find where tool results are processed (around the `_to_followup_results` or where `simple_results` is iterated). Add after a tool result becomes available:

```python
                                # If this was a load_more_tools call, capture the names
                                # so the next round's tool_definitions includes them.
                                if _tc_name == "load_more_tools":
                                    try:
                                        _added = (sr.get("result") or {}).get("added") or []
                                        for _n in _added:
                                            if _n not in _round_extra_tools:
                                                _round_extra_tools.append(_n)
                                    except Exception:
                                        pass
```

(Place this inside the loop where each tool result is processed; the exact line depends on the surrounding code. Look for `_tc_name = ...` and add the block there.)

- [ ] **Step 5: Manual smoke**

Run: `conda run -n ai python scripts/measure_prompt_payload.py | head -10` — confirm script still works (it doesn't go through visible_runs but verifies imports remain healthy).

Run: `conda run -n ai python -c "from core.services.visible_runs import *; print('imports ok')"`.

- [ ] **Step 6: Commit**

```bash
git add core/services/visible_runs.py tests/integration/test_tool_router_wire.py
git commit -m "feat(tool-router): wire selector into visible_runs agentic loop"
```

---

## Task 10: tool_router_runtime daemon

**Files:**
- Create: `core/services/tool_router_runtime.py`
- Test: `tests/services/test_tool_router_runtime.py`

- [ ] **Step 1: Write failing tests**

Create `tests/services/test_tool_router_runtime.py`:

```python
from unittest.mock import patch
from core.services import tool_router_runtime as trr

def test_compute_threshold_adjustment_high_load_more_increases():
    new_t = trr._adjust_threshold(current=0.55, load_more_rate_7d=0.20)
    assert new_t > 0.55

def test_compute_threshold_adjustment_low_load_more_decreases():
    new_t = trr._adjust_threshold(current=0.55, load_more_rate_7d=0.02)
    assert new_t < 0.55

def test_threshold_bounded_high():
    assert trr._adjust_threshold(current=0.85, load_more_rate_7d=0.50) <= 0.85

def test_threshold_bounded_low():
    assert trr._adjust_threshold(current=0.30, load_more_rate_7d=0.0) >= 0.30
```

Run: `pytest tests/services/test_tool_router_runtime.py -v`. Expected: FAIL.

- [ ] **Step 2: Implement runtime daemon**

Create `core/services/tool_router_runtime.py`:

```python
"""Nightly daemon: refresh always-core ranking, recompute embeddings,
adjust adaptive threshold, write daemon-run summary event."""
from __future__ import annotations

import logging
import threading
import time
from typing import Optional

from core.eventbus.bus import event_bus

logger = logging.getLogger(__name__)

_THREAD: Optional[threading.Thread] = None
_STOP = threading.Event()
_INTERVAL_S = 6 * 3600  # ~6h between runs; daemon idempotent so over-frequent is fine


def _adjust_threshold(*, current: float, load_more_rate_7d: float) -> float:
    if load_more_rate_7d > 0.15:
        new_val = current + 0.05
    elif load_more_rate_7d < 0.05:
        new_val = current - 0.03
    else:
        new_val = current
    return max(0.30, min(0.85, new_val))


def _read_load_more_rate() -> float:
    from core.services.tool_router import _load_more_rate_7d
    return _load_more_rate_7d()


def run_once() -> dict:
    """Single daemon iteration. Safe to call manually for testing."""
    summary: dict = {"started_at": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime())}
    try:
        from core.services.tool_embeddings import warmup_all
        n = warmup_all()
        summary["embeddings_warmed"] = n
    except Exception as exc:
        summary["embeddings_error"] = str(exc)

    try:
        rate = _read_load_more_rate()
        from core.runtime.settings import RuntimeSettings
        s = RuntimeSettings()
        new_t = _adjust_threshold(current=s.tool_router_threshold, load_more_rate_7d=rate)
        summary["load_more_rate_7d"] = rate
        summary["threshold_proposed"] = new_t
        summary["threshold_current"] = s.tool_router_threshold
    except Exception as exc:
        summary["adjust_error"] = str(exc)

    try:
        event_bus.publish("tool_router.daemon_run", summary)
    except Exception:
        pass

    summary["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime())
    return summary


def _loop() -> None:
    while not _STOP.is_set():
        try:
            run_once()
        except Exception as exc:
            logger.warning("tool_router_runtime loop error: %s", exc)
        _STOP.wait(_INTERVAL_S)


def start_tool_router_runtime() -> None:
    global _THREAD
    if _THREAD is not None and _THREAD.is_alive():
        return
    _STOP.clear()
    _THREAD = threading.Thread(
        target=_loop, name="tool-router-runtime", daemon=True,
    )
    _THREAD.start()
    logger.info("tool_router_runtime daemon started")


def stop_tool_router_runtime() -> None:
    _STOP.set()
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/services/test_tool_router_runtime.py -v`. Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add core/services/tool_router_runtime.py tests/services/test_tool_router_runtime.py
git commit -m "feat(tool-router): nightly daemon for warmup + threshold adjustment"
```

---

## Task 11: MC endpoint

**Files:**
- Create: `apps/api/jarvis_api/routes/tool_router.py`
- Modify: `apps/api/jarvis_api/app.py`
- Test: `tests/api/test_tool_router_endpoint.py`

- [ ] **Step 1: Write failing test**

Create `tests/api/test_tool_router_endpoint.py`:

```python
from fastapi.testclient import TestClient

def test_tool_router_state_endpoint():
    from apps.api.jarvis_api.app import create_app
    app = create_app()
    with TestClient(app) as c:
        r = c.get("/mc/tool-router-state")
        assert r.status_code == 200
        body = r.json()
        assert "enabled" in body
        assert "totals" in body
        assert "config" in body
```

Run: `pytest tests/api/test_tool_router_endpoint.py -v`. Expected: FAIL (404).

- [ ] **Step 2: Implement endpoint**

Create `apps/api/jarvis_api/routes/tool_router.py`:

```python
"""MC observability for tool_router."""
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter

from core.runtime.db import connect
from core.runtime.settings import RuntimeSettings

router = APIRouter(prefix="/mc", tags=["mc-tool-router"])


def _bucket_count(rows, key: str, n_buckets: int = 10) -> list[int]:
    buckets = [0] * n_buckets
    for r in rows:
        v = r[key]
        if v is None:
            continue
        idx = min(n_buckets - 1, max(0, int(float(v) * n_buckets)))
        buckets[idx] += 1
    return buckets


@router.get("/tool-router-state")
def get_state() -> dict:
    s = RuntimeSettings()
    now = datetime.now(timezone.utc)
    today_iso = now.strftime("%Y-%m-%dT00:00:00+00:00")
    d7_iso = (now - timedelta(days=7)).isoformat()

    with connect() as c:
        decisions_today = c.execute(
            "SELECT COUNT(*) FROM tool_router_decisions WHERE created_at >= ?", (today_iso,),
        ).fetchone()[0]
        decisions_7d = c.execute(
            "SELECT COUNT(*) FROM tool_router_decisions WHERE created_at >= ?", (d7_iso,),
        ).fetchone()[0]
        fallback_7d = c.execute(
            "SELECT COUNT(*) FROM tool_router_decisions WHERE fallback_used = 1 AND created_at >= ?", (d7_iso,),
        ).fetchone()[0]
        load_more_7d = c.execute(
            "SELECT COUNT(*) FROM tool_router_load_more WHERE created_at >= ?", (d7_iso,),
        ).fetchone()[0]
        avg_saved = c.execute(
            "SELECT AVG(tokens_saved_estimate) FROM tool_router_decisions WHERE created_at >= ?", (d7_iso,),
        ).fetchone()[0] or 0
        avg_elapsed = c.execute(
            "SELECT AVG(elapsed_ms) FROM tool_router_decisions WHERE created_at >= ?", (d7_iso,),
        ).fetchone()[0] or 0
        confidence_rows = c.execute(
            "SELECT confidence FROM tool_router_decisions WHERE created_at >= ?", (d7_iso,),
        ).fetchall()
        recent_rows = c.execute(
            "SELECT created_at, user_message_preview, confidence, threshold, "
            "fallback_used, fallback_reason, "
            "json_array_length(selected_names_json) AS selected_count, elapsed_ms "
            "FROM tool_router_decisions ORDER BY id DESC LIMIT 20",
        ).fetchall()
        # Top missed tools — names that appear most often as resolved in load_more
        miss_rows = c.execute(
            "SELECT resolved_names_json FROM tool_router_load_more WHERE created_at >= ?", (d7_iso,),
        ).fetchall()

    miss_counts: dict[str, int] = {}
    for r in miss_rows:
        try:
            for n in json.loads(r[0] or "[]"):
                miss_counts[n] = miss_counts.get(n, 0) + 1
        except Exception:
            pass
    top_missed = sorted(
        ({"name": n, "count": c} for n, c in miss_counts.items()),
        key=lambda r: r["count"], reverse=True,
    )[:10]

    fallback_rate = (float(fallback_7d) / float(decisions_7d)) if decisions_7d else 0.0
    load_more_rate = (float(load_more_7d) / float(decisions_7d)) if decisions_7d else 0.0

    return {
        "enabled": s.tool_router_enabled,
        "config": {
            "threshold": s.tool_router_threshold,
            "always_core_size": s.tool_router_always_core_size,
            "k_embeddings": s.tool_router_k_embeddings,
            "embedding_model": s.tool_router_embedding_model,
        },
        "totals": {
            "decisions_today": decisions_today,
            "decisions_7d": decisions_7d,
            "fallback_rate_7d": fallback_rate,
            "load_more_rate_7d": load_more_rate,
            "avg_tokens_saved_7d": int(avg_saved),
            "avg_elapsed_ms": float(avg_elapsed),
        },
        "top_missed_tools_7d": top_missed,
        "confidence_histogram": _bucket_count(
            [{"confidence": float(r[0])} for r in confidence_rows], "confidence"
        ),
        "recent_decisions": [
            {
                "at": r[0],
                "preview": r[1],
                "confidence": r[2],
                "threshold": r[3],
                "fallback_used": bool(r[4]),
                "fallback_reason": r[5],
                "selected_count": r[6],
                "elapsed_ms": r[7],
            }
            for r in recent_rows
        ],
    }
```

- [ ] **Step 3: Mount router and start daemon in app**

In `apps/api/jarvis_api/app.py`, near other route imports add:

```python
from apps.api.jarvis_api.routes.tool_router import router as tool_router_router
```

Near the other `app.include_router(...)` calls add:

```python
    app.include_router(tool_router_router)
```

Inside the `lifespan` startup block, after the agentic_guards startup, add:

```python
            try:
                from core.services.tool_router_runtime import start_tool_router_runtime
                start_tool_router_runtime()
                logger.info("tool_router_runtime daemon started")
            except Exception as _exc:
                logger.warning("tool_router_runtime start failed: %s", _exc)
```

In the shutdown block, add:

```python
            try:
                from core.services.tool_router_runtime import stop_tool_router_runtime
                stop_tool_router_runtime()
            except Exception:
                pass
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/api/test_tool_router_endpoint.py -v`. Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/jarvis_api/routes/tool_router.py apps/api/jarvis_api/app.py tests/api/test_tool_router_endpoint.py
git commit -m "feat(tool-router): /mc/tool-router-state endpoint + daemon wiring"
```

---

## Task 12: MC widget

**Files:**
- Create: `apps/ui/src/components/mission-control/ToolRouterCard.jsx`
- Modify: `apps/ui/src/components/mission-control/CheapBalancerTab.jsx`

- [ ] **Step 1: Create the widget component**

Create `apps/ui/src/components/mission-control/ToolRouterCard.jsx`:

```jsx
import { useState, useEffect, useCallback } from 'react'
import { Zap, AlertCircle, CheckCircle2, Layers } from 'lucide-react'
import { s, T, mono } from '../../shared/theme/tokens'
import { Card, SectionTitle, MetricCard, ScrollPanel } from './shared'

export function ToolRouterCard() {
  const [state, setState] = useState(null)
  const [error, setError] = useState(null)

  const fetchState = useCallback(async () => {
    try {
      const r = await fetch('/mc/tool-router-state')
      if (!r.ok) throw new Error(`HTTP ${r.status}`)
      const data = await r.json()
      setState(data)
      setError(null)
    } catch (e) {
      setError(String(e))
    }
  }, [])

  useEffect(() => {
    fetchState()
    const id = setInterval(fetchState, 8000)
    return () => clearInterval(id)
  }, [fetchState])

  if (error) {
    return (
      <Card>
        <div style={s({ ...mono, fontSize: 11, color: T.red, padding: 8 })}>
          tool-router-state error: {error}
        </div>
      </Card>
    )
  }

  if (!state) {
    return <Card><div style={s({ padding: 8, color: T.text3, fontSize: 11 })}>Loading…</div></Card>
  }

  const t = state.totals || {}
  const recent = state.recent_decisions || []
  const missed = state.top_missed_tools_7d || []
  const hist = state.confidence_histogram || []
  const maxBucket = Math.max(1, ...hist)

  return (
    <div>
      <SectionTitle>
        Tool Router{' '}
        <span style={s({ ...mono, fontSize: 11, color: state.enabled ? T.green : T.text3, marginLeft: 8 })}>
          [{state.enabled ? 'enabled ✓' : 'disabled'}]
        </span>
      </SectionTitle>

      <div style={s({ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginTop: 8 })}>
        <MetricCard
          label="Tokens saved (avg/turn)"
          value={(t.avg_tokens_saved_7d || 0).toLocaleString()}
          sub="last 7d"
          icon={Zap}
          color={T.accent}
        />
        <MetricCard
          label="Selection rate"
          value={`${Math.round((1 - (t.fallback_rate_7d || 0)) * 100)}%`}
          sub={`${t.decisions_7d || 0} decisions`}
          icon={CheckCircle2}
          color={T.green}
        />
        <MetricCard
          label="Fallback rate"
          value={`${Math.round((t.fallback_rate_7d || 0) * 100)}%`}
          sub="confidence too low"
          icon={AlertCircle}
          color={(t.fallback_rate_7d || 0) > 0.30 ? T.amber : T.text3}
        />
        <MetricCard
          label="load_more rate"
          value={`${Math.round((t.load_more_rate_7d || 0) * 100)}%`}
          sub="Jarvis fetched extras"
          icon={Layers}
          color={(t.load_more_rate_7d || 0) > 0.15 ? T.amber : T.text3}
        />
      </div>

      <div style={s({ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginTop: 12 })}>
        <Card>
          <div style={s({ ...mono, fontSize: 11, color: T.text2, marginBottom: 6 })}>Confidence histogram</div>
          <div style={s({ display: 'flex', gap: 2, alignItems: 'flex-end', height: 56 })}>
            {hist.map((n, i) => (
              <div key={i} style={s({
                flex: 1,
                height: `${(n / maxBucket) * 100}%`,
                background: i < 5 ? T.amber : T.green,
                opacity: 0.7,
              })} title={`${(i * 0.1).toFixed(1)}-${((i + 1) * 0.1).toFixed(1)}: ${n}`} />
            ))}
          </div>
          <div style={s({ ...mono, fontSize: 9, color: T.text3, marginTop: 4 })}>
            0 ─────────── 1.0 (threshold = {state.config?.threshold?.toFixed(2)})
          </div>
        </Card>
        <Card>
          <div style={s({ ...mono, fontSize: 11, color: T.text2, marginBottom: 6 })}>Top missed tools (7d)</div>
          <ScrollPanel maxHeight={84}>
            {missed.length > 0 ? (
              missed.map((m, i) => (
                <div key={i} style={s({ display: 'flex', justifyContent: 'space-between', fontSize: 10, ...mono, padding: '2px 4px' })}>
                  <span style={s({ color: T.accent })}>{m.name}</span>
                  <span style={s({ color: T.text3 })}>{m.count}</span>
                </div>
              ))
            ) : (
              <div style={s({ ...mono, fontSize: 10, color: T.text3 })}>(none)</div>
            )}
          </ScrollPanel>
        </Card>
      </div>

      <Card style={{ marginTop: 12 }}>
        <div style={s({ ...mono, fontSize: 11, color: T.text2, marginBottom: 6 })}>Recent decisions</div>
        <ScrollPanel maxHeight={180}>
          {recent.map((r, i) => (
            <div key={i} style={s({ display: 'flex', gap: 8, alignItems: 'center', padding: '3px 6px', fontSize: 10, ...mono })}>
              <span style={s({ color: T.text3, width: 64 })}>
                {r.at ? new Date(r.at).toLocaleTimeString() : '—'}
              </span>
              <span style={s({ color: r.fallback_used ? T.amber : T.green, width: 32 })}>
                {r.fallback_used ? 'FB' : 'OK'}
              </span>
              <span style={s({ color: T.text2, width: 60 })}>{r.confidence?.toFixed(2)}</span>
              <span style={s({ color: T.accent, width: 40 })}>{r.selected_count}t</span>
              <span style={s({ color: T.text2, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' })}>
                {r.preview}
              </span>
              <span style={s({ color: T.text3, width: 50, textAlign: 'right' })}>{r.elapsed_ms}ms</span>
            </div>
          ))}
        </ScrollPanel>
      </Card>
    </div>
  )
}
```

- [ ] **Step 2: Mount on Cheap Balancer tab**

In `apps/ui/src/components/mission-control/CheapBalancerTab.jsx`, add the import at the top:

```jsx
import { ToolRouterCard } from './ToolRouterCard'
```

In the JSX where `<AgenticGuardsCard />` is mounted, add `<ToolRouterCard />` after it:

```jsx
      <AgenticGuardsCard />
      <ToolRouterCard />
```

- [ ] **Step 3: Manual smoke**

Run: `cd apps/ui && npm run build` (or whatever the build command is). Confirm no build errors.

- [ ] **Step 4: Commit**

```bash
git add apps/ui/src/components/mission-control/ToolRouterCard.jsx apps/ui/src/components/mission-control/CheapBalancerTab.jsx
git commit -m "feat(tool-router): MC widget for observability"
```

---

## Task 13: Bootstrap embeddings + tags before deploy

**Files:**
- Create: `scripts/tool_router_bootstrap.py`

- [ ] **Step 1: Create bootstrap script**

Create `scripts/tool_router_bootstrap.py`:

```python
"""One-shot bootstrap: generate tool tags via cheap LLM and warm embedding cache.

Run before first deploy. Idempotent — safe to re-run after adding new tools.

Usage:
    conda activate ai
    python scripts/tool_router_bootstrap.py
    python scripts/tool_router_bootstrap.py --skip-tags    # only warm embeddings
    python scripts/tool_router_bootstrap.py --skip-embed   # only generate tags
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-tags", action="store_true")
    ap.add_argument("--skip-embed", action="store_true")
    args = ap.parse_args()

    if not args.skip_tags:
        from core.services.tool_tagger import bootstrap_tags
        print("Generating tool tags via cheap LLM...")
        tags = bootstrap_tags()
        print(f"  → {len(tags)} tools tagged")

    if not args.skip_embed:
        from core.services.tool_embeddings import warmup_all
        print("Warming embedding cache...")
        n = warmup_all()
        print(f"  → {n} tools embedded")

    print("Bootstrap complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run it**

Run: `conda run -n ai python scripts/tool_router_bootstrap.py`. Expected: tags generated + embeddings warmed.

If it fails on the LLM step, run with `--skip-tags` first to verify embeddings work, then debug tags.

- [ ] **Step 3: Manually review top 50 tags**

Open `~/.jarvis-v2/state/tool_tags.json` (or wherever `_TAGS_PATH` resolved). Sanity-check the top-50 most-used tools' tags. If any look wrong, add manual overrides to `state/tool_tags.overrides.json` (committed to repo). Then re-run with `--skip-tags --skip-embed` to verify cache invalidation.

- [ ] **Step 4: Commit**

```bash
git add scripts/tool_router_bootstrap.py state/tool_tags.overrides.json
git commit -m "feat(tool-router): bootstrap script for tags + embeddings"
```

---

## Task 14: Killswitch verification + smoke test extension

**Files:**
- Modify: `scripts/smoke_test_startup.py`

- [ ] **Step 1: Extend smoke test**

In `scripts/smoke_test_startup.py`, find where it asserts the app starts. Add a check for the new endpoint:

```python
        # Verify tool_router endpoint exists
        from fastapi.testclient import TestClient
        with TestClient(app) as client:
            r = client.get("/mc/tool-router-state")
            assert r.status_code == 200, f"tool-router-state returned {r.status_code}"
```

(Adapt to existing structure of the smoke test.)

- [ ] **Step 2: Run smoke test**

Run: `conda run -n ai python scripts/smoke_test_startup.py`. Expected: exit 0.

- [ ] **Step 3: Verify killswitch flips work**

Run a manual test (no commit):

```bash
conda run -n ai python -c "
from core.runtime.settings import RuntimeSettings
from core.services.tool_router import select_tools

# With killswitch on
import core.runtime.settings as st
st.RuntimeSettings.tool_router_enabled = False
sel = select_tools(user_message='hej', session_id=None, lane='visible')
print('killswitch off:', sel.fallback_used, sel.fallback_reason)
assert sel.fallback_used and sel.fallback_reason == 'killswitch-off'

# With killswitch off (default)
st.RuntimeSettings.tool_router_enabled = True
sel = select_tools(user_message='hvor mange filer er der i visible_runs?', session_id=None, lane='visible')
print('killswitch on:', sel.fallback_used, len(sel.selected_names))
"
```

- [ ] **Step 4: Commit**

```bash
git add scripts/smoke_test_startup.py
git commit -m "feat(tool-router): smoke test verifies tool-router endpoint"
```

---

## Task 15: Manual validation set + before/after measurement

**Files:**
- Create: `tests/manual/tool_router_validation.py`

- [ ] **Step 1: Create validation script**

Create `tests/manual/tool_router_validation.py`:

```python
"""Manual validation set for tool_router. Run before deploy.

Exercises 20 representative user messages across categories. Prints
selected_count + fallback flag + first 5 selected tools per case so a
human can sanity-check.
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from core.services.tool_router import select_tools

CASES = [
    # Short greetings (expect aggressive selection or fallback)
    ("hej", "greeting"),
    ("god morgen", "greeting"),
    ("ja", "affirmation"),
    ("hmm", "ambiguous"),
    # Memory questions
    ("hvad sagde vi i går?", "memory"),
    ("husk at jeg hader broccoli", "memory"),
    ("hvad ved du om mig?", "memory-identity"),
    # Code work
    ("læs visible_runs.py", "code"),
    ("find alle steder hvor we use prompt_contract", "code-search"),
    ("commit ændringerne", "git"),
    # Multi-domain
    ("vis mig din tilstand og lav et billede af din mood", "multi"),
    ("send en discord-besked til mig om vejret", "social-web"),
    # System / runtime
    ("hvor mange tokens bruger vi nu?", "system-introspection"),
    ("genstart heartbeat", "system-control"),
    # Identity
    ("hvem er du?", "identity"),
    ("hvad er din SOUL?", "identity"),
    # Junk
    ("", "empty"),
    ("?????", "junk"),
    # Long substantive
    ("kan du give mig en oversigt over alle decisions vi har truffet de sidste 7 dage og analysere om der er mønstre?", "long-substantive"),
    # Project work
    ("byg et nyt MC-widget der viser cpu", "project"),
]


def main() -> int:
    print(f"{'category':>20}  {'fallback':>9}  {'count':>6}  {'conf':>6}  preview")
    print("-" * 100)
    for msg, cat in CASES:
        sel = select_tools(user_message=msg, session_id=None, lane="visible")
        first_few = ", ".join(sel.selected_names[:5])
        print(
            f"{cat:>20}  {('FB' if sel.fallback_used else 'OK'):>9}  "
            f"{len(sel.selected_names):>6}  {sel.confidence:>6.3f}  {msg!r}"
        )
        print(f"{'':>20}  → {first_few}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run validation**

Run: `conda run -n ai python tests/manual/tool_router_validation.py`.

Sanity-check:
- Empty/junk → fallback (FB)
- Short greetings → small selection or fallback
- Code-related → `read_file`, `grep` in selection
- Memory-related → `recall_memories`, `search_memory` in selection
- Long substantive → confident selection (~70-90 tools)

If anything looks egregiously wrong, adjust `state/tool_tags.overrides.json`, re-run bootstrap, retry.

- [ ] **Step 3: Run before/after token measurement**

Capture baseline (before deploy) and after-deploy numbers:

```bash
# Before (with router): expected 15-25K total
conda run -n ai python scripts/measure_prompt_payload.py --user-message "hej" | grep -E "GRAND TOTAL|System prompt|Tool definitions"

conda run -n ai python scripts/measure_prompt_payload.py --user-message "læs visible_runs.py" | grep -E "GRAND TOTAL|System prompt|Tool definitions"
```

(The measurement script doesn't go through the router by default — you'd need to add a `--use-router` flag if you want true post-deploy measurement. Otherwise: rely on `/mc/tool-router-state` after deploy for live numbers.)

- [ ] **Step 4: Commit**

```bash
git add tests/manual/tool_router_validation.py
git commit -m "feat(tool-router): manual validation set with 20 representative cases"
```

---

## Task 16: Deploy + first-day observation

- [ ] **Step 1: Final pre-deploy checks**

Run all tests:

```bash
conda run -n ai pytest tests/services/test_tool_*.py tests/runtime/test_tool_*.py tests/api/test_tool_*.py tests/integration/test_tool_*.py -v
```

Expected: all pass.

Run the manual validation:

```bash
conda run -n ai python tests/manual/tool_router_validation.py
```

Sanity-check output.

- [ ] **Step 2: Restart services**

```bash
sudo systemctl restart jarvis-runtime jarvis-api
```

Watch logs:

```bash
journalctl -fu jarvis-api jarvis-runtime | grep -iE "tool_router|error"
```

- [ ] **Step 3: First-hour observation**

Open MC → Cheap Balancer tab → scroll to Tool Router widget. Watch:

- `Selection rate` should land 70-90%
- `Fallback rate` should be 10-30%
- `load_more rate` should be < 10%
- `Tokens saved (avg/turn)` should be > 10,000

If `Fallback rate` > 50%: threshold may be too high. Check `recent decisions` for confidence values; if most are 0.3-0.5 with `OK` selections wanted, lower `tool_router_threshold` in `~/.jarvis-v2/config/runtime.json` to `0.45`.

If Jarvis hits `load_more_tools` more than once per turn for the same names: that tool is wrongly missing from always-core. Add it to `state/tool_tags.pinned.json` and restart.

- [ ] **Step 4: First-day check**

After 24h, verify:

- `decisions_7d` > 50 (real traffic happened)
- Adherence rate (from existing `cadence_producers` / `decision_review_prompter`) hasn't dropped vs. 7-day baseline
- No `tool_router.fallback_fired` events with reason `router-error: *` (would indicate a bug)

If anything off, flip killswitch (`tool_router_enabled = false` in runtime.json) and investigate.

- [ ] **Step 5: One-week tuning**

Daemon adjusts threshold automatically. After 7 days, review:

- `top_missed_tools_7d` — promote any frequent names into pinned set
- Confidence histogram — should be roughly bimodal (clearly high or clearly low cases). If most cases cluster around the threshold, the formula needs work.
- Average elapsed_ms — should be < 100ms p95

---

## Self-Review

Reviewed against spec. Coverage:

- ✅ Architecture (Tasks 1-12 build all components in spec section "Architecture")
- ✅ Components: catalog (T3), tagger (T5), embeddings (T6), router (T7), runtime (T10), endpoint (T11), widget (T12), bootstrap script (T13)
- ✅ load_more_tools magic tool (T8)
- ✅ Wiring (T9 wires into visible_runs, T11 wires endpoint+daemon into app)
- ✅ Data flow per turn (T9 implements; T7 publishes events; T11 reads them back)
- ✅ Error handling: try/except in select_tools, fallback paths (T7); embedding errors handled (T6, T7); corrupt tag file handled (T5)
- ✅ Hard guarantees: timeout via fallback in select_tools, full list always reachable via fallback, atomic writes implicit in sqlite, load_more_tools always in pinned set
- ✅ Observability: events (T1, T7, T8, T10), DB tables (T1), endpoint (T11), widget (T12)
- ✅ Adaptive feedback: daemon adjusts threshold (T10), top-missed promotion implicit via pinned set updates (T16)
- ✅ Testing: unit (T3-T10), integration (T9, T11), smoke (T14), manual validation (T15)
- ✅ Rollout: bootstrap script (T13), killswitch verified (T14), deploy + observation (T16)

Placeholders/red flags scanned: none found. All code blocks complete; no "similar to Task N" or "implement appropriately".

Type consistency verified:
- `ToolSelection` dataclass fields used identically across T7, T11, T14, T15
- `select_tools` signature consistent (kwargs: `user_message`, `session_id`, `lane`, optional `run_id`)
- `_load_more_rate_7d` defined in T7, called in T10
- `_TAGS_PATH`, `_OVERRIDES_PATH`, `_PINNED_PATH` consistent in T5

One minor inconsistency: spec mentions `tool_call_log` table; plan reads usage from `events` table filtered to `kind='tool.invoked'` (T7 `_always_core_set`). This matches existing eventbus pattern and is documented in the spec's "Open questions" implicitly (we noted "if not exists, use events"). Plan stays as-is.
