"""Missions Pipeline — flerfase opgaver med state-machine.

Missions er langvarige multi-step opgaver der spænder over sessions:
- researcher-fase: undersøg scope, context, constraints
- implementer-fase: udfør ændringerne
- reviewer-fase: verificér + dokumentér

State-machine:
    created → planning → running → completed
                 ↓          ↓
              failed     failed

Hver mission kan have messages (mission_messages) for at passe context
mellem faser og sessions.

v2-tilpasning: simpler end forgænger (ikke real subagent-spawn — roles er
tags). Ingen budget/economic-guardrails (skal kobles til eksisterende
cost_governance hvis behov). SQLite i stedet for workspace JSON.

Porteret i spirit fra jarvis-ai/agent/orchestration/missions.py (505L → 380L).
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

_VALID_STATUSES = {"created", "planning", "running", "completed", "failed"}
_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "created": {"planning", "failed"},
    "planning": {"running", "failed"},
    "running": {"completed", "failed"},
    "completed": set(),
    "failed": set(),
}

_VALID_ROLES = {"researcher", "implementer", "reviewer", "coordinator", "observer"}


class MissionError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _ensure_tables() -> None:
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cognitive_missions (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'created',
                goal TEXT NOT NULL DEFAULT '',
                constraints TEXT NOT NULL DEFAULT '',
                success_criteria TEXT NOT NULL DEFAULT '',
                roles_json TEXT NOT NULL DEFAULT '[]',
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                started_at TEXT NOT NULL DEFAULT '',
                completed_at TEXT NOT NULL DEFAULT ''
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cognitive_missions_status "
            "ON cognitive_missions(status, updated_at DESC)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cognitive_mission_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mission_id TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'coordinator',
                content TEXT NOT NULL,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                FOREIGN KEY (mission_id) REFERENCES cognitive_missions(id)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cognitive_mission_messages_mission "
            "ON cognitive_mission_messages(mission_id, id)"
        )
        conn.commit()


def _row_to_mission(row: Any) -> dict[str, Any]:
    d = dict(row)
    try:
        d["roles"] = json.loads(d.pop("roles_json", "[]") or "[]")
    except Exception:
        d["roles"] = []
    try:
        d["metadata"] = json.loads(d.pop("metadata_json", "{}") or "{}")
    except Exception:
        d["metadata"] = {}
    return d


def create_mission(
    *,
    title: str,
    description: str = "",
    goal: str = "",
    constraints: str = "",
    success_criteria: str = "",
    roles: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a new mission in 'created' status."""
    _ensure_tables()
    title_c = str(title or "").strip()
    if not title_c:
        raise MissionError("invalid_title", "Mission title is required")

    # Validate roles
    role_list = [str(r).strip().lower() for r in (roles or []) if str(r).strip()]
    for r in role_list:
        if r not in _VALID_ROLES:
            raise MissionError(
                "invalid_role",
                f"Role '{r}' not in {sorted(_VALID_ROLES)}",
            )

    mid = f"mission_{uuid4().hex[:12]}"
    now = _now_iso()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO cognitive_missions
                (id, title, description, status, goal, constraints, success_criteria,
                 roles_json, metadata_json, created_at, updated_at)
            VALUES (?, ?, ?, 'created', ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                mid, title_c, str(description or "").strip(),
                str(goal or "").strip(),
                str(constraints or "").strip(),
                str(success_criteria or "").strip(),
                json.dumps(role_list, ensure_ascii=False),
                json.dumps(metadata or {}, ensure_ascii=False),
                now, now,
            ),
        )
        conn.commit()

    try:
        event_bus.publish("cognitive_mission.created", {
            "mission_id": mid, "title": title_c,
        })
    except Exception:
        pass
    return get_mission(mission_id=mid) or {}


def get_mission(*, mission_id: str) -> dict[str, Any] | None:
    _ensure_tables()
    mid = str(mission_id or "").strip()
    if not mid:
        return None
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM cognitive_missions WHERE id = ?", (mid,),
        ).fetchone()
    return _row_to_mission(row) if row else None


def transition_mission_state(
    *,
    mission_id: str,
    new_status: str,
    reason: str = "",
) -> dict[str, Any]:
    """Transition mission to new status, respecting _ALLOWED_TRANSITIONS."""
    _ensure_tables()
    mission = get_mission(mission_id=mission_id)
    if mission is None:
        raise MissionError("not_found", f"Mission {mission_id} not found")

    current = str(mission.get("status") or "").strip().lower()
    target = str(new_status or "").strip().lower()
    if target not in _VALID_STATUSES:
        raise MissionError("invalid_status", f"Invalid status '{target}'")

    allowed = _ALLOWED_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise MissionError(
            "invalid_transition",
            f"Cannot transition from '{current}' to '{target}' "
            f"(allowed: {sorted(allowed)})",
        )

    now = _now_iso()
    started_at = mission.get("started_at") or ""
    completed_at = mission.get("completed_at") or ""
    if target == "running" and not started_at:
        started_at = now
    if target in ("completed", "failed") and not completed_at:
        completed_at = now

    with connect() as conn:
        conn.execute(
            """
            UPDATE cognitive_missions
               SET status = ?, updated_at = ?, started_at = ?, completed_at = ?
             WHERE id = ?
            """,
            (target, now, started_at, completed_at, mission_id),
        )
        # Record transition as a mission message
        conn.execute(
            """
            INSERT INTO cognitive_mission_messages
                (mission_id, role, content, metadata_json, created_at)
            VALUES (?, 'coordinator', ?, ?, ?)
            """,
            (
                mission_id,
                f"status_transition: {current} → {target}"
                + (f" ({reason})" if reason else ""),
                json.dumps({"from": current, "to": target, "reason": reason},
                           ensure_ascii=False),
                now,
            ),
        )
        conn.commit()

    try:
        event_bus.publish("cognitive_mission.status_transition", {
            "mission_id": mission_id, "from": current, "to": target,
            "reason": reason[:200],
        })
    except Exception:
        pass
    return get_mission(mission_id=mission_id) or {}


def send_mission_message(
    *,
    mission_id: str,
    role: str = "coordinator",
    content: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Post a message on the mission channel. Roles: researcher/implementer/reviewer etc."""
    _ensure_tables()
    mission = get_mission(mission_id=mission_id)
    if mission is None:
        raise MissionError("not_found", f"Mission {mission_id} not found")

    role_c = str(role or "coordinator").strip().lower()
    if role_c not in _VALID_ROLES:
        raise MissionError("invalid_role", f"Role '{role_c}' not valid")

    content_c = str(content or "").strip()
    if not content_c:
        raise MissionError("empty_content", "Message content required")

    now = _now_iso()
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO cognitive_mission_messages
                (mission_id, role, content, metadata_json, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                mission_id, role_c, content_c,
                json.dumps(metadata or {}, ensure_ascii=False),
                now,
            ),
        )
        msg_id = int(cursor.lastrowid)
        # Touch mission updated_at
        conn.execute(
            "UPDATE cognitive_missions SET updated_at = ? WHERE id = ?",
            (now, mission_id),
        )
        conn.commit()

    try:
        event_bus.publish("cognitive_mission.message_posted", {
            "mission_id": mission_id, "role": role_c, "message_id": msg_id,
        })
    except Exception:
        pass
    return {"id": msg_id, "mission_id": mission_id, "role": role_c,
            "content": content_c, "created_at": now}


def list_mission_messages(*, mission_id: str, limit: int = 50) -> list[dict[str, Any]]:
    _ensure_tables()
    lim = max(1, min(int(limit or 50), 500))
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM cognitive_mission_messages "
            "WHERE mission_id = ? ORDER BY id ASC LIMIT ?",
            (str(mission_id), lim),
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        try:
            d["metadata"] = json.loads(d.pop("metadata_json", "{}") or "{}")
        except Exception:
            d["metadata"] = {}
        out.append(d)
    return out


def list_missions(*, status: str = "", limit: int = 30) -> list[dict[str, Any]]:
    _ensure_tables()
    lim = max(1, min(int(limit or 30), 200))
    s = str(status or "").strip().lower()
    with connect() as conn:
        if s in _VALID_STATUSES:
            rows = conn.execute(
                "SELECT * FROM cognitive_missions WHERE status = ? "
                "ORDER BY updated_at DESC LIMIT ?",
                (s, lim),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM cognitive_missions ORDER BY updated_at DESC LIMIT ?",
                (lim,),
            ).fetchall()
    return [_row_to_mission(r) for r in rows]


def build_missions_surface() -> dict[str, Any]:
    _ensure_tables()
    active_statuses = ["planning", "running"]
    active = []
    for s in active_statuses:
        active.extend(list_missions(status=s, limit=10))
    recent_completed = list_missions(status="completed", limit=5)
    recent_failed = list_missions(status="failed", limit=3)
    has_active = bool(active)
    summary = (
        f"{len(active)} active ({sum(1 for m in active if m.get('status') == 'running')} running), "
        f"{len(recent_completed)} completed"
    )
    return {
        "active": has_active,
        "summary": summary,
        "active_missions": active,
        "recent_completed": recent_completed,
        "recent_failed": recent_failed,
    }
