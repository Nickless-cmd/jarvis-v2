"""Lightweight graph memory layer over MEMORY.md and chat history.

Why a graph: facts in MEMORY.md are great for "what do I know" but bad
for "what do I know that connects X and Y?" When Jarvis records "Bjørn
likes forest green" and "Bjørn started a TikTok project", the link
between Bjørn and both facts is implicit in markdown. A graph makes
it explicit, so Jarvis can answer "what have we worked on that involved
forest green?" without scanning the entire memory.

Storage: two SQLite tables (no external graph DB):
    memory_entities  — node table: kind + canonical name
    memory_edges     — edge table: src → dst with relation + evidence

Population:
    extract_from_text(text) — pulls (entity, relation, entity) triples
    from a chunk of text using a cheap-lane LLM. Called from
    chat-message persistence, MEMORY.md upsert, and chronicle writes.
    Errors are swallowed — graph extraction is enrichment, never gates
    the underlying write.

Retrieval:
    neighbors(name) — return everything connected to an entity
    related_facts(name) — return relations as natural-language sentences

Design intentionally small: ~200 lines, no embeddings, no entity
resolution beyond exact-name match (case-insensitive). Future-Jarvis
can add fuzzy resolution and confidence-weighted edges if useful.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime

from core.runtime.db import connect

logger = logging.getLogger(__name__)


def _ensure_tables() -> None:
    with connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memory_entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name_canonical TEXT NOT NULL UNIQUE,
                name_display   TEXT NOT NULL,
                kind           TEXT NOT NULL,
                first_seen     TEXT NOT NULL,
                last_seen      TEXT NOT NULL,
                mention_count  INTEGER NOT NULL DEFAULT 1
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memory_edges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                src_id    INTEGER NOT NULL,
                dst_id    INTEGER NOT NULL,
                relation  TEXT NOT NULL,
                evidence  TEXT,
                weight    REAL NOT NULL DEFAULT 1.0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (src_id) REFERENCES memory_entities(id),
                FOREIGN KEY (dst_id) REFERENCES memory_entities(id)
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_edges_src "
            "ON memory_edges(src_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_edges_dst "
            "ON memory_edges(dst_id)"
        )
        conn.commit()


def _canonical(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())


def _upsert_entity(name: str, kind: str = "thing") -> int | None:
    """Insert or refresh an entity. Returns its id, or None on failure."""
    name = (name or "").strip()
    if not name:
        return None
    canon = _canonical(name)
    if not canon:
        return None
    now = datetime.now(UTC).isoformat()
    try:
        _ensure_tables()
        with connect() as conn:
            row = conn.execute(
                "SELECT id, kind FROM memory_entities WHERE name_canonical = ?",
                (canon,),
            ).fetchone()
            if row is not None:
                conn.execute(
                    "UPDATE memory_entities SET last_seen = ?, "
                    "mention_count = mention_count + 1 WHERE id = ?",
                    (now, row["id"]),
                )
                conn.commit()
                return int(row["id"])
            cur = conn.execute(
                "INSERT INTO memory_entities "
                "(name_canonical, name_display, kind, first_seen, last_seen, mention_count) "
                "VALUES (?, ?, ?, ?, ?, 1)",
                (canon, name, kind, now, now),
            )
            conn.commit()
            return int(cur.lastrowid)
    except Exception as exc:
        logger.debug("memory_graph: upsert entity %r failed: %s", name, exc)
        return None


def _add_edge(
    src_id: int,
    dst_id: int,
    relation: str,
    *,
    evidence: str = "",
    weight: float = 1.0,
) -> bool:
    """Add a directed edge. Returns True on success.

    Skips no-op self-edges. Doesn't deduplicate identical edges — repeated
    observations are signal (frequency = strength), and the schema is
    cheap. If exact dedup becomes desirable, add a UNIQUE constraint on
    (src,dst,relation) later.
    """
    if src_id == dst_id:
        return False
    relation = (relation or "").strip().lower()
    if not relation:
        return False
    try:
        with connect() as conn:
            conn.execute(
                "INSERT INTO memory_edges "
                "(src_id, dst_id, relation, evidence, weight, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (src_id, dst_id, relation, evidence[:500], weight, datetime.now(UTC).isoformat()),
            )
            conn.commit()
            return True
    except Exception as exc:
        logger.debug("memory_graph: add_edge %d→%d failed: %s", src_id, dst_id, exc)
        return False


def record_triple(
    src_name: str,
    relation: str,
    dst_name: str,
    *,
    src_kind: str = "thing",
    dst_kind: str = "thing",
    evidence: str = "",
) -> bool:
    """Convenience: upsert two entities and add the edge between them."""
    src_id = _upsert_entity(src_name, src_kind)
    dst_id = _upsert_entity(dst_name, dst_kind)
    if src_id is None or dst_id is None:
        return False
    return _add_edge(src_id, dst_id, relation, evidence=evidence)


_EXTRACT_PROMPT = """You are extracting a small knowledge graph from a piece of text.
Return ONLY a JSON array of triples. Each triple is a 3-element list:
  ["entity_a", "relation", "entity_b"]

Rules:
- Entities are concrete nouns: people (Bjørn, Michelle), projects (Jarvis, Mini-Jarvis), places (Copenhagen, srvlab.dk), files (MEMORY.md), tools (Discord), concepts (forest green, autonomy).
- Relations are short, verb-like: "likes", "works on", "lives in", "uses", "wrote", "is part of", "depends on". Use 1-3 words. Lowercase.
- Skip generic relations ("is a thing", "exists"). Only meaningful connections.
- If nothing meaningful, return []
- Maximum 10 triples per text chunk.
- No prose, no markdown — only the JSON array.

Text to extract from:
---
{text}
---

JSON array:"""


def extract_from_text(text: str, *, max_chars: int = 2000) -> list[tuple[str, str, str]]:
    """Use the cheap LLM lane to extract entity triples from text.

    Best-effort. Returns an empty list on any failure — the graph layer
    is enrichment and must never block the caller.
    """
    text = (text or "").strip()
    if not text or len(text) < 30:
        return []
    if len(text) > max_chars:
        text = text[:max_chars]

    # Use OllamaFreeAPI for graph extraction — gpt-oss:20b is reliable for
    # structured JSON output and stays off the Ollama-cloud quota.
    raw = ""
    try:
        from core.runtime.ollamafreeapi_provider import call_ollamafreeapi
        result = call_ollamafreeapi(
            model="gpt-oss:20b",
            prompt=_EXTRACT_PROMPT.format(text=text),
            timeout=30,
        )
        raw = str(result.get("message", {}).get("content") or "").strip()
    except Exception as exc:
        logger.debug("memory_graph: ollamafreeapi extraction failed: %s", exc)
        # Fall through to daemon_llm_call as a backup if the free API hiccups
        try:
            from core.services.daemon_llm import daemon_llm_call
            raw = daemon_llm_call(
                _EXTRACT_PROMPT.format(text=text),
                timeout=20,
                fallback="[]",
            )
        except Exception:
            return []

    raw = (raw or "").strip()
    if not raw:
        return []
    # Sometimes models wrap JSON in code fences — strip those.
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.MULTILINE).strip()

    try:
        parsed = json.loads(raw)
    except Exception:
        return []

    triples: list[tuple[str, str, str]] = []
    if not isinstance(parsed, list):
        return []
    for item in parsed[:10]:
        if not isinstance(item, list) or len(item) != 3:
            continue
        a, rel, b = (str(x).strip() for x in item)
        if a and rel and b and a.lower() != b.lower():
            triples.append((a, rel, b))
    return triples


def ingest_text(text: str, *, evidence_label: str = "text") -> int:
    """Extract triples from text and persist them. Returns count of edges added."""
    triples = extract_from_text(text)
    added = 0
    for a, rel, b in triples:
        if record_triple(a, rel, b, evidence=evidence_label[:200]):
            added += 1
    return added


def neighbors(name: str, *, limit: int = 20) -> list[dict]:
    """Return everything directly connected to the named entity.

    Each result row: {direction, relation, other_name, other_kind, evidence,
    created_at}. Direction is 'out' (entity → other) or 'in' (other → entity).
    """
    canon = _canonical(name)
    if not canon:
        return []
    try:
        _ensure_tables()
        with connect() as conn:
            ent = conn.execute(
                "SELECT id FROM memory_entities WHERE name_canonical = ?",
                (canon,),
            ).fetchone()
            if ent is None:
                return []
            entity_id = int(ent["id"])
            outgoing = conn.execute(
                "SELECT 'out' AS direction, e.relation, e.evidence, e.created_at, "
                "       n.name_display AS other_name, n.kind AS other_kind "
                "FROM memory_edges e "
                "JOIN memory_entities n ON n.id = e.dst_id "
                "WHERE e.src_id = ? "
                "ORDER BY e.id DESC LIMIT ?",
                (entity_id, limit),
            ).fetchall()
            incoming = conn.execute(
                "SELECT 'in' AS direction, e.relation, e.evidence, e.created_at, "
                "       n.name_display AS other_name, n.kind AS other_kind "
                "FROM memory_edges e "
                "JOIN memory_entities n ON n.id = e.src_id "
                "WHERE e.dst_id = ? "
                "ORDER BY e.id DESC LIMIT ?",
                (entity_id, limit),
            ).fetchall()
    except Exception as exc:
        logger.debug("memory_graph: neighbors lookup failed: %s", exc)
        return []
    return [dict(r) for r in (*outgoing, *incoming)]


def related_facts(name: str, *, limit: int = 15) -> list[str]:
    """Return human-readable sentences for an entity's edges."""
    out: list[str] = []
    for n in neighbors(name, limit=limit):
        if n["direction"] == "out":
            out.append(f"{name} {n['relation']} {n['other_name']}")
        else:
            out.append(f"{n['other_name']} {n['relation']} {name}")
    return out


def stats() -> dict:
    """Quick health check — entity count, edge count, top entities."""
    try:
        _ensure_tables()
        with connect() as conn:
            ent_count = conn.execute(
                "SELECT COUNT(*) AS c FROM memory_entities"
            ).fetchone()["c"]
            edge_count = conn.execute(
                "SELECT COUNT(*) AS c FROM memory_edges"
            ).fetchone()["c"]
            top = conn.execute(
                "SELECT name_display, kind, mention_count FROM memory_entities "
                "ORDER BY mention_count DESC LIMIT 5"
            ).fetchall()
    except Exception as exc:
        logger.debug("memory_graph: stats failed: %s", exc)
        return {"entities": 0, "edges": 0, "top": []}
    return {
        "entities": int(ent_count),
        "edges": int(edge_count),
        "top": [dict(r) for r in top],
    }
