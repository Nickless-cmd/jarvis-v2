"""Reflection → Plan — konvertér reflection/tanke til eksekverbar plan.

Dette er den STØRSTE "internt liv → handling"-bro fra forgængeren.
Tager en reflection (fra inner_voice, self_review, dream_hypothesis,
blind_spot, decision) og bruger LLM til at transformere den til en
struktureret plan med konkrete skridt.

Forgængerens agent/reflection_planner.py brugte plan_schema.validate_plan
+ tool_router + 520L infrastructure. v2 har ikke samme struktur — denne
port er en afgrænset v2-native implementation der:

1. Tager ren tekst som input
2. LLM-genererer plan: liste af {title, description, suggested_tool}
3. Persisterer som cognitive_reflective_plans
4. Kan merges til visible_work_units eller eksekveres direkte via
   simple_tools.execute_tool

Porteret i spirit fra jarvis-ai/agent/reflection_planner.py (2026-04-22).

LLM-path: daemon_llm_call (cheap lane). Plan-steps er suggestions,
ikke auto-eksekveret. Kræver explicit accept_reflective_plan() call.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import connect

logger = logging.getLogger(__name__)

_MAX_STEPS = 6


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _ensure_tables() -> None:
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cognitive_reflective_plans (
                id TEXT PRIMARY KEY,
                source_kind TEXT NOT NULL DEFAULT 'unknown',
                source_id TEXT NOT NULL DEFAULT '',
                reflection_text TEXT NOT NULL,
                plan_summary TEXT NOT NULL DEFAULT '',
                steps_json TEXT NOT NULL DEFAULT '[]',
                status TEXT NOT NULL DEFAULT 'proposed',
                confidence REAL NOT NULL DEFAULT 0.5,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cognitive_reflective_plans_status "
            "ON cognitive_reflective_plans(status, created_at DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cognitive_reflective_plans_source "
            "ON cognitive_reflective_plans(source_kind, source_id)"
        )
        conn.commit()


def _build_planning_prompt(
    reflection_text: str,
    source_kind: str,
    available_tools: list[str],
) -> str:
    tools_str = ", ".join(sorted(available_tools[:30])) if available_tools else "ingen"
    return (
        "Du er Jarvis der konverterer en refleksion til en konkret plan.\n\n"
        f"Refleksions-kilde: {source_kind}\n"
        f"Refleksion:\n{reflection_text[:800]}\n\n"
        f"Tilgængelige tools (valgfri): {tools_str[:400]}\n\n"
        "Skriv en plan med 1-6 konkrete skridt der adresserer refleksionen.\n"
        "Hver skridt skal være:\n"
        "- konkret (ikke 'tænk over det')\n"
        "- handlbart (kan udføres)\n"
        "- lille (én fil / ét commit / én verifikation)\n\n"
        "Hvis refleksionen ikke er handlbar (fx 'jeg er træt'), skriv tom liste.\n\n"
        "Svar KUN med JSON:\n"
        "{\n"
        '  "summary": "hvad planen dybest set handler om (én sætning)",\n'
        '  "steps": [\n'
        '    {"title": "kort titel", "description": "hvad skal gøres",\n'
        '     "suggested_tool": "tool_name eller null"},\n'
        "    ..\n"
        "  ],\n"
        '  "confidence": 0.0-1.0\n'
        "}"
    )


def _extract_plan_json(raw: str) -> dict[str, Any] | None:
    text = str(raw or "").strip()
    if not text:
        return None
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    end = -1
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                end = i
                break
    if end < 0:
        return None
    try:
        parsed = json.loads(text[start:end + 1])
    except Exception:
        return None
    return parsed if isinstance(parsed, dict) else None


def _available_tools() -> list[str]:
    """Get list of tool names from simple_tools registry."""
    try:
        from core.tools.simple_tools import _TOOL_HANDLERS
        return sorted(list(_TOOL_HANDLERS.keys()))
    except Exception:
        return []


def create_reflective_plan(
    *,
    reflection_text: str,
    source_kind: str = "unknown",
    source_id: str = "",
    min_length: int = 20,
) -> dict[str, Any]:
    """Generate a plan from a reflection using LLM.

    source_kind examples: inner_voice, self_review, dream_hypothesis,
    blind_spot, decision, regret, paradox.
    """
    _ensure_tables()
    text = str(reflection_text or "").strip()
    if len(text) < min_length:
        return {"outcome": "skipped", "reason": "reflection_too_short"}

    tools = _available_tools()
    prompt = _build_planning_prompt(text, source_kind, tools)

    try:
        from core.services.daemon_llm import daemon_llm_call
        raw = daemon_llm_call(
            prompt,
            max_len=600,
            fallback="",
            daemon_name="reflection_to_plan",
        )
    except Exception as exc:
        logger.debug("reflection→plan LLM call failed: %s", exc)
        return {"outcome": "skipped", "reason": "llm_error"}

    parsed = _extract_plan_json(raw)
    if not parsed:
        return {"outcome": "skipped", "reason": "llm_no_json"}

    raw_steps = parsed.get("steps") or []
    if not isinstance(raw_steps, list) or not raw_steps:
        return {"outcome": "skipped", "reason": "empty_plan"}

    steps: list[dict[str, Any]] = []
    for s in raw_steps[:_MAX_STEPS]:
        if not isinstance(s, dict):
            continue
        title = str(s.get("title") or "").strip()
        if not title:
            continue
        steps.append({
            "title": title[:120],
            "description": str(s.get("description") or "").strip()[:400],
            "suggested_tool": str(s.get("suggested_tool") or "").strip() or None,
        })
    if not steps:
        return {"outcome": "skipped", "reason": "no_valid_steps"}

    summary = str(parsed.get("summary") or "").strip()[:200]
    try:
        confidence = float(parsed.get("confidence") or 0.5)
    except Exception:
        confidence = 0.5
    confidence = max(0.0, min(1.0, confidence))

    plan_id = f"rplan_{uuid4().hex[:12]}"
    now = _now_iso()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO cognitive_reflective_plans
                (id, source_kind, source_id, reflection_text, plan_summary,
                 steps_json, status, confidence, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, 'proposed', ?, ?, ?)
            """,
            (
                plan_id, source_kind, source_id, text[:2000], summary,
                json.dumps(steps, ensure_ascii=False), float(confidence),
                now, now,
            ),
        )
        conn.commit()

    try:
        event_bus.publish("cognitive_reflective_plan.proposed", {
            "plan_id": plan_id, "source_kind": source_kind,
            "step_count": len(steps), "confidence": confidence,
        })
    except Exception:
        pass

    return {
        "outcome": "proposed",
        "plan_id": plan_id,
        "summary": summary,
        "steps": steps,
        "confidence": confidence,
        "source_kind": source_kind,
    }


def accept_reflective_plan(*, plan_id: str) -> dict[str, Any] | None:
    """Mark plan as accepted. Returns plan dict or None if not found."""
    _ensure_tables()
    now = _now_iso()
    with connect() as conn:
        cursor = conn.execute(
            "UPDATE cognitive_reflective_plans "
            "SET status = 'accepted', updated_at = ? WHERE id = ? AND status = 'proposed'",
            (now, str(plan_id)),
        )
        if cursor.rowcount <= 0:
            return None
        row = conn.execute(
            "SELECT * FROM cognitive_reflective_plans WHERE id = ?",
            (str(plan_id),),
        ).fetchone()
        conn.commit()
    if row:
        try:
            event_bus.publish("cognitive_reflective_plan.accepted", {
                "plan_id": plan_id,
            })
        except Exception:
            pass
        return _row_to_plan(row)
    return None


def complete_reflective_plan(*, plan_id: str, outcome_note: str = "") -> dict[str, Any] | None:
    _ensure_tables()
    now = _now_iso()
    with connect() as conn:
        cursor = conn.execute(
            "UPDATE cognitive_reflective_plans "
            "SET status = 'completed', updated_at = ? WHERE id = ?",
            (now, str(plan_id)),
        )
        if cursor.rowcount <= 0:
            return None
        row = conn.execute(
            "SELECT * FROM cognitive_reflective_plans WHERE id = ?",
            (str(plan_id),),
        ).fetchone()
        conn.commit()
    if row:
        try:
            event_bus.publish("cognitive_reflective_plan.completed", {
                "plan_id": plan_id, "outcome_note": outcome_note[:200],
            })
        except Exception:
            pass
        return _row_to_plan(row)
    return None


def reject_reflective_plan(*, plan_id: str, reason: str = "") -> dict[str, Any] | None:
    _ensure_tables()
    now = _now_iso()
    with connect() as conn:
        cursor = conn.execute(
            "UPDATE cognitive_reflective_plans "
            "SET status = 'rejected', updated_at = ? WHERE id = ?",
            (now, str(plan_id)),
        )
        if cursor.rowcount <= 0:
            return None
        row = conn.execute(
            "SELECT * FROM cognitive_reflective_plans WHERE id = ?",
            (str(plan_id),),
        ).fetchone()
        conn.commit()
    return _row_to_plan(row) if row else None


def _row_to_plan(row: Any) -> dict[str, Any]:
    d = dict(row)
    try:
        d["steps"] = json.loads(d.pop("steps_json", "[]") or "[]")
    except Exception:
        d["steps"] = []
    return d


def list_reflective_plans(*, status: str = "", limit: int = 30) -> list[dict[str, Any]]:
    _ensure_tables()
    lim = max(1, min(int(limit or 30), 200))
    s = str(status or "").strip().lower()
    with connect() as conn:
        if s in ("proposed", "accepted", "completed", "rejected"):
            rows = conn.execute(
                "SELECT * FROM cognitive_reflective_plans WHERE status = ? "
                "ORDER BY created_at DESC LIMIT ?",
                (s, lim),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM cognitive_reflective_plans "
                "ORDER BY created_at DESC LIMIT ?",
                (lim,),
            ).fetchall()
    return [_row_to_plan(r) for r in rows]


def build_reflection_to_plan_surface() -> dict[str, Any]:
    _ensure_tables()
    proposed = list_reflective_plans(status="proposed", limit=10)
    accepted = list_reflective_plans(status="accepted", limit=5)
    completed = list_reflective_plans(status="completed", limit=5)
    active = bool(proposed or accepted)
    summary = (
        f"{len(proposed)} proposed, {len(accepted)} accepted, "
        f"{len(completed)} completed"
    )
    return {
        "active": active,
        "summary": summary,
        "proposed": proposed,
        "accepted": accepted,
        "recent_completed": completed,
    }


# --- Auto-planning hooks -----------------------------------------------------

def plan_from_inner_voice_thought(*, thought: str, voice_id: str = "") -> dict[str, Any]:
    """Convenience: convert inner_voice thought to plan if substantive enough."""
    return create_reflective_plan(
        reflection_text=thought,
        source_kind="inner_voice",
        source_id=voice_id,
        min_length=40,
    )


def plan_from_blind_spot(*, description: str, blind_spot_id: int = 0) -> dict[str, Any]:
    return create_reflective_plan(
        reflection_text=f"Blind spot discovered: {description}",
        source_kind="blind_spot",
        source_id=str(blind_spot_id),
        min_length=20,
    )


def plan_from_self_review(*, lessons: list[str], review_id: int = 0) -> dict[str, Any]:
    if not lessons:
        return {"outcome": "skipped", "reason": "no_lessons"}
    text = "Lessons from self-review:\n" + "\n".join(f"- {l}" for l in lessons[:5])
    return create_reflective_plan(
        reflection_text=text,
        source_kind="self_review",
        source_id=str(review_id),
        min_length=30,
    )
