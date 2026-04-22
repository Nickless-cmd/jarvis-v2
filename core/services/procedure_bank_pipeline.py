"""Procedure Bank Pipeline — lærte rutiner der kan pin'es og matches.

v2's procedure_bank.py er 50L stub. Dette modul giver fuld CRUD +
trigger-matching + pin/unpin + execution-suggestion.

En procedure er en navngiven sekvens af skridt der matches på et
trigger-string. Når trigger matches i samtale eller inner_voice,
kan Jarvis foreslå at køre proceduren.

Eksempel:
- name: "daily mail check"
- trigger: "check mails" or "nye beskeder"
- procedure: "1. mail_check, 2. notify ntfy, 3. update log"
- pinned: True → altid tilgængelig

Porteret fra jarvis-ai/agent/cognition/procedure_bank.py (2026-04-22).

v2-tilpasning: dedikeret tabel cognitive_procedures (ikke rør memory_items
eller procedures der er v1-specifikke). Simplere schema, ingen workspace_id.
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import connect

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _ensure_table() -> None:
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cognitive_procedures (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                trigger TEXT NOT NULL DEFAULT '',
                procedure TEXT NOT NULL DEFAULT '',
                pinned INTEGER NOT NULL DEFAULT 0,
                hit_count INTEGER NOT NULL DEFAULT 0,
                last_triggered_at TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                deleted INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cognitive_procedures_pinned "
            "ON cognitive_procedures(pinned DESC, updated_at DESC)"
        )
        conn.commit()


def upsert_procedure(
    *,
    name: str,
    trigger: str = "",
    procedure: str,
    pinned: bool = False,
) -> dict[str, Any] | None:
    _ensure_table()
    name_c = str(name or "").strip()
    proc_c = str(procedure or "").strip()
    trig_c = str(trigger or "").strip()
    if not name_c or not proc_c:
        return None
    now = _now_iso()
    with connect() as conn:
        row = conn.execute(
            "SELECT id FROM cognitive_procedures WHERE name = ? AND deleted = 0",
            (name_c,),
        ).fetchone()
        if row:
            pid = str(row["id"])
            conn.execute(
                """
                UPDATE cognitive_procedures
                   SET trigger = ?, procedure = ?, pinned = ?, updated_at = ?
                 WHERE id = ?
                """,
                (trig_c, proc_c, 1 if pinned else 0, now, pid),
            )
        else:
            pid = f"proc_{uuid4().hex[:12]}"
            conn.execute(
                """
                INSERT INTO cognitive_procedures
                    (id, name, trigger, procedure, pinned, hit_count,
                     last_triggered_at, created_at, updated_at, deleted)
                VALUES (?, ?, ?, ?, ?, 0, '', ?, ?, 0)
                """,
                (pid, name_c, trig_c, proc_c, 1 if pinned else 0, now, now),
            )
        conn.commit()

    result = get_procedure(procedure_id=pid)
    try:
        event_bus.publish("cognitive_procedure.upserted", {
            "procedure_id": pid, "name": name_c, "pinned": pinned,
        })
    except Exception:
        pass
    return result


def get_procedure(*, procedure_id: str = "", procedure_name: str = "") -> dict[str, Any] | None:
    _ensure_table()
    pid = str(procedure_id or "").strip()
    name = str(procedure_name or "").strip()
    if not pid and not name:
        return None
    with connect() as conn:
        if pid:
            row = conn.execute(
                "SELECT * FROM cognitive_procedures WHERE id = ? AND deleted = 0",
                (pid,),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM cognitive_procedures WHERE name = ? AND deleted = 0",
                (name,),
            ).fetchone()
    return dict(row) if row else None


def list_procedures(*, query: str = "", pinned_only: bool = False, limit: int = 100) -> list[dict[str, Any]]:
    _ensure_table()
    lim = max(1, min(int(limit or 100), 500))
    q_clean = str(query or "").strip()
    with connect() as conn:
        sql = "SELECT * FROM cognitive_procedures WHERE deleted = 0"
        args: list[Any] = []
        if pinned_only:
            sql += " AND pinned = 1"
        if q_clean:
            like = f"%{q_clean}%"
            sql += " AND (name LIKE ? OR trigger LIKE ? OR procedure LIKE ?)"
            args.extend([like, like, like])
        sql += " ORDER BY pinned DESC, updated_at DESC, name ASC LIMIT ?"
        args.append(lim)
        rows = conn.execute(sql, args).fetchall()
    return [dict(r) for r in rows]


def set_procedure_pinned(*, procedure_id: str = "", procedure_name: str = "", pinned: bool) -> dict[str, Any] | None:
    _ensure_table()
    now = _now_iso()
    pid = str(procedure_id or "").strip()
    name = str(procedure_name or "").strip()
    if not pid and not name:
        return None
    with connect() as conn:
        if pid:
            cursor = conn.execute(
                "UPDATE cognitive_procedures SET pinned = ?, updated_at = ? WHERE id = ?",
                (1 if pinned else 0, now, pid),
            )
        else:
            cursor = conn.execute(
                "UPDATE cognitive_procedures SET pinned = ?, updated_at = ? WHERE name = ?",
                (1 if pinned else 0, now, name),
            )
        conn.commit()
        if cursor.rowcount <= 0:
            return None
    return get_procedure(procedure_id=pid, procedure_name=name)


def delete_procedure(*, procedure_id: str = "", procedure_name: str = "") -> bool:
    _ensure_table()
    now = _now_iso()
    pid = str(procedure_id or "").strip()
    name = str(procedure_name or "").strip()
    if not pid and not name:
        return False
    with connect() as conn:
        if pid:
            cursor = conn.execute(
                "UPDATE cognitive_procedures SET deleted = 1, updated_at = ? WHERE id = ?",
                (now, pid),
            )
        else:
            cursor = conn.execute(
                "UPDATE cognitive_procedures SET deleted = 1, updated_at = ? WHERE name = ?",
                (now, name),
            )
        conn.commit()
    return cursor.rowcount > 0


def match_procedures_for_text(text: str, *, limit: int = 3) -> list[dict[str, Any]]:
    """Find procedures whose trigger-string matches given text.

    Used e.g. by inner_voice/visible_model to suggest running a pinned
    procedure when a chat message matches its trigger.
    """
    _ensure_table()
    safe = str(text or "").strip().lower()
    if not safe:
        return []
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM cognitive_procedures WHERE deleted = 0 "
            "AND trigger != '' ORDER BY pinned DESC, hit_count DESC LIMIT 200"
        ).fetchall()
    matched: list[dict[str, Any]] = []
    for r in rows:
        trig = str(r["trigger"] or "").strip().lower()
        if not trig:
            continue
        # Accept if ANY trigger token (separated by comma or "or") is in text
        tokens = [t.strip() for t in trig.replace("|", ",").replace(" or ", ",").split(",") if t.strip()]
        if any(tok in safe for tok in tokens):
            matched.append(dict(r))
            if len(matched) >= int(limit):
                break

    # Update hit_count + last_triggered_at for matches
    if matched:
        now = _now_iso()
        with connect() as conn:
            for m in matched:
                conn.execute(
                    "UPDATE cognitive_procedures SET hit_count = hit_count + 1, "
                    "last_triggered_at = ? WHERE id = ?",
                    (now, str(m.get("id"))),
                )
            conn.commit()
    return matched


def build_procedure_bank_surface() -> dict[str, Any]:
    _ensure_table()
    all_procs = list_procedures(limit=50)
    pinned = [p for p in all_procs if p.get("pinned")]
    active = bool(all_procs)
    summary = (
        f"{len(all_procs)} procedures ({len(pinned)} pinned)"
        if all_procs else "No procedures yet"
    )
    return {
        "active": active,
        "summary": summary,
        "pinned": pinned[:10],
        "recent": [p for p in all_procs if not p.get("pinned")][:10],
        "total_count": len(all_procs),
    }
