"""FTS5 full-text search over session summaries and chat messages.

Memory repair 2026-09-04 (R5): "hvad sagde du i går om X" was a guess — no
full-text index existed over the 14.845 session summaries or the chat
history. SQLite on CT105 and locally is built with FTS5, so two external-
content FTS tables mirror the base tables through triggers. Base tables stay
the source of truth; the FTS tables can be rebuilt at any time with
``rebuild_fts()``.

Everything here is best-effort: if FTS5 is unavailable the ensure step logs
and the search functions return [].
"""
from __future__ import annotations

import logging
import os
import re
import sqlite3
from typing import Any

from core.runtime.db import connect

logger = logging.getLogger(__name__)

_FTS_SPECS: tuple[tuple[str, str, str, tuple[str, ...]], ...] = (
    # (fts table, base table, rowid column, indexed columns)
    ("session_summaries_fts", "session_summaries", "id", ("summary", "key_topics", "decisions_made")),
    ("chat_messages_fts", "chat_messages", "id", ("content",)),
)

_TOKEN_RE = re.compile(r"[0-9A-Za-zÆØÅæøå_\-.]{2,}")


def fts5_available(conn: sqlite3.Connection) -> bool:
    try:
        conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS _fts5_probe USING fts5(x)")
        conn.execute("DROP TABLE IF EXISTS _fts5_probe")
        return True
    except sqlite3.OperationalError:  # FTS5 is optional; absence is a supported capability state.
        return False


def _base_table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)
    ).fetchone()
    return row is not None


def ensure_fts_tables(conn: sqlite3.Connection) -> list[str]:
    """Create the FTS tables + sync triggers for every base table that exists.

    Returns the names of FTS tables that are ready. Safe to call repeatedly.
    A freshly created FTS table is populated with a one-off rebuild so
    existing rows become searchable immediately.
    """
    ready: list[str] = []
    # Read-only probes (scripts/memory_probe.py mod en live DB) må ikke oprette
    # tabeller/triggere: JARVIS_FTS_READONLY=1 → brug kun det der allerede findes.
    if os.environ.get("JARVIS_FTS_READONLY") == "1":
        return [fts for fts, _b, _r, _c in _FTS_SPECS if _base_table_exists(conn, fts)]
    if not fts5_available(conn):
        logger.warning("db_fts: FTS5 not available in this SQLite build")
        return ready
    for fts, base, rowid_col, cols in _FTS_SPECS:
        if not _base_table_exists(conn, base):
            continue
        existed = _base_table_exists(conn, fts)
        col_list = ", ".join(cols)
        conn.execute(
            f"CREATE VIRTUAL TABLE IF NOT EXISTS {fts} USING fts5("
            f"{col_list}, content='{base}', content_rowid='{rowid_col}', tokenize='unicode61')"
        )
        new_vals = ", ".join(f"new.{c}" for c in cols)
        old_vals = ", ".join(f"old.{c}" for c in cols)
        conn.execute(
            f"CREATE TRIGGER IF NOT EXISTS {base}_fts_ai AFTER INSERT ON {base} BEGIN "
            f"INSERT INTO {fts}(rowid, {col_list}) VALUES (new.{rowid_col}, {new_vals}); END"
        )
        conn.execute(
            f"CREATE TRIGGER IF NOT EXISTS {base}_fts_ad AFTER DELETE ON {base} BEGIN "
            f"INSERT INTO {fts}({fts}, rowid, {col_list}) VALUES ('delete', old.{rowid_col}, {old_vals}); END"
        )
        conn.execute(
            f"CREATE TRIGGER IF NOT EXISTS {base}_fts_au AFTER UPDATE ON {base} BEGIN "
            f"INSERT INTO {fts}({fts}, rowid, {col_list}) VALUES ('delete', old.{rowid_col}, {old_vals}); "
            f"INSERT INTO {fts}(rowid, {col_list}) VALUES (new.{rowid_col}, {new_vals}); END"
        )
        if not existed:
            conn.execute(f"INSERT INTO {fts}({fts}) VALUES ('rebuild')")
        ready.append(fts)
    conn.commit()
    return ready


def rebuild_fts() -> dict[str, int]:
    """Rebuild every FTS table from its base table. Returns row counts."""
    out: dict[str, int] = {}
    with connect() as conn:
        ready = ensure_fts_tables(conn)
        for fts in ready:
            conn.execute(f"INSERT INTO {fts}({fts}) VALUES ('rebuild')")
            row = conn.execute(f"SELECT count(*) FROM {fts}").fetchone()
            out[fts] = int(row[0] if row else 0)
        conn.commit()
    return out


def to_match_query(query: str, *, max_terms: int = 8) -> str:
    """Turn free text into a tolerant FTS5 MATCH expression.

    Tokens (≥ 2 chars) become quoted prefix terms joined with OR, so
    "pfsense nøgle" → '"pfsense"* OR "nøgle"*'. Returns "" when no usable token.
    """
    terms: list[str] = []
    seen: set[str] = set()
    for tok in _TOKEN_RE.findall(str(query or "")):
        t = tok.strip("-._").lower()
        if len(t) < 2 or t in seen:
            continue
        seen.add(t)
        terms.append(f'"{t}"*')
        if len(terms) >= max_terms:
            break
    return " OR ".join(terms)


def _bm25_to_score(rank: float) -> float:
    """FTS5 bm25() returns lower-is-better negative numbers; map to (0, 1]."""
    try:
        return 1.0 / (1.0 + abs(float(rank)))
    except (TypeError, ValueError):  # Invalid ranks are treated as the lowest score.
        return 0.0


def _equivalent_principals(_conn: sqlite3.Connection, canonical_uid: str) -> tuple[str, ...]:
    """Return stored principals that resolve to the current canonical user.

    Older chat rows may contain an external login subject while the request
    context already contains the canonical account id. Treating those two
    spellings as different users hides the owner's own history. Resolution is
    deliberately fail-closed: an unreadable link is not included.
    """
    try:
        from core.services.routine_migration import canonical_identity_aliases

        aliases = canonical_identity_aliases(canonical_uid)
        return aliases or (canonical_uid,)
    except Exception:
        logger.debug("db_fts: principal alias resolution failed", exc_info=True)
        return (canonical_uid,)


def search_session_summaries(query: str, *, limit: int = 8) -> list[dict[str, Any]]:
    """Keyword search over session_summaries FOR THIS USER.

    Målt 6/10-2026: denne FTS-søgning havde intet bruger-scope, og `recall`
    (recall.py:180, med `session_summary` i DEFAULT_SOURCES) eksponerede den
    direkte. BEVIST AKTIV: et recall efter «aftensmadopskrift med kylling
    tomater mælk pasta kartofler» returnerede Michelles private samtale fra
    29/9 som top-hit (score 1,00).

    Samme retning som `chat_crypto.should_encrypt`: ekskludér KUN sessioner der
    beviseligt tilhører en anden bruger — ustemplede/legacy og egne slipper
    igennem, så ingen mister adgang til sin egen historik. Uden uid
    (daemon/autonomt) er adfærden uændret.
    """
    match = to_match_query(query)
    if not match:
        return []
    try:
        from core.services.scoped_recall_policy import require_private_scope
        uid = require_private_scope()
    except Exception:  # Missing principal must hide all private summary rows.
        return []
    try:
        with connect() as conn:
            if "session_summaries_fts" not in ensure_fts_tables(conn):
                return []
            if _base_table_exists(conn, "recall_ownership_quarantine"):
                quarantine_hashes = {
                    str(row[0]) for row in conn.execute(
                        "SELECT source_id_hash FROM recall_ownership_quarantine "
                        "WHERE source_kind='chat_session'"
                    ).fetchall()
                }
            else:
                quarantine_hashes = set()
            if uid:
                principals = _equivalent_principals(conn, uid)
                marks = ",".join("?" for _ in principals)
                # Only sessions proven to belong solely to this principal.
                rows = conn.execute(
                    "SELECT s.id, s.session_id, s.run_id, s.summary, s.key_topics, "
                    "s.decisions_made, s.created_at, bm25(session_summaries_fts) AS rank "
                    "FROM session_summaries_fts f JOIN session_summaries s ON s.id = f.rowid "
                    "WHERE session_summaries_fts MATCH ? "
                    "AND EXISTS (SELECT 1 FROM chat_messages own "
                    f"  WHERE own.session_id=s.session_id AND own.user_id IN ({marks})) "
                    "AND NOT EXISTS (SELECT 1 FROM chat_messages foreign_row "
                    "  WHERE foreign_row.session_id=s.session_id "
                    "  AND foreign_row.user_id IS NOT NULL AND foreign_row.user_id<>'' "
                    f"  AND foreign_row.user_id NOT IN ({marks})) "
                    "ORDER BY rank LIMIT ?",
                    (match, *principals, *principals, int(limit)),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT s.id, s.session_id, s.run_id, s.summary, s.key_topics, "
                    "s.decisions_made, s.created_at, bm25(session_summaries_fts) AS rank "
                    "FROM session_summaries_fts f JOIN session_summaries s ON s.id = f.rowid "
                    "WHERE session_summaries_fts MATCH ? ORDER BY rank LIMIT ?",
                    (match, int(limit)),
                ).fetchall()
    except sqlite3.OperationalError as exc:
        logger.debug("db_fts: summaries search failed: %s", exc)
        return []
    import hashlib
    return [
        {
            "id": r[0], "session_id": r[1], "run_id": r[2], "summary": r[3],
            "key_topics": r[4], "decisions_made": r[5], "created_at": r[6],
            "score": _bm25_to_score(r[7]),
        }
        for r in rows
        if hashlib.sha256(str(r[1]).encode("utf-8")).hexdigest() not in quarantine_hashes
    ]


def search_chat_messages(
    query: str, *, limit: int = 8, session_id: str | None = None, role: str | None = None,
) -> list[dict[str, Any]]:
    """Keyword search over chat_messages FOR THIS USER. Each hit: id, message_id,
    session_id, role, content, created_at, score.

    Samme bruger-scope som `search_session_summaries` (målt 6/10-2026): `chat` er
    en opt-in recall-kilde (recall.py:194, `_source_chat`), så uden scope kunne et
    recall med `sources=['chat']` læse en anden brugers sessioner. Kilden er ikke i
    DEFAULT_SOURCES, men det er samme dør i samme væg — og et halvt fix på en
    lækage giver falsk tryghed.
    """
    match = to_match_query(query)
    if not match:
        return []
    try:
        from core.services.scoped_recall_policy import require_private_scope
        uid = require_private_scope()
    except Exception:  # Missing principal must hide all private chat rows.
        return []
    sql = (
        "SELECT m.id, m.message_id, m.session_id, m.role, m.content, m.created_at, "
        "bm25(chat_messages_fts) AS rank FROM chat_messages_fts f "
        "JOIN chat_messages m ON m.id = f.rowid WHERE chat_messages_fts MATCH ?"
    )
    params: list[Any] = [match]
    if session_id:
        sql += " AND m.session_id = ?"
        params.append(session_id)
    if role:
        sql += " AND m.role = ?"
        params.append(role)
    try:
        with connect() as conn:
            if "chat_messages_fts" not in ensure_fts_tables(conn):
                return []
            if uid:
                principals = _equivalent_principals(conn, uid)
                marks = ",".join("?" for _ in principals)
                sql += (
                    " AND EXISTS (SELECT 1 FROM chat_messages own "
                    f"  WHERE own.session_id=m.session_id AND own.user_id IN ({marks}))"
                    " AND NOT EXISTS (SELECT 1 FROM chat_messages foreign_row "
                    "  WHERE foreign_row.session_id=m.session_id "
                    "  AND foreign_row.user_id IS NOT NULL AND foreign_row.user_id<>'' "
                    f"  AND foreign_row.user_id NOT IN ({marks}))"
                )
                params.extend(principals)
                params.extend(principals)
            sql += " ORDER BY rank LIMIT ?"
            params.append(int(limit))
            if _base_table_exists(conn, "recall_ownership_quarantine"):
                # Quarantine stores only SHA-256 source hashes; SQLite has no
                # portable sha256(), so fetch the bounded FTS set then filter
                # conflicted session hashes below.
                quarantine_hashes = {
                    str(row[0]) for row in conn.execute(
                        "SELECT source_id_hash FROM recall_ownership_quarantine "
                        "WHERE source_kind='chat_session'"
                    ).fetchall()
                }
            else:
                quarantine_hashes = set()
            rows = conn.execute(sql, params).fetchall()
    except sqlite3.OperationalError as exc:
        logger.debug("db_fts: chat search failed: %s", exc)
        return []
    import hashlib
    return [
        {
            "id": r[0], "message_id": r[1], "session_id": r[2], "role": r[3],
            "content": r[4], "created_at": r[5], "score": _bm25_to_score(r[6]),
        }
        for r in rows
        if hashlib.sha256(str(r[2]).encode("utf-8")).hexdigest() not in quarantine_hashes
    ]
