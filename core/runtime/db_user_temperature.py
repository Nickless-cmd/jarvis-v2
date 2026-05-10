"""DB helpers for user_temperature_active (Lag 10 user temperature field).

Single-row-per-workspace UPSERT. Read API bypasses kill-switch — the
engine's get_active_field() wraps this with the enabled-check.
"""
from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from core.runtime.db import connect


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def upsert_active_field(
    *,
    workspace_id: str,
    struct: dict[str, Any],
    struct_signals: dict[str, float],
    llm: dict[str, Any] | None,
    combined: dict[str, Any],
    baseline: dict[str, Any],
) -> dict[str, Any]:
    """INSERT or UPDATE the single active field row for a workspace."""
    now = _now()
    field_id = f"tf_{workspace_id}_{uuid.uuid4().hex[:12]}"

    llm_valens = llm["valens"] if llm else None
    llm_arousal = llm["arousal"] if llm else None
    llm_texture = llm["texture"] if llm else None
    llm_confidence = llm["confidence"] if llm else None
    llm_rationale = (llm["rationale"] if llm else "") or ""
    last_llm_at = now if llm else None

    with connect() as conn:
        # Try update first
        cur = conn.execute(
            "UPDATE user_temperature_active SET "
            "  field_valens = ?, field_arousal = ?, field_texture = ?, "
            "  field_intensity = ?, field_conflict = ?, "
            "  struct_valens = ?, struct_arousal = ?, struct_texture = ?, "
            "  struct_confidence = ?, struct_signals_json = ?, last_structural_at = ?, "
            "  llm_valens = COALESCE(?, llm_valens), "
            "  llm_arousal = COALESCE(?, llm_arousal), "
            "  llm_texture = COALESCE(?, llm_texture), "
            "  llm_confidence = COALESCE(?, llm_confidence), "
            "  llm_rationale = CASE WHEN ? != '' THEN ? ELSE llm_rationale END, "
            "  last_llm_at = COALESCE(?, last_llm_at), "
            "  baseline_message_count = ?, baseline_built_at = ?, "
            "  baseline_stats_json = ?, updated_at = ? "
            "WHERE workspace_id = ?",
            (
                float(combined["field_valens"]), float(combined["field_arousal"]),
                str(combined["field_texture"]), float(combined["field_intensity"]),
                int(bool(combined["field_conflict"])),
                float(struct["valens"]), float(struct["arousal"]),
                str(struct["texture"]), float(struct["confidence"]),
                json.dumps(struct_signals), now,
                llm_valens, llm_arousal, llm_texture, llm_confidence,
                llm_rationale, llm_rationale, last_llm_at,
                int(baseline.get("message_count", 0)),
                str(baseline.get("built_at") or ""),
                json.dumps({k: v for k, v in baseline.items() if k != "ready"}),
                now, workspace_id,
            ),
        )
        if cur.rowcount == 0:
            # Insert new row
            conn.execute(
                "INSERT INTO user_temperature_active "
                "(field_id, workspace_id, "
                "field_valens, field_arousal, field_texture, "
                "field_intensity, field_conflict, "
                "struct_valens, struct_arousal, struct_texture, "
                "struct_confidence, struct_signals_json, last_structural_at, "
                "llm_valens, llm_arousal, llm_texture, llm_confidence, "
                "llm_rationale, last_llm_at, llm_trigger_pending, "
                "baseline_message_count, baseline_built_at, baseline_stats_json, "
                "created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, "
                "        ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?)",
                (
                    field_id, workspace_id,
                    float(combined["field_valens"]), float(combined["field_arousal"]),
                    str(combined["field_texture"]), float(combined["field_intensity"]),
                    int(bool(combined["field_conflict"])),
                    float(struct["valens"]), float(struct["arousal"]),
                    str(struct["texture"]), float(struct["confidence"]),
                    json.dumps(struct_signals), now,
                    llm_valens, llm_arousal, llm_texture, llm_confidence,
                    llm_rationale, last_llm_at,
                    int(baseline.get("message_count", 0)),
                    str(baseline.get("built_at") or ""),
                    json.dumps({k: v for k, v in baseline.items() if k != "ready"}),
                    now, now,
                ),
            )
    return {"workspace_id": workspace_id, "updated_at": now}


def get_active_field_raw(*, workspace_id: str) -> dict[str, Any] | None:
    """Read the active field row, parsed JSON columns expanded.

    Does NOT honor the user_temperature_enabled kill-switch — engine wraps.
    """
    with connect() as conn:
        row = conn.execute(
            "SELECT field_id, workspace_id, "
            "  field_valens, field_arousal, field_texture, "
            "  field_intensity, field_conflict, "
            "  struct_valens, struct_arousal, struct_texture, "
            "  struct_confidence, struct_signals_json, last_structural_at, "
            "  llm_valens, llm_arousal, llm_texture, llm_confidence, "
            "  llm_rationale, last_llm_at, llm_trigger_pending, "
            "  baseline_message_count, baseline_built_at, baseline_stats_json, "
            "  created_at, updated_at "
            "FROM user_temperature_active WHERE workspace_id = ?",
            (workspace_id,),
        ).fetchone()
    if row is None:
        return None
    return {
        "field_id": row[0],
        "workspace_id": row[1],
        "field_valens": float(row[2] or 0.0),
        "field_arousal": float(row[3] or 0.0),
        "field_texture": str(row[4] or "cool"),
        "field_intensity": float(row[5] or 0.0),
        "field_conflict": bool(row[6]),
        "struct_valens": float(row[7] or 0.0),
        "struct_arousal": float(row[8] or 0.0),
        "struct_texture": str(row[9] or "cool"),
        "struct_confidence": float(row[10] or 0.0),
        "struct_signals": json.loads(row[11] or "{}"),
        "last_structural_at": str(row[12] or ""),
        "llm_valens": (float(row[13]) if row[13] is not None else None),
        "llm_arousal": (float(row[14]) if row[14] is not None else None),
        "llm_texture": (str(row[15]) if row[15] is not None else None),
        "llm_confidence": (float(row[16]) if row[16] is not None else None),
        "llm_rationale": str(row[17] or ""),
        "last_llm_at": (str(row[18]) if row[18] else None),
        "llm_trigger_pending": bool(row[19]),
        "baseline_message_count": int(row[20] or 0),
        "baseline_built_at": str(row[21] or ""),
        "baseline_stats": json.loads(row[22] or "{}"),
        "created_at": str(row[23] or ""),
        "updated_at": str(row[24] or ""),
    }


def set_llm_trigger_pending(*, workspace_id: str) -> bool:
    """Mark LLM stream as needing a refresh on next daemon cycle."""
    now = _now()
    with connect() as conn:
        cur = conn.execute(
            "UPDATE user_temperature_active SET "
            "  llm_trigger_pending = 1, updated_at = ? "
            "WHERE workspace_id = ?",
            (now, workspace_id),
        )
        return cur.rowcount > 0


def consume_llm_trigger_pending(*, workspace_id: str) -> bool:
    """Read+clear the trigger flag atomically. Returns True if was pending."""
    now = _now()
    with connect() as conn:
        row = conn.execute(
            "SELECT llm_trigger_pending FROM user_temperature_active "
            "WHERE workspace_id = ?",
            (workspace_id,),
        ).fetchone()
        if not row or not row[0]:
            return False
        conn.execute(
            "UPDATE user_temperature_active SET "
            "  llm_trigger_pending = 0, updated_at = ? "
            "WHERE workspace_id = ?",
            (now, workspace_id),
        )
        return True
