"""Jarvis Brain — kurateret vidensjournal. Kerne-CRUD-laget.

Kun ren læs/skriv + søg. Ingen daemon-logik (det ligger i jarvis_brain_daemon.py).
Ingen LLM-kald (konsolidering ligger i daemonen).

Spec: docs/superpowers/specs/2026-05-02-jarvis-brain-design.md
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import hashlib
import math
import os
import re
import secrets
import sqlite3
import time

import yaml

# Prøv python-ulid først, fallback til lokal Crockford b32 generator.
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
_VALID_TRIGGER = {
    "spontaneous",
    "post_web_search",
    "reflection_slot",
    "adopted_proposal",
}


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
            raise ValueError(f"invalid kind: {self.kind!r}")
        if self.visibility not in _VALID_VISIBILITY:
            raise ValueError(f"invalid visibility: {self.visibility!r}")
        if self.status not in _VALID_STATUS:
            raise ValueError(f"invalid status: {self.status!r}")
        if self.trigger not in _VALID_TRIGGER:
            raise ValueError(f"invalid trigger: {self.trigger!r}")


# ---------------------------------------------------------------------------
# File I/O helpers — frontmatter + atomic write
# ---------------------------------------------------------------------------


def _atomic_write(path: Path, content: str) -> None:
    """Atomic file write via tmp + rename. Creates parent dirs as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


def parse_frontmatter(path: Path) -> tuple[dict, str]:
    """Parse YAML frontmatter + body from a markdown file.

    Returns (frontmatter_dict, body_string). Raises ValueError if frontmatter
    is missing or unterminated.
    """
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"missing frontmatter in {path}")
    parts = text.split("\n---\n", 1)
    if len(parts) != 2:
        raise ValueError(f"unterminated frontmatter in {path}")
    yaml_text = parts[0][len("---\n"):]
    body = parts[1]
    fm = yaml.safe_load(yaml_text) or {}
    if not isinstance(fm, dict):
        raise ValueError(f"frontmatter is not a mapping in {path}")
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
    """Render a BrainEntry as markdown with YAML frontmatter."""
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
    """Build a BrainEntry from parsed frontmatter dict + body string."""
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


# ---------------------------------------------------------------------------
# Paths + SQLite index
# ---------------------------------------------------------------------------


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
    return Path(
        os.environ.get("JARVIS_WORKSPACES_ROOT")
        or Path.home() / ".jarvis-v2" / "workspaces"
    )


def _state_root() -> Path:
    return Path(
        os.environ.get("JARVIS_STATE_ROOT")
        or Path.home() / ".jarvis-v2" / "state"
    )


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
    """Skriver en ny brain-entry til disk og indexerer den (uden embedding endnu).

    Returnerer den nye entry's id.
    """
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
    """Read a BrainEntry by id (loads from disk via index lookup)."""
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


def _index_path_for(entry_id: str) -> str:
    """Returns the relative path stored in brain_index for entry_id."""
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


# ---------------------------------------------------------------------------
# Decay + salience
# ---------------------------------------------------------------------------


_HALFLIFE_DAYS = {
    "observation": 14.0,
    "fakta": 180.0,
    "indsigt": 365.0,
    "reference": float("inf"),
}
_SALIENCE_FLOOR = 0.02


def compute_effective_salience(entry: BrainEntry, now: datetime) -> float:
    """Compute time-decayed salience with bump amplification.

    Formula:
        effective = max(floor, base * exp(-days/halflife) * (1 + 0.3*log2(1+bumps)))

    references never decay (halflife = inf).
    """
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
