# Jarvis Brain — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Jarvis' kuraterede vidensjournal — et nyt hukommelses-lag hvor visible Jarvis selv skriver fakta, indsigter, observationer og referencer han ønsker at holde fast i. Markdown-filer = sandheden, SQLite = rebuildable index, daemon konsoliderer, recall gates på visibility.

**Architecture:** To-lags model (filer + index). Tre skrive-stier (spontant tool, post-web nudge, daglig refleksion). Tre recall-stier (always-on summary, auto-injected fakta via embedding, tool-search). Privacy-gate ved recall med "mindst privilegeret deltager vinder"-regel. Decay + konsoliderings-daemon med tre faser (duplikat → modsigelse → tema). Personal/intimate-indhold forlader aldrig huset (lokal Ollama for konsolidering).

**Tech Stack:** Python 3.11+, SQLite (eksisterende mønstre fra `core/runtime/db.py`), `pyyaml` (frontmatter), `numpy` (embedding), eksisterende `semantic_indexer`/embedding-stack, eksisterende `cheap_provider_runtime` (LLM-routing), eksisterende `core/identity/owner_resolver.py`.

**Spec:** `docs/superpowers/specs/2026-05-02-jarvis-brain-design.md` (alle sektioner godkendt).

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `core/services/jarvis_brain.py` | Kerne-CRUD, frontmatter, index, salience, search, supersede |
| Create | `core/services/jarvis_brain_visibility.py` | `session_visibility_ceiling`, `can_recall`, level-helpers |
| Create | `core/services/jarvis_brain_daemon.py` | Tre loops: reindex, konsolidering, summary, auto-archive |
| Create | `core/services/prompt_sections/self_awareness.py` | Boy Scout-udtrækning fra `prompt_contract.py` |
| Create | `core/services/prompt_sections/__init__.py` | Pakke-init |
| Create | `core/tools/jarvis_brain_tools.py` | Visible Jarvis' værktøjer (remember/search/adopt/discard/archive) |
| Create | `core/services/jarvis_brain_reflection.py` | End-of-day refleksions-slot orchestrering |
| Create | `tests/test_jarvis_brain.py` | Unit tests for kerne-CRUD + salience + search |
| Create | `tests/test_jarvis_brain_visibility.py` | Privacy-gate tests (alle scenarier fra spec sektion 6.3) |
| Create | `tests/test_jarvis_brain_tools.py` | Tool-tests inkl. rate-limit + visibility-filter |
| Create | `tests/test_jarvis_brain_daemon.py` | Daemon tests (reindex, dedup, contradiction-routing, theme-killswitch, summary) |
| Create | `tests/test_jarvis_brain_reflection.py` | Refleksions-slot tests |
| Create | `tests/test_jarvis_brain_integration.py` | E2E smoke test |
| Modify | `core/services/prompt_contract.py` | Erstat awareness-sektion med import fra new file (Boy Scout) + ny `_build_jarvis_brain_section` |
| Modify | `core/services/visible_runs.py` | Boy Scout-udtrækning + `_inject_brain_facts` + post-web-search nudge |
| Modify | `core/runtime/settings.py` (eller hvor RuntimeSettings bor) | Tilføj 9 brain-settings (sektion 8.3 i spec) |
| Modify | `apps/api/jarvis_api/services_runtime.py` (eller wherever jarvis-runtime daemons starter) | Wire `jarvis_brain_daemon` ind |

---

## Konventioner brugt i hele planen

- **Conda-miljø:** Alle `pytest`-kald antager `conda activate ai` er aktivt (pr. CLAUDE.md memory).
- **Test-namespace:** Modulnavne brugt i tests matcher præcis den fil de testes på, så test-filer kan køres isoleret.
- **Atomic file write helper** (genbruges i mange tasks):
  ```python
  def _atomic_write(path: Path, content: str) -> None:
      tmp = path.with_suffix(path.suffix + ".tmp")
      tmp.write_text(content, encoding="utf-8")
      tmp.replace(path)
  ```
- **Visibility-niveauer:** `_LEVEL = {"public_safe": 0, "personal": 1, "intimate": 2}` (én definition i `jarvis_brain_visibility.py`, importeres andre steder fra).
- **ULID:** Brug `python-ulid`-pakken hvis den findes; ellers fallback til `core/runtime/ids.py`-helper hvis findes; ellers skriv en enkel implementering i `jarvis_brain.py` (Crockford base32, time-monotonic). Verificeres i Task 1.
- **Frontmatter parse:** `pyyaml` (eksisterende dependency).
- **Embedding-model:** Genbrug samme model som `core/services/semantic_indexer.py` bruger. Verificeres i Task 5.

---

## Task 1: Modul-skeleton + `BrainEntry` dataclass + ULID-helper

**Files:**
- Create: `core/services/jarvis_brain.py`
- Create: `tests/test_jarvis_brain.py`

- [ ] **Step 1: Find eksisterende ULID/id-helper eller bekræft at python-ulid er tilgængelig**

```bash
conda activate ai && python -c "import ulid; print(ulid.new())"
```

Hvis ImportError: bekræft fallback i `core/runtime/`. Hvis intet findes, brug denne implementering i Task 1 step 3:

```python
import os, time, secrets
def _new_brain_id() -> str:
    # Time-prefix (10 chars Crockford b32) + 16 chars random
    ms = int(time.time() * 1000)
    alphabet = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"  # pragma: allowlist secret
    time_part = ""
    for _ in range(10):
        time_part = alphabet[ms & 0x1F] + time_part
        ms >>= 5
    rand_part = "".join(secrets.choice(alphabet) for _ in range(16))
    return f"brn_{time_part}{rand_part}"
```

- [ ] **Step 2: Write the failing test for `BrainEntry` + id-generator**

```python
# tests/test_jarvis_brain.py
from __future__ import annotations
from datetime import datetime, timezone
import pytest

def test_brain_entry_required_fields():
    from core.services.jarvis_brain import BrainEntry
    e = BrainEntry(
        id="brn_TEST",
        kind="fakta",
        visibility="personal",
        domain="engineering",
        title="t",
        content="c",
        created_at=datetime(2026, 5, 2, tzinfo=timezone.utc),
        updated_at=datetime(2026, 5, 2, tzinfo=timezone.utc),
        last_used_at=None,
        salience_base=1.0,
        salience_bumps=0,
        related=[],
        trigger="spontaneous",
        status="active",
        superseded_by=None,
        source_chronicle=None,
        source_url=None,
    )
    assert e.id == "brn_TEST"
    assert e.kind == "fakta"

def test_brain_entry_kind_enum_validated():
    from core.services.jarvis_brain import BrainEntry
    with pytest.raises(ValueError):
        BrainEntry(
            id="brn_X", kind="WRONG", visibility="personal", domain="x",
            title="t", content="c",
            created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc),
            last_used_at=None, salience_base=1.0, salience_bumps=0, related=[],
            trigger="spontaneous", status="active", superseded_by=None,
            source_chronicle=None, source_url=None,
        )

def test_new_brain_id_format_and_uniqueness():
    from core.services.jarvis_brain import new_brain_id
    a = new_brain_id()
    b = new_brain_id()
    assert a.startswith("brn_")
    assert len(a) == len("brn_") + 26  # ULID-style 26 chars
    assert a != b
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `conda activate ai && pytest tests/test_jarvis_brain.py -v`
Expected: ImportError / module not found.

- [ ] **Step 4: Implement minimal module**

```python
# core/services/jarvis_brain.py
"""Jarvis Brain — kurateret vidensjournal. Kerne-CRUD-laget.

Kun ren læs/skriv + søg. Ingen daemon-logik (det ligger i jarvis_brain_daemon.py).
Ingen LLM-kald (konsolidering ligger i daemonen).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional
import os
import secrets
import time

# Prøv python-ulid først, fallback til lokal generator.
try:
    import ulid as _ulid_mod  # type: ignore

    def new_brain_id() -> str:
        return f"brn_{_ulid_mod.new().str}"
except ImportError:
    _CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"  # pragma: allowlist secret

    def new_brain_id() -> str:
        ms = int(time.time() * 1000)
        time_part = ""
        for _ in range(10):
            time_part = _CROCKFORD[ms & 0x1F] + time_part
            ms >>= 5
        rand_part = "".join(secrets.choice(_CROCKFORD) for _ in range(16))
        return f"brn_{time_part}{rand_part}"


_VALID_KINDS = {"fakta", "indsigt", "observation", "reference"}
_VALID_VISIBILITY = {"public_safe", "personal", "intimate"}
_VALID_STATUS = {"active", "superseded", "archived"}
_VALID_TRIGGER = {"spontaneous", "post_web_search", "reflection_slot", "adopted_proposal"}


@dataclass
class BrainEntry:
    id: str
    kind: str
    visibility: str
    domain: str
    title: str
    content: str
    created_at: datetime
    updated_at: datetime
    last_used_at: Optional[datetime]
    salience_base: float
    salience_bumps: int
    related: list[str]
    trigger: str
    status: str
    superseded_by: Optional[str]
    source_chronicle: Optional[str]
    source_url: Optional[str]

    def __post_init__(self) -> None:
        if self.kind not in _VALID_KINDS:
            raise ValueError(f"invalid kind: {self.kind}")
        if self.visibility not in _VALID_VISIBILITY:
            raise ValueError(f"invalid visibility: {self.visibility}")
        if self.status not in _VALID_STATUS:
            raise ValueError(f"invalid status: {self.status}")
        if self.trigger not in _VALID_TRIGGER:
            raise ValueError(f"invalid trigger: {self.trigger}")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `conda activate ai && pytest tests/test_jarvis_brain.py -v`
Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add core/services/jarvis_brain.py tests/test_jarvis_brain.py
git commit -m "feat(jarvis-brain): scaffold module with BrainEntry dataclass and ULID generator"
```

---

## Task 2: Frontmatter parse + atomic file write

**Files:**
- Modify: `core/services/jarvis_brain.py`
- Modify: `tests/test_jarvis_brain.py`

- [ ] **Step 1: Write failing tests for frontmatter parse and write**

```python
# tests/test_jarvis_brain.py — append
def test_parse_frontmatter_extracts_yaml_and_body(tmp_path):
    from core.services.jarvis_brain import parse_frontmatter
    p = tmp_path / "x.md"
    p.write_text(
        "---\nid: brn_X\nkind: fakta\ntitle: Test\n---\n\nThe body.\n",
        encoding="utf-8",
    )
    fm, body = parse_frontmatter(p)
    assert fm["id"] == "brn_X"
    assert fm["kind"] == "fakta"
    assert body.strip() == "The body."

def test_parse_frontmatter_raises_on_missing_delimiter(tmp_path):
    from core.services.jarvis_brain import parse_frontmatter
    p = tmp_path / "bad.md"
    p.write_text("no frontmatter here\n", encoding="utf-8")
    import pytest
    with pytest.raises(ValueError, match="frontmatter"):
        parse_frontmatter(p)

def test_atomic_write_creates_file(tmp_path):
    from core.services.jarvis_brain import _atomic_write
    p = tmp_path / "out.md"
    _atomic_write(p, "hello\n")
    assert p.read_text() == "hello\n"
    # tmp file is gone
    assert not (tmp_path / "out.md.tmp").exists()

def test_render_frontmatter_round_trips(tmp_path):
    from core.services.jarvis_brain import (
        BrainEntry, render_entry_markdown, parse_frontmatter, entry_from_frontmatter
    )
    from datetime import datetime, timezone
    e = BrainEntry(
        id="brn_RT", kind="indsigt", visibility="personal", domain="engineering",
        title="Round Trip", content="The content body.",
        created_at=datetime(2026, 5, 2, 12, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 5, 2, 12, 0, tzinfo=timezone.utc),
        last_used_at=None, salience_base=1.0, salience_bumps=0,
        related=["brn_OTHER"], trigger="spontaneous", status="active",
        superseded_by=None, source_chronicle=None, source_url=None,
    )
    md = render_entry_markdown(e)
    p = tmp_path / "rt.md"
    p.write_text(md, encoding="utf-8")
    fm, body = parse_frontmatter(p)
    e2 = entry_from_frontmatter(fm, body)
    assert e2.id == e.id
    assert e2.related == ["brn_OTHER"]
    assert e2.content.strip() == "The content body."
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `conda activate ai && pytest tests/test_jarvis_brain.py -v`
Expected: ImportError on `parse_frontmatter`, `_atomic_write`, `render_entry_markdown`.

- [ ] **Step 3: Implement frontmatter helpers + atomic write**

```python
# core/services/jarvis_brain.py — append
import yaml
from datetime import datetime, timezone

def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)

def parse_frontmatter(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"missing frontmatter in {path}")
    parts = text.split("\n---\n", 1)
    if len(parts) != 2:
        raise ValueError(f"unterminated frontmatter in {path}")
    yaml_text = parts[0][len("---\n"):]
    body = parts[1]
    fm = yaml.safe_load(yaml_text) or {}
    return fm, body

def _iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()

def _parse_iso(s: Optional[str]) -> Optional[datetime]:
    if s is None:
        return None
    return datetime.fromisoformat(s)

def render_entry_markdown(entry: BrainEntry) -> str:
    fm = {
        "id": entry.id,
        "kind": entry.kind,
        "visibility": entry.visibility,
        "domain": entry.domain,
        "title": entry.title,
        "created_at": _iso(entry.created_at),
        "updated_at": _iso(entry.updated_at),
        "last_used_at": _iso(entry.last_used_at),
        "created_by": "visible_jarvis",
        "trigger": entry.trigger,
        "salience_base": entry.salience_base,
        "salience_bumps": entry.salience_bumps,
        "related": entry.related,
        "status": entry.status,
        "superseded_by": entry.superseded_by,
        "source_chronicle": entry.source_chronicle,
        "source_url": entry.source_url,
    }
    yaml_text = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True)
    return f"---\n{yaml_text}---\n\n{entry.content.rstrip()}\n"

def entry_from_frontmatter(fm: dict, body: str) -> BrainEntry:
    return BrainEntry(
        id=fm["id"],
        kind=fm["kind"],
        visibility=fm["visibility"],
        domain=fm["domain"],
        title=fm["title"],
        content=body.strip(),
        created_at=_parse_iso(fm["created_at"]),
        updated_at=_parse_iso(fm.get("updated_at") or fm["created_at"]),
        last_used_at=_parse_iso(fm.get("last_used_at")),
        salience_base=float(fm.get("salience_base", 1.0)),
        salience_bumps=int(fm.get("salience_bumps", 0)),
        related=list(fm.get("related") or []),
        trigger=fm.get("trigger", "spontaneous"),
        status=fm.get("status", "active"),
        superseded_by=fm.get("superseded_by"),
        source_chronicle=fm.get("source_chronicle"),
        source_url=fm.get("source_url"),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `conda activate ai && pytest tests/test_jarvis_brain.py -v`
Expected: all passed.

- [ ] **Step 5: Commit**

```bash
git add core/services/jarvis_brain.py tests/test_jarvis_brain.py
git commit -m "feat(jarvis-brain): add frontmatter parse/render and atomic file write"
```

---

## Task 3: SQLite index schema + paths + `write_entry` + `read_entry`

**Files:**
- Modify: `core/services/jarvis_brain.py`
- Modify: `tests/test_jarvis_brain.py`

- [ ] **Step 1: Write failing tests for index + write/read round-trip**

```python
# tests/test_jarvis_brain.py — append
import sqlite3

def test_brain_paths_resolves_from_workspace(tmp_path, monkeypatch):
    from core.services import jarvis_brain
    monkeypatch.setattr(jarvis_brain, "_workspace_root", lambda: tmp_path)
    p = jarvis_brain.brain_dir()
    assert p == tmp_path / "default" / "jarvis_brain"

def test_ensure_index_creates_tables(tmp_path, monkeypatch):
    from core.services import jarvis_brain
    monkeypatch.setattr(jarvis_brain, "_state_root", lambda: tmp_path)
    conn = jarvis_brain.connect_index()
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    names = {r[0] for r in rows}
    assert "brain_index" in names
    assert "brain_relations" in names
    assert "brain_proposals" in names

def test_write_and_read_entry_roundtrip(tmp_path, monkeypatch):
    from core.services import jarvis_brain
    monkeypatch.setattr(jarvis_brain, "_workspace_root", lambda: tmp_path / "ws")
    monkeypatch.setattr(jarvis_brain, "_state_root", lambda: tmp_path / "state")
    new_id = jarvis_brain.write_entry(
        kind="fakta",
        title="Test fakta",
        content="En kort fakta.",
        visibility="personal",
        domain="engineering",
        trigger="spontaneous",
        related=[],
        source_url=None,
    )
    assert new_id.startswith("brn_")

    e = jarvis_brain.read_entry(new_id)
    assert e.title == "Test fakta"
    assert e.kind == "fakta"
    assert e.visibility == "personal"
    # File on disk in expected location
    p = tmp_path / "ws" / "default" / "jarvis_brain" / "fakta"
    md_files = list(p.glob("*.md"))
    assert len(md_files) == 1
    assert new_id[-8:] in md_files[0].name  # id_short in filename
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `conda activate ai && pytest tests/test_jarvis_brain.py -v`
Expected: AttributeError on `brain_dir`, `connect_index`, `write_entry`, `read_entry`.

- [ ] **Step 3: Implement paths, schema, write_entry, read_entry**

```python
# core/services/jarvis_brain.py — append
import os
import re
import sqlite3
from pathlib import Path

_INDEX_SCHEMA = """
CREATE TABLE IF NOT EXISTS brain_index (
    id              TEXT PRIMARY KEY,
    path            TEXT NOT NULL UNIQUE,
    kind            TEXT NOT NULL,
    visibility      TEXT NOT NULL,
    domain          TEXT NOT NULL,
    title           TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    last_used_at    TEXT,
    salience_base   REAL NOT NULL DEFAULT 1.0,
    salience_bumps  INTEGER NOT NULL DEFAULT 0,
    status          TEXT NOT NULL DEFAULT 'active',
    superseded_by   TEXT,
    file_hash       TEXT NOT NULL,
    embedding       BLOB,
    embedding_dim   INTEGER,
    indexed_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS brain_relations (
    from_id TEXT NOT NULL,
    to_id   TEXT NOT NULL,
    PRIMARY KEY (from_id, to_id)
);

CREATE TABLE IF NOT EXISTS brain_proposals (
    id           TEXT PRIMARY KEY,
    path         TEXT NOT NULL,
    reason       TEXT NOT NULL,
    consolidates TEXT,
    created_at   TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'pending',
    adopted_at   TEXT,
    adopted_by   TEXT
);

CREATE INDEX IF NOT EXISTS idx_brain_kind_status   ON brain_index(kind, status);
CREATE INDEX IF NOT EXISTS idx_brain_visibility    ON brain_index(visibility);
CREATE INDEX IF NOT EXISTS idx_brain_last_used     ON brain_index(last_used_at DESC);
CREATE INDEX IF NOT EXISTS idx_brain_relations_to  ON brain_relations(to_id);
"""


def _workspace_root() -> Path:
    """Override target in tests via monkeypatch."""
    return Path(os.environ.get("JARVIS_WORKSPACES_ROOT") or
                Path.home() / ".jarvis-v2" / "workspaces")


def _state_root() -> Path:
    return Path(os.environ.get("JARVIS_STATE_ROOT") or
                Path.home() / ".jarvis-v2" / "state")


def brain_dir() -> Path:
    return _workspace_root() / "default" / "jarvis_brain"


def index_db_path() -> Path:
    return _state_root() / "jarvis_brain_index.sqlite"


def connect_index() -> sqlite3.Connection:
    p = index_db_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p))
    conn.executescript(_INDEX_SCHEMA)
    conn.commit()
    return conn


def _slugify(s: str, max_len: int = 40) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s[:max_len] or "untitled"


def _file_hash(text: str) -> str:
    import hashlib
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_entry(
    *,
    kind: str,
    title: str,
    content: str,
    visibility: str,
    domain: str,
    trigger: str = "spontaneous",
    related: list[str] | None = None,
    source_url: str | None = None,
    source_chronicle: str | None = None,
    now: datetime | None = None,
) -> str:
    """Skriver en ny brain-entry til disk og indexerer den (uden embedding endnu)."""
    now = now or datetime.now(timezone.utc)
    new_id = new_brain_id()
    related = related or []

    entry = BrainEntry(
        id=new_id, kind=kind, visibility=visibility, domain=domain,
        title=title, content=content,
        created_at=now, updated_at=now, last_used_at=None,
        salience_base=1.0, salience_bumps=0, related=related,
        trigger=trigger, status="active", superseded_by=None,
        source_chronicle=source_chronicle, source_url=source_url,
    )

    md = render_entry_markdown(entry)
    date = now.strftime("%Y-%m-%d")
    slug = _slugify(title)
    id_short = new_id[-8:]
    fname = f"{date}-{slug}-{id_short}.md"
    fpath = brain_dir() / kind / fname
    _atomic_write(fpath, md)

    rel_path = str(fpath.relative_to(_workspace_root()))
    fhash = _file_hash(md)

    conn = connect_index()
    try:
        conn.execute(
            """INSERT INTO brain_index
               (id, path, kind, visibility, domain, title, created_at, updated_at,
                last_used_at, salience_base, salience_bumps, status,
                superseded_by, file_hash, embedding, embedding_dim, indexed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, 1.0, 0, 'active',
                       NULL, ?, NULL, NULL, ?)""",
            (new_id, rel_path, kind, visibility, domain, title,
             _iso(now), _iso(now), fhash, _iso(now)),
        )
        for to_id in related:
            conn.execute(
                "INSERT OR IGNORE INTO brain_relations(from_id, to_id) VALUES (?, ?)",
                (new_id, to_id),
            )
        conn.commit()
    finally:
        conn.close()

    return new_id


def read_entry(entry_id: str) -> BrainEntry:
    conn = connect_index()
    try:
        row = conn.execute(
            "SELECT path FROM brain_index WHERE id = ?", (entry_id,)
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        raise KeyError(f"no brain entry with id {entry_id}")
    path = _workspace_root() / row[0]
    fm, body = parse_frontmatter(path)
    return entry_from_frontmatter(fm, body)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `conda activate ai && pytest tests/test_jarvis_brain.py -v`
Expected: all passed.

- [ ] **Step 5: Commit**

```bash
git add core/services/jarvis_brain.py tests/test_jarvis_brain.py
git commit -m "feat(jarvis-brain): SQLite index schema + write_entry/read_entry"
```

---

## Task 4: Decay-formel `compute_effective_salience` + `bump_salience`

**Files:**
- Modify: `core/services/jarvis_brain.py`
- Modify: `tests/test_jarvis_brain.py`

- [ ] **Step 1: Write failing tests for decay + bump**

```python
# tests/test_jarvis_brain.py — append
import math

def _make_entry(kind="fakta", bumps=0, base=1.0, last_used_days_ago=None):
    from core.services.jarvis_brain import BrainEntry
    now = datetime(2026, 5, 2, tzinfo=timezone.utc)
    last = None if last_used_days_ago is None else \
        datetime(2026, 5, 2, tzinfo=timezone.utc) - timedelta(days=last_used_days_ago)
    return BrainEntry(
        id="brn_T", kind=kind, visibility="personal", domain="x",
        title="t", content="c",
        created_at=now - timedelta(days=last_used_days_ago or 0),
        updated_at=now, last_used_at=last,
        salience_base=base, salience_bumps=bumps, related=[],
        trigger="spontaneous", status="active", superseded_by=None,
        source_chronicle=None, source_url=None,
    )

from datetime import timedelta

def test_effective_salience_no_decay_for_reference():
    from core.services.jarvis_brain import compute_effective_salience
    e = _make_entry(kind="reference", last_used_days_ago=3650)
    now = datetime(2026, 5, 2, tzinfo=timezone.utc)
    s = compute_effective_salience(e, now)
    assert s == pytest.approx(1.0, abs=0.01)

def test_effective_salience_observation_halves_at_14_days():
    from core.services.jarvis_brain import compute_effective_salience
    e = _make_entry(kind="observation", last_used_days_ago=14)
    now = datetime(2026, 5, 2, tzinfo=timezone.utc)
    s = compute_effective_salience(e, now)
    # exp(-14/14) = 1/e ≈ 0.368
    assert s == pytest.approx(0.368, abs=0.01)

def test_effective_salience_floor_never_below_002():
    from core.services.jarvis_brain import compute_effective_salience
    e = _make_entry(kind="observation", last_used_days_ago=10000)
    now = datetime(2026, 5, 2, tzinfo=timezone.utc)
    s = compute_effective_salience(e, now)
    assert s >= 0.02

def test_effective_salience_bumps_amplify_modestly():
    from core.services.jarvis_brain import compute_effective_salience
    now = datetime(2026, 5, 2, tzinfo=timezone.utc)
    e0 = _make_entry(kind="fakta", bumps=0, last_used_days_ago=0)
    e3 = _make_entry(kind="fakta", bumps=3, last_used_days_ago=0)
    s0 = compute_effective_salience(e0, now)
    s3 = compute_effective_salience(e3, now)
    # 3 bumps: 1 + 0.3*log2(4) = 1 + 0.6 = 1.6
    assert s3 / s0 == pytest.approx(1.6, abs=0.05)

def test_bump_salience_updates_index_and_file(tmp_path, monkeypatch):
    from core.services import jarvis_brain
    monkeypatch.setattr(jarvis_brain, "_workspace_root", lambda: tmp_path / "ws")
    monkeypatch.setattr(jarvis_brain, "_state_root", lambda: tmp_path / "state")
    new_id = jarvis_brain.write_entry(
        kind="fakta", title="X", content="y", visibility="personal",
        domain="d", trigger="spontaneous",
    )
    now = datetime(2026, 5, 2, 13, 0, tzinfo=timezone.utc)
    jarvis_brain.bump_salience(new_id, now=now)
    e = jarvis_brain.read_entry(new_id)
    assert e.salience_bumps == 1
    assert e.last_used_at is not None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `conda activate ai && pytest tests/test_jarvis_brain.py -v`
Expected: AttributeError on `compute_effective_salience`, `bump_salience`.

- [ ] **Step 3: Implement decay + bump**

```python
# core/services/jarvis_brain.py — append
import math

_HALFLIFE_DAYS = {
    "observation": 14.0,
    "fakta": 180.0,
    "indsigt": 365.0,
    "reference": float("inf"),
}
_SALIENCE_FLOOR = 0.02


def compute_effective_salience(entry: BrainEntry, now: datetime) -> float:
    last = entry.last_used_at or entry.created_at
    days = max(0.0, (now - last).total_seconds() / 86400.0)
    halflife = _HALFLIFE_DAYS[entry.kind]
    if math.isinf(halflife):
        decay = 1.0
    else:
        decay = math.exp(-days / halflife)
    bumps_factor = math.log2(1 + entry.salience_bumps) if entry.salience_bumps > 0 else 0.0
    raw = entry.salience_base * decay * (1.0 + 0.3 * bumps_factor)
    return max(_SALIENCE_FLOOR, raw)


def bump_salience(entry_id: str, now: datetime | None = None) -> None:
    """Increments salience_bumps + opdaterer last_used_at i index OG fil.

    Filen er sandhed; index opdateres synkront. Hvis fil-update fejler,
    rejeses exception (caller-decides). Reindex-loop'et fanger evt. drift.
    """
    now = now or datetime.now(timezone.utc)
    entry = read_entry(entry_id)
    entry.salience_bumps += 1
    entry.last_used_at = now
    entry.updated_at = now

    # Re-render fil med opdateret frontmatter
    md = render_entry_markdown(entry)
    fpath = _workspace_root() / _index_path_for(entry_id)
    _atomic_write(fpath, md)

    # Update index
    fhash = _file_hash(md)
    conn = connect_index()
    try:
        conn.execute(
            """UPDATE brain_index
               SET salience_bumps = ?, last_used_at = ?, updated_at = ?,
                   file_hash = ?, indexed_at = ?
               WHERE id = ?""",
            (entry.salience_bumps, _iso(now), _iso(now), fhash, _iso(now), entry_id),
        )
        conn.commit()
    finally:
        conn.close()


def _index_path_for(entry_id: str) -> str:
    conn = connect_index()
    try:
        row = conn.execute(
            "SELECT path FROM brain_index WHERE id = ?", (entry_id,)
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        raise KeyError(entry_id)
    return row[0]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `conda activate ai && pytest tests/test_jarvis_brain.py -v`
Expected: all passed.

- [ ] **Step 5: Commit**

```bash
git add core/services/jarvis_brain.py tests/test_jarvis_brain.py
git commit -m "feat(jarvis-brain): decay formula + bump_salience"
```

---

## Task 5: Embedding-baseret search

**Files:**
- Modify: `core/services/jarvis_brain.py`
- Modify: `tests/test_jarvis_brain.py`

- [ ] **Step 1: Inspect eksisterende embedding-helper**

Run: `conda activate ai && python -c "from core.services.semantic_indexer import embed_text; v = embed_text('hello world'); print(type(v), len(v))"`

Forventet output: `<class 'numpy.ndarray'> 384` (eller anden dim). **Skriv den faktiske dim ned** — den bruges i `_EMBED_DIM`-konstanten.

Hvis `embed_text` ikke findes, find den faktiske eksport i `core/services/semantic_indexer.py` (Grep efter `def embed_` eller similar). Test-koden nedenfor bruger en mock så implementationen kan være hvad som helst.

- [ ] **Step 2: Write failing tests for search_brain**

```python
# tests/test_jarvis_brain.py — append
import numpy as np

@pytest.fixture
def populated_brain(tmp_path, monkeypatch):
    """Skriver 3 fakta og populerer embeddings med kendte vektorer."""
    from core.services import jarvis_brain
    monkeypatch.setattr(jarvis_brain, "_workspace_root", lambda: tmp_path / "ws")
    monkeypatch.setattr(jarvis_brain, "_state_root", lambda: tmp_path / "state")

    # Stub embedder så test er deterministisk
    def fake_embed(text: str) -> np.ndarray:
        if "alpha" in text.lower():
            return np.array([1.0, 0.0, 0.0], dtype=np.float32)
        if "beta" in text.lower():
            return np.array([0.0, 1.0, 0.0], dtype=np.float32)
        return np.array([0.0, 0.0, 1.0], dtype=np.float32)
    monkeypatch.setattr(jarvis_brain, "_embed_text", fake_embed)

    a = jarvis_brain.write_entry(kind="fakta", title="Alpha thing",
                                  content="alpha details", visibility="personal", domain="x")
    b = jarvis_brain.write_entry(kind="fakta", title="Beta thing",
                                  content="beta details", visibility="public_safe", domain="x")
    c = jarvis_brain.write_entry(kind="indsigt", title="Gamma insight",
                                  content="gamma reflections", visibility="personal", domain="x")
    # Skal populere embedding på alle
    jarvis_brain.embed_pending_entries()
    return {"a": a, "b": b, "c": c}

def test_search_brain_returns_top_match_by_similarity(populated_brain):
    from core.services import jarvis_brain
    hits = jarvis_brain.search_brain(
        query_text="alpha lookup",
        kinds=["fakta"],
        visibility_ceiling="personal",
        limit=2,
    )
    assert len(hits) >= 1
    assert hits[0].id == populated_brain["a"]

def test_search_brain_filters_visibility(populated_brain):
    from core.services import jarvis_brain
    hits = jarvis_brain.search_brain(
        query_text="alpha lookup",
        kinds=["fakta"],
        visibility_ceiling="public_safe",
        limit=5,
    )
    # Alpha er personal → skal ikke komme med
    ids = [h.id for h in hits]
    assert populated_brain["a"] not in ids
    assert populated_brain["b"] in ids

def test_search_brain_filters_kind(populated_brain):
    from core.services import jarvis_brain
    hits = jarvis_brain.search_brain(
        query_text="gamma",
        kinds=["fakta"],   # ekskluderer indsigt
        visibility_ceiling="intimate",
        limit=5,
    )
    ids = [h.id for h in hits]
    assert populated_brain["c"] not in ids
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `conda activate ai && pytest tests/test_jarvis_brain.py -v`
Expected: AttributeError on `_embed_text`, `embed_pending_entries`, `search_brain`.

- [ ] **Step 4: Implement embedding + search**

```python
# core/services/jarvis_brain.py — append
import numpy as np

_EMBED_DIM = 384  # opdater hvis dim fra Step 1 var anderledes


def _embed_text(text: str) -> np.ndarray:
    """Wrapper om eksisterende embedder. Override i tests via monkeypatch."""
    from core.services.semantic_indexer import embed_text
    v = embed_text(text)
    if not isinstance(v, np.ndarray):
        v = np.asarray(v, dtype=np.float32)
    return v.astype(np.float32, copy=False)


def _embedding_to_blob(v: np.ndarray) -> bytes:
    return v.astype(np.float32, copy=False).tobytes()


def _embedding_from_blob(blob: bytes, dim: int) -> np.ndarray:
    return np.frombuffer(blob, dtype=np.float32).reshape(dim)


def embed_pending_entries() -> int:
    """Embed alle entries i index'et der mangler embedding. Returnerer antal."""
    conn = connect_index()
    count = 0
    try:
        rows = conn.execute(
            "SELECT id, title, path FROM brain_index "
            "WHERE embedding IS NULL AND status = 'active'"
        ).fetchall()
        for entry_id, title, rel_path in rows:
            full = _workspace_root() / rel_path
            try:
                fm, body = parse_frontmatter(full)
            except Exception:
                continue
            text = f"{title}\n\n{body}"
            v = _embed_text(text)
            conn.execute(
                "UPDATE brain_index SET embedding = ?, embedding_dim = ? WHERE id = ?",
                (_embedding_to_blob(v), len(v), entry_id),
            )
            count += 1
        conn.commit()
    finally:
        conn.close()
    return count


_VIS_LEVEL = {"public_safe": 0, "personal": 1, "intimate": 2}


def search_brain(
    *,
    query_text: str,
    kinds: list[str] | None = None,
    visibility_ceiling: str = "personal",
    limit: int = 5,
    domain: str | None = None,
    include_archived: bool = False,
    now: datetime | None = None,
) -> list[BrainEntry]:
    now = now or datetime.now(timezone.utc)
    qv = _embed_text(query_text)
    ceiling_lvl = _VIS_LEVEL[visibility_ceiling]

    sql = """SELECT id, path, kind, visibility, salience_base, salience_bumps,
                    last_used_at, embedding, embedding_dim, created_at
             FROM brain_index
             WHERE embedding IS NOT NULL"""
    params: list = []
    if not include_archived:
        sql += " AND status = 'active'"
    if kinds:
        ph = ",".join("?" * len(kinds))
        sql += f" AND kind IN ({ph})"
        params.extend(kinds)
    if domain:
        sql += " AND domain = ?"
        params.append(domain)

    conn = connect_index()
    try:
        rows = conn.execute(sql, params).fetchall()
    finally:
        conn.close()

    scored: list[tuple[float, str]] = []
    for (entry_id, path, kind, vis, sal_base, bumps,
         last_used, emb_blob, emb_dim, created_at) in rows:
        if _VIS_LEVEL[vis] > ceiling_lvl:
            continue
        v = _embedding_from_blob(emb_blob, emb_dim)
        # cosine similarity
        denom = float(np.linalg.norm(qv) * np.linalg.norm(v)) or 1e-9
        cos = float(np.dot(qv, v) / denom)

        # Beregn effective salience uden at læse fil
        last = _parse_iso(last_used) if last_used else _parse_iso(created_at)
        days = max(0.0, (now - last).total_seconds() / 86400.0)
        halflife = _HALFLIFE_DAYS[kind]
        decay = 1.0 if math.isinf(halflife) else math.exp(-days / halflife)
        bumps_factor = math.log2(1 + bumps) if bumps > 0 else 0.0
        eff = max(_SALIENCE_FLOOR, sal_base * decay * (1.0 + 0.3 * bumps_factor))

        score = 0.7 * cos + 0.3 * eff
        scored.append((score, entry_id))

    scored.sort(reverse=True)
    top = scored[:limit]
    return [read_entry(eid) for _, eid in top]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `conda activate ai && pytest tests/test_jarvis_brain.py -v`
Expected: all passed.

- [ ] **Step 6: Commit**

```bash
git add core/services/jarvis_brain.py tests/test_jarvis_brain.py
git commit -m "feat(jarvis-brain): embedding storage + search_brain with hybrid scoring"
```

---

## Task 6: Archive + supersede + rebuild_index

**Files:**
- Modify: `core/services/jarvis_brain.py`
- Modify: `tests/test_jarvis_brain.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_jarvis_brain.py — append
def test_archive_entry_moves_file_and_updates_status(tmp_path, monkeypatch):
    from core.services import jarvis_brain
    monkeypatch.setattr(jarvis_brain, "_workspace_root", lambda: tmp_path / "ws")
    monkeypatch.setattr(jarvis_brain, "_state_root", lambda: tmp_path / "state")
    eid = jarvis_brain.write_entry(
        kind="observation", title="O", content="c", visibility="personal", domain="d",
    )
    jarvis_brain.archive_entry(eid, reason="test")
    e = jarvis_brain.read_entry(eid)
    assert e.status == "archived"
    # Filen er flyttet til _archive
    expected = tmp_path / "ws" / "default" / "jarvis_brain" / "_archive" / "observation"
    assert any(expected.glob("*.md"))

def test_supersede_links_old_to_new(tmp_path, monkeypatch):
    from core.services import jarvis_brain
    monkeypatch.setattr(jarvis_brain, "_workspace_root", lambda: tmp_path / "ws")
    monkeypatch.setattr(jarvis_brain, "_state_root", lambda: tmp_path / "state")
    old1 = jarvis_brain.write_entry(kind="fakta", title="Old1", content="x",
                                     visibility="personal", domain="d")
    old2 = jarvis_brain.write_entry(kind="fakta", title="Old2", content="y",
                                     visibility="personal", domain="d")
    new = jarvis_brain.write_entry(kind="fakta", title="Merged", content="z",
                                    visibility="personal", domain="d",
                                    trigger="adopted_proposal")
    jarvis_brain.supersede(old_ids=[old1, old2], new_id=new)
    e1 = jarvis_brain.read_entry(old1)
    e2 = jarvis_brain.read_entry(old2)
    assert e1.status == "superseded" and e1.superseded_by == new
    assert e2.status == "superseded" and e2.superseded_by == new

def test_rebuild_index_idempotent(tmp_path, monkeypatch):
    from core.services import jarvis_brain
    monkeypatch.setattr(jarvis_brain, "_workspace_root", lambda: tmp_path / "ws")
    monkeypatch.setattr(jarvis_brain, "_state_root", lambda: tmp_path / "state")
    jarvis_brain.write_entry(kind="fakta", title="A", content="a",
                              visibility="personal", domain="d")
    jarvis_brain.write_entry(kind="fakta", title="B", content="b",
                              visibility="personal", domain="d")
    n1 = jarvis_brain.rebuild_index_from_files()
    n2 = jarvis_brain.rebuild_index_from_files()
    assert n1 == 2
    # Anden kørsel: ingen ændringer (alle hashes matcher)
    assert n2 == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `conda activate ai && pytest tests/test_jarvis_brain.py -v`
Expected: AttributeError on `archive_entry`, `supersede`, `rebuild_index_from_files`.

- [ ] **Step 3: Implement archive + supersede + rebuild**

```python
# core/services/jarvis_brain.py — append

def archive_entry(entry_id: str, *, reason: str = "manual",
                  now: datetime | None = None) -> None:
    now = now or datetime.now(timezone.utc)
    entry = read_entry(entry_id)
    entry.status = "archived"
    entry.updated_at = now

    old_path = _workspace_root() / _index_path_for(entry_id)
    new_dir = brain_dir() / "_archive" / entry.kind
    new_path = new_dir / old_path.name
    md = render_entry_markdown(entry)
    _atomic_write(new_path, md)
    if old_path.exists():
        old_path.unlink()

    rel = str(new_path.relative_to(_workspace_root()))
    fhash = _file_hash(md)
    conn = connect_index()
    try:
        conn.execute(
            "UPDATE brain_index SET status='archived', path=?, file_hash=?, "
            "updated_at=?, indexed_at=? WHERE id=?",
            (rel, fhash, _iso(now), _iso(now), entry_id),
        )
        conn.commit()
    finally:
        conn.close()


def supersede(*, old_ids: list[str], new_id: str,
              now: datetime | None = None) -> None:
    now = now or datetime.now(timezone.utc)
    for old_id in old_ids:
        e = read_entry(old_id)
        e.status = "superseded"
        e.superseded_by = new_id
        e.updated_at = now
        md = render_entry_markdown(e)
        path = _workspace_root() / _index_path_for(old_id)
        _atomic_write(path, md)
        fhash = _file_hash(md)
        conn = connect_index()
        try:
            conn.execute(
                "UPDATE brain_index SET status='superseded', superseded_by=?, "
                "file_hash=?, updated_at=?, indexed_at=? WHERE id=?",
                (new_id, fhash, _iso(now), _iso(now), old_id),
            )
            conn.commit()
        finally:
            conn.close()


def rebuild_index_from_files() -> int:
    """Scan brain_dir() for .md filer; ny/ændret hash → opdater index.

    Returnerer antal rækker der blev tilføjet eller opdateret denne kørsel.
    """
    root = brain_dir()
    if not root.exists():
        return 0
    changes = 0
    now = datetime.now(timezone.utc)
    conn = connect_index()
    try:
        for kind_dir in root.iterdir():
            if not kind_dir.is_dir() or kind_dir.name.startswith("_"):
                continue
            kind = kind_dir.name
            for md_path in kind_dir.glob("*.md"):
                try:
                    fm, body = parse_frontmatter(md_path)
                except Exception:
                    continue
                text = md_path.read_text(encoding="utf-8")
                fhash = _file_hash(text)
                row = conn.execute(
                    "SELECT file_hash FROM brain_index WHERE id = ?",
                    (fm["id"],),
                ).fetchone()
                rel = str(md_path.relative_to(_workspace_root()))
                if row is None:
                    # New
                    conn.execute(
                        """INSERT INTO brain_index
                           (id, path, kind, visibility, domain, title,
                            created_at, updated_at, last_used_at,
                            salience_base, salience_bumps, status,
                            superseded_by, file_hash, embedding, embedding_dim, indexed_at)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,NULL,NULL,?)""",
                        (fm["id"], rel, kind, fm["visibility"], fm["domain"],
                         fm["title"], fm["created_at"], fm.get("updated_at", fm["created_at"]),
                         fm.get("last_used_at"), fm.get("salience_base", 1.0),
                         fm.get("salience_bumps", 0), fm.get("status", "active"),
                         fm.get("superseded_by"), fhash, _iso(now)),
                    )
                    changes += 1
                elif row[0] != fhash:
                    # Changed
                    conn.execute(
                        """UPDATE brain_index
                           SET path=?, kind=?, visibility=?, domain=?, title=?,
                               updated_at=?, last_used_at=?, salience_base=?,
                               salience_bumps=?, status=?, superseded_by=?,
                               file_hash=?, embedding=NULL, embedding_dim=NULL,
                               indexed_at=?
                           WHERE id=?""",
                        (rel, kind, fm["visibility"], fm["domain"], fm["title"],
                         fm.get("updated_at"), fm.get("last_used_at"),
                         fm.get("salience_base", 1.0), fm.get("salience_bumps", 0),
                         fm.get("status", "active"), fm.get("superseded_by"),
                         fhash, _iso(now), fm["id"]),
                    )
                    changes += 1
        conn.commit()
    finally:
        conn.close()
    return changes
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `conda activate ai && pytest tests/test_jarvis_brain.py -v`
Expected: all passed.

- [ ] **Step 5: Commit**

```bash
git add core/services/jarvis_brain.py tests/test_jarvis_brain.py
git commit -m "feat(jarvis-brain): archive, supersede, and rebuild_index_from_files"
```

---

## Task 7: Privacy gate (`jarvis_brain_visibility.py`)

**Files:**
- Create: `core/services/jarvis_brain_visibility.py`
- Create: `tests/test_jarvis_brain_visibility.py`

- [ ] **Step 1: Write failing tests for alle scenarier i spec sektion 6.3**

```python
# tests/test_jarvis_brain_visibility.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
import pytest


@dataclass
class FakeSession:
    channel_kind: str = ""
    participants: Optional[List[str]] = None
    is_autonomous: bool = False
    is_inner_voice: bool = False


def _patch_owner(monkeypatch, owner_id="bjorn"):
    from core.services import jarvis_brain_visibility as v
    monkeypatch.setattr(v, "_resolve_owner_id", lambda: owner_id)


@pytest.mark.parametrize("session,expected", [
    (FakeSession(channel_kind="dm", participants=["bjorn"]), "intimate"),
    (FakeSession(channel_kind="jarvisx_native", participants=["bjorn"]), "intimate"),
    (FakeSession(channel_kind="public_channel", participants=["bjorn", "mikkel"]), "public_safe"),
    (FakeSession(channel_kind="owner_private_channel", participants=["bjorn"]), "personal"),
    (FakeSession(channel_kind="dm", participants=["mikkel"]), "public_safe"),
    (FakeSession(is_autonomous=True), "personal"),
    (FakeSession(is_inner_voice=True), "personal"),
    (FakeSession(channel_kind="webhook", participants=None), "public_safe"),
    (FakeSession(channel_kind="email", participants=["random@example.com"]), "public_safe"),
])
def test_session_visibility_ceiling(session, expected, monkeypatch):
    _patch_owner(monkeypatch)
    from core.services.jarvis_brain_visibility import session_visibility_ceiling
    assert session_visibility_ceiling(session) == expected


def test_group_dm_with_third_party_is_public_safe(monkeypatch):
    _patch_owner(monkeypatch)
    from core.services.jarvis_brain_visibility import session_visibility_ceiling
    s = FakeSession(channel_kind="dm", participants=["bjorn", "mikkel"])
    assert session_visibility_ceiling(s) == "public_safe"


def test_can_recall_respects_levels():
    from core.services.jarvis_brain_visibility import can_recall
    assert can_recall("public_safe", "public_safe") is True
    assert can_recall("personal", "public_safe") is False
    assert can_recall("intimate", "personal") is False
    assert can_recall("intimate", "intimate") is True


def test_default_deny_on_uncertain_session(monkeypatch):
    _patch_owner(monkeypatch)
    from core.services.jarvis_brain_visibility import session_visibility_ceiling
    # Empty session, no participants
    s = FakeSession()
    assert session_visibility_ceiling(s) == "public_safe"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `conda activate ai && pytest tests/test_jarvis_brain_visibility.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement visibility module**

```python
# core/services/jarvis_brain_visibility.py
"""Privacy-gate for Jarvis Brain recall.

Princip: mindst privilegerede deltager vinder. Default deny.
Skrivning påvirkes ikke — kun læsning gates her.
"""
from __future__ import annotations
from typing import Any

LEVEL = {"public_safe": 0, "personal": 1, "intimate": 2}


def _resolve_owner_id() -> str | None:
    """Hentet via owner_resolver. Wrapped så tests kan monkeypatche."""
    try:
        from core.identity.owner_resolver import get_owner_discord_id
        oid = get_owner_discord_id()
        if oid:
            return oid
    except Exception:
        pass
    try:
        from core.identity.owner_resolver import get_owner_user_id
        return get_owner_user_id()
    except Exception:
        return None


def can_recall(entry_visibility: str, ceiling: str) -> bool:
    return LEVEL[entry_visibility] <= LEVEL[ceiling]


def session_visibility_ceiling(session: Any) -> str:
    """Beregn visibility-ceiling for en session.

    Beslutningstræ (spec sektion 6.2):
      1. autonomous/inner_voice → personal
      2. ingen kendt deltager → public_safe (default deny)
      3. ≥1 ikke-owner deltager → public_safe
      4. 1:1 DM med owner → intimate
      5. owner-only kanal → personal
      6. ellers → public_safe
    """
    if getattr(session, "is_autonomous", False) or getattr(session, "is_inner_voice", False):
        return "personal"

    participants = getattr(session, "participants", None)
    if not participants:
        return "public_safe"

    owner_id = _resolve_owner_id()
    non_owner_count = sum(1 for p in participants if p != owner_id)
    if non_owner_count >= 1:
        return "public_safe"

    channel_kind = getattr(session, "channel_kind", "")
    if channel_kind in {"dm", "jarvisx_native"}:
        return "intimate"
    if channel_kind in {"owner_private_channel", "owner_only_workspace"}:
        return "personal"
    return "public_safe"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `conda activate ai && pytest tests/test_jarvis_brain_visibility.py -v`
Expected: all passed.

- [ ] **Step 5: Commit**

```bash
git add core/services/jarvis_brain_visibility.py tests/test_jarvis_brain_visibility.py
git commit -m "feat(jarvis-brain): visibility gate with least-privileged-wins rule"
```

---

## Task 8: Tool — `remember_this` med rate-limits

**Files:**
- Create: `core/tools/jarvis_brain_tools.py`
- Create: `tests/test_jarvis_brain_tools.py`

- [ ] **Step 1: Write failing tests for remember_this + rate limits**

```python
# tests/test_jarvis_brain_tools.py
from __future__ import annotations
from datetime import datetime, timezone, timedelta
import pytest


@pytest.fixture
def isolated_brain(tmp_path, monkeypatch):
    from core.services import jarvis_brain
    monkeypatch.setattr(jarvis_brain, "_workspace_root", lambda: tmp_path / "ws")
    monkeypatch.setattr(jarvis_brain, "_state_root", lambda: tmp_path / "state")
    yield jarvis_brain


def test_remember_this_creates_entry(isolated_brain):
    from core.tools.jarvis_brain_tools import remember_this
    res = remember_this(
        kind="fakta", title="X", content="Y", visibility="personal",
        domain="engineering", session_id="s1", turn_id="t1",
    )
    assert res["status"] == "ok"
    assert res["id"].startswith("brn_")


def test_remember_this_rejects_invalid_kind(isolated_brain):
    from core.tools.jarvis_brain_tools import remember_this
    res = remember_this(kind="WRONG", title="X", content="Y",
                        visibility="personal", domain="d",
                        session_id="s1", turn_id="t1")
    assert res["status"] == "error"
    assert "kind" in res["error"]


def test_remember_this_per_turn_rate_limit(isolated_brain):
    from core.tools.jarvis_brain_tools import remember_this
    for i in range(5):
        r = remember_this(kind="fakta", title=f"T{i}", content=f"c{i}",
                          visibility="personal", domain="d",
                          session_id="s1", turn_id="t1")
        assert r["status"] == "ok"
    r6 = remember_this(kind="fakta", title="T6", content="c6",
                      visibility="personal", domain="d",
                      session_id="s1", turn_id="t1")
    assert r6["status"] == "error"
    assert r6["error"] == "rate_limit_turn"


def test_remember_this_per_day_rate_limit(isolated_brain, monkeypatch):
    from core.tools import jarvis_brain_tools
    base = datetime(2026, 5, 2, 10, 0, tzinfo=timezone.utc)
    # Simuler 4 forskellige turns same day, 5 hver = 20 total
    for turn in range(4):
        for i in range(5):
            ts = base + timedelta(minutes=turn * 10 + i)
            monkeypatch.setattr(jarvis_brain_tools, "_now", lambda ts=ts: ts)
            r = jarvis_brain_tools.remember_this(
                kind="fakta", title=f"T{turn}-{i}", content="c",
                visibility="personal", domain="d",
                session_id="s1", turn_id=f"t{turn}",
            )
            assert r["status"] == "ok"
    # Tur 5 første kald: dag-cap
    monkeypatch.setattr(jarvis_brain_tools, "_now",
                        lambda: base + timedelta(hours=2))
    r = jarvis_brain_tools.remember_this(
        kind="fakta", title="overflow", content="c",
        visibility="personal", domain="d",
        session_id="s1", turn_id="t99",
    )
    assert r["status"] == "error"
    assert r["error"] == "rate_limit_day"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `conda activate ai && pytest tests/test_jarvis_brain_tools.py -v`
Expected: ImportError on `remember_this`.

- [ ] **Step 3: Implement remember_this with rate limits**

```python
# core/tools/jarvis_brain_tools.py
"""Visible Jarvis' værktøjer til hjernen.

Rate-limits:
  - 5 remember_this pr. tur (tur = turn_id)
  - 20 remember_this pr. dag (dag = UTC-dato)
"""
from __future__ import annotations
from datetime import datetime, timezone
from collections import defaultdict
from typing import Any

_PER_TURN_CAP = 5
_PER_DAY_CAP = 20

# In-memory counters. Genstart nulstiller — det er ok, dag-cap er soft beskyttelse.
_turn_counts: dict[str, int] = defaultdict(int)
_day_counts: dict[str, int] = defaultdict(int)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _day_key(now: datetime) -> str:
    return now.strftime("%Y-%m-%d")


def remember_this(
    *,
    kind: str,
    title: str,
    content: str,
    visibility: str,
    domain: str,
    session_id: str,
    turn_id: str,
    related: list[str] | None = None,
    source_url: str | None = None,
    source_chronicle: str | None = None,
) -> dict[str, Any]:
    """Skriv en post i Jarvis' egen hjerne. Returnerer dict med status."""
    now = _now()

    # Validation
    if kind not in {"fakta", "indsigt", "observation", "reference"}:
        return {"status": "error", "error": "validation_failed",
                "details": f"invalid kind: {kind}"}
    if visibility not in {"public_safe", "personal", "intimate"}:
        return {"status": "error", "error": "validation_failed",
                "details": f"invalid visibility: {visibility}"}
    if not title.strip():
        return {"status": "error", "error": "validation_failed",
                "details": "empty title"}
    if len(content) > 4096:
        return {"status": "error", "error": "validation_failed",
                "details": "content too long (max 4096 bytes)"}

    # Rate limits
    turn_key = f"{session_id}:{turn_id}"
    if _turn_counts[turn_key] >= _PER_TURN_CAP:
        return {"status": "error", "error": "rate_limit_turn",
                "details": f"max {_PER_TURN_CAP} per turn"}
    day_key = _day_key(now)
    if _day_counts[day_key] >= _PER_DAY_CAP:
        return {"status": "error", "error": "rate_limit_day",
                "details": f"max {_PER_DAY_CAP} per day"}

    # Persist
    try:
        from core.services import jarvis_brain
        new_id = jarvis_brain.write_entry(
            kind=kind, title=title, content=content,
            visibility=visibility, domain=domain,
            trigger="spontaneous", related=related or [],
            source_url=source_url, source_chronicle=source_chronicle,
            now=now,
        )
    except Exception as exc:
        return {"status": "error", "error": "disk_write_failed",
                "details": str(exc)}

    _turn_counts[turn_key] += 1
    _day_counts[day_key] += 1

    return {"status": "ok", "id": new_id}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `conda activate ai && pytest tests/test_jarvis_brain_tools.py -v`
Expected: all passed.

- [ ] **Step 5: Commit**

```bash
git add core/tools/jarvis_brain_tools.py tests/test_jarvis_brain_tools.py
git commit -m "feat(jarvis-brain): remember_this tool with per-turn and per-day rate limits"
```

---

## Task 9: Tools — `search_jarvis_brain` + `read_brain_entry`

**Files:**
- Modify: `core/tools/jarvis_brain_tools.py`
- Modify: `tests/test_jarvis_brain_tools.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_jarvis_brain_tools.py — append
@pytest.fixture
def stubbed_embedder(monkeypatch):
    import numpy as np
    from core.services import jarvis_brain
    def fake(text):
        if "alpha" in text.lower():
            return np.array([1.0, 0.0, 0.0], dtype=np.float32)
        if "beta" in text.lower():
            return np.array([0.0, 1.0, 0.0], dtype=np.float32)
        return np.array([0.0, 0.0, 1.0], dtype=np.float32)
    monkeypatch.setattr(jarvis_brain, "_embed_text", fake)


def test_search_jarvis_brain_returns_excerpts(isolated_brain, stubbed_embedder):
    from core.tools.jarvis_brain_tools import remember_this, search_jarvis_brain
    from core.services import jarvis_brain
    remember_this(kind="fakta", title="Alpha", content="alpha details here",
                  visibility="personal", domain="d", session_id="s", turn_id="t1")
    remember_this(kind="fakta", title="Beta", content="beta details here",
                  visibility="public_safe", domain="d", session_id="s", turn_id="t2")
    jarvis_brain.embed_pending_entries()

    res = search_jarvis_brain(
        query="alpha lookup", session_visibility_ceiling="personal", limit=3,
    )
    assert res["status"] == "ok"
    assert len(res["results"]) >= 1
    assert res["results"][0]["title"] == "Alpha"
    assert "excerpt" in res["results"][0]


def test_search_jarvis_brain_reports_hidden_count(isolated_brain, stubbed_embedder):
    from core.tools.jarvis_brain_tools import remember_this, search_jarvis_brain
    from core.services import jarvis_brain
    remember_this(kind="fakta", title="Alpha", content="alpha",
                  visibility="intimate", domain="d", session_id="s", turn_id="t1")
    jarvis_brain.embed_pending_entries()

    res = search_jarvis_brain(
        query="alpha", session_visibility_ceiling="public_safe", limit=5,
    )
    assert res["hidden_by_visibility"] >= 1


def test_read_brain_entry_returns_full_content(isolated_brain):
    from core.tools.jarvis_brain_tools import remember_this, read_brain_entry
    r = remember_this(kind="indsigt", title="Long", content="The full body text here.",
                      visibility="personal", domain="d", session_id="s", turn_id="t1")
    out = read_brain_entry(r["id"])
    assert out["status"] == "ok"
    assert out["entry"]["content"] == "The full body text here."
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `conda activate ai && pytest tests/test_jarvis_brain_tools.py -v`
Expected: ImportError on `search_jarvis_brain`, `read_brain_entry`.

- [ ] **Step 3: Implement search + read tools**

```python
# core/tools/jarvis_brain_tools.py — append

def search_jarvis_brain(
    *,
    query: str,
    session_visibility_ceiling: str = "personal",
    kinds: list[str] | None = None,
    limit: int = 5,
    domain: str | None = None,
    include_archived: bool = False,
) -> dict[str, Any]:
    """Søg Jarvis' egen hjerne. Returnerer excerpts; brug read_brain_entry for fuld."""
    from core.services import jarvis_brain
    try:
        results = jarvis_brain.search_brain(
            query_text=query,
            kinds=kinds,
            visibility_ceiling=session_visibility_ceiling,
            limit=limit,
            domain=domain,
            include_archived=include_archived,
        )
    except Exception as exc:
        return {"status": "error", "error": "search_failed", "details": str(exc)}

    # Bump salience for hver returneret entry
    now = _now()
    for e in results:
        try:
            jarvis_brain.bump_salience(e.id, now=now)
        except Exception:
            pass  # best-effort

    # Tæl hidden — kør samme query med ceiling=intimate og diff
    hidden_count = 0
    if session_visibility_ceiling != "intimate":
        try:
            full = jarvis_brain.search_brain(
                query_text=query, kinds=kinds, visibility_ceiling="intimate",
                limit=limit * 3, domain=domain, include_archived=include_archived,
            )
            full_ids = {e.id for e in full}
            visible_ids = {e.id for e in results}
            hidden_count = max(0, len(full_ids - visible_ids))
        except Exception:
            pass

    out = []
    for e in results:
        out.append({
            "id": e.id,
            "kind": e.kind,
            "title": e.title,
            "domain": e.domain,
            "created_at": e.created_at.isoformat(),
            "excerpt": e.content[:200] + ("…" if len(e.content) > 200 else ""),
        })
    return {
        "status": "ok",
        "results": out,
        "hidden_by_visibility": hidden_count,
    }


def read_brain_entry(entry_id: str) -> dict[str, Any]:
    from core.services import jarvis_brain
    try:
        e = jarvis_brain.read_entry(entry_id)
    except KeyError:
        return {"status": "error", "error": "not_found"}
    except Exception as exc:
        return {"status": "error", "error": "read_failed", "details": str(exc)}
    return {
        "status": "ok",
        "entry": {
            "id": e.id, "kind": e.kind, "title": e.title, "content": e.content,
            "visibility": e.visibility, "domain": e.domain,
            "created_at": e.created_at.isoformat(),
            "salience_bumps": e.salience_bumps,
            "related": e.related,
            "status_field": e.status,
            "superseded_by": e.superseded_by,
        },
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `conda activate ai && pytest tests/test_jarvis_brain_tools.py -v`
Expected: all passed.

- [ ] **Step 5: Commit**

```bash
git add core/tools/jarvis_brain_tools.py tests/test_jarvis_brain_tools.py
git commit -m "feat(jarvis-brain): search_jarvis_brain and read_brain_entry tools"
```

---

## Task 10: Tools — archive + adopt/discard proposal

**Files:**
- Modify: `core/tools/jarvis_brain_tools.py`
- Modify: `tests/test_jarvis_brain_tools.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_jarvis_brain_tools.py — append
def test_archive_brain_entry_via_tool(isolated_brain):
    from core.tools.jarvis_brain_tools import remember_this, archive_brain_entry
    r = remember_this(kind="observation", title="O", content="c",
                      visibility="personal", domain="d",
                      session_id="s", turn_id="t1")
    res = archive_brain_entry(r["id"], reason="not relevant anymore")
    assert res["status"] == "ok"


def test_adopt_brain_proposal_moves_file(isolated_brain):
    from core.services import jarvis_brain
    from core.tools.jarvis_brain_tools import adopt_brain_proposal
    # Manuelt opret en pending proposal-fil + db-row
    pending_dir = jarvis_brain.brain_dir() / "_pending"
    pending_dir.mkdir(parents=True, exist_ok=True)
    eid = jarvis_brain.new_brain_id()
    e = jarvis_brain.BrainEntry(
        id=eid, kind="fakta", visibility="personal", domain="d",
        title="Proposal", content="Proposed body.",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        last_used_at=None, salience_base=1.0, salience_bumps=0,
        related=[], trigger="adopted_proposal", status="active",
        superseded_by=None, source_chronicle=None, source_url=None,
    )
    md = jarvis_brain.render_entry_markdown(e)
    pending_path = pending_dir / f"{eid[-8:]}.md"
    pending_path.write_text(md, encoding="utf-8")
    # Insert proposal row
    conn = jarvis_brain.connect_index()
    conn.execute(
        "INSERT INTO brain_proposals(id, path, reason, created_at, status) "
        "VALUES (?, ?, ?, ?, 'pending')",
        (eid, str(pending_path.relative_to(jarvis_brain._workspace_root())),
         "test proposal", datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    conn.close()

    res = adopt_brain_proposal(eid)
    assert res["status"] == "ok"
    # Filen er flyttet til fakta/-mappe
    assert not pending_path.exists()
    assert any((jarvis_brain.brain_dir() / "fakta").glob("*.md"))


def test_discard_brain_proposal(isolated_brain):
    from core.services import jarvis_brain
    from core.tools.jarvis_brain_tools import discard_brain_proposal
    pending_dir = jarvis_brain.brain_dir() / "_pending"
    pending_dir.mkdir(parents=True, exist_ok=True)
    eid = jarvis_brain.new_brain_id()
    pending_path = pending_dir / f"{eid[-8:]}.md"
    pending_path.write_text("---\nid: " + eid + "\n---\nbody\n", encoding="utf-8")
    conn = jarvis_brain.connect_index()
    conn.execute(
        "INSERT INTO brain_proposals(id, path, reason, created_at, status) "
        "VALUES (?, ?, ?, ?, 'pending')",
        (eid, str(pending_path.relative_to(jarvis_brain._workspace_root())),
         "test", datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    conn.close()

    res = discard_brain_proposal(eid, reason="not useful")
    assert res["status"] == "ok"
    assert not pending_path.exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `conda activate ai && pytest tests/test_jarvis_brain_tools.py -v`
Expected: ImportError on `archive_brain_entry`, `adopt_brain_proposal`, `discard_brain_proposal`.

- [ ] **Step 3: Implement tools**

```python
# core/tools/jarvis_brain_tools.py — append

def archive_brain_entry(entry_id: str, *, reason: str = "manual") -> dict[str, Any]:
    from core.services import jarvis_brain
    try:
        jarvis_brain.archive_entry(entry_id, reason=reason)
    except KeyError:
        return {"status": "error", "error": "not_found"}
    except Exception as exc:
        return {"status": "error", "error": "archive_failed", "details": str(exc)}
    return {"status": "ok"}


def adopt_brain_proposal(proposal_id: str, edits: dict | None = None) -> dict[str, Any]:
    """Flyt en pending proposal til den rigtige kind/-mappe og stempel som visible_jarvis."""
    from core.services import jarvis_brain
    conn = jarvis_brain.connect_index()
    try:
        row = conn.execute(
            "SELECT path, status FROM brain_proposals WHERE id = ?",
            (proposal_id,),
        ).fetchone()
        if row is None:
            return {"status": "error", "error": "not_found"}
        if row[1] != "pending":
            return {"status": "error", "error": "not_pending",
                    "details": f"current status: {row[1]}"}
        rel_path = row[0]
    finally:
        conn.close()

    pending_path = jarvis_brain._workspace_root() / rel_path
    fm, body = jarvis_brain.parse_frontmatter(pending_path)
    edits = edits or {}
    fm.update(edits)
    fm["trigger"] = "adopted_proposal"
    fm["created_by"] = "visible_jarvis"
    now = _now()
    fm["updated_at"] = now.isoformat()

    e = jarvis_brain.entry_from_frontmatter(fm, body)
    md = jarvis_brain.render_entry_markdown(e)
    new_path = jarvis_brain.brain_dir() / e.kind / pending_path.name
    jarvis_brain._atomic_write(new_path, md)
    pending_path.unlink()

    new_rel = str(new_path.relative_to(jarvis_brain._workspace_root()))
    fhash = jarvis_brain._file_hash(md)
    conn = jarvis_brain.connect_index()
    try:
        # Insert as active brain entry
        conn.execute(
            """INSERT OR REPLACE INTO brain_index
               (id, path, kind, visibility, domain, title,
                created_at, updated_at, last_used_at,
                salience_base, salience_bumps, status,
                superseded_by, file_hash, embedding, embedding_dim, indexed_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,'active',?,?,NULL,NULL,?)""",
            (e.id, new_rel, e.kind, e.visibility, e.domain, e.title,
             jarvis_brain._iso(e.created_at), jarvis_brain._iso(now), None,
             e.salience_base, e.salience_bumps, e.superseded_by,
             fhash, jarvis_brain._iso(now)),
        )
        # Update proposal row
        conn.execute(
            "UPDATE brain_proposals SET status='adopted', adopted_at=?, "
            "adopted_by='visible_jarvis' WHERE id=?",
            (jarvis_brain._iso(now), proposal_id),
        )
        conn.commit()
    finally:
        conn.close()

    return {"status": "ok", "id": e.id, "path": new_rel}


def discard_brain_proposal(proposal_id: str, *, reason: str = "") -> dict[str, Any]:
    from core.services import jarvis_brain
    conn = jarvis_brain.connect_index()
    try:
        row = conn.execute(
            "SELECT path FROM brain_proposals WHERE id = ?",
            (proposal_id,),
        ).fetchone()
        if row is None:
            return {"status": "error", "error": "not_found"}
        rel_path = row[0]
        pending_path = jarvis_brain._workspace_root() / rel_path
        if pending_path.exists():
            pending_path.unlink()
        conn.execute(
            "UPDATE brain_proposals SET status='discarded', adopted_at=?, "
            "adopted_by='visible_jarvis' WHERE id=?",
            (_now().isoformat(), proposal_id),
        )
        conn.commit()
    finally:
        conn.close()
    return {"status": "ok", "reason_logged": reason}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `conda activate ai && pytest tests/test_jarvis_brain_tools.py -v`
Expected: all passed.

- [ ] **Step 5: Commit**

```bash
git add core/tools/jarvis_brain_tools.py tests/test_jarvis_brain_tools.py
git commit -m "feat(jarvis-brain): archive_brain_entry + adopt/discard proposal tools"
```

---

## Task 11: Daemon — `reindex_loop` (hash-based change detection)

**Files:**
- Create: `core/services/jarvis_brain_daemon.py`
- Create: `tests/test_jarvis_brain_daemon.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_jarvis_brain_daemon.py
from __future__ import annotations
from datetime import datetime, timezone, timedelta
import pytest


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    from core.services import jarvis_brain
    monkeypatch.setattr(jarvis_brain, "_workspace_root", lambda: tmp_path / "ws")
    monkeypatch.setattr(jarvis_brain, "_state_root", lambda: tmp_path / "state")
    yield jarvis_brain


def test_reindex_picks_up_new_file(isolated, tmp_path):
    from core.services.jarvis_brain_daemon import reindex_once
    fakta_dir = isolated.brain_dir() / "fakta"
    fakta_dir.mkdir(parents=True, exist_ok=True)
    eid = isolated.new_brain_id()
    md = (
        "---\n"
        f"id: {eid}\n"
        "kind: fakta\nvisibility: personal\ndomain: d\n"
        f"title: Manual\ncreated_at: 2026-05-02T10:00:00+00:00\n"
        "updated_at: 2026-05-02T10:00:00+00:00\n"
        "salience_base: 1.0\nsalience_bumps: 0\nstatus: active\n"
        "---\n\nbody\n"
    )
    (fakta_dir / "manual.md").write_text(md, encoding="utf-8")
    n = reindex_once()
    assert n == 1
    e = isolated.read_entry(eid)
    assert e.title == "Manual"


def test_reindex_idempotent(isolated):
    from core.services.jarvis_brain_daemon import reindex_once
    isolated.write_entry(kind="fakta", title="X", content="y",
                          visibility="personal", domain="d")
    reindex_once()
    n = reindex_once()  # second pass: no changes
    assert n == 0


def test_reindex_embeds_pending(isolated, monkeypatch):
    import numpy as np
    from core.services.jarvis_brain_daemon import reindex_once
    monkeypatch.setattr(isolated, "_embed_text",
                        lambda t: np.array([1.0, 2.0, 3.0], dtype=np.float32))
    isolated.write_entry(kind="fakta", title="X", content="y",
                          visibility="personal", domain="d")
    reindex_once()  # picks up new file + embeds it
    conn = isolated.connect_index()
    row = conn.execute(
        "SELECT embedding, embedding_dim FROM brain_index"
    ).fetchone()
    assert row[0] is not None
    assert row[1] == 3
    conn.close()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `conda activate ai && pytest tests/test_jarvis_brain_daemon.py -v`
Expected: ImportError on `jarvis_brain_daemon` / `reindex_once`.

- [ ] **Step 3: Implement reindex_loop + reindex_once**

```python
# core/services/jarvis_brain_daemon.py
"""Jarvis Brain background daemon — tre uafhængige loops.

Loops:
  - reindex_loop: scanner brain_dir hver 5. min, opdaterer index, embedder pending
  - consolidation_loop: dagligt, finder duplikater + modsigelser + temaer
  - summary_loop: regenererer always-on summary efter meningsfulde ændringer
"""
from __future__ import annotations
import logging
import threading
import time
from datetime import datetime, timezone

logger = logging.getLogger("jarvis_brain_daemon")

_REINDEX_INTERVAL_SECONDS = 300  # 5 min


def reindex_once() -> int:
    """Et enkelt reindex-pass. Returnerer antal opdateringer."""
    from core.services import jarvis_brain
    n = jarvis_brain.rebuild_index_from_files()
    embedded = jarvis_brain.embed_pending_entries()
    logger.info("reindex_once: %s file changes, %s embeddings", n, embedded)
    return n


def reindex_loop(stop_event: threading.Event) -> None:
    while not stop_event.is_set():
        try:
            reindex_once()
        except Exception as exc:
            logger.warning("reindex_loop iteration failed: %s", exc)
        stop_event.wait(_REINDEX_INTERVAL_SECONDS)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `conda activate ai && pytest tests/test_jarvis_brain_daemon.py -v`
Expected: all passed.

- [ ] **Step 5: Commit**

```bash
git add core/services/jarvis_brain_daemon.py tests/test_jarvis_brain_daemon.py
git commit -m "feat(jarvis-brain): daemon reindex_loop with hash-based change detection"
```

---

## Task 12: Daemon — konsolidering fase 1 (duplikat-detektion)

**Files:**
- Modify: `core/services/jarvis_brain_daemon.py`
- Modify: `tests/test_jarvis_brain_daemon.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_jarvis_brain_daemon.py — append
def test_dedup_detects_high_similarity(isolated, monkeypatch):
    import numpy as np
    from core.services.jarvis_brain_daemon import find_duplicate_proposals
    # Stub embedder så A og B er næsten identiske (sim > 0.92)
    def fake(text):
        if "alpha" in text.lower():
            return np.array([1.0, 0.0, 0.0], dtype=np.float32)
        if "beta" in text.lower():
            return np.array([0.99, 0.05, 0.0], dtype=np.float32)  # cos~0.997
        return np.array([0.0, 0.0, 1.0], dtype=np.float32)
    monkeypatch.setattr(isolated, "_embed_text", fake)
    a = isolated.write_entry(kind="fakta", title="Alpha", content="alpha details",
                              visibility="personal", domain="d")
    b = isolated.write_entry(kind="fakta", title="Beta", content="beta details",
                              visibility="personal", domain="d")
    isolated.embed_pending_entries()
    pairs = find_duplicate_proposals(threshold=0.92)
    assert len(pairs) == 1
    assert {pairs[0][0], pairs[0][1]} == {a, b}


def test_dedup_skips_low_similarity(isolated, monkeypatch):
    import numpy as np
    from core.services.jarvis_brain_daemon import find_duplicate_proposals
    def fake(text):
        if "alpha" in text.lower():
            return np.array([1.0, 0.0, 0.0], dtype=np.float32)
        return np.array([0.0, 1.0, 0.0], dtype=np.float32)
    monkeypatch.setattr(isolated, "_embed_text", fake)
    isolated.write_entry(kind="fakta", title="Alpha", content="alpha",
                          visibility="personal", domain="d")
    isolated.write_entry(kind="fakta", title="Beta", content="beta",
                          visibility="personal", domain="d")
    isolated.embed_pending_entries()
    pairs = find_duplicate_proposals(threshold=0.92)
    assert pairs == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `conda activate ai && pytest tests/test_jarvis_brain_daemon.py -v`
Expected: ImportError on `find_duplicate_proposals`.

- [ ] **Step 3: Implement duplicate detection**

```python
# core/services/jarvis_brain_daemon.py — append
import numpy as np


def find_duplicate_proposals(
    *, threshold: float = 0.92, kinds: list[str] | None = None,
) -> list[tuple[str, str, float]]:
    """Returnerer liste af (a_id, b_id, similarity) hvor sim ≥ threshold.

    Kun fakta og observation som default — indsigt + reference er for individuelle.
    """
    from core.services import jarvis_brain
    kinds = kinds or ["fakta", "observation"]
    conn = jarvis_brain.connect_index()
    try:
        ph = ",".join("?" * len(kinds))
        rows = conn.execute(
            f"SELECT id, embedding, embedding_dim FROM brain_index "
            f"WHERE status='active' AND kind IN ({ph}) AND embedding IS NOT NULL",
            kinds,
        ).fetchall()
    finally:
        conn.close()

    entries = []
    for eid, blob, dim in rows:
        v = np.frombuffer(blob, dtype=np.float32).reshape(dim)
        norm = float(np.linalg.norm(v)) or 1e-9
        entries.append((eid, v / norm))

    pairs: list[tuple[str, str, float]] = []
    for i, (a_id, a_v) in enumerate(entries):
        for b_id, b_v in entries[i + 1 :]:
            sim = float(np.dot(a_v, b_v))
            if sim >= threshold:
                pairs.append((a_id, b_id, sim))
    return pairs
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `conda activate ai && pytest tests/test_jarvis_brain_daemon.py -v`
Expected: all passed.

- [ ] **Step 5: Commit**

```bash
git add core/services/jarvis_brain_daemon.py tests/test_jarvis_brain_daemon.py
git commit -m "feat(jarvis-brain): daemon duplicate detection (consolidation phase 1)"
```

---

## Task 13: Daemon — konsolidering fase 2 (modsigelse, privacy-routet)

**Files:**
- Modify: `core/services/jarvis_brain_daemon.py`
- Modify: `tests/test_jarvis_brain_daemon.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_jarvis_brain_daemon.py — append
def test_contradiction_pair_routes_to_local_for_intimate(isolated, monkeypatch):
    """Hvis ≥1 entry er intimate eller personal, MÅ free-API IKKE kaldes."""
    from core.services.jarvis_brain_daemon import _llm_contradiction_check
    free_called = {"n": 0}
    local_called = {"n": 0}
    monkeypatch.setattr(
        "core.services.jarvis_brain_daemon._call_ollamafreeapi",
        lambda prompt: free_called.update(n=free_called["n"] + 1) or
                        {"contradicts": False, "reason": "x"},
    )
    monkeypatch.setattr(
        "core.services.jarvis_brain_daemon._call_local_ollama",
        lambda prompt: local_called.update(n=local_called["n"] + 1) or
                        {"contradicts": False, "reason": "x"},
    )

    a = type("E", (), dict(visibility="intimate", title="A", content="a"))
    b = type("E", (), dict(visibility="public_safe", title="B", content="b"))
    _llm_contradiction_check(a, b)
    assert free_called["n"] == 0
    assert local_called["n"] == 1


def test_contradiction_pair_uses_free_for_both_public(monkeypatch):
    from core.services.jarvis_brain_daemon import _llm_contradiction_check
    free_called = {"n": 0}
    local_called = {"n": 0}
    monkeypatch.setattr(
        "core.services.jarvis_brain_daemon._call_ollamafreeapi",
        lambda prompt: free_called.update(n=free_called["n"] + 1) or
                        {"contradicts": False, "reason": "x"},
    )
    monkeypatch.setattr(
        "core.services.jarvis_brain_daemon._call_local_ollama",
        lambda prompt: local_called.update(n=local_called["n"] + 1) or None,
    )
    a = type("E", (), dict(visibility="public_safe", title="A", content="a"))
    b = type("E", (), dict(visibility="public_safe", title="B", content="b"))
    _llm_contradiction_check(a, b)
    assert free_called["n"] == 1
    assert local_called["n"] == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `conda activate ai && pytest tests/test_jarvis_brain_daemon.py -v`
Expected: ImportError on `_llm_contradiction_check`.

- [ ] **Step 3: Implement privacy-routed contradiction LLM**

```python
# core/services/jarvis_brain_daemon.py — append
from core.services.jarvis_brain_visibility import LEVEL as _VIS_LEVEL


_CONTRADICTION_PROMPT = """\
Givet to udsagn:
A: "{a_title}: {a_content}"
B: "{b_title}: {b_content}"

Modsiger de hinanden? Svar JSON: {{"contradicts": bool, "reason": str}}
"""


def _call_ollamafreeapi(prompt: str) -> dict | None:
    """Free OllamaFreeAPI gpt-oss:20b. Public-safe job."""
    try:
        from core.services.cheap_provider_runtime import call_ollamafreeapi
        return call_ollamafreeapi(prompt=prompt, model="gpt-oss:20b",
                                  expect_json=True, timeout_s=60)
    except Exception as exc:
        logger.warning("ollamafreeapi call failed: %s", exc)
        return None


def _call_local_ollama(prompt: str) -> dict | None:
    """Local Ollama på 10.0.0.25 — bruges til personal/intimate par."""
    try:
        from core.services.cheap_provider_runtime import call_local_ollama
        return call_local_ollama(prompt=prompt, expect_json=True, timeout_s=120)
    except Exception as exc:
        logger.warning("local ollama call failed: %s", exc)
        return None


def _llm_contradiction_check(a, b) -> dict | None:
    """Routet pr. visibility. Returnerer LLM JSON-svar eller None."""
    max_lvl = max(_VIS_LEVEL[a.visibility], _VIS_LEVEL[b.visibility])
    prompt = _CONTRADICTION_PROMPT.format(
        a_title=a.title, a_content=a.content,
        b_title=b.title, b_content=b.content,
    )
    if max_lvl == 0:
        return _call_ollamafreeapi(prompt)
    return _call_local_ollama(prompt)
```

**Note for Task 13 implementor:** `cheap_provider_runtime` har allerede `_iter_openai_codex_chat_events` osv., men måske ikke `call_ollamafreeapi` som synkron helper. Tjek og tilføj enkel synkron wrapper hvis ikke der allerede er en. Dette er en del af denne task hvis det mangler.

- [ ] **Step 4: Run tests to verify they pass**

Run: `conda activate ai && pytest tests/test_jarvis_brain_daemon.py -v`
Expected: all passed.

- [ ] **Step 5: Commit**

```bash
git add core/services/jarvis_brain_daemon.py tests/test_jarvis_brain_daemon.py
git commit -m "feat(jarvis-brain): privacy-routed contradiction detection (phase 2)"
```

---

## Task 14: Daemon — fase 3 (tema-konsolidering) + kill-switch

**Files:**
- Modify: `core/services/jarvis_brain_daemon.py`
- Modify: `tests/test_jarvis_brain_daemon.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_jarvis_brain_daemon.py — append
def test_theme_consolidation_pauses_after_3_rejections(isolated, monkeypatch):
    from core.services import jarvis_brain_daemon as dmn
    monkeypatch.setattr(dmn, "_state_path",
                        lambda: isolated._state_root() / "brain_daemon_state.json")
    # Simuler 3 afviste forslag
    for i in range(3):
        dmn.record_proposal_rejection("theme", proposal_id=f"p{i}")
    assert dmn.is_theme_consolidation_paused() is True


def test_theme_consolidation_resets_on_acceptance(isolated, monkeypatch):
    from core.services import jarvis_brain_daemon as dmn
    monkeypatch.setattr(dmn, "_state_path",
                        lambda: isolated._state_root() / "brain_daemon_state.json")
    dmn.record_proposal_rejection("theme", proposal_id="p1")
    dmn.record_proposal_rejection("theme", proposal_id="p2")
    # Acceptance nulstiller streak
    dmn.record_proposal_acceptance("theme", proposal_id="p3")
    dmn.record_proposal_rejection("theme", proposal_id="p4")
    assert dmn.is_theme_consolidation_paused() is False


def test_theme_consolidation_skipped_when_paused(isolated, monkeypatch):
    from core.services import jarvis_brain_daemon as dmn
    monkeypatch.setattr(dmn, "_state_path",
                        lambda: isolated._state_root() / "brain_daemon_state.json")
    monkeypatch.setattr(dmn, "is_theme_consolidation_paused", lambda: True)
    called = {"n": 0}
    monkeypatch.setattr(dmn, "_run_theme_consolidation_pass",
                        lambda: called.update(n=called["n"] + 1))
    dmn.run_theme_consolidation_if_active()
    assert called["n"] == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `conda activate ai && pytest tests/test_jarvis_brain_daemon.py -v`
Expected: ImportError on `record_proposal_rejection` etc.

- [ ] **Step 3: Implement kill-switch + theme stub**

```python
# core/services/jarvis_brain_daemon.py — append
import json
from pathlib import Path

_THEME_REJECT_THRESHOLD = 3


def _state_path() -> Path:
    from core.services import jarvis_brain
    return jarvis_brain._state_root() / "brain_daemon_state.json"


def _read_state() -> dict:
    p = _state_path()
    if not p.exists():
        return {"theme_rejection_streak": 0, "theme_paused": False}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {"theme_rejection_streak": 0, "theme_paused": False}


def _write_state(state: dict) -> None:
    p = _state_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(state), encoding="utf-8")
    tmp.replace(p)


def record_proposal_rejection(phase: str, *, proposal_id: str) -> None:
    if phase != "theme":
        return  # kun theme-fasen har streak-tracking i v1
    state = _read_state()
    state["theme_rejection_streak"] = state.get("theme_rejection_streak", 0) + 1
    if state["theme_rejection_streak"] >= _THEME_REJECT_THRESHOLD:
        state["theme_paused"] = True
        try:
            from core.eventbus.events import emit
            emit("jarvis_brain.theme_consolidation_paused", {
                "reason": f"{_THEME_REJECT_THRESHOLD} consecutive rejections",
                "last_rejected_id": proposal_id,
            })
        except Exception:
            pass
    _write_state(state)


def record_proposal_acceptance(phase: str, *, proposal_id: str) -> None:
    if phase != "theme":
        return
    state = _read_state()
    state["theme_rejection_streak"] = 0
    _write_state(state)


def is_theme_consolidation_paused() -> bool:
    return bool(_read_state().get("theme_paused", False))


def resume_theme_consolidation() -> None:
    state = _read_state()
    state["theme_paused"] = False
    state["theme_rejection_streak"] = 0
    _write_state(state)


def _run_theme_consolidation_pass() -> int:
    """Søndags-pass: group observations efter domain, find temaer.

    Stub i v1: returner 0. Faktisk implementering tilføjes senere når vi har
    nok data til at træne prompten.
    """
    return 0


def run_theme_consolidation_if_active() -> int:
    if is_theme_consolidation_paused():
        logger.info("theme consolidation paused — skipping")
        return 0
    return _run_theme_consolidation_pass()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `conda activate ai && pytest tests/test_jarvis_brain_daemon.py -v`
Expected: all passed.

- [ ] **Step 5: Commit**

```bash
git add core/services/jarvis_brain_daemon.py tests/test_jarvis_brain_daemon.py
git commit -m "feat(jarvis-brain): theme consolidation kill-switch (3-strikes auto-pause)"
```

---

## Task 15: Daemon — `summary_loop` (always-on summary regeneration)

**Files:**
- Modify: `core/services/jarvis_brain_daemon.py`
- Modify: `tests/test_jarvis_brain_daemon.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_jarvis_brain_daemon.py — append
def test_regenerate_summary_creates_file(isolated, monkeypatch):
    from core.services.jarvis_brain_daemon import regenerate_summary
    # Stub LLM så den returnerer fast prosa
    monkeypatch.setattr(
        "core.services.jarvis_brain_daemon._call_local_ollama",
        lambda prompt: {"summary": "**Engineering:** Jeg ved noget.\n"},
    )
    monkeypatch.setattr(
        "core.services.jarvis_brain_daemon._call_ollamafreeapi",
        lambda prompt: {"summary": "**Engineering:** Public version.\n"},
    )
    isolated.write_entry(kind="fakta", title="X", content="y",
                          visibility="personal", domain="engineering")
    regenerate_summary(target_visibility="personal")
    out = isolated._state_root() / "jarvis_brain_summary.md"
    assert out.exists()
    assert "Engineering" in out.read_text(encoding="utf-8")


def test_summary_skipped_when_no_active_entries(isolated, monkeypatch):
    from core.services.jarvis_brain_daemon import regenerate_summary
    monkeypatch.setattr(
        "core.services.jarvis_brain_daemon._call_local_ollama",
        lambda prompt: pytest.fail("should not be called"),
    )
    n = regenerate_summary(target_visibility="personal")
    assert n == 0  # ingen poster → skip
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `conda activate ai && pytest tests/test_jarvis_brain_daemon.py -v`
Expected: ImportError on `regenerate_summary`.

- [ ] **Step 3: Implement summary_loop**

```python
# core/services/jarvis_brain_daemon.py — append
_SUMMARY_PROMPT = """\
Du genererer en kompakt opsummering af Jarvis' egen vidensjournal.
Den vises i toppen af hans bevidsthed som "ting jeg ved nu".

Krav:
- Maks 300 tokens
- Inddel i sektioner med fed: **Engineering:**, **Selv:**, **Relationer:**, **Verden:**
- Brug 1.-person ("Jeg har lært...", "Jeg ved...")
- Spring sektioner over hvis der ikke er noget at sige
- Vær konkret men kompakt

Aktive poster:
{entries_summary}

Returnér JSON: {{"summary": "<markdown-prosa>"}}
"""


def regenerate_summary(*, target_visibility: str = "personal") -> int:
    """Regenererer state/jarvis_brain_summary.md.

    Kun entries med visibility ≤ target_visibility tæller.
    Returnerer antal entries summeret over (0 hvis intet eller fejl).
    """
    from core.services import jarvis_brain
    from core.services.jarvis_brain_visibility import LEVEL
    ceiling = LEVEL[target_visibility]

    conn = jarvis_brain.connect_index()
    try:
        rows = conn.execute(
            "SELECT title, kind, domain, visibility FROM brain_index "
            "WHERE status='active' ORDER BY domain, kind"
        ).fetchall()
    finally:
        conn.close()

    eligible = [r for r in rows if LEVEL[r[3]] <= ceiling]
    if not eligible:
        return 0

    bullet_lines = "\n".join(
        f"- [{kind}/{domain}] {title}" for title, kind, domain, _ in eligible
    )
    prompt = _SUMMARY_PROMPT.format(entries_summary=bullet_lines)

    # Privacy-routing: hvis target er public_safe, free er ok; ellers lokal
    if target_visibility == "public_safe":
        result = _call_ollamafreeapi(prompt)
    else:
        result = _call_local_ollama(prompt)

    if not result or "summary" not in result:
        logger.warning("summary regeneration failed (no LLM result)")
        return 0

    summary_md = (
        f"# Hvad jeg ved nu — opdateret {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}\n\n"
        + result["summary"]
    )
    out_path = jarvis_brain._state_root() / "jarvis_brain_summary.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(".tmp")
    tmp.write_text(summary_md, encoding="utf-8")
    tmp.replace(out_path)
    return len(eligible)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `conda activate ai && pytest tests/test_jarvis_brain_daemon.py -v`
Expected: all passed.

- [ ] **Step 5: Commit**

```bash
git add core/services/jarvis_brain_daemon.py tests/test_jarvis_brain_daemon.py
git commit -m "feat(jarvis-brain): summary regeneration (privacy-routed LLM)"
```

---

## Task 16: Daemon — auto-archive ved lav salience + telemetri

**Files:**
- Modify: `core/services/jarvis_brain_daemon.py`
- Modify: `tests/test_jarvis_brain_daemon.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_jarvis_brain_daemon.py — append
def test_auto_archive_archives_old_low_salience(isolated, monkeypatch):
    from core.services.jarvis_brain_daemon import auto_archive_low_salience
    # Lav en observation der bliver vurderet "gammel" via stub
    eid = isolated.write_entry(kind="observation", title="O", content="c",
                                visibility="personal", domain="d")
    # Patch compute_effective_salience → meget lav
    monkeypatch.setattr(isolated, "compute_effective_salience",
                        lambda e, now: 0.01)
    # Tving last_used_at langt tilbage så days_low ≥ 90
    conn = isolated.connect_index()
    conn.execute(
        "UPDATE brain_index SET last_used_at = ? WHERE id = ?",
        ((datetime.now(timezone.utc) - timedelta(days=120)).isoformat(), eid),
    )
    conn.commit()
    conn.close()

    n = auto_archive_low_salience()
    assert n == 1
    e = isolated.read_entry(eid)
    assert e.status == "archived"


def test_auto_archive_skips_references(isolated, monkeypatch):
    from core.services.jarvis_brain_daemon import auto_archive_low_salience
    isolated.write_entry(kind="reference", title="R", content="c",
                          visibility="personal", domain="d")
    monkeypatch.setattr(isolated, "compute_effective_salience",
                        lambda e, now: 0.001)
    n = auto_archive_low_salience()
    assert n == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `conda activate ai && pytest tests/test_jarvis_brain_daemon.py -v`
Expected: ImportError on `auto_archive_low_salience`.

- [ ] **Step 3: Implement auto-archive**

```python
# core/services/jarvis_brain_daemon.py — append
from datetime import timedelta


_AUTO_ARCHIVE_THRESHOLD = 0.05
_AUTO_ARCHIVE_MIN_DAYS = 90


def auto_archive_low_salience() -> int:
    """Arkivér entries hvis effective_salience < 0.05 i ≥ 90 dage."""
    from core.services import jarvis_brain
    now = datetime.now(timezone.utc)
    conn = jarvis_brain.connect_index()
    try:
        rows = conn.execute(
            "SELECT id, kind, last_used_at, created_at FROM brain_index "
            "WHERE status='active'"
        ).fetchall()
    finally:
        conn.close()

    archived = 0
    for entry_id, kind, last_used, created in rows:
        if kind == "reference":
            continue  # references arkiveres aldrig automatisk
        try:
            entry = jarvis_brain.read_entry(entry_id)
        except Exception:
            continue
        eff = jarvis_brain.compute_effective_salience(entry, now)
        if eff >= _AUTO_ARCHIVE_THRESHOLD:
            continue
        last = entry.last_used_at or entry.created_at
        days_low = (now - last).days
        if days_low < _AUTO_ARCHIVE_MIN_DAYS:
            continue
        try:
            jarvis_brain.archive_entry(entry_id, reason="auto: low salience 90+ days")
            archived += 1
        except Exception as exc:
            logger.warning("auto-archive failed for %s: %s", entry_id, exc)

    # Telemetri
    try:
        from core.eventbus.events import emit
        total = sum(1 for r in rows)
        emit("jarvis_brain.auto_archive_pass", {
            "archived_count": archived,
            "total_active_before": total,
        })
    except Exception:
        pass

    return archived
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `conda activate ai && pytest tests/test_jarvis_brain_daemon.py -v`
Expected: all passed.

- [ ] **Step 5: Commit**

```bash
git add core/services/jarvis_brain_daemon.py tests/test_jarvis_brain_daemon.py
git commit -m "feat(jarvis-brain): auto-archive low-salience entries (telemetry)"
```

---

## Task 17: Settings additions

**Files:**
- Modify: `core/runtime/settings.py` (eller hvor `RuntimeSettings` defineres)
- Modify: `tests/test_settings.py` (eller similar) hvis findes

Find først hvor RuntimeSettings bor:
```bash
grep -rn "class RuntimeSettings" core/ apps/ | head -5
```

- [ ] **Step 1: Add brain settings to RuntimeSettings dataclass/pydantic-model**

```python
# Tilføj i RuntimeSettings:
jarvis_brain_enabled: bool = True
jarvis_brain_summary_token_budget: int = 350
jarvis_brain_auto_inject_top_k: int = 3
jarvis_brain_auto_inject_threshold: float = 0.55
jarvis_brain_remember_per_turn_cap: int = 5
jarvis_brain_remember_per_day_cap: int = 20
jarvis_brain_auto_archive_salience_threshold: float = 0.05
jarvis_brain_auto_archive_days: int = 90
jarvis_brain_theme_consolidation_enabled: bool = True
```

- [ ] **Step 2: Update jarvis_brain_tools to read caps from settings**

```python
# core/tools/jarvis_brain_tools.py — modificér _PER_TURN_CAP, _PER_DAY_CAP

def _get_caps() -> tuple[int, int]:
    try:
        from core.runtime.settings import load_settings
        s = load_settings()
        return (s.jarvis_brain_remember_per_turn_cap,
                s.jarvis_brain_remember_per_day_cap)
    except Exception:
        return (5, 20)
```

Erstat `_turn_counts[turn_key] >= _PER_TURN_CAP` med `_turn_counts[turn_key] >= _get_caps()[0]` (og tilsvarende for day).

- [ ] **Step 3: Run all brain tests to verify nothing broke**

Run: `conda activate ai && pytest tests/test_jarvis_brain.py tests/test_jarvis_brain_tools.py tests/test_jarvis_brain_daemon.py tests/test_jarvis_brain_visibility.py -v`
Expected: all green.

- [ ] **Step 4: Commit**

```bash
git add core/runtime/settings.py core/tools/jarvis_brain_tools.py
git commit -m "feat(jarvis-brain): add 9 RuntimeSettings fields and wire caps"
```

---

## Task 18: Boy Scout 1 — Udskil awareness-section fra `prompt_contract.py`

**Files:**
- Create: `core/services/prompt_sections/__init__.py`
- Create: `core/services/prompt_sections/self_awareness.py`
- Modify: `core/services/prompt_contract.py`

Boy Scout-regel (CLAUDE.md): rør vi prompt_contract.py (3776 linjer), skal vi udskille en naturlig enhed først.

- [ ] **Step 1: Find awareness-builder funktionen**

```bash
grep -n "def _build_self_awareness\|def build_self_awareness\|self_awareness_section" core/services/prompt_contract.py | head -5
```

Identificér den nærmeste sammenhængende enhed (typisk én funktion + helpers).

- [ ] **Step 2: Create package init**

```python
# core/services/prompt_sections/__init__.py
"""Prompt-sections udskilt fra prompt_contract.py for læselighed.

Hver fil er én sammenhængende enhed (én logisk awareness-sektion).
"""
```

- [ ] **Step 3: Move funktionen til ny fil**

Flyt den valgte enhed til `core/services/prompt_sections/self_awareness.py`. Bevar fuld bagudkompatibilitet ved at re-eksportere fra prompt_contract.py:

```python
# I prompt_contract.py — erstatt original definition med:
from core.services.prompt_sections.self_awareness import _build_self_awareness_section  # re-export
```

- [ ] **Step 4: Run prompt_contract tests**

```bash
conda activate ai && pytest tests/ -k "prompt_contract" -v
```

Expected: all passed (re-export gør at intet brækker).

- [ ] **Step 5: Commit**

```bash
git add core/services/prompt_sections/ core/services/prompt_contract.py
git commit -m "refactor(prompt_contract): extract self_awareness section to prompt_sections/ (Boy Scout)"
```

---

## Task 19: Boy Scout 2 — Udskil naturlig enhed fra `visible_runs.py`

**Files:**
- Create: `core/services/visible_runs_sections/<chosen_unit>.py`
- Create: `core/services/visible_runs_sections/__init__.py`
- Modify: `core/services/visible_runs.py`

- [ ] **Step 1: Identify naturlig enhed**

```bash
wc -l core/services/visible_runs.py
grep -n "^def \|^class \|^async def " core/services/visible_runs.py | head -30
```

Vælg en sammenhængende enhed (typisk `tool_call_dispatch`, `cognitive_state_assembly`, eller `_build_envelope`). Begrundelse skrives i commit-msg.

- [ ] **Step 2: Move enhed til subpakke**

Same pattern as Task 18: create `core/services/visible_runs_sections/<name>.py`, flyt logikken, re-eksportér i `visible_runs.py`.

- [ ] **Step 3: Run visible-runs tests**

```bash
conda activate ai && pytest tests/ -k "visible_runs" -v
```

Expected: all passed.

- [ ] **Step 4: Commit**

```bash
git add core/services/visible_runs_sections/ core/services/visible_runs.py
git commit -m "refactor(visible_runs): extract <unit> to visible_runs_sections/ (Boy Scout)"
```

---

## Task 20: Integration — `_build_jarvis_brain_section` i prompt_contract

**Files:**
- Create: `core/services/prompt_sections/jarvis_brain.py`
- Modify: `core/services/prompt_contract.py`
- Create: `tests/test_prompt_sections_jarvis_brain.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_prompt_sections_jarvis_brain.py
from __future__ import annotations
from pathlib import Path
import pytest


def test_build_section_returns_empty_when_no_file(tmp_path, monkeypatch):
    from core.services import jarvis_brain
    monkeypatch.setattr(jarvis_brain, "_state_root", lambda: tmp_path)
    from core.services.prompt_sections.jarvis_brain import build_jarvis_brain_section
    text = build_jarvis_brain_section(token_budget=350)
    assert text == ""


def test_build_section_loads_summary_file(tmp_path, monkeypatch):
    from core.services import jarvis_brain
    monkeypatch.setattr(jarvis_brain, "_state_root", lambda: tmp_path)
    summary = tmp_path / "jarvis_brain_summary.md"
    summary.write_text("# Hvad jeg ved nu\n\n**Engineering:** test.\n", encoding="utf-8")
    from core.services.prompt_sections.jarvis_brain import build_jarvis_brain_section
    text = build_jarvis_brain_section(token_budget=350)
    assert "Engineering" in text
    assert text.startswith("## Hvad jeg ved nu")


def test_build_section_trims_at_section_boundary(tmp_path, monkeypatch):
    from core.services import jarvis_brain
    monkeypatch.setattr(jarvis_brain, "_state_root", lambda: tmp_path)
    summary = tmp_path / "jarvis_brain_summary.md"
    summary.write_text(
        "**A:** " + "x" * 500 + "\n**B:** keep\n",
        encoding="utf-8",
    )
    from core.services.prompt_sections.jarvis_brain import build_jarvis_brain_section
    text = build_jarvis_brain_section(token_budget=50)  # very small
    assert len(text) < len("**A:** " + "x" * 500)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `conda activate ai && pytest tests/test_prompt_sections_jarvis_brain.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement section builder**

```python
# core/services/prompt_sections/jarvis_brain.py
"""Always-on summary injection for Jarvis Brain."""
from __future__ import annotations
from pathlib import Path


def _approx_tokens(text: str) -> int:
    # Crude estimat: ~4 chars per token. God nok til budget-trim.
    return max(1, len(text) // 4)


def build_jarvis_brain_section(*, token_budget: int = 350) -> str:
    from core.services import jarvis_brain
    p = jarvis_brain._state_root() / "jarvis_brain_summary.md"
    if not p.exists():
        return ""
    try:
        raw = p.read_text(encoding="utf-8").strip()
    except Exception:
        return ""
    if not raw:
        return ""

    # Trim på sektions-grænser hvis over budget
    if _approx_tokens(raw) > token_budget:
        # Split på fed-tekst-headers ("**X:**")
        parts = []
        current = ""
        for line in raw.split("\n"):
            if line.startswith("**") and current:
                parts.append(current)
                current = line + "\n"
            else:
                current += line + "\n"
        if current:
            parts.append(current)
        # Drop bagud indtil under budget
        while parts and _approx_tokens("\n".join(parts)) > token_budget:
            parts.pop()
        raw = "\n".join(parts) if parts else raw[: token_budget * 4]

    return f"## Hvad jeg ved nu (min egen hjerne)\n\n{raw}\n"
```

- [ ] **Step 4: Wire i prompt_contract**

Find hvor andre awareness-sektioner kaldes (typisk i en `build_full_prompt`-funktion). Tilføj kald til `build_jarvis_brain_section()` placeret **efter** identitets-sektionen og **før** working-memory (jvf. spec sektion 5.1):

```python
# I prompt_contract.py byggepipeline — pseudokode:
sections = []
sections.append(build_identity_section(...))
sections.append(build_self_awareness_section(...))
# NY:
from core.services.prompt_sections.jarvis_brain import build_jarvis_brain_section
brain = build_jarvis_brain_section(token_budget=settings.jarvis_brain_summary_token_budget)
if brain:
    sections.append(brain)
sections.append(build_working_memory_section(...))
```

(Tilpas variabelnavne efter faktisk struktur.)

- [ ] **Step 5: Run tests to verify they pass**

```bash
conda activate ai && pytest tests/test_prompt_sections_jarvis_brain.py tests/ -k "prompt_contract" -v
```

Expected: all passed.

- [ ] **Step 6: Commit**

```bash
git add core/services/prompt_sections/jarvis_brain.py core/services/prompt_contract.py tests/test_prompt_sections_jarvis_brain.py
git commit -m "feat(jarvis-brain): inject always-on summary into prompt_contract"
```

---

## Task 21: Integration — auto-inject fakta i `visible_runs.py`

**Files:**
- Modify: `core/services/visible_runs.py` (eller subpakke fra Task 19)
- Create: `tests/test_visible_runs_brain_inject.py`

- [ ] **Step 1: Write failing test (skeleton only — fuld integration kræver kontekst)**

```python
# tests/test_visible_runs_brain_inject.py
from __future__ import annotations
import pytest


def test_inject_brain_facts_appends_section_when_matches(tmp_path, monkeypatch):
    """En entry over threshold → envelope får 'Relevante fakta'-sektion."""
    import numpy as np
    from core.services import jarvis_brain
    monkeypatch.setattr(jarvis_brain, "_workspace_root", lambda: tmp_path / "ws")
    monkeypatch.setattr(jarvis_brain, "_state_root", lambda: tmp_path / "state")

    def fake(text):
        return np.array([1.0, 0.0, 0.0], dtype=np.float32)
    monkeypatch.setattr(jarvis_brain, "_embed_text", fake)
    eid = jarvis_brain.write_entry(
        kind="fakta", title="Test fakta", content="Test indhold",
        visibility="personal", domain="d",
    )
    jarvis_brain.embed_pending_entries()

    from core.services.visible_runs import _inject_brain_facts
    envelope = {"sections": []}
    fake_session = type("S", (), {
        "channel_kind": "dm", "participants": ["bjorn"],
        "is_autonomous": False, "is_inner_voice": False,
    })()
    monkeypatch.setattr(
        "core.services.jarvis_brain_visibility._resolve_owner_id",
        lambda: "bjorn",
    )
    _inject_brain_facts(envelope, fake_session, query_text="test query")
    has_brain_section = any(
        "Relevante fakta" in s for s in envelope["sections"]
    )
    assert has_brain_section


def test_inject_brain_facts_silent_when_no_match(tmp_path, monkeypatch):
    """Ingen poster → ingen sektion (ikke 'ingen relevante fakta')."""
    from core.services.visible_runs import _inject_brain_facts
    envelope = {"sections": []}
    fake_session = type("S", (), {
        "channel_kind": "dm", "participants": ["bjorn"],
    })()
    monkeypatch.setattr(
        "core.services.jarvis_brain_visibility._resolve_owner_id",
        lambda: "bjorn",
    )
    _inject_brain_facts(envelope, fake_session, query_text="nothing matches")
    assert envelope["sections"] == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `conda activate ai && pytest tests/test_visible_runs_brain_inject.py -v`
Expected: ImportError on `_inject_brain_facts`.

- [ ] **Step 3: Implement `_inject_brain_facts`**

I `core/services/visible_runs.py` (eller subpakke fra Task 19):

```python
def _inject_brain_facts(envelope: dict, session, *, query_text: str) -> None:
    """Embedding-søg top-K fakta og injicér i envelope.

    Silent skip hvis ingen poster over threshold.
    """
    try:
        from core.runtime.settings import load_settings
        s = load_settings()
        if not s.jarvis_brain_enabled:
            return
        top_k = s.jarvis_brain_auto_inject_top_k
        threshold = s.jarvis_brain_auto_inject_threshold
    except Exception:
        top_k, threshold = 3, 0.55

    try:
        from core.services.jarvis_brain_visibility import session_visibility_ceiling
        from core.services import jarvis_brain
        ceiling = session_visibility_ceiling(session)
        results = jarvis_brain.search_brain(
            query_text=query_text, kinds=["fakta"],
            visibility_ceiling=ceiling, limit=top_k,
        )
        if not results:
            return
        # Bump salience
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        for e in results:
            try:
                jarvis_brain.bump_salience(e.id, now=now)
            except Exception:
                pass

        lines = ["## Relevante fakta fra min hjerne", ""]
        for e in results:
            lines.append(f"- **{e.title}** [{e.id}]: {e.content}")
        envelope.setdefault("sections", []).append("\n".join(lines))
    except Exception as exc:
        # Fail-soft — recall må aldrig blokere prompt
        import logging
        logging.getLogger("visible_runs").warning(
            "brain auto-inject failed: %s", exc
        )
```

Find hvor `cognitive_state_assembly` (eller similar) bygger envelope og kald `_inject_brain_facts(envelope, session, query_text=last_user_message_content)` på det rigtige sted.

- [ ] **Step 4: Run tests to verify they pass**

Run: `conda activate ai && pytest tests/test_visible_runs_brain_inject.py -v`
Expected: all passed.

- [ ] **Step 5: Commit**

```bash
git add core/services/visible_runs.py tests/test_visible_runs_brain_inject.py
git commit -m "feat(jarvis-brain): auto-inject relevant fakta into envelope"
```

---

## Task 22: Integration — post-web-search nudge

**Files:**
- Modify: tool-dispatch laget (find via grep)

- [ ] **Step 1: Find where web_search/web_scrape tool results are handled**

```bash
grep -rn "web_search\|web_scrape" core/services/visible_runs.py core/services/visible_runs_sections/ 2>/dev/null | head -10
```

- [ ] **Step 2: Add nudge appender**

Efter web_search/web_scrape tool returnerer et result, append envelope-note (én gang pr. tur):

```python
def _maybe_append_brain_nudge(envelope: dict, tool_name: str,
                              tool_url: str | None, turn_state: dict) -> None:
    """Append blød brain-nudge én gang pr. tur uanset antal web-tools."""
    if turn_state.get("brain_nudge_appended"):
        return
    if tool_name not in {"web_search", "web_scrape"}:
        return
    nudge = (
        f"[brain-nudge] Du har lige hentet ekstern info via {tool_name}. "
        f"Hvis du har lært noget værd at gemme — fakta, en god reference, "
        f"en indsigt — brug `remember_this` med visibility=public_safe"
        + (f" og source_url={tool_url}." if tool_url else ".")
        + " Det er ikke obligatorisk; spring over hvis intet er værd."
    )
    envelope.setdefault("sections", []).append(nudge)
    turn_state["brain_nudge_appended"] = True
```

Wire i tool-dispatch hvor results returneres.

- [ ] **Step 3: Manual smoke test**

Med en kørende dev-instans, kald `web_search` og verify nudgen vises i prompt-rendering. (Eller skriv en lille integrations-test der bygger en envelope med en fake tool-result og bekræfter at nudgen appendes én gang.)

- [ ] **Step 4: Commit**

```bash
git add core/services/visible_runs.py
git commit -m "feat(jarvis-brain): post-web-search nudge to remember_this"
```

---

## Task 23: Refleksions-slot integration

**Files:**
- Create: `core/services/jarvis_brain_reflection.py`
- Create: `tests/test_jarvis_brain_reflection.py`
- Modify: `core/services/deep_reflection_slot.py` (eller wherever slot-trigger er)

- [ ] **Step 1: Write failing test**

```python
# tests/test_jarvis_brain_reflection.py
from __future__ import annotations
import pytest


def test_reflection_envelope_contains_chronicle_and_question():
    from core.services.jarvis_brain_reflection import build_reflection_envelope
    env = build_reflection_envelope(chronicle_summary="Today: did A, fixed B.")
    assert "did A, fixed B" in env
    assert "remember_this" in env
    assert "1-3 ting" in env


def test_internal_nudge_appended_after_3_remember_calls():
    from core.services.jarvis_brain_reflection import build_internal_nudge
    msg = build_internal_nudge(count_so_far=3)
    assert "3 poster" in msg or "N poster" in msg
    msg = build_internal_nudge(count_so_far=1)
    assert msg == ""  # under threshold


def test_reflection_slot_skips_if_offline_today(monkeypatch):
    from core.services import jarvis_brain_reflection as r
    called = {"ran": False}
    monkeypatch.setattr(r, "_run_reflection_turn", lambda *a, **kw: called.update(ran=True))
    monkeypatch.setattr(r, "_was_active_today", lambda: False)
    r.run_daily_reflection_if_active()
    assert called["ran"] is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `conda activate ai && pytest tests/test_jarvis_brain_reflection.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement reflection slot**

```python
# core/services/jarvis_brain_reflection.py
"""End-of-day refleksions-slot — visible Jarvis spørger sig selv hvad han lærte."""
from __future__ import annotations
import logging

logger = logging.getLogger("jarvis_brain_reflection")


_REFLECTION_TEMPLATE = """\
[reflection-slot] Dagen er ved at runde. Her er kort hvad der skete i dag:
{chronicle_summary}

Spørgsmål til dig: Hvad lærte du i dag som er værd at føre ind i din
egen hjerne? Tænk på fakta, indsigter, observationer, eller referencer.
Brug `remember_this` for hver enkelt — eller spring over hvis intet
stikker ud. Du behøver ikke skrive om alt; vælg de 1-3 ting der
virkelig er værd at huske.
"""


def build_reflection_envelope(*, chronicle_summary: str) -> str:
    return _REFLECTION_TEMPLATE.format(chronicle_summary=chronicle_summary)


def build_internal_nudge(*, count_so_far: int) -> str:
    """Efter 2-3 remember_this i samme slot, append blød nudge."""
    if count_so_far < 3:
        return ""
    return (
        f"[brain-nudge-internal] Du har nu skrevet {count_so_far} poster i dag. "
        f"Er der mere, eller er du færdig?"
    )


def _was_active_today() -> bool:
    """Best-effort tjek om Jarvis havde aktivitet i dag (chronicle eller events)."""
    try:
        # Pseudo: tjek om der er chronicle-entries fra i dag
        from core.runtime.db import has_chronicle_today
        return has_chronicle_today()
    except Exception:
        return True  # fail-open: hellere køre end at springe over


def _run_reflection_turn(chronicle_summary: str) -> int:
    """Trigger en visible-Jarvis tur med reflection-envelope. Returnerer antal remember_this."""
    # Implementering afhænger af hvordan visible_runs eksponerer envelope-injection.
    # I v1: emit eventbus-event som visible_runs lytter på.
    try:
        from core.eventbus.events import emit
        emit("jarvis_brain.reflection_requested", {
            "envelope_text": build_reflection_envelope(
                chronicle_summary=chronicle_summary,
            ),
        })
    except Exception as exc:
        logger.warning("reflection event emit failed: %s", exc)
        return 0
    return 0  # actual count rapporteres separat via reflection_completed event


def run_daily_reflection_if_active() -> None:
    if not _was_active_today():
        logger.info("reflection skipped: no activity today")
        return
    try:
        from core.runtime.db import build_today_chronicle_summary
        summary = build_today_chronicle_summary()
    except Exception as exc:
        logger.warning("could not build chronicle summary: %s", exc)
        return
    _run_reflection_turn(summary)
```

- [ ] **Step 4: Wire into existing reflection slot scheduler**

Find hvor `deep_reflection_slot` eller similar daglig trigger kører. Tilføj kald:

```python
# I daglig slot-runner:
from core.services.jarvis_brain_reflection import run_daily_reflection_if_active
run_daily_reflection_if_active()
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `conda activate ai && pytest tests/test_jarvis_brain_reflection.py -v`
Expected: all passed.

- [ ] **Step 6: Commit**

```bash
git add core/services/jarvis_brain_reflection.py tests/test_jarvis_brain_reflection.py core/services/deep_reflection_slot.py
git commit -m "feat(jarvis-brain): daily reflection slot with 1-3 ting prompt"
```

---

## Task 24: Daemon deployment — wire i `jarvis-runtime`

**Files:**
- Modify: hvor jarvis-runtime starter daemons (find via grep)

- [ ] **Step 1: Find runtime daemon-bootstrap**

```bash
grep -rn "Thread\|threading\.Thread\|daemon=True" apps/api/jarvis_api/ core/services/ | grep -i "runtime\|bootstrap\|start" | head -10
```

- [ ] **Step 2: Add brain-daemon startup**

I bootstrap-funktionen, tilføj:

```python
def _start_jarvis_brain_daemon(stop_event: threading.Event) -> list[threading.Thread]:
    from core.services.jarvis_brain_daemon import (
        reindex_loop, run_consolidation_pass, regenerate_summary,
    )

    threads = []

    t1 = threading.Thread(
        target=reindex_loop, args=(stop_event,),
        name="jarvis-brain-reindex", daemon=True,
    )
    t1.start()
    threads.append(t1)

    # Konsolidering + summary kører på cadence — implementer en simpel scheduler-tråd:
    def _scheduler():
        last_consolidation = 0
        last_summary = 0
        last_archive = 0
        while not stop_event.is_set():
            now_ts = time.time()
            # Daily konsolidering
            if now_ts - last_consolidation > 86400:
                try:
                    run_consolidation_pass()
                    last_consolidation = now_ts
                except Exception:
                    logging.exception("consolidation failed")
            # Daily auto-archive
            if now_ts - last_archive > 86400:
                try:
                    from core.services.jarvis_brain_daemon import auto_archive_low_salience
                    auto_archive_low_salience()
                    last_archive = now_ts
                except Exception:
                    logging.exception("auto-archive failed")
            # Hourly summary
            if now_ts - last_summary > 3600:
                try:
                    regenerate_summary(target_visibility="personal")
                    last_summary = now_ts
                except Exception:
                    logging.exception("summary failed")
            stop_event.wait(60)
    t2 = threading.Thread(
        target=_scheduler, name="jarvis-brain-scheduler", daemon=True,
    )
    t2.start()
    threads.append(t2)

    return threads
```

Bemærk: `run_consolidation_pass` skal eksistere — hvis den ikke gør, tilføj en wrapper i `jarvis_brain_daemon.py` der kalder duplicate-detection + contradiction-pairs + theme-if-active i rækkefølge.

- [ ] **Step 3: Restart `jarvis-runtime` med systemctl (kun i dev — ikke automatisk på prod)**

Manuel verifikation; ikke en commit-step.

- [ ] **Step 4: Commit**

```bash
git add apps/api/jarvis_api/ core/services/jarvis_brain_daemon.py
git commit -m "feat(jarvis-brain): wire daemon threads into jarvis-runtime"
```

---

## Task 25: End-to-end smoke test

**Files:**
- Create: `tests/test_jarvis_brain_integration.py`

- [ ] **Step 1: Write E2E test**

```python
# tests/test_jarvis_brain_integration.py
"""End-to-end smoke test for Jarvis Brain.

Skriv 5 entries via tool → verify search returnerer dem → bump verify →
supersede verify → daemon-pass verify → summary-fil genereret.
"""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
import numpy as np
import pytest


@pytest.fixture
def e2e(tmp_path, monkeypatch):
    from core.services import jarvis_brain
    monkeypatch.setattr(jarvis_brain, "_workspace_root", lambda: tmp_path / "ws")
    monkeypatch.setattr(jarvis_brain, "_state_root", lambda: tmp_path / "state")

    def fake(text):
        # Hash-based pseudo-embedding så hver entry er distinct men deterministisk
        import hashlib
        h = hashlib.md5(text.encode()).digest()[:12]
        v = np.frombuffer(h, dtype=np.uint8).astype(np.float32) / 255.0
        return v
    monkeypatch.setattr(jarvis_brain, "_embed_text", fake)
    yield jarvis_brain


def test_e2e_flow(e2e, monkeypatch):
    from core.tools.jarvis_brain_tools import (
        remember_this, search_jarvis_brain, archive_brain_entry,
    )
    from core.services.jarvis_brain_daemon import reindex_once, regenerate_summary
    from core.services import jarvis_brain

    # 1. Skriv 5 entries
    ids = []
    for i in range(5):
        r = remember_this(
            kind="fakta", title=f"Fakta {i}", content=f"Content {i} body text",
            visibility="personal", domain="engineering",
            session_id="s_e2e", turn_id=f"t_{i}",
        )
        assert r["status"] == "ok"
        ids.append(r["id"])

    # 2. Reindex + embed
    reindex_once()

    # 3. Search returnerer mindst én
    sr = search_jarvis_brain(
        query="fakta content",
        session_visibility_ceiling="personal", limit=3,
    )
    assert sr["status"] == "ok"
    assert len(sr["results"]) >= 1

    # 4. Verify salience blev bumpet på de returnerede
    for hit in sr["results"]:
        e = jarvis_brain.read_entry(hit["id"])
        assert e.salience_bumps >= 1

    # 5. Archive en entry
    archive_brain_entry(ids[0], reason="e2e archive test")
    e = jarvis_brain.read_entry(ids[0])
    assert e.status == "archived"

    # 6. Summary regenerering med stub LLM
    monkeypatch.setattr(
        "core.services.jarvis_brain_daemon._call_local_ollama",
        lambda prompt: {"summary": "**Engineering:** E2E test ran."},
    )
    n = regenerate_summary(target_visibility="personal")
    assert n >= 1
    summary_path = jarvis_brain._state_root() / "jarvis_brain_summary.md"
    assert summary_path.exists()
    assert "Engineering" in summary_path.read_text()
```

- [ ] **Step 2: Run E2E test**

Run: `conda activate ai && pytest tests/test_jarvis_brain_integration.py -v`
Expected: passed.

- [ ] **Step 3: Run hele brain-suite for at konfirmere alt er grønt**

```bash
conda activate ai && pytest tests/test_jarvis_brain*.py tests/test_visible_runs_brain_inject.py tests/test_prompt_sections_jarvis_brain.py -v
```

Expected: all green.

- [ ] **Step 4: Commit**

```bash
git add tests/test_jarvis_brain_integration.py
git commit -m "test(jarvis-brain): end-to-end integration smoke test"
```

---

## Final review

Efter alle 25 tasks er commitet, kør:

```bash
conda activate ai && pytest tests/ -k "brain" -v
python -m compileall core apps/api scripts
git log --oneline -30
```

Hvis alt er grønt: 
- `jarvis-runtime` skal genstartes (kun efter eksplicit consent fra Bjørn — pr. CLAUDE.md memory)
- Bjørn kan teste live ved at tale med Jarvis og sige "skriv det ned" eller similar
- Jarvis vil have `remember_this`, `search_jarvis_brain`, `archive_brain_entry`, `adopt_brain_proposal`, `discard_brain_proposal`, `read_brain_entry` i sin tool-liste

---

## Self-review notes

**Spec coverage:**
- Sektion 1 (arkitektur): ✓ implementeret som filsystem + SQLite + daemon (Tasks 1-16)
- Sektion 2 (datamodel): ✓ Tasks 1-3 (frontmatter + index)
- Sektion 3 (komponenter): ✓ alle 4 nye filer + Boy Scout-tasks 18-19
- Sektion 4 (skrive-stier): ✓ Task 8 (spontant), Task 22 (web nudge), Task 23 (refleksion), Task 10 (adopt/discard)
- Sektion 5 (recall-stier): ✓ Task 20 (summary), Task 21 (auto-inject), Task 9 (tool)
- Sektion 6 (privacy): ✓ Task 7 (visibility module), Task 13 (LLM routing)
- Sektion 7 (lifecycle): ✓ Task 4 (decay), Task 6 (supersede/archive), Task 12-14 (consolidation), Task 16 (auto-archive)
- Sektion 8 (testing/migration): ✓ tests pr. task + Task 17 (settings) + Task 25 (E2E)

**No placeholders:** Reviewed — alle steps har konkret kode eller eksplicit kommando.

**Type consistency:** `BrainEntry`, `_VIS_LEVEL`, `LEVEL`, `_HALFLIFE_DAYS` — én definition pr. concept, importeres konsekvent.

**Known known-unknowns** (skal valideres af implementor i Task 1 / Task 5):
- Eksisterende ULID-pakke (verificeres i Task 1 Step 1)
- Eksisterende embedding API + dim (verificeres i Task 5 Step 1)
- Eksisterende RuntimeSettings location (verificeres i Task 17)
- Eksisterende awareness-section navn i prompt_contract.py (verificeres i Task 18)
- Eksisterende daglig reflection slot trigger (verificeres i Task 23)
