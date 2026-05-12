"""Curiosity-budget tools — Phase 1 (AGI track #6 Åben udforskning).

9 read-only wrappers Jarvis kan bruge til at udforske sit eget mentale
landskab. Hver wrapper:
  1. Tjekker killswitch + budget
  2. Validerer at observation:str er sat (påkrævet)
  3. Kalder underliggende handler (eller implementerer action direkte)
  4. Persisterer observation
  5. Dekrementerer budget
  6. Returnerer {status, observation_id, remaining, result}

Mirror plan_revise_tool.py / world_model_tools.py pattern.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from core.services.curiosity_budget import (
    curiosity_enabled,
    decrement_budget,
    load_or_reset_budget,
    record_observation,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared wrapper: validation + observation persistence + budget decrement
# ---------------------------------------------------------------------------

def _curiosity_wrap(
    *,
    action: str,
    args: dict[str, Any],
    underlying_call: Callable[[dict[str, Any]], dict[str, Any]],
    underlying_args: dict[str, Any],
) -> dict[str, Any]:
    """Common path for all 9 curiosity-tool wrappers."""
    # Killswitch
    if not curiosity_enabled():
        return {"status": "error", "error": "curiosity disabled (killswitch)"}
    # Budget pre-check (cheap fail-fast before calling underlying tool)
    state = load_or_reset_budget()
    if state["remaining"] <= 0:
        return {"status": "error", "error": "curiosity budget brugt op for i dag"}
    # observation:str required
    observation = str(args.get("observation") or "").strip()
    if not observation:
        return {
            "status": "error",
            "error": "observation er påkrævet (kort prosa om hvorfor du kigger)",
        }
    follow_up_hint = str(args.get("follow_up_hint") or "").strip() or None

    # Underlying action
    try:
        underlying_result = underlying_call(underlying_args)
    except Exception as exc:
        logger.warning("curiosity %s underlying call failed: %s", action, exc)
        underlying_result = {"status": "error", "error": str(exc)}

    # Persist observation
    obs_id = record_observation(
        action=action,
        args_json=json.dumps(underlying_args, ensure_ascii=False, default=str),
        observation_text=observation,
        follow_up_hint=follow_up_hint,
    )

    # Decrement budget (emits cognitive_state.curiosity_action_taken)
    dec = decrement_budget(action=action, observation_id=obs_id)
    if dec["status"] != "ok":
        return {
            "status": "error",
            "error": dec.get("error", "budget exhausted"),
            "observation_id": obs_id,
        }

    return {
        "status": "ok",
        "observation_id": obs_id,
        "remaining": dec["remaining"],
        "result": underlying_result,
    }


# ---------------------------------------------------------------------------
# Direct introspection actions (no wrapped tool — implemented here)
# ---------------------------------------------------------------------------

def _direct_list_skills(_args: dict[str, Any]) -> dict[str, Any]:
    """List skill files in workspace/skills/. Read-only, lightweight."""
    skills_dir = Path.home() / ".jarvis-v2" / "workspaces" / "default" / "skills"
    if not skills_dir.exists():
        skills_dir = Path(__file__).resolve().parents[2] / "workspace" / "skills"
    if not skills_dir.exists():
        return {"skills": [], "note": "no skills directory found"}
    out: list[dict[str, Any]] = []
    for p in sorted(skills_dir.glob("*.md"))[:200]:
        try:
            head = p.read_text(encoding="utf-8")[:200]
        except Exception:
            head = ""
        out.append({"name": p.stem, "path": str(p), "head": head})
    return {"skills": out, "count": len(out)}


def _direct_list_tools(_args: dict[str, Any]) -> dict[str, Any]:
    """Return all currently-registered tool names + descriptions."""
    from core.tools.simple_tools import TOOL_DEFINITIONS
    out: list[dict[str, str]] = []
    for entry in TOOL_DEFINITIONS:
        if not isinstance(entry, dict):
            continue
        fn = entry.get("function") or {}
        name = str(fn.get("name") or "")
        desc = str(fn.get("description") or "")[:200]
        if name:
            out.append({"name": name, "description": desc})
    return {"tools": out, "count": len(out)}


def _direct_search_events(args: dict[str, Any]) -> dict[str, Any]:
    """SELECT from events table — read-only, parameterised, bounded."""
    from core.runtime.db import connect

    family = str(args.get("family") or "").strip()
    kind = str(args.get("kind") or "").strip()
    limit = int(args.get("limit") or 20)
    limit = max(1, min(limit, 100))

    where: list[str] = []
    params: list[Any] = []
    if family:
        where.append("family = ?")
        params.append(family)
    if kind:
        where.append("kind = ?")
        params.append(kind)

    sql = "SELECT event_id, family, kind, created_at FROM events"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    with connect() as conn:
        rows = conn.execute(sql, tuple(params)).fetchall()
    return {"rows": [dict(r) for r in rows], "count": len(rows)}


# ---------------------------------------------------------------------------
# 9 wrapper handlers
# ---------------------------------------------------------------------------

def _exec_curiosity_search_memory(args: dict[str, Any]) -> dict[str, Any]:
    from core.tools.simple_tools import _exec_search_memory
    return _curiosity_wrap(
        action="search_memory",
        args=args,
        underlying_call=_exec_search_memory,
        underlying_args={"query": str(args.get("query") or "")},
    )


def _exec_curiosity_read_chronicles(args: dict[str, Any]) -> dict[str, Any]:
    from core.tools.simple_tools import _exec_read_chronicles
    return _curiosity_wrap(
        action="read_chronicles",
        args=args,
        underlying_call=_exec_read_chronicles,
        underlying_args={"limit": int(args.get("limit") or 10)},
    )


def _exec_curiosity_read_dreams(args: dict[str, Any]) -> dict[str, Any]:
    from core.tools.simple_tools import _exec_read_dreams
    return _curiosity_wrap(
        action="read_dreams",
        args=args,
        underlying_call=_exec_read_dreams,
        underlying_args={"limit": int(args.get("limit") or 10)},
    )


def _exec_curiosity_read_model_config(args: dict[str, Any]) -> dict[str, Any]:
    from core.tools.simple_tools import _exec_read_model_config
    return _curiosity_wrap(
        action="read_model_config",
        args=args,
        underlying_call=_exec_read_model_config,
        underlying_args={},
    )


def _exec_curiosity_read_mood(args: dict[str, Any]) -> dict[str, Any]:
    from core.tools.simple_tools import _exec_read_mood
    return _curiosity_wrap(
        action="read_mood",
        args=args,
        underlying_call=_exec_read_mood,
        underlying_args={},
    )


def _exec_curiosity_list_skills(args: dict[str, Any]) -> dict[str, Any]:
    return _curiosity_wrap(
        action="list_skills",
        args=args,
        underlying_call=_direct_list_skills,
        underlying_args={},
    )


def _exec_curiosity_list_tools(args: dict[str, Any]) -> dict[str, Any]:
    return _curiosity_wrap(
        action="list_tools",
        args=args,
        underlying_call=_direct_list_tools,
        underlying_args={},
    )


def _exec_curiosity_search_events(args: dict[str, Any]) -> dict[str, Any]:
    return _curiosity_wrap(
        action="search_events",
        args=args,
        underlying_call=_direct_search_events,
        underlying_args={
            "family": str(args.get("family") or ""),
            "kind": str(args.get("kind") or ""),
            "limit": int(args.get("limit") or 20),
        },
    )


def _exec_curiosity_search_sessions(args: dict[str, Any]) -> dict[str, Any]:
    from core.tools.simple_tools import _exec_search_sessions
    return _curiosity_wrap(
        action="search_sessions",
        args=args,
        underlying_call=_exec_search_sessions,
        underlying_args={
            "query": str(args.get("query") or ""),
            "limit": int(args.get("limit") or 20),
        },
    )


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

_OBS_PARAM = {
    "observation": {
        "type": "string",
        "description": (
            "Påkrævet: kort prosa (1-2 sætninger) om hvorfor du kigger på "
            "dette. Husk: dette tæller på dit curiosity-budget (5/dag), så "
            "kig kun hvis noget trækker."
        ),
    },
    "follow_up_hint": {
        "type": "string",
        "description": (
            "Valgfri: breadcrumb til dig selv hvis du vil følge op senere. "
            "Vises IKKE i awareness — kun en privat note."
        ),
    },
}


def _make_def(name: str, description: str, extra_props: dict[str, Any], required: list[str]) -> dict[str, Any]:
    props = {**_OBS_PARAM, **extra_props}
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": props,
                "required": ["observation", *required],
            },
        },
    }


CURIOSITY_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    _make_def(
        "curiosity_search_memory",
        "Curiosity: søg i din egen semantiske hukommelse. Bruger 1/5 actions.",
        {"query": {"type": "string", "description": "Søge-string"}},
        ["query"],
    ),
    _make_def(
        "curiosity_read_chronicles",
        "Curiosity: læs dine egne chronicles (narrative selvhistorik). Bruger 1/5 actions.",
        {"limit": {"type": "integer", "description": "Antal entries (default 10)"}},
        [],
    ),
    _make_def(
        "curiosity_read_dreams",
        "Curiosity: læs dine idle-genererede drømme/refleksioner. Bruger 1/5 actions.",
        {"limit": {"type": "integer", "description": "Antal entries (default 10)"}},
        [],
    ),
    _make_def(
        "curiosity_read_model_config",
        "Curiosity: se din nuværende model-config (hvilke modeller, hvilken state). Bruger 1/5 actions.",
        {},
        [],
    ),
    _make_def(
        "curiosity_read_mood",
        "Curiosity: kig på dit eget affektive landskab. Bruger 1/5 actions.",
        {},
        [],
    ),
    _make_def(
        "curiosity_list_skills",
        "Curiosity: list dine egne skills — hvad kan du? Bruger 1/5 actions.",
        {},
        [],
    ),
    _make_def(
        "curiosity_list_tools",
        "Curiosity: list alle dine værktøjer — hvad har du, hvad har du måske aldrig prøvet? Bruger 1/5 actions.",
        {},
        [],
    ),
    _make_def(
        "curiosity_search_events",
        "Curiosity: søg i dine egne runtime-events (fx 'hvilke tool errors havde jeg sidste uge?'). Bruger 1/5 actions.",
        {
            "family": {"type": "string", "description": "Event family (fx 'tool', 'cognitive_state')"},
            "kind": {"type": "string", "description": "Event kind (fx 'error', 'plan_revised')"},
            "limit": {"type": "integer", "description": "Antal rækker (default 20, max 100)"},
        },
        [],
    ),
    _make_def(
        "curiosity_search_sessions",
        "Curiosity: søg i din længste hukommelse — chat-sessions på tværs af Discord/Telegram/web. Bruger 1/5 actions.",
        {
            "query": {"type": "string", "description": "Søge-string"},
            "limit": {"type": "integer", "description": "Antal sessions (default 20)"},
        },
        ["query"],
    ),
]


CURIOSITY_TOOL_HANDLERS: dict[str, Any] = {
    "curiosity_search_memory": _exec_curiosity_search_memory,
    "curiosity_read_chronicles": _exec_curiosity_read_chronicles,
    "curiosity_read_dreams": _exec_curiosity_read_dreams,
    "curiosity_read_model_config": _exec_curiosity_read_model_config,
    "curiosity_read_mood": _exec_curiosity_read_mood,
    "curiosity_list_skills": _exec_curiosity_list_skills,
    "curiosity_list_tools": _exec_curiosity_list_tools,
    "curiosity_search_events": _exec_curiosity_search_events,
    "curiosity_search_sessions": _exec_curiosity_search_sessions,
}
