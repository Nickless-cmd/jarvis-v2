"""Core infrastructure for core.runtime.db modulet.

Indeholder:
- DB_PATH konstant
- ClosingConnection (context-manager wrapper)
- connect() — primær DB-forbindelse
- Konstant-ranks (_CONFIDENCE_RANKS, _EVIDENCE_CLASS_RANKS, _SOURCE_KIND_RANKS)
- Helper-funktioner (_rank_for, _stronger_ranked_value, _merge_text_fragments)
- Runtime-state KV (set/get_runtime_state_value)
- _now_iso() helper
- _SIGNAL_TABLES_WITH_STATUS — liste af signal-tabeller med status-felt
- _ensure-once cache infrastructure (_ENSURED_TABLES, _install_ensure_once_cache,
  _install_ensure_once_cache_for, _conn_db_id, invalidate_ensure_once_cache)

Andre db_*.py submoduler må KUN importere fra dette modul (forhindrer
cirkulære imports). Alle public symboler re-eksporteres fra
core.runtime.db facaden for bagudkompat.

Split-spec: docs/superpowers/specs/2026-05-15-db-split-design.md
"""
from __future__ import annotations

import json as _json
import logging as _logging
import sqlite3
import sys as _sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from core.runtime.config import STATE_DIR


# === Constants, ClosingConnection, connect, helpers, runtime-state KV (verbatim from db.py L11-103) ===
# Note: init_db() forbliver i db.py fordi den kalder ~117 _ensure_*_table-funcs
# der lever der. Flytning vil ske i senere fase når _ensure_* også flyttes.
DB_PATH = Path(STATE_DIR) / "jarvis.db"
_DB_CONNECT_LOGGED: bool = False
_core_logger = _logging.getLogger("uvicorn.error")
_CONFIDENCE_RANKS = {"low": 1, "medium": 2, "high": 3}
_EVIDENCE_CLASS_RANKS = {
    "weak_signal": 1,
    "runtime_support_only": 2,
    "single_session_pattern": 3,
    "explicit_user_statement": 4,
    "repeated_cross_session": 5,
}
_SOURCE_KIND_RANKS = {
    "runtime-derived-support": 1,
    "single-session-pattern": 2,
    "session-evidence": 3,
    "repeated-user-correction": 3,
    "user-explicit": 4,
}


class ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, factory=ClosingConnection)
    conn.row_factory = sqlite3.Row
    global _DB_CONNECT_LOGGED
    if not _DB_CONNECT_LOGGED:
        rows = conn.execute("PRAGMA database_list").fetchall()
        _core_logger.info("DB_CONNECT_FIRST: path=%s | db_list=%s", DB_PATH, rows)
        _DB_CONNECT_LOGGED = True
    return conn


def _rank_for(ranks: dict[str, int], value: str) -> int:
    return int(ranks.get(str(value or "").strip().lower(), 0))


def _stronger_ranked_value(current: str, proposed: str, ranks: dict[str, int]) -> str:
    if _rank_for(ranks, proposed) >= _rank_for(ranks, current):
        return str(proposed or "")
    return str(current or "")


def _merge_text_fragments(current: str, proposed: str, *, limit: int = 3) -> str:
    parts: list[str] = []
    seen: set[str] = set()
    for raw in (current, proposed):
        for piece in str(raw or "").split(" | "):
            normalized = " ".join(piece.split()).strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            parts.append(normalized)
            if len(parts) >= limit:
                return " | ".join(parts)
    return " | ".join(parts)


def set_runtime_state_value(key: str, value: object, *, updated_at: str = "") -> None:
    normalized_key = str(key or "").strip()
    if not normalized_key:
        raise ValueError("key must not be empty")
    timestamp = updated_at or datetime.now(UTC).isoformat()
    payload = _json.dumps(value, ensure_ascii=False)
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO runtime_state_kv (key, value_json, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value_json = excluded.value_json,
                updated_at = excluded.updated_at
            """,
            (normalized_key, payload, timestamp),
        )


def get_runtime_state_value(key: str, default: object = None) -> object:
    normalized_key = str(key or "").strip()
    if not normalized_key:
        return default
    with connect() as conn:
        row = conn.execute(
            "SELECT value_json FROM runtime_state_kv WHERE key = ?",
            (normalized_key,),
        ).fetchone()
    if row is None:
        return default
    try:
        return _json.loads(str(row["value_json"]))
    except Exception:
        return default




# === _now_iso helper (verbatim from db.py L29797-29799) ===
def _now_iso() -> str:
    from datetime import UTC, datetime
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


# === _SIGNAL_TABLES_WITH_STATUS (verbatim from db.py L33554-33590) ===
_SIGNAL_TABLES_WITH_STATUS: list[str] = [
    "runtime_attachment_topology_signals",
    "runtime_autonomy_pressure_signals",
    "runtime_awareness_signals",
    "runtime_chronicle_consolidation_signals",
    "runtime_consolidation_target_signals",
    "runtime_diary_synthesis_signals",
    "runtime_dream_hypothesis_signals",
    "runtime_executive_contradiction_signals",
    "runtime_goal_signals",
    "runtime_inner_visible_support_signals",
    "runtime_internal_opposition_signals",
    "runtime_loyalty_gradient_signals",
    "runtime_meaning_significance_signals",
    "runtime_metabolism_state_signals",
    "runtime_open_loop_signals",
    "runtime_private_initiative_tension_signals",
    "runtime_private_inner_interplay_signals",
    "runtime_private_inner_note_signals",
    "runtime_private_temporal_promotion_signals",
    "runtime_proactive_loop_lifecycle_signals",
    "runtime_reflection_signals",
    "runtime_regulation_homeostasis_signals",
    "runtime_relation_continuity_signals",
    "runtime_relation_state_signals",
    "runtime_release_marker_signals",
    "runtime_remembered_fact_signals",
    "runtime_self_model_signals",
    "runtime_self_narrative_continuity_signals",
    "runtime_self_review_cadence_signals",
    "runtime_self_review_signals",
    "runtime_temperament_tendency_signals",
    "runtime_temporal_recurrence_signals",
    "runtime_user_understanding_signals",
    "runtime_witness_signals",
    "runtime_world_model_signals",
]


# === Ensure-once cache infrastructure (modified from db.py L33998-34070) ===
_ENSURED_TABLES: set[tuple[str, str]] = set()


def _conn_db_id(conn: sqlite3.Connection) -> str:
    """Stable identifier for a sqlite connection's underlying database.

    For file-backed DBs this is the file path — same across all
    connect() calls in production. For :memory: DBs each connection
    has its own private database, so we use id(conn) as the discriminator
    to force per-connection re-ensure (which is what tests need).
    """
    try:
        rows = conn.execute("PRAGMA database_list").fetchall()
        for row in rows:
            # PRAGMA database_list yields (seq, name, file). Look for 'main'.
            name = row[1] if len(row) > 1 else ""
            path = row[2] if len(row) > 2 else ""
            if str(name) == "main":
                if path:
                    return str(path)
                # In-memory: per-connection identity so tests get fresh ensure
                return f"memory:{id(conn)}"
    except Exception:
        pass
    return f"unknown:{id(conn)}"


def _install_ensure_once_cache() -> None:
    """Bagudkompat-shim: wrapper _ensure_*_table funcs på core.runtime.db
    (facaden). Kaldes fra db.py i bunden EFTER alle re-eksporter, så
    også flyttede _ensure_*-funcs fra submoduler dækkes på facade-niveau.

    Implementation delegerer til _install_ensure_once_cache_for("core.runtime.db").
    """
    _install_ensure_once_cache_for("core.runtime.db")


def invalidate_ensure_once_cache(table_name: str | None = None) -> None:
    """Force re-run of `_ensure_*_table` on next call.

    Pass None to clear all (e.g. after switching DB files in tests).
    Pass a specific table name to re-ensure that one table (matches by
    function-name prefix across all DB paths).
    """
    if table_name is None:
        _ENSURED_TABLES.clear()
    else:
        # Remove all cache entries whose function name matches.
        to_remove = {key for key in _ENSURED_TABLES if key[0] == table_name}
        for key in to_remove:
            _ENSURED_TABLES.discard(key)




def _install_ensure_once_cache_for(module_name: str) -> None:
    """Wrap _ensure_*_table funcs i target-modul med once-cache.

    Tidligere version (_install_ensure_once_cache) scannede kun sit eget
    namespace (sys.modules[__name__]). Denne nye signatur tager target-
    modulnavn så hvert domæne-submodul kan kalde det på sig selv efter
    at have defineret sine _ensure_*_table-funktioner.

    Bagudkompat: _install_ensure_once_cache() shimmer dette ved at kalde
    _install_ensure_once_cache_for("core.runtime.db").
    """
    _mod = _sys.modules[module_name]
    _names = [
        _n for _n in vars(_mod).keys()
        if _n.startswith("_ensure_") and _n.endswith("_table") and callable(getattr(_mod, _n, None))
    ]
    for _name in _names:
        _orig = getattr(_mod, _name)
        if getattr(_orig, "_ensure_once_wrapped", False):
            continue

        def _make_wrapped(_fn, _fname):
            def _wrapped(*args, **kwargs):
                conn = args[0] if args else kwargs.get("conn")
                db_id = _conn_db_id(conn) if conn is not None else "no-conn"
                cache_key = (_fname, db_id)
                if cache_key in _ENSURED_TABLES:
                    return None
                _result = _fn(*args, **kwargs)
                _ENSURED_TABLES.add(cache_key)
                return _result
            _wrapped.__name__ = _fn.__name__
            _wrapped.__qualname__ = _fn.__qualname__
            _wrapped.__doc__ = _fn.__doc__
            _wrapped._ensure_once_wrapped = True  # type: ignore[attr-defined]
            _wrapped._ensure_once_orig = _fn  # type: ignore[attr-defined]
            return _wrapped
        setattr(_mod, _name, _make_wrapped(_orig, _name))
