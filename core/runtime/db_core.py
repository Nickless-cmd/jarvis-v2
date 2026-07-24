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
from datetime import UTC, datetime
from pathlib import Path

from core.runtime.config import STATE_DIR


# === Constants, ClosingConnection, connect, helpers, runtime-state KV (verbatim from db.py L11-103) ===
# Note: init_db() forbliver i db.py fordi den kalder ~117 _ensure_*_table-funcs
# der lever der. Flytning vil ske i senere fase når _ensure_* også flyttes.
DB_PATH = Path(STATE_DIR) / "jarvis.db"
_DB_CONNECT_LOGGED: bool = False
# WAL-init + mkdir er PERSISTENTE/idempotente → kun nødvendige ÉN gang pr. proces.
# Sat pr. connect var 78%-CPU-hotspot (py-spy 6. jul): `PRAGMA journal_mode=WAL` alene = 178/3415
# samples. WAL er persistent i DB-headeren, så re-sætning hver query er ren spild. Race på flaget
# er harmløs (værste tilfælde: WAL sættes få ekstra gange — idempotent).
_DB_WAL_INITIALIZED: bool = False
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


class PooledConnection(sqlite3.Connection):
    """Som ClosingConnection men LUKKER IKKE ved __exit__/close() — poolen ejer
    livscyklussen (thread-local genbrug). __exit__ committer/rollbacker som normalt."""
    def __exit__(self, exc_type, exc_value, traceback):
        # commit på succes / rollback på fejl (super), MEN behold forbindelsen åben.
        return super().__exit__(exc_type, exc_value, traceback)

    def close(self):  # no-op — brug _hard_close_pooled() for rigtig lukning
        pass


import os as _os_pool
import threading as _threading_pool
_conn_pool = _threading_pool.local()
# Kill-switch: JARVIS_DB_NOPOOL=1 → gammel adfærd (frisk forbindelse pr. connect()).
_POOL_DISABLED = bool(_os_pool.environ.get("JARVIS_DB_NOPOOL"))


def _make_connection(_factory) -> sqlite3.Connection:
    """Åbn ÉN ny sqlite-forbindelse + sæt PRAGMAs (busy_timeout, WAL-once, synchronous)."""
    global _DB_WAL_INITIALIZED, _DB_CONNECT_LOGGED
    if not _DB_WAL_INITIALIZED:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, factory=_factory)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA busy_timeout = 5000")   # rider korte låse af (§1. jul)
        if not _DB_WAL_INITIALIZED:
            conn.execute("PRAGMA journal_mode = WAL")  # læsere + 1 writer samtidigt (§4. jul)
            _DB_WAL_INITIALIZED = True
        conn.execute("PRAGMA synchronous = NORMAL")
    except Exception:
        pass
    if not _DB_CONNECT_LOGGED:
        try:
            rows = conn.execute("PRAGMA database_list").fetchall()
            _core_logger.info("DB_CONNECT_FIRST: path=%s | db_list=%s", DB_PATH, rows)
        except Exception:
            pass
        _DB_CONNECT_LOGGED = True
    return conn


def close_pooled_connection() -> None:
    """Luk DENNE tråds pooled forbindelse rigtigt (shutdown/tests). Self-safe."""
    conn = getattr(_conn_pool, "conn", None)
    if conn is not None:
        try:
            sqlite3.Connection.close(conn)
        except Exception:
            pass
        _conn_pool.conn = None


def connect() -> sqlite3.Connection:
    """DEL 1 — connection pooling (2026-07-12): genbrug ÉN thread-local forbindelse i
    stedet for at åbne en frisk (open + PRAGMA×2 + close) ved HVERT opslag. Profilering
    viste 1.091 sqlite-connects pr. prompt-assembly → direkte overhead + WAL-lås-kontention
    (samme familie som survival-branden). Nu: ~1 pr. tråd. busy_timeout/synchronous/WAL er
    persistente for forbindelsens levetid → sikkert at sætte én gang. `with connect() as c:`
    committer stadig (PooledConnection.__exit__), men lukker ikke. Kill-switch:
    JARVIS_DB_NOPOOL=1 → frisk forbindelse pr. kald (gammel adfærd)."""
    if _POOL_DISABLED:
        return _make_connection(ClosingConnection)
    conn = getattr(_conn_pool, "conn", None)
    if conn is not None and getattr(_conn_pool, "conn_path", None) != DB_PATH:
        # Korrekthed (2026-07-24): pool'en ignorerede DB_PATH-skift. Tests repointer
        # DB_PATH pr. test — en efterladt forbindelse til en TIDLIGERE DB blev genbrugt
        # → lækket state / "no such table" på tværs af tests. Produktion skifter aldrig
        # DB_PATH i drift, så dette er en billig same-Path-sammenligning der ALTID
        # matcher der (pool uændret); kun tests trigger reconnect'et.
        try:
            sqlite3.Connection.close(conn)
        except Exception:
            pass
        _conn_pool.conn = None
        conn = None
    if conn is not None:
        try:
            if conn.in_transaction:
                conn.rollback()          # defensivt: ryd evt. efterladt transaktion
            conn.execute("SELECT 1")     # liveness — billigt ift. fuld connect
            return conn
        except Exception:
            try:
                sqlite3.Connection.close(conn)
            except Exception:
                pass
            _conn_pool.conn = None
    conn = _make_connection(PooledConnection)
    _conn_pool.conn = conn
    _conn_pool.conn_path = DB_PATH
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


def _upsert_signal(
    *,
    conn: sqlite3.Connection,
    table: str,
    id_col: str,
    type_col: str,
    id_val: str,
    type_val: str,
    canonical_key: str,
    lookup_statuses: tuple[str, ...],
    overwrite_cols: list[tuple[str, object]],
    rank_cols: list[tuple[str, object, dict[str, int]]],
    merge_text_cols: list[tuple[str, object, int]],
    accumulate_cols: list[tuple[str, int]],
    created_at: str,
    updated_at: str,
) -> tuple[str, dict[str, object]]:
    """Generic merge-forward upsert for the runtime_*_signal families.

    Behaviour-identical extraction of the near-identical ``upsert_runtime_*``
    bodies. Only the COLUMN SET / table / key columns differ per family; the
    merge semantics are fixed:

    - ``overwrite_cols``  → set verbatim from the incoming payload (status,
      title, summary, rationale, run_id, session_id, ...). Compared verbatim
      in the same-payload short-circuit.
    - ``rank_cols``       → ``_stronger_ranked_value`` against the existing row
      (source_kind, confidence, evidence_class, ...).
    - ``merge_text_cols`` → ``_merge_text_fragments`` against the existing row
      (evidence_summary, support_summary, status_reason, ...).
    - ``accumulate_cols`` → ``max(existing, max(incoming, 1))`` (support_count,
      session_count, ...); on INSERT stored as ``max(incoming, 1)``.
    - ``merge_count``     → 0 on insert, ``COALESCE(merge_count,0)+1`` on update.
    - ``created_at``      → immutable on existing (only written on insert).
    - ``updated_at``      → written on both insert and update.

    Caller keeps its own ``with connect() as conn:`` block and calls its
    ``_ensure_*_table(conn)`` before invoking this, exactly as the hand-written
    bodies did. Returns ``(resolved_id, meta)`` where meta is the
    ``was_created``/``was_updated``/``merge_state`` dict; the caller performs
    the final ``get_*(resolved_id)`` read AFTER its own ``with`` block closes,
    exactly as the hand-written bodies did.
    """
    # SELECT columns for the existing-row lookup: id + the merge-relevant
    # payload columns + support/session accumulators + merge_count + timestamps.
    select_cols = (
        [id_col]
        + [c for c, _ in overwrite_cols]
        + [c for c, _, _ in rank_cols]
        + [c for c, _, _ in merge_text_cols]
        + [c for c, _ in accumulate_cols]
        + ["merge_count", "created_at", "updated_at"]
    )
    existing = None
    if canonical_key:
        placeholders = ", ".join("'" + s.replace("'", "''") + "'" for s in lookup_statuses)
        existing = conn.execute(
            f"""
            SELECT {", ".join(select_cols)}
            FROM {table}
            WHERE canonical_key = ?
              AND status IN ({placeholders})
            ORDER BY id DESC
            LIMIT 1
            """,
            (canonical_key,),
        ).fetchone()

    if existing is None:
        insert_cols = (
            [id_col, type_col, "canonical_key"]
            + [c for c, _ in overwrite_cols]
            + [c for c, _, _ in rank_cols]
            + [c for c, _, _ in merge_text_cols]
            + [c for c, _ in accumulate_cols]
            + ["merge_count", "created_at", "updated_at"]
        )
        insert_vals: list[object] = (
            [id_val, type_val, canonical_key]
            + [v for _, v in overwrite_cols]
            + [v for _, v, _ in rank_cols]
            + [v for _, v, _ in merge_text_cols]
            + [max(int(v or 0), 1) for _, v in accumulate_cols]
            + [0, created_at, updated_at]
        )
        conn.execute(
            f"""
            INSERT INTO {table} ({", ".join(insert_cols)})
            VALUES ({", ".join("?" for _ in insert_cols)})
            """,
            tuple(insert_vals),
        )
        conn.commit()
        resolved_id = id_val
        meta = {"was_created": True, "was_updated": True, "merge_state": "created"}
    else:
        resolved_id = str(existing[id_col])
        merged_rank = {
            col: _stronger_ranked_value(str(existing[col] or ""), val, ranks)
            for col, val, ranks in rank_cols
        }
        merged_text = {
            col: _merge_text_fragments(str(existing[col] or ""), val, limit=limit)
            for col, val, limit in merge_text_cols
        }
        merged_accum = {
            col: max(int(existing[col] or 0), max(int(val or 0), 1))
            for col, val in accumulate_cols
        }

        same_payload = (
            all(val == str(existing[col] or "") for col, val in overwrite_cols)
            and all(merged_rank[col] == str(existing[col] or "") for col, _, _ in rank_cols)
            and all(merged_text[col] == str(existing[col] or "") for col, _, _ in merge_text_cols)
            and all(merged_accum[col] == int(existing[col] or 0) for col, _ in accumulate_cols)
        )
        if same_payload:
            meta = {
                "was_created": False,
                "was_updated": False,
                "merge_state": "unchanged",
            }
        else:
            set_cols = (
                [c for c, _ in overwrite_cols]
                + [c for c, _, _ in rank_cols]
                + [c for c, _, _ in merge_text_cols]
                + [c for c, _ in accumulate_cols]
            )
            set_vals: list[object] = (
                [v for _, v in overwrite_cols]
                + [merged_rank[c] for c, _, _ in rank_cols]
                + [merged_text[c] for c, _, _ in merge_text_cols]
                + [merged_accum[c] for c, _ in accumulate_cols]
            )
            set_clause = ", ".join(f"{c} = ?" for c in set_cols)
            conn.execute(
                f"""
                UPDATE {table}
                SET
                    {set_clause},
                    merge_count = COALESCE(merge_count, 0) + 1,
                    updated_at = ?
                WHERE {id_col} = ?
                """,
                (*set_vals, updated_at, resolved_id),
            )
            conn.commit()
            meta = {
                "was_created": False,
                "was_updated": True,
                "merge_state": "merged",
            }

    return resolved_id, meta


# ── runtime_state read-cache (2026-07-12, connection-churn-fix, del 2) ──
# Profilering: ÉN prompt-assembly åbnede 1.091 sqlite-forbindelser — de fleste fra
# gentagne get_runtime_state_value/_kv_get-opslag af SAMME flag/vægt (composer læste
# vægte 85×). Kort TTL-cache kollapser dem: samme nøgle læses fra DB max hver _RS_TTL sek.
# Write-through på set → egen-proces ser ændringer straks; kryds-proces ≤ TTL lag (fint for
# flags/config/state). Del 1 (thread-local connection pooling) er den systemiske fortsættelse.
import time as _time_rs
import threading as _threading_rs
_RS_CACHE: dict[str, tuple[object, float]] = {}
_RS_TTL = 2.0
_RS_LOCK = _threading_rs.Lock()
_RS_MISS = object()


def _rs_cache_put(key: str, value: object) -> None:
    with _RS_LOCK:
        _RS_CACHE[key] = (value, _time_rs.monotonic() + _RS_TTL)


def clear_runtime_state_cache() -> None:
    """Ryd hele read-cachen (til tests / tvungen frisk læsning). Self-safe."""
    with _RS_LOCK:
        _RS_CACHE.clear()


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
    _rs_cache_put(normalized_key, value)  # write-through: egen-proces ser det straks


def get_runtime_state_value(key: str, default: object = None) -> object:
    normalized_key = str(key or "").strip()
    if not normalized_key:
        return default
    # Read-cache (se set_runtime_state_value): frisk hit → ingen sqlite-forbindelse.
    _now = _time_rs.monotonic()
    with _RS_LOCK:
        _hit = _RS_CACHE.get(normalized_key)
        if _hit is not None and _hit[1] > _now:
            return default if _hit[0] is _RS_MISS else _hit[0]
    with connect() as conn:
        row = conn.execute(
            "SELECT value_json FROM runtime_state_kv WHERE key = ?",
            (normalized_key,),
        ).fetchone()
    if row is None:
        _rs_cache_put(normalized_key, _RS_MISS)
        return default
    try:
        _val = _json.loads(str(row["value_json"]))
    except Exception:
        _rs_cache_put(normalized_key, _RS_MISS)
        return default
    _rs_cache_put(normalized_key, _val)
    return _val


# Strings that a human/CLI/migration might store for a boolean flag but that
# bool() would misread. bool("off") is True (non-empty str) — that trap left
# agent_tools_enabled reading ON while stored as the string "off" (2026-07-14).
_FALSEY_FLAG_STRINGS = frozenset({"", "0", "off", "false", "no", "none", "null", "disabled"})


def get_runtime_state_bool(key: str, default: bool = False) -> bool:
    """Read a runtime-state flag and coerce it to bool ROBUSTLY.

    Unlike ``bool(get_runtime_state_value(...))``, this treats string
    representations correctly: "off"/"false"/"no"/"0"/"" → False,
    "on"/"true"/"1"/"yes" → True (case-insensitive). Real bools and numbers
    pass through Python truthiness. Absent key or read error → ``default``.

    Use this for EVERY boolean flag read — never ``bool(value)`` directly, or a
    flag stored as the string "off" reads as True."""
    _sentinel = object()
    val = get_runtime_state_value(key, _sentinel)
    if val is _sentinel:
        return default
    if isinstance(val, str):
        return val.strip().lower() not in _FALSEY_FLAG_STRINGS
    return bool(val)


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
