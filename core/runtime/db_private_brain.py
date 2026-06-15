"""Private brain records — Jarvis' EGNE private lag (private-carry-erindringer med
salience-decay, domæner og lifecycle-status).

Udskilt fra db.py (Boy Scout-reglen, 2026-06-15) — én naturlig sammenhængende
enhed: tabel-DDL + insert/list/get/status/salience/decay + row→dict-helper.
Re-eksporteres fra db.py for bagudkompat (mange daemons bruger
`from core.runtime.db import insert_private_brain_record` osv.).

#154: per-bruger-scope — insert stamper scope_uid(); list/get/get_salient
filtrerer user_id (et medlem ser ikke Jarvis'/owners private lag). Decay +
status/salience-update er bevidst uscopet (intern housekeeping pr. record_id).
"""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from typing import Any

from core.runtime.db_core import connect


def _ensure_private_brain_records_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS private_brain_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_id TEXT NOT NULL UNIQUE,
            record_type TEXT NOT NULL DEFAULT 'private-carry',
            layer TEXT NOT NULL DEFAULT 'private_brain',
            session_id TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            focus TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            detail TEXT NOT NULL DEFAULT '',
            source_signals TEXT NOT NULL DEFAULT '',
            confidence TEXT NOT NULL DEFAULT 'medium',
            status TEXT NOT NULL DEFAULT 'active',
            salience REAL NOT NULL DEFAULT 1.0,
            domain TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            user_id TEXT
        )
        """
    )
    # Idempotente kolonne-tilføjelser for eksisterende tabeller.
    try:
        conn.execute("ALTER TABLE private_brain_records ADD COLUMN salience REAL NOT NULL DEFAULT 1.0")
        conn.commit()
    except Exception:
        pass
    try:
        conn.execute("ALTER TABLE private_brain_records ADD COLUMN domain TEXT NOT NULL DEFAULT ''")
        conn.commit()
    except Exception:
        pass
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_private_brain_records_status "
        "ON private_brain_records(status, id DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_private_brain_records_session "
        "ON private_brain_records(session_id, id DESC)"
    )


def _private_brain_record_from_row(row: sqlite3.Row) -> dict[str, Any]:
    d = dict(row)
    return {
        "record_id": d.get("record_id", ""),
        "record_type": d.get("record_type", ""),
        "layer": d.get("layer", ""),
        "session_id": d.get("session_id", ""),
        "run_id": d.get("run_id", ""),
        "focus": d.get("focus", ""),
        "summary": d.get("summary", ""),
        "detail": d.get("detail", ""),
        "source_signals": d.get("source_signals", ""),
        "confidence": d.get("confidence", ""),
        "status": d.get("status", "active"),
        "salience": float(d.get("salience") or 1.0),
        "domain": d.get("domain", ""),
        "created_at": d.get("created_at", ""),
        "updated_at": d.get("updated_at", ""),
    }


def insert_private_brain_record(
    *,
    record_id: str,
    record_type: str,
    layer: str,
    session_id: str,
    run_id: str,
    focus: str,
    summary: str,
    detail: str,
    source_signals: str,
    confidence: str,
    created_at: str,
    domain: str = "",
) -> dict[str, Any]:
    from core.services.user_scope import scope_uid
    with connect() as conn:
        _ensure_private_brain_records_table(conn)
        conn.execute(
            """
            INSERT OR IGNORE INTO private_brain_records
                (record_id, record_type, layer, session_id, run_id,
                 focus, summary, detail, source_signals, confidence,
                 status, domain, created_at, updated_at, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?, ?)
            """,
            (
                record_id, record_type, layer, session_id, run_id,
                focus, summary, detail, source_signals, confidence,
                domain, created_at, created_at, scope_uid() or None,
            ),
        )
        conn.commit()
    return get_private_brain_record(record_id) or {}


def list_private_brain_records(
    *,
    limit: int = 20,
    session_id: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    from core.services.user_scope import scope_uid
    with connect() as conn:
        _ensure_private_brain_records_table(conn)
        clauses = []
        params: list[object] = []
        _uid = scope_uid()
        if _uid:
            clauses.append("user_id = ?")  # #154: kun egne private-brain-rækker
            params.append(_uid)
        if session_id:
            clauses.append("session_id = ?")
            params.append(session_id)
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"SELECT * FROM private_brain_records {where} ORDER BY id DESC LIMIT ?",
            (*params, limit),
        ).fetchall()
    return [_private_brain_record_from_row(row) for row in rows]


def update_private_brain_record_status(
    record_id: str,
    *,
    status: str,
    updated_at: str,
) -> dict[str, Any] | None:
    """Lifecycle-overgang (active|settling|fading|released). Non-destruktiv."""
    with connect() as conn:
        _ensure_private_brain_records_table(conn)
        conn.execute(
            "UPDATE private_brain_records SET status = ?, updated_at = ? WHERE record_id = ?",
            (status, updated_at, record_id),
        )
        conn.commit()
    return get_private_brain_record(record_id)


def get_private_brain_record(record_id: str) -> dict[str, Any] | None:
    from core.services.user_scope import scope_uid
    _uid = scope_uid()
    with connect() as conn:
        _ensure_private_brain_records_table(conn)
        if _uid:
            row = conn.execute(
                "SELECT * FROM private_brain_records WHERE record_id = ? AND user_id = ?",
                (record_id, _uid),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM private_brain_records WHERE record_id = ?",
                (record_id,),
            ).fetchone()
    if row is None:
        return None
    return _private_brain_record_from_row(row)


def update_private_brain_record_salience(record_id: str, salience: float) -> None:
    """Sæt salience (0.0–1.0) for en private-brain-record."""
    salience = max(0.0, min(1.0, salience))
    with connect() as conn:
        _ensure_private_brain_records_table(conn)
        conn.execute(
            "UPDATE private_brain_records SET salience = ?, updated_at = ? WHERE record_id = ?",
            (salience, datetime.now(UTC).isoformat(), record_id),
        )
        conn.commit()


def get_salient_private_brain_records(
    threshold: float = 0.3, limit: int = 20
) -> list[dict[str, Any]]:
    """Aktive records med salience >= threshold, salience-sorteret."""
    from core.services.user_scope import scope_uid
    _uid = scope_uid()
    with connect() as conn:
        _ensure_private_brain_records_table(conn)
        if _uid:
            rows = conn.execute(
                "SELECT * FROM private_brain_records WHERE status = 'active' AND salience >= ? "
                "AND user_id = ? ORDER BY salience DESC LIMIT ?",
                (threshold, _uid, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM private_brain_records WHERE status = 'active' AND salience >= ? "
                "ORDER BY salience DESC LIMIT ?",
                (threshold, limit),
            ).fetchall()
    return [_private_brain_record_from_row(r) for r in rows]


def decay_private_brain_records(decay_rate: float = 0.05, limit: int = 100) -> int:
    """Reducér salience på gamle aktive records. Returnerer antal opdaterede."""
    with connect() as conn:
        _ensure_private_brain_records_table(conn)
        now_iso = datetime.now(UTC).isoformat()
        rows = conn.execute(
            "SELECT record_id, salience FROM private_brain_records WHERE status = 'active' AND salience > 0 LIMIT ?",
            (limit,),
        ).fetchall()
        updated = 0
        for row in rows:
            new_salience = max(0.0, float(row["salience"]) - decay_rate)
            conn.execute(
                "UPDATE private_brain_records SET salience = ?, updated_at = ? WHERE record_id = ?",
                (new_salience, now_iso, row["record_id"]),
            )
            updated += 1
        conn.commit()
    return updated


def decay_private_brain_records_by_domain(
    domain_decay_rates: dict[str, float],
    default_rate: float = 0.05,
    limit: int = 200,
) -> dict[str, int]:
    """Per-domæne salience-decay på aktive records. Returnerer {domæne: antal}."""
    with connect() as conn:
        _ensure_private_brain_records_table(conn)
        now_iso = datetime.now(UTC).isoformat()
        rows = conn.execute(
            "SELECT record_id, salience, domain FROM private_brain_records "
            "WHERE status = 'active' AND salience > 0 LIMIT ?",
            (limit,),
        ).fetchall()
        counts: dict[str, int] = {}
        for row in rows:
            dom = str(row["domain"] or "").strip()
            rate = domain_decay_rates.get(dom, default_rate)
            new_salience = max(0.0, float(row["salience"]) - rate)
            conn.execute(
                "UPDATE private_brain_records SET salience = ?, updated_at = ? WHERE record_id = ?",
                (new_salience, now_iso, row["record_id"]),
            )
            bucket = dom if dom else "default"
            counts[bucket] = counts.get(bucket, 0) + 1
        conn.commit()
    return counts
