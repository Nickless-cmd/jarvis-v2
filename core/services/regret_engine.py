"""Regret Engine — systematisk tracking af fortrydelser og læring.

Åbner en "regret" når en forventet udfald ikke matcher det faktiske,
eller når konfidensen falder markant efter en beslutning. Hver regret
bærer på en lesson — det der kan læres. Resolves når lektionen er
integreret eller niveauet er faldet under tærsklen.

Porteret fra jarvis-ai/agent/cognition/regret_engine.py (2026-04-21).

LLM-path: ingen — ren beslutnings-telemetri. Al logik er lokal.
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from core.eventbus.bus import event_bus
from core.runtime.db import connect

logger = logging.getLogger(__name__)

_REGRET_THRESHOLD = 0.25
_RECONCILE_CLOSE_BELOW = 0.15


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _clamp(value: object, default: float = 0.0, lo: float = 0.0, hi: float = 1.0) -> float:
    try:
        v = float(value)  # type: ignore[arg-type]
    except Exception:
        return default
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


def _ensure_table() -> None:
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cognitive_regrets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                decision_id TEXT NOT NULL DEFAULT '',
                context_json TEXT NOT NULL DEFAULT '{}',
                expected_outcome TEXT NOT NULL DEFAULT '',
                actual_outcome TEXT NOT NULL DEFAULT '',
                regret_level REAL NOT NULL DEFAULT 0.0,
                lesson TEXT NOT NULL DEFAULT '',
                confidence_before REAL NOT NULL DEFAULT 0.5,
                confidence_after REAL NOT NULL DEFAULT 0.5,
                linked_run_id TEXT NOT NULL DEFAULT '',
                linked_session_id TEXT NOT NULL DEFAULT '',
                linked_incident_id TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'open',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cognitive_regrets_status "
            "ON cognitive_regrets(status, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cognitive_regrets_decision "
            "ON cognitive_regrets(decision_id, status)"
        )
        conn.commit()


def compute_regret_level(
    *,
    expected_outcome: str,
    actual_outcome: str,
    confidence_before: object = 0.5,
    confidence_after: object = 0.5,
) -> float:
    """Compute regret level ∈ [0, 1] from outcome mismatch + confidence drop."""
    expected = str(expected_outcome or "").strip().lower()
    actual = str(actual_outcome or "").strip().lower()

    if expected and actual and expected == actual:
        mismatch = 0.0
    elif expected and actual and expected in actual:
        mismatch = 0.35
    else:
        mismatch = 0.55

    before = _clamp(confidence_before, default=0.5)
    after = _clamp(confidence_after, default=0.5)
    confidence_drop = max(0.0, before - after)

    level = mismatch + (confidence_drop * 0.8)

    if actual in {"failed", "error", "rejected", "incident", "degraded"}:
        level += 0.25

    return _clamp(level, default=0.0)


def _row_to_dict(row: Any) -> dict[str, object]:
    if row is None:
        return {}
    d = dict(row)
    try:
        d["context"] = json.loads(d.pop("context_json", "{}") or "{}")
    except Exception:
        d["context"] = {}
    return d


def open_or_update_regret(
    *,
    decision_id: str,
    context: dict[str, object] | None = None,
    expected_outcome: str,
    actual_outcome: str,
    lesson: str = "",
    confidence_before: object = 0.5,
    confidence_after: object = 0.5,
    linked_run_id: str = "",
    linked_session_id: str = "",
    linked_incident_id: str = "",
) -> dict[str, object]:
    """Open a new regret, or update an existing open one for this decision_id.

    Returns {"outcome": "opened"|"updated"|"skipped", ...}.
    """
    _ensure_table()
    level = compute_regret_level(
        expected_outcome=expected_outcome,
        actual_outcome=actual_outcome,
        confidence_before=confidence_before,
        confidence_after=confidence_after,
    )
    if level < _REGRET_THRESHOLD:
        return {
            "outcome": "skipped",
            "reason": "regret_threshold_not_met",
            "regret_level": level,
        }

    safe_decision = str(decision_id or "").strip()
    ctx_json = json.dumps(context or {}, ensure_ascii=False)
    now = _now_iso()

    with connect() as conn:
        existing = None
        if safe_decision:
            row = conn.execute(
                "SELECT * FROM cognitive_regrets "
                "WHERE decision_id = ? AND status = 'open' "
                "ORDER BY id DESC LIMIT 1",
                (safe_decision,),
            ).fetchone()
            existing = _row_to_dict(row) if row else None

        if existing is None:
            cursor = conn.execute(
                """
                INSERT INTO cognitive_regrets (
                    decision_id, context_json, expected_outcome, actual_outcome,
                    regret_level, lesson,
                    confidence_before, confidence_after,
                    linked_run_id, linked_session_id, linked_incident_id,
                    status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?, ?)
                """,
                (
                    safe_decision,
                    ctx_json,
                    str(expected_outcome or ""),
                    str(actual_outcome or ""),
                    float(level),
                    str(lesson or ""),
                    _clamp(confidence_before, default=0.5),
                    _clamp(confidence_after, default=0.5),
                    str(linked_run_id or ""),
                    str(linked_session_id or ""),
                    str(linked_incident_id or ""),
                    now,
                    now,
                ),
            )
            conn.commit()
            new_id = int(cursor.lastrowid)
            row = conn.execute(
                "SELECT * FROM cognitive_regrets WHERE id = ?", (new_id,)
            ).fetchone()
            regret = _row_to_dict(row)
            try:
                event_bus.publish("regret.opened", {
                    "regret_id": new_id,
                    "decision_id": safe_decision,
                    "regret_level": level,
                })
            except Exception:
                pass
            return {"outcome": "opened", "regret": regret}

        regret_id = int(existing.get("id") or 0)
        conn.execute(
            """
            UPDATE cognitive_regrets
               SET actual_outcome = ?,
                   lesson = ?,
                   regret_level = ?,
                   confidence_after = ?,
                   updated_at = ?
             WHERE id = ?
            """,
            (
                str(actual_outcome or ""),
                str(lesson or existing.get("lesson") or ""),
                float(level),
                _clamp(confidence_after, default=0.5),
                now,
                regret_id,
            ),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM cognitive_regrets WHERE id = ?", (regret_id,)
        ).fetchone()
        regret = _row_to_dict(row)
        try:
            event_bus.publish("regret.updated", {
                "regret_id": regret_id,
                "decision_id": safe_decision,
                "regret_level": level,
            })
        except Exception:
            pass
        return {"outcome": "updated", "regret": regret}


def resolve_regret(
    *,
    regret_id: int | str,
    actual_outcome: str = "",
    lesson: str = "",
    confidence_after: object | None = None,
) -> dict[str, object]:
    """Mark a regret as resolved. Optionally update final outcome + lesson."""
    _ensure_table()
    rid = int(str(regret_id).strip() or 0)
    if rid <= 0:
        return {"outcome": "skipped", "reason": "regret_not_found"}
    now = _now_iso()
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM cognitive_regrets WHERE id = ?", (rid,)
        ).fetchone()
        if row is None:
            return {"outcome": "skipped", "reason": "regret_not_found"}
        existing = _row_to_dict(row)
        new_actual = str(actual_outcome or existing.get("actual_outcome") or "")
        new_lesson = str(lesson or existing.get("lesson") or "")
        new_conf = _clamp(
            confidence_after if confidence_after is not None else existing.get("confidence_after"),
            default=0.5,
        )
        conn.execute(
            """
            UPDATE cognitive_regrets
               SET actual_outcome = ?, lesson = ?, confidence_after = ?,
                   status = 'resolved', updated_at = ?
             WHERE id = ?
            """,
            (new_actual, new_lesson, new_conf, now, rid),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM cognitive_regrets WHERE id = ?", (rid,)
        ).fetchone()
        regret = _row_to_dict(row)
    try:
        event_bus.publish("regret.resolved", {"regret_id": rid})
    except Exception:
        pass
    return {"outcome": "resolved", "regret": regret}


def list_regrets(
    *,
    status: str = "",
    limit: int = 100,
) -> list[dict[str, object]]:
    _ensure_table()
    status = str(status or "").strip().lower()
    lim = max(1, min(int(limit or 100), 500))
    with connect() as conn:
        if status in {"open", "resolved"}:
            rows = conn.execute(
                "SELECT * FROM cognitive_regrets WHERE status = ? "
                "ORDER BY id DESC LIMIT ?",
                (status, lim),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM cognitive_regrets ORDER BY id DESC LIMIT ?",
                (lim,),
            ).fetchall()
    return [_row_to_dict(r) for r in rows]


def summarize_regrets() -> dict[str, object]:
    _ensure_table()
    with connect() as conn:
        open_count = int(
            conn.execute(
                "SELECT COUNT(*) FROM cognitive_regrets WHERE status = 'open'"
            ).fetchone()[0]
            or 0
        )
        resolved_count = int(
            conn.execute(
                "SELECT COUNT(*) FROM cognitive_regrets WHERE status = 'resolved'"
            ).fetchone()[0]
            or 0
        )
        avg_level_row = conn.execute(
            "SELECT AVG(regret_level) FROM cognitive_regrets WHERE status = 'open'"
        ).fetchone()
        avg_open_level = float(avg_level_row[0] or 0.0) if avg_level_row else 0.0
        top_row = conn.execute(
            "SELECT * FROM cognitive_regrets WHERE status = 'open' "
            "ORDER BY regret_level DESC, id DESC LIMIT 1"
        ).fetchone()
        top = _row_to_dict(top_row) if top_row else None
    return {
        "open_count": open_count,
        "resolved_count": resolved_count,
        "total": open_count + resolved_count,
        "avg_open_level": round(avg_open_level, 3),
        "top_open": top,
    }


def reconcile_open_regrets(
    *,
    close_below: float = _RECONCILE_CLOSE_BELOW,
) -> list[dict[str, object]]:
    """Auto-resolve regrets whose level has decayed below the threshold.

    Called from maintenance / decay daemons. Returns list of resolved regrets.
    """
    _ensure_table()
    now = _now_iso()
    threshold = _clamp(close_below, default=_RECONCILE_CLOSE_BELOW)
    resolved: list[dict[str, object]] = []
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM cognitive_regrets WHERE status = 'open' "
            "AND regret_level <= ? ORDER BY id DESC LIMIT 300",
            (float(threshold),),
        ).fetchall()
        for row in rows:
            rid = int(row["id"])
            try:
                conn.execute(
                    "UPDATE cognitive_regrets SET status = 'resolved', updated_at = ? "
                    "WHERE id = ?",
                    (now, rid),
                )
                resolved.append(_row_to_dict(row))
            except Exception as exc:
                logger.debug("regret reconcile failed for id=%s: %s", rid, exc)
        conn.commit()
    for r in resolved:
        try:
            event_bus.publish("regret.resolved", {
                "regret_id": int(r.get("id") or 0),
                "reason": "auto_reconcile_below_threshold",
            })
        except Exception:
            pass
    return resolved


def build_regret_engine_surface() -> dict[str, object]:
    """MC surface — returns current regret state for Mission Control."""
    _ensure_table()
    summary = summarize_regrets()
    recent_open = list_regrets(status="open", limit=5)
    active = int(summary.get("open_count") or 0) > 0
    top = summary.get("top_open") or {}
    summary_line = (
        f"{summary.get('open_count', 0)} åbne / "
        f"{summary.get('resolved_count', 0)} løste"
    )
    if isinstance(top, dict) and top.get("expected_outcome"):
        summary_line += f" — top: {str(top.get('expected_outcome'))[:60]}"
    return {
        "active": active,
        "summary": summary_line,
        "stats": summary,
        "recent_open": recent_open,
    }
