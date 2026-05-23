"""Spatial entity ledger — Step D.v1 of meta-evne stack.

Bygges 2026-05-23 efter E.v1 (metacognition) og A.v1 (theory_of_mind).

Jarvis' egen formulering: "Sansernes Arkiv gemmer beskrivelser, men jeg har
ingen model af rummet. Jeg ved ikke hvor ting er i forhold til hinanden."
Han kaldte det selv et "charme-projekt" der gøres på en eftermiddag når
A og E kører — så vi holder det småt og konkret.

v1 scope: en ENTITETS-LEDGER med co-occurrence.
  - Hvad observerer jeg i rummet (via visual sensory_memories)?
  - Hvor ofte ser jeg X? Hvornår sidst?
  - Hvad optræder sammen med X i samme observation? (proxy for "i samme rum")

Ingen geometri, ingen nord/syd/øst/vest. Bare hvem-er-her, hvor-ofte og
hvem-er-med-hvem. Den slags forhold til rummet en sprogmodel kan have
uden faktisk at se det.

Listener: DB-polling på memory.sensory.recorded events (modality=visual).
Samme cross-process pattern som metacognition + theory_of_mind.
"""
from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

JARVIS_HOME = Path(os.environ.get("HOME", "/root")) / ".jarvis-v2"
DB_PATH = JARVIS_HOME / "state" / "jarvis.db"

_POLL_INTERVAL_SECONDS = 5.0

# Hand-curated Danish lexicon of common room objects + people-words.
# Conservative: only items we'd actually expect to recur in Bjørn's
# workspace descriptions. Extends naturally over time as the listener
# gathers data — for v1 just the obvious anchors.
_ROOM_ENTITY_LEXICON: frozenset[str] = frozenset({
    # Furniture
    "sofa", "stol", "bord", "skrivebord", "seng", "sengen", "reol",
    "hylde", "skab", "tæppe", "lampe",
    # Apertures / structure
    "vindue", "vinduet", "dør", "døren", "døråbning", "væg", "loft", "gulv",
    # Items typically present
    "skærm", "skærmen", "computer", "tastatur", "mus", "telefon",
    "kop", "koppen", "flaske", "bog", "papir", "kabel",
    "kaffe", "te", "vand",
    # People
    "person", "personer", "hund", "kat",
    # Light / atmosphere markers
    "lys", "lyset", "dagslys", "skygge", "skygger", "mørke",
})

# Words that look like nouns but are actually function-words for rooms.
# We exclude them from entity capture.
_NON_ENTITY_TOKENS: frozenset[str] = frozenset({
    "rum", "rummet", "rummets", "stedet", "atmosfære", "atmosfæren",
    "stemning", "stemningen", "tilstand", "tilstanden", "følelse",
    "kontrast", "kontrasten", "verden", "verdens", "synet",
})

_WORD_RE = re.compile(r"[a-zæøåA-ZÆØÅ]{3,}")


# ── DB ───────────────────────────────────────────────────────────────────


def _ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS room_entity_observations (
            entity_label TEXT PRIMARY KEY,
            observation_count INTEGER NOT NULL DEFAULT 0,
            first_seen_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL,
            co_entities_json TEXT NOT NULL DEFAULT '{}',
            latest_excerpt TEXT
        )"""
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_room_entity_last "
        "ON room_entity_observations(last_seen_at)"
    )


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    _ensure_table(conn)
    return conn


# ── Extraction ───────────────────────────────────────────────────────────


def _lemmatize(token: str) -> str:
    """Lemmatize-then-check approach for Danish room nouns.

    Tries hand-curated mappings first, then strips common definite/plural
    suffixes (-en, -et, -erne, -er) to see if a root form exists in the
    lexicon. Returns the original if nothing reduces to a lexicon entry.
    """
    explicit = {
        "vinduet": "vindue", "døren": "dør", "rummet": "rum",
        "koppen": "kop", "skærmen": "skærm", "lyset": "lys",
        "sengen": "seng", "sofaen": "sofa", "stolen": "stol",
        "bordet": "bord", "skrivebordet": "skrivebord",
        "lampen": "lampe", "computeren": "computer",
        "personen": "person", "personer": "person",
        "hunden": "hund", "katten": "kat",
        "skyggen": "skygge", "skygger": "skygge",
        "tæppet": "tæppe", "skabet": "skab",
        "døråbningen": "døråbning", "væggen": "væg",
        "loftet": "loft", "gulvet": "gulv",
        "telefonen": "telefon", "tastaturet": "tastatur",
        "musen": "mus", "bogen": "bog", "kablet": "kabel",
        "flasken": "flaske", "dagslyset": "dagslys",
        "mørket": "mørke", "papiret": "papir",
        "reolen": "reol", "hylden": "hylde",
    }
    if token in explicit:
        return explicit[token]
    # Generic fallback: strip -en/-et/-erne and probe lexicon
    for suffix in ("erne", "ene", "en", "et"):
        if token.endswith(suffix) and len(token) > len(suffix) + 2:
            stem = token[: -len(suffix)]
            if stem in _ROOM_ENTITY_LEXICON:
                return stem
    return token


def extract_entities(text: str) -> set[str]:
    """Pull lexicon-matching entity labels from a sensory description.

    Lowercases tokens, drops function-words ("rum", "atmosfære"),
    lemmatizes definite forms ("sofaen" → "sofa"), then checks the
    lexicon. Returns canonical lemma forms.
    """
    if not text:
        return set()
    tokens = {t.lower() for t in _WORD_RE.findall(text)}
    found: set[str] = set()
    for tok in tokens:
        if tok in _NON_ENTITY_TOKENS:
            continue
        # Lemmatize first; THEN check lexicon
        lemma = _lemmatize(tok)
        if lemma in _ROOM_ENTITY_LEXICON or tok in _ROOM_ENTITY_LEXICON:
            found.add(lemma if lemma in _ROOM_ENTITY_LEXICON else tok)
    return found


# ── Recording ────────────────────────────────────────────────────────────


def record_observation(text: str, *, when: datetime | None = None) -> dict[str, Any]:
    """Process a single sensory description: extract entities, upsert
    each one with incremented count + co-entity tally.
    """
    entities = extract_entities(text)
    if not entities:
        return {"recorded": 0, "entities": []}
    now_iso = (when or datetime.now(UTC)).isoformat()
    excerpt = (text or "")[:160]
    try:
        with _connect() as conn:
            for ent in entities:
                row = conn.execute(
                    "SELECT observation_count, co_entities_json "
                    "FROM room_entity_observations WHERE entity_label = ?",
                    (ent,),
                ).fetchone()
                co_others = {e: 1 for e in entities if e != ent}
                if row:
                    existing_co = {}
                    try:
                        existing_co = json.loads(row["co_entities_json"] or "{}")
                    except (ValueError, TypeError):
                        pass
                    for other, n in co_others.items():
                        existing_co[other] = int(existing_co.get(other, 0)) + n
                    conn.execute(
                        """UPDATE room_entity_observations
                           SET observation_count = ?, last_seen_at = ?,
                               co_entities_json = ?, latest_excerpt = ?
                           WHERE entity_label = ?""",
                        (
                            int(row["observation_count"]) + 1, now_iso,
                            json.dumps(existing_co, ensure_ascii=False),
                            excerpt, ent,
                        ),
                    )
                else:
                    conn.execute(
                        """INSERT INTO room_entity_observations
                           (entity_label, observation_count, first_seen_at,
                            last_seen_at, co_entities_json, latest_excerpt)
                           VALUES (?, 1, ?, ?, ?, ?)""",
                        (ent, now_iso, now_iso,
                         json.dumps(co_others, ensure_ascii=False), excerpt),
                    )
            conn.commit()
    except Exception:
        logger.exception("spatial_entity_ledger: record failed")
        return {"recorded": 0, "entities": list(entities)}
    return {"recorded": len(entities), "entities": sorted(entities)}


# ── Queries ──────────────────────────────────────────────────────────────


def list_observed_entities(*, limit: int = 20) -> list[dict[str, Any]]:
    try:
        with _connect() as conn:
            rows = conn.execute(
                """SELECT entity_label, observation_count, last_seen_at, latest_excerpt
                   FROM room_entity_observations
                   ORDER BY observation_count DESC LIMIT ?""",
                (limit,),
            ).fetchall()
    except Exception:
        return []
    return [dict(r) for r in rows]


def co_entities_for(entity_label: str, *, limit: int = 8) -> list[tuple[str, int]]:
    """What other entities tend to co-occur with this one?"""
    try:
        with _connect() as conn:
            row = conn.execute(
                "SELECT co_entities_json FROM room_entity_observations "
                "WHERE entity_label = ?",
                (entity_label,),
            ).fetchone()
    except Exception:
        return []
    if not row:
        return []
    try:
        co = json.loads(row["co_entities_json"] or "{}")
    except (ValueError, TypeError):
        return []
    return sorted(co.items(), key=lambda kv: -int(kv[1]))[:limit]


def recently_observed(*, hours: int = 24, limit: int = 10) -> list[dict[str, Any]]:
    cutoff = (datetime.now(UTC) - timedelta(hours=hours)).isoformat()
    try:
        with _connect() as conn:
            rows = conn.execute(
                """SELECT entity_label, observation_count, last_seen_at
                   FROM room_entity_observations
                   WHERE last_seen_at >= ?
                   ORDER BY last_seen_at DESC LIMIT ?""",
                (cutoff, limit),
            ).fetchall()
    except Exception:
        return []
    return [dict(r) for r in rows]


# ── Awareness surface ────────────────────────────────────────────────────


def room_entities_section(*, top_n: int = 6) -> str | None:
    """One-liner of top-observed entities. Quiet when ledger is empty
    or has fewer than 3 entities (need some signal before surfacing)."""
    entities = list_observed_entities(limit=top_n)
    if len(entities) < 3:
        return None
    parts = [
        f"{e['entity_label']} (×{e['observation_count']})"
        for e in entities
    ]
    return "Rummets faste entiteter (set i Sansernes Arkiv): " + ", ".join(parts)


# ── DB-polling listener ──────────────────────────────────────────────────


_listener_thread: threading.Thread | None = None
_listener_running = False


def _listener_loop() -> None:
    """Poll events table for memory.sensory.recorded (visual only)."""
    import time as _time
    global _listener_running
    try:
        with _connect() as conn:
            row = conn.execute(
                "SELECT COALESCE(MAX(id), 0) FROM events"
            ).fetchone()
            last_id = int(row[0] or 0) if row else 0
    except Exception:
        last_id = 0

    while _listener_running:
        _time.sleep(_POLL_INTERVAL_SECONDS)
        try:
            with _connect() as conn:
                rows = conn.execute(
                    """SELECT id, payload_json
                       FROM events
                       WHERE id > ?
                         AND kind = 'memory.sensory.recorded'
                       ORDER BY id ASC
                       LIMIT 100""",
                    (last_id,),
                ).fetchall()
            for r in rows:
                last_id = max(last_id, int(r["id"]))
                try:
                    payload = json.loads(r["payload_json"] or "{}")
                except (ValueError, TypeError):
                    continue
                if not isinstance(payload, dict):
                    continue
                if payload.get("modality") != "visual":
                    continue
                # Fetch full content from sensory_memories
                mem_id = payload.get("id")
                if not mem_id:
                    continue
                try:
                    with _connect() as conn:
                        mrow = conn.execute(
                            "SELECT content, timestamp FROM sensory_memories "
                            "WHERE id = ?",
                            (mem_id,),
                        ).fetchone()
                except Exception:
                    continue
                if not mrow:
                    continue
                content = str(mrow["content"] or "")
                if len(content) < 20:
                    continue
                try:
                    when = datetime.fromisoformat(str(mrow["timestamp"]))
                except (ValueError, TypeError):
                    when = datetime.now(UTC)
                record_observation(content, when=when)
        except Exception:
            logger.exception("spatial_entity_ledger: poll cycle failed")


def start_spatial_entity_ledger() -> None:
    """Start DB-polling listener. Idempotent."""
    global _listener_thread, _listener_running
    if _listener_thread and _listener_thread.is_alive():
        return
    try:
        _listener_running = True
        _listener_thread = threading.Thread(
            target=_listener_loop, daemon=True,
            name="spatial-entity-ledger",
        )
        _listener_thread.start()
        logger.warning("spatial_entity_ledger: DB-polling listener started")
    except Exception:
        logger.exception("spatial_entity_ledger: failed to start")


def stop_spatial_entity_ledger() -> None:
    global _listener_running
    _listener_running = False


# ── Backfill ─────────────────────────────────────────────────────────────


def backfill_from_existing() -> dict[str, Any]:
    """Process all historical visual sensory_memories once. Useful first
    boot since 1500+ visual descriptions already exist before D.v1 exists.
    Idempotent: re-running just re-counts, but co_entities will grow
    monotonically — so call this exactly once after table creation.
    """
    processed = 0
    try:
        with _connect() as conn:
            rows = conn.execute(
                "SELECT content, timestamp FROM sensory_memories "
                "WHERE modality = 'visual' ORDER BY id ASC"
            ).fetchall()
        for r in rows:
            try:
                when = datetime.fromisoformat(str(r["timestamp"]))
            except (ValueError, TypeError):
                when = datetime.now(UTC)
            result = record_observation(str(r["content"] or ""), when=when)
            if result["recorded"]:
                processed += 1
    except Exception:
        logger.exception("spatial_entity_ledger: backfill failed")
    return {"processed_observations": processed}
