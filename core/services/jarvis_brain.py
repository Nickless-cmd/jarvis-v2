"""Jarvis Brain — kurateret vidensjournal. Kerne-CRUD-laget.

Kun ren læs/skriv + søg. Ingen daemon-logik (det ligger i jarvis_brain_daemon.py).
Ingen LLM-kald (konsolidering ligger i daemonen).

Spec: docs/superpowers/specs/2026-05-02-jarvis-brain-design.md
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import hashlib
import json
import math
import os
import re
import secrets
import sqlite3
import time

import numpy as np
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


_IMPORTANCE_BY_KIND: dict[str, float] = {
    "observation": 0.4,
    "fakta":       0.8,
    "indsigt":     0.7,
    "reference":   0.9,
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
    recall_count: int = 0  # total number of times entry has been recalled (Memory Fix Phase 1, 2026-06-08)
    # Importance + the structural fields that follow it now have sensible
    # defaults (2026-05-15). Production call-sites in entry_from_frontmatter
    # and create_brain_entry pass them explicitly via _IMPORTANCE_BY_KIND
    # lookup. Defaults are for test fixtures and one-off construction
    # where the caller doesn't care about these axes.
    importance: float = 0.5  # 0.0–1.0, styrer hvor hurtigt entry glemmes
    related: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)  # metadata tags for filtering (B3, 2026-06-09)
    trigger: str = "spontaneous"
    status: str = "active"
    superseded_by: Optional[str] = None
    source_chronicle: Optional[str] = None
    source_url: Optional[str] = None

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


def _parse_iso(s) -> Optional[datetime]:
    """Parse ISO timestamp from string or pass-through if already datetime.

    PyYAML parses ISO timestamps directly as datetime objects, so we accept
    either form for round-trip robustness.
    """
    if s is None:
        return None
    if isinstance(s, datetime):
        return s if s.tzinfo else s.replace(tzinfo=timezone.utc)
    return datetime.fromisoformat(str(s))


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
        "importance": entry.importance,
        "related": entry.related,
        "tags": entry.tags,
        "status": entry.status,
        "superseded_by": entry.superseded_by,
        "source_chronicle": entry.source_chronicle,
        "source_url": entry.source_url,
    }
    yaml_text = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True)
    return f"---\n{yaml_text}---\n\n{entry.content.rstrip()}\n"


def entry_from_frontmatter(fm: dict, body: str) -> BrainEntry:
    """Build a BrainEntry from parsed frontmatter dict + body string."""
    kind = fm["kind"]
    return BrainEntry(
        id=fm["id"],
        kind=kind,
        visibility=fm["visibility"],
        domain=fm["domain"],
        title=fm["title"],
        content=body.strip(),
        created_at=_parse_iso(fm["created_at"]),
        updated_at=_parse_iso(fm.get("updated_at") or fm["created_at"]),
        last_used_at=_parse_iso(fm.get("last_used_at")),
        salience_base=float(fm.get("salience_base", 1.0)),
        salience_bumps=int(fm.get("salience_bumps", 0)),
        recall_count=int(fm.get("recall_count", 0)),
        importance=float(fm.get("importance", _IMPORTANCE_BY_KIND.get(kind, 0.5))),
        related=list(fm.get("related") or []),
        tags=list(fm.get("tags") or []),
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
    recall_count    INTEGER NOT NULL DEFAULT 0,
    importance      REAL NOT NULL DEFAULT 0.5,
    tags            TEXT NOT NULL DEFAULT '[]',  -- JSON array of tag strings (B3, 2026-06-09)
    related         TEXT NOT NULL DEFAULT '[]',  -- JSON array of related entry IDs (B4, 2026-06-09)
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

CREATE TABLE IF NOT EXISTS brain_temporal_edges (
    from_id       TEXT NOT NULL,
    to_id         TEXT NOT NULL,
    relation_type TEXT NOT NULL,  -- temporal|semantic|entity|chain
    confidence    REAL NOT NULL DEFAULT 0.0,
    inferred_at   TEXT NOT NULL,
    PRIMARY KEY (from_id, to_id, relation_type)
);

CREATE INDEX IF NOT EXISTS idx_temporal_edges_from ON brain_temporal_edges(from_id);
CREATE INDEX IF NOT EXISTS idx_temporal_edges_to   ON brain_temporal_edges(to_id);
"""


def _workspace_root() -> Path:
    """Base dir for brain-relative paths. Override in tests via monkeypatch.

    Returns JARVIS_HOME so paths like shared/jarvis_brain/... are correctly
    relative. Used by brain_dir() and all relative-path storage in the index.

    NOTE: existing DB entries stored paths relative to the old workspaces/ base
    (e.g. 'default/jarvis_brain/...'). Those are reconstructed via the
    JARVIS_WORKSPACES_ROOT env override in tests. New entries store paths
    relative to JARVIS_HOME (e.g. 'shared/jarvis_brain/...').
    """
    if os.environ.get("JARVIS_WORKSPACES_ROOT"):
        # Test override: keep backwards compat for tests that monkeypatch this
        return Path(os.environ["JARVIS_WORKSPACES_ROOT"])
    return Path(os.environ.get("JARVIS_HOME") or Path.home() / ".jarvis-v2")


def _state_root() -> Path:
    return Path(
        os.environ.get("JARVIS_STATE_ROOT")
        or Path.home() / ".jarvis-v2" / "state"
    )


def brain_dir() -> Path:
    """Return the brain storage dir under JARVIS_HOME/shared/jarvis_brain.

    Uses _workspace_root() as base so tests can monkeypatch it. In production
    _workspace_root() returns JARVIS_HOME (~/.jarvis-v2), so the final path
    is ~/.jarvis-v2/shared/jarvis_brain.
    """
    return _workspace_root() / "shared" / "jarvis_brain"


def index_db_path() -> Path:
    return _state_root() / "jarvis_brain_index.sqlite"


def connect_index() -> sqlite3.Connection:
    p = index_db_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p))
    conn.executescript(_INDEX_SCHEMA)
    _ensure_index_schema_migrations(conn)
    conn.commit()
    return conn


def _ensure_index_schema_migrations(conn: sqlite3.Connection) -> None:
    """Bring pre-existing brain_index tables up to the current schema.

    ``CREATE TABLE IF NOT EXISTS`` does not add columns to old SQLite tables.
    Keep this idempotent so daemon startup can safely repair schema drift.
    """
    cols = {
        str(row[1])
        for row in conn.execute("PRAGMA table_info(brain_index)").fetchall()
    }
    if "importance" not in cols:
        conn.execute(
            "ALTER TABLE brain_index ADD COLUMN importance REAL NOT NULL DEFAULT 0.5"
        )
    if "recall_count" not in cols:
        conn.execute(
            "ALTER TABLE brain_index ADD COLUMN recall_count INTEGER NOT NULL DEFAULT 0"
        )
    if "tags" not in cols:
        conn.execute(
            "ALTER TABLE brain_index ADD COLUMN tags TEXT NOT NULL DEFAULT '[]'"
        )
    if "related" not in cols:
        # 2026-06-09 (B4 schema repair, Claude): infer_temporal_edges()
        # SELECTs `related` directly from brain_index, but the column was
        # never added — every B4 catchup pass logged
        # "no such column: related" (~14 errors/hour). Add the column +
        # backfill from brain_relations so existing entries get their
        # links the next time the daemon runs.
        conn.execute(
            "ALTER TABLE brain_index ADD COLUMN related TEXT NOT NULL DEFAULT '[]'"
        )
        try:
            conn.execute(
                """UPDATE brain_index
                   SET related = COALESCE(
                       (SELECT json_group_array(to_id)
                        FROM brain_relations
                        WHERE from_id = brain_index.id),
                       '[]'
                   )"""
            )
        except sqlite3.OperationalError:
            # brain_relations may not exist yet on a fresh DB — leave
            # default '[]' and let write_entry populate it going forward.
            pass


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
    tags: list[str] | None = None,
    source_url: str | None = None,
    source_chronicle: str | None = None,
    importance: float | None = None,
    now: datetime | None = None,
    skip_temporal: bool = False,
) -> str:
    """Skriver en ny brain-entry til disk og indexerer den (uden embedding endnu).

    Returnerer den nye entry's id.
    """
    now = now or datetime.now(timezone.utc)
    new_id = new_brain_id()
    related = related or []
    tags = tags or []

    # Importance-gate: hvis ikke angivet, brug kind-baseret default
    if importance is None:
        importance = _IMPORTANCE_BY_KIND.get(kind, 0.5)
    importance = max(0.0, min(1.0, importance))

    # salience_base sættes fra importance — lavere importance = hurtigere glemsel
    salience_base = importance

    entry = BrainEntry(
        id=new_id, kind=kind, visibility=visibility, domain=domain,
        title=title, content=content,
        created_at=now, updated_at=now, last_used_at=None,
        salience_base=salience_base, salience_bumps=0,
        importance=importance, related=related, tags=tags,
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
                last_used_at, salience_base, salience_bumps, recall_count, importance,
                tags, related, status, superseded_by, file_hash, embedding, embedding_dim, indexed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, 0, 0, ?, ?, ?,
                       'active', NULL, ?, NULL, NULL, ?)""",
            (new_id, rel_path, kind, visibility, domain, title,
             _iso(now), _iso(now), salience_base, importance,
             json.dumps(tags), json.dumps(related), fhash, _iso(now)),
        )
        for to_id in related:
            conn.execute(
                "INSERT OR IGNORE INTO brain_relations(from_id, to_id) VALUES (?, ?)",
                (new_id, to_id),
            )
        conn.commit()
    finally:
        conn.close()

    # B4 — temporal linking: infer edges to existing entries (2026-06-09)
    if not skip_temporal:
        try:
            infer_temporal_edges(new_id, now=now)
        except Exception:
            # Never let inference failure block the write
            pass

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
    """Compute time-decayed salience with bump amplification + importance gate.

    Formula:
        effective = max(floor, importance * decay * (1 + 0.3*log2(1+bumps)))

    importance bliver den øvre grænse — en entry med importance=0.3 kan max
    have 0.3 i effektiv salience, uanset bumps. Det er importance-gaten.
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
    # Importance-ceiling: effektiv salience kan aldrig overstige importance
    effective = min(raw, entry.importance)
    return max(_SALIENCE_FLOOR, effective)


# ---------------------------------------------------------------------------
# Embedding + search
# ---------------------------------------------------------------------------


def _embed_text(text: str) -> np.ndarray:
    """Wrapper around eksisterende embedder. Override in tests via monkeypatch.

    Uses semantic_memory's nomic-embed-text via Ollama (768-dim float32).
    """
    from core.services.semantic_memory import _embed_ollama
    v = _embed_ollama(text)
    if v is None:
        # Fallback: zero vector (will sort to end of any cosine ranking)
        return np.zeros(768, dtype=np.float32)
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
                _, body = parse_frontmatter(full)
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
    tags: list[str] | None = None,
    include_archived: bool = False,
    now: datetime | None = None,
    use_temporal_boost: bool = True,
) -> list[BrainEntry]:
    """Hybrid embedding search: 0.7*cosine + 0.3*effective_salience + temporal boost.

    Visibility_ceiling filtrerer ud poster med højere visibility-niveau.
    Tags: hvis angivet, returnér kun entries der har ALLE de angivne tags (AND-match).
    Temporal boost (B4 Phase 2, 2026-06-09): entries with strong temporal edges
    to other entries get a lift of up to +0.15 on their final score.
    """
    now = now or datetime.now(timezone.utc)
    qv = _embed_text(query_text)
    ceiling_lvl = _VIS_LEVEL[visibility_ceiling]

    sql = """SELECT id, kind, visibility, salience_base, salience_bumps,
                    last_used_at, embedding, embedding_dim, created_at, tags
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

    candidate_ids: list[str] = []
    scored: list[tuple[float, str]] = []
    for row in rows:
        entry_id, kind, vis, sal_base, bumps, last_used, emb_blob, emb_dim, created_at = row[:9]
        entry_tags_raw = row[9] if len(row) > 9 else "[]"
        if _VIS_LEVEL[vis] > ceiling_lvl:
            continue

        # Tags filter: AND-match — alle angivne tags skal være til stede
        if tags:
            try:
                entry_tags = json.loads(entry_tags_raw) if isinstance(entry_tags_raw, str) else (entry_tags_raw or [])
            except (json.JSONDecodeError, TypeError):
                entry_tags = []
            if not all(t in entry_tags for t in tags):
                continue

        v = _embedding_from_blob(emb_blob, emb_dim)
        denom = float(np.linalg.norm(qv) * np.linalg.norm(v)) or 1e-9
        cos = float(np.dot(qv, v) / denom)

        # Effektiv salience uden at læse fil (genberegnet inline)
        last = _parse_iso(last_used) if last_used else _parse_iso(created_at)
        days = max(0.0, (now - last).total_seconds() / 86400.0)
        halflife = _HALFLIFE_DAYS[kind]
        decay = 1.0 if math.isinf(halflife) else math.exp(-days / halflife)
        bumps_factor = math.log2(1 + bumps) if bumps > 0 else 0.0
        eff = max(_SALIENCE_FLOOR, sal_base * decay * (1.0 + 0.3 * bumps_factor))

        score = 0.7 * cos + 0.3 * eff
        scored.append((score, entry_id))
        candidate_ids.append(entry_id)

    # B4 Phase 2 — temporal boost: entries with strong edges get a lift
    if use_temporal_boost and candidate_ids:
        temporal_boosts = _compute_search_temporal_boost(candidate_ids)
        scored = [
            (s + temporal_boosts.get(eid, 0.0), eid)
            for s, eid in scored
        ]

    scored.sort(reverse=True)
    top = scored[:limit]
    return [read_entry(eid) for _, eid in top]


def _compute_search_temporal_boost(
    candidate_ids: list[str],
    *,
    boost_factor: float = 0.15,
    min_confidence: float = 0.5,
) -> dict[str, float]:
    """Compute temporal boost for search candidates.

    For each candidate, looks up its combined temporal edges and returns
    a boost value: boost_factor × max(confidence) for edges ≥ min_confidence.
    Candidates with no qualifying edges get 0.0 boost.
    """
    if not candidate_ids:
        return {}
    n = len(candidate_ids)
    ph = ",".join("?" * n)
    sql = (
        f"SELECT entry_id, MAX(confidence) AS best_conf FROM ("
        f"  SELECT from_id AS entry_id, confidence FROM brain_temporal_edges "
        f"    WHERE from_id IN ({ph}) AND relation_type='combined' AND confidence >= ?"
        f"  UNION ALL "
        f"  SELECT to_id AS entry_id, confidence FROM brain_temporal_edges "
        f"    WHERE to_id IN ({ph}) AND relation_type='combined' AND confidence >= ?"
        f") GROUP BY entry_id"
    )
    params = (*candidate_ids, min_confidence, *candidate_ids, min_confidence)

    conn = connect_index()
    try:
        rows = conn.execute(sql, params).fetchall()
    finally:
        conn.close()

    boosts: dict[str, float] = {}
    for entry_id, best_conf in rows:
        boost = round(best_conf * boost_factor, 4)
        if boost > 0.0:
            boosts[entry_id] = boost
    return boosts


def bump_salience(entry_id: str, now: datetime | None = None) -> None:
    """Increments salience_bumps + recall_count + opdaterer last_used_at i index OG fil.

    Filen er sandhed; index opdateres synkront. Hvis fil-update fejler,
    rejeses exception (caller-decides). Reindex-loop'et fanger evt. drift.

    2026-06-08 (Memory Fix Phase 1): adds recall_count increment alongside
    salience_bumps. recall_count tracks total reads (search hits + direct
    reads), while salience_bumps tracks search-surface frequency specifically.
    """
    now = now or datetime.now(timezone.utc)
    entry = read_entry(entry_id)
    entry.salience_bumps += 1
    entry.recall_count += 1
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
               SET salience_bumps = ?, recall_count = ?, last_used_at = ?,
                   updated_at = ?, file_hash = ?, indexed_at = ?
               WHERE id = ?""",
            (entry.salience_bumps, entry.recall_count, _iso(now),
             _iso(now), fhash, _iso(now), entry_id),
        )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Lifecycle: archive, supersede, rebuild_index
# ---------------------------------------------------------------------------


def archive_entry(
    entry_id: str, *, reason: str = "manual", now: datetime | None = None,
) -> None:
    """Mark entry as archived and move file to _archive/<kind>/."""
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


def supersede(
    *, old_ids: list[str], new_id: str, now: datetime | None = None,
) -> None:
    """Mark old entries as superseded by new_id (keeps files in place)."""
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
    """Scan brain_dir() for .md files; new/changed hash → update index.

    Returnerer antal rækker der blev tilføjet eller opdateret denne kørsel.
    Idempotent — anden kørsel uden ændringer returnerer 0.
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
            if kind not in _VALID_KINDS:
                continue
            for md_path in kind_dir.glob("*.md"):
                try:
                    fm, _body = parse_frontmatter(md_path)
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
                    conn.execute(
                        """INSERT INTO brain_index
                           (id, path, kind, visibility, domain, title,
                            created_at, updated_at, last_used_at,
                            salience_base, salience_bumps, recall_count,
                            importance, tags, related, status, superseded_by,
                            file_hash, embedding, embedding_dim, indexed_at)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,NULL,NULL,?)""",
                        (
                            fm["id"], rel, kind, fm["visibility"], fm["domain"],
                            fm["title"], fm["created_at"],
                            fm.get("updated_at", fm["created_at"]),
                            fm.get("last_used_at"),
                            fm.get("salience_base", 1.0),
                            fm.get("salience_bumps", 0),
                            int(fm.get("recall_count", 0)),
                            float(fm.get("importance", _IMPORTANCE_BY_KIND.get(kind, 0.5))),
                            json.dumps(fm.get("tags") or []),
                            json.dumps(fm.get("related") or []),
                            fm.get("status", "active"),
                            fm.get("superseded_by"),
                            fhash,
                            _iso(now),
                        ),
                    )
                    changes += 1
                elif row[0] != fhash:
                    conn.execute(
                        """UPDATE brain_index
                           SET path=?, kind=?, visibility=?, domain=?, title=?,
                               updated_at=?, last_used_at=?, salience_base=?,
                               salience_bumps=?, recall_count=?, importance=?,
                               tags=?, related=?, status=?, superseded_by=?,
                               file_hash=?, embedding=NULL, embedding_dim=NULL,
                               indexed_at=?
                           WHERE id=?""",
                        (
                            rel, kind, fm["visibility"], fm["domain"], fm["title"],
                            fm.get("updated_at"), fm.get("last_used_at"),
                            fm.get("salience_base", 1.0),
                            fm.get("salience_bumps", 0),
                            int(fm.get("recall_count", 0)),
                            float(fm.get("importance", _IMPORTANCE_BY_KIND.get(kind, 0.5))),
                            json.dumps(fm.get("tags") or []),
                            json.dumps(fm.get("related") or []),
                            fm.get("status", "active"),
                            fm.get("superseded_by"),
                            fhash,
                            _iso(now),
                            fm["id"],
                        ),
                    )
                    changes += 1
        conn.commit()
    finally:
        conn.close()
    return changes


# ---------------------------------------------------------------------------
# B4 — Temporal linking (2026-06-09)
# ---------------------------------------------------------------------------


def _extract_text_for_entry(entry_id: str) -> str:
    """Read entry content from disk for entity/semantic analysis."""
    entry = read_entry(entry_id)
    return f"{entry.title}\n\n{entry.content}"


def _temporal_similarity_score(hours_apart: float) -> float:
    """Score 0.0–1.0 based on temporal proximity. 1.0 at ≤1h, decays to 0 at 24h."""
    if hours_apart <= 1.0:
        return 1.0
    if hours_apart >= 24.0:
        return 0.0
    # Exponential decay from 1→0 over the remaining 23h
    return max(0.0, 1.0 - (hours_apart - 1.0) / 23.0)


def _cosine_similarity(a_vec: np.ndarray, b_vec: np.ndarray) -> float:
    denom = float(np.linalg.norm(a_vec) * np.linalg.norm(b_vec))
    if denom < 1e-9:
        return 0.0
    return float(np.dot(a_vec, b_vec) / denom)


def _compute_temporal_confidence(
    *,
    temporal: float,
    semantic: float,
    entity: float,
    is_chain: bool,
    chain_score: float = 0.0,
) -> float:
    """Combine four signals into a single confidence score (0.0–1.0).

    Formula: 0.4×temporal + 0.4×semantic + 0.2×entity, +0.15×chain_score.
    Cap at 0.98 max.
    """
    confidence = 0.4 * temporal + 0.4 * semantic + 0.2 * entity
    chain_bonus = 0.15 * chain_score
    confidence += chain_bonus
    return min(confidence, 0.98)


def _compute_chain_score(
    *,
    new_entry: BrainEntry,
    cand_entry: BrainEntry,
    hours_apart: float,
    cand_related: list[str],
) -> float:
    """Compute chain signal score (0.0–1.0) between two entries.

    Three sub-signals fused with decreasing weight:
    1. **Sequence** (0.5): Same domain + close in time (≤2h) → strong chain
    2. **Topic thread** (0.3): Similar title stems (common prefix ≥4 chars) → moderate
    3. **Reference overlap** (0.2): Shared entries in ``related`` fields → weak

    Returns a score in [0.0, 1.0].
    """
    # --- 1. Sequence detection ---
    seq_score = 0.0
    if new_entry.domain == cand_entry.domain and hours_apart <= 2.0:
        seq_score = 1.0 - (hours_apart / 2.0)  # linear decay 1→0 over 2h

    # --- 2. Topic thread detection ---
    topic_score = 0.0
    new_title = new_entry.title.lower()
    cand_title = cand_entry.title.lower()
    # Find common prefix of non-empty words
    new_words = new_title.split()
    cand_words = cand_title.split()
    common_prefix_len = 0
    for a, b in zip(new_words, cand_words):
        if a == b and len(a) >= 4:
            common_prefix_len += len(a)
        else:
            break
    if common_prefix_len >= 4 and common_prefix_len >= len(new_title.replace(" ", "")) * 0.3:
        topic_score = min(1.0, common_prefix_len / 20.0)

    # --- 3. Reference overlap ---
    ref_score = 0.0
    new_related = set(new_entry.related or [])
    if cand_related:
        shared = new_related & set(cand_related)
        if shared and new_related:
            ref_score = len(shared) / max(len(new_related), 1)

    # Fuse with weights
    chain_score = 0.5 * seq_score + 0.3 * topic_score + 0.2 * ref_score
    return min(chain_score, 1.0)


def infer_temporal_edges(
    new_entry_id: str,
    now: datetime | None = None,
) -> int:
    """Run four-signal inference between a new entry and all existing active entries.

    For each candidate pair, computes temporal, semantic, entity and chain signals,
    combines into a confidence score (0.4×temporal + 0.4×semantic + 0.2×entity
    +0.15 if chain), and stores qualifying edges (confidence ≥ 0.4) in
    ``brain_temporal_edges``.

    Returns the number of edges created.
    """
    now = now or datetime.now(timezone.utc)
    from core.services.multi_signal_retrieval import entity_overlap_score

    new_entry = read_entry(new_entry_id)
    new_text = f"{new_entry.title}\n\n{new_entry.content}"
    new_created = new_entry.created_at

    # Embed the new entry inline (it was just written — no embedding yet)
    new_vec = _embed_text(new_text)

    conn = connect_index()
    try:
        candidates = conn.execute(
            """SELECT id, created_at, embedding, embedding_dim, title, domain, related
               FROM brain_index
               WHERE id != ? AND status = 'active'
                 AND embedding IS NOT NULL""",
            (new_entry_id,),
        ).fetchall()
    finally:
        conn.close()

    edges_created = 0

    for cand_id, cand_created_str, emb_blob, emb_dim, cand_title, cand_domain, cand_related_raw in candidates:
        cand_created = _parse_iso(cand_created_str)
        if cand_created is None:
            continue

        # --- 1. Temporal signal ---
        hours_apart = abs((new_created - cand_created).total_seconds()) / 3600.0
        temporal_score = _temporal_similarity_score(hours_apart)

        # --- 2. Semantic signal ---
        if emb_blob is not None and emb_dim is not None:
            cand_vec = _embedding_from_blob(emb_blob, emb_dim)
            semantic_score = _cosine_similarity(new_vec, cand_vec)
        else:
            semantic_score = 0.0

        # --- 3. Entity signal ---
        try:
            cand_text = _extract_text_for_entry(cand_id)
        except KeyError:
            continue
        entity_score = entity_overlap_score(new_text, cand_text)

        # --- 4. Chain signal (B4 Phase 4, 2026-06-09) ---
        cand_related = []
        if cand_related_raw:
            try:
                cand_related = json.loads(cand_related_raw) if isinstance(cand_related_raw, str) else (cand_related_raw or [])
            except (json.JSONDecodeError, TypeError):
                cand_related = []
        cand_entry = BrainEntry(
            id=cand_id, kind="", visibility="", domain=cand_domain or "",
            title=cand_title, content="",
            created_at=cand_created, updated_at=cand_created,
            last_used_at=None, salience_base=0.5, salience_bumps=0,
            importance=0.5, related=cand_related, tags=[],
            trigger="spontaneous", status="active",
        )
        chain_score = _compute_chain_score(
            new_entry=new_entry,
            cand_entry=cand_entry,
            hours_apart=hours_apart,
            cand_related=cand_related,
        )

        confidence = _compute_temporal_confidence(
            temporal=temporal_score,
            semantic=semantic_score,
            entity=entity_score,
            is_chain=chain_score >= 0.5,
            chain_score=chain_score,
        )

        if confidence < 0.4:
            continue

        # Reasoning string for audit trail
        reasoning = (
            f"t={temporal_score:.2f}/s={semantic_score:.2f}/"
            f"e={entity_score:.2f}/c={chain_score:.2f}"
        )

        _store_temporal_edge(
            from_id=new_entry_id,
            to_id=cand_id,
            confidence=confidence,
            reasoning=reasoning,
            now=now,
        )
        edges_created += 1

    return edges_created


def _store_temporal_edge(
    from_id: str,
    to_id: str,
    confidence: float,
    reasoning: str,
    now: datetime,
) -> None:
    """Insert or update a temporal edge with combined confidence.

    Stores a single row per pair with ``relation_type='combined'``.
    Individual signal breakdown is captured in ``reasoning`` for audit
    (structure: ``t=0.xx/s=0.xx/e=0.xx/c=True|False``).
    """
    conn = connect_index()
    try:
        conn.execute(
            """INSERT OR REPLACE INTO brain_temporal_edges
               (from_id, to_id, relation_type, confidence, inferred_at)
               VALUES (?, ?, 'combined', ?, ?)""",
            (from_id, to_id, round(confidence, 4), _iso(now)),
        )
        conn.commit()
    finally:
        conn.close()


def get_temporal_neighbors(
    entry_id: str,
    min_confidence: float = 0.4,
    limit: int = 10,
) -> list[tuple[str, float]]:
    """Get tidligere inferred temporal neighbors for an entry.

    Returns a list of (neighbor_id, combined_confidence) sorted descending.
    Combined confidence = max of individual relation_type confidences for
    that neighbor pair.
    """
    conn = connect_index()
    try:
        rows = conn.execute(
            """SELECT
                   CASE WHEN from_id = ? THEN to_id ELSE from_id END AS neighbor,
                   MAX(confidence) AS combined_conf
               FROM brain_temporal_edges
               WHERE (from_id = ? OR to_id = ?)
                 AND confidence >= ?
               GROUP BY neighbor
               ORDER BY combined_conf DESC
               LIMIT ?""",
            (entry_id, entry_id, entry_id, min_confidence, limit),
        ).fetchall()
    finally:
        conn.close()
    return [(row[0], row[1]) for row in rows]


def temporal_boost_recall(
    entry_ids: list[str],
    *,
    boost_factor: float = 0.15,
    min_confidence: float = 0.5,
) -> dict[str, float]:
    """Compute temporal boost scores for a set of entry IDs.

    For each entry in ``entry_ids``, finds its temporal neighbors and returns
    a map ``{neighbor_id: boost_score}`` where:
      boost_score = boost_factor × edge_confidence

    The boost is only applied if at least one of the queried entries has
    a temporal edge to the neighbor — this prevents stale/distant relations
    from artificially inflating scores.

    Returns:
        Dict mapping neighbor_id (NOT in entry_ids) to boost score.
    """
    if not entry_ids:
        return {}

    if not entry_ids:
        return {}

    n = len(entry_ids)
    ph = ",".join("?" * n)
    # SQL with 4× placeholders + 1× confidence = 4n + 1 params
    sql = (
        f"SELECT CASE WHEN from_id IN ({ph}) THEN to_id ELSE from_id END AS neighbor, "
        f"MAX(confidence) AS best_conf "
        f"FROM brain_temporal_edges "
        f"WHERE (from_id IN ({ph}) OR to_id IN ({ph})) "
        f"AND relation_type = 'combined' AND confidence >= ? "
        f"AND CASE WHEN from_id IN ({ph}) THEN to_id ELSE from_id END NOT IN ({ph}) "
        f"GROUP BY neighbor ORDER BY best_conf DESC"
    )
    params = (*entry_ids, *entry_ids, *entry_ids, min_confidence, *entry_ids, *entry_ids)
    # 4n + 1 = 6n... no. Let's verify: ph in {ph} = n params
    # SQL has 5× {ph}, each = n → 5n params + 1 confidence = 5n + 1
    # Params: entry_ids(1) + entry_ids(2) + entry_ids(3) + conf + entry_ids(4) + entry_ids(5) = 5n + 1 ✓

    conn = connect_index()
    try:
        rows = conn.execute(sql, params).fetchall()
    finally:
        conn.close()

    boosts: dict[str, float] = {}
    for neighbor_id, best_conf in rows:
        boost = best_conf * boost_factor
        if boost > 0.0:
            boosts[neighbor_id] = round(boost, 4)
    return boosts


def prune_stale_edges(
    *,
    max_age_days: int = 90,
    min_confidence: float = 0.2,
) -> int:
    """Remove stale temporal edges with low confidence.

    Retains edges where confidence ≥ min_confidence (even if old — high-confidence
    relations are valuable). Removes old + low-confidence noise.

    Returns number of deleted edges.
    """
    cutoff = datetime.now(timezone.utc).isoformat()
    conn = connect_index()
    try:
        result = conn.execute(
            """DELETE FROM brain_temporal_edges
               WHERE inferred_at < date('now', ? || ' days')
                 AND confidence < ?""",
            (f"-{max_age_days}", min_confidence),
        )
        conn.commit()
        return result.rowcount
    finally:
        conn.close()


def full_rebuild(
    *,
    batch_size: int = 20,
) -> dict:
    """Genberegn alle temporale edges fra bunden.

    Truncater ``brain_temporal_edges``, kører fuld inferens på tværs af alle
    aktive entries (dem med embeddings), og returnerer statistik.

    Bruges ved schema-migration, manuel repair, eller efter import af
    eksisterende entries.

    Idempotent: kørsel to gange producerer samme edges (samme confidence).
    """
    conn = connect_index()
    try:
        conn.execute("DELETE FROM brain_temporal_edges")
        conn.commit()
    finally:
        conn.close()

    # Hent alle aktive entries med embeddings, sorteret efter created_at
    conn = connect_index()
    try:
        rows = conn.execute(
            "SELECT id FROM brain_index "
            "WHERE status = 'active' AND embedding IS NOT NULL "
            "ORDER BY created_at ASC"
        ).fetchall()
    finally:
        conn.close()

    total = len(rows)
    if total == 0:
        return {"total_entries": 0, "edges_created": 0, "errors": []}

    edges_created = 0
    errors: list[str] = []
    processed = 0

    for row in rows:
        eid = row[0]
        try:
            n = infer_temporal_edges(eid)
            edges_created += n
        except Exception as exc:
            errors.append(f"{eid}: {exc}")
        processed += 1

    _emit_jarvis_brain_event("temporal_full_rebuild", {
        "total_entries": total,
        "edges_created": edges_created,
        "errors": len(errors),
    })

    return {
        "total_entries": total,
        "edges_created": edges_created,
        "errors": errors,
    }


def build_jarvis_brain_surface() -> dict[str, object]:
    """Mission Control surface — read-only meta-projection.

    Added during 2026-05-13 coverage push (system_cartographer dark-edge
    closure). Reports module presence so the cartographer registers it as
    observed. Specific state-readers added as the module evolves.
    """
    return {
        "active": True,
        "mode": "jarvis_brain",
        "summary": "Module loaded; entry points available.",
        "authority": "derived-read-only",
    }


def _emit_jarvis_brain_event(kind: str, payload: dict[str, object] | None = None) -> None:
    """Emit a scoped event — defensive, never blocks caller.
    Cartographer scans for event_bus.publish() text.
    """
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(
            f"jarvis_brain.{kind}",
            payload or {},
        )
    except Exception:
        pass

