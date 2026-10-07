"""spawn_agent_task som modelvendt vaerktoej.

Udskilt fra core/tools/simple_tools_native.py (Boy Scout, 2026-10-07) foer
agent-contract-v1 B aendrede logikken. Re-eksporteret derfra, saa
`simple_tools` og testene finder den uaendret.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _herkomst(args: dict[str, Any]) -> dict[str, str]:
    """Hvem og hvilken tur der foedte barnet. Runtime injicerer felterne i hvert
    kald; tomme udelades, saa en manglende vaerdi aldrig bliver en opfundet ejer
    (agent-contract-v1 binder kun naar baade ejer og session er kendt)."""
    return {k: v for k, v in (
        ("parent_session_id", str(args.get("_runtime_session_id") or "").strip()),
        ("parent_run_id", str(args.get("_runtime_turn_id") or "").strip()),
        ("user_id", str(args.get("_runtime_user_id") or "").strip()),
    ) if v}


def _exec_spawn_agent_task(args: dict[str, Any]) -> dict[str, Any]:
    role = str(args.get("role") or "researcher").strip() or "researcher"
    goal = str(args.get("goal") or "").strip()
    if not goal:
        return {"status": "error", "error": "goal is required"}
    # 0 = ubegraenset, med max_turns (20) som det egentlige net. Vaerktoejs-laget
    # klemte tidligere til default 2000 / loft 8000 — praecis den strangulering
    # juli-fixet fjernede i motoren: agenten braendte budgettet paa tool-kald og
    # naaede aldrig frem til et svar, saa runnet stod «completed men tomt».
    # Rettelsen var lavet ét lag nede og overlevede ikke herop.
    budget = max(int(args.get("budget_tokens") or 0), 0)
    persistent = bool(args.get("persistent") or False)
    ttl_seconds = int(args.get("ttl_seconds") or 600)
    # Axis 2 (menu-lock lifted): Jarvis may write the agent's own prompt,
    # override its tool policy, and hand it a tool allowlist. All optional —
    # when omitted, spawn_agent_task falls back to the role start-template
    # (fully backward compatible).
    system_prompt = str(args.get("system_prompt") or "").strip()
    tool_policy = str(args.get("tool_policy") or "").strip()
    raw_allowed = args.get("allowed_tools")
    allowed_tools = None
    if isinstance(raw_allowed, list):
        allowed_tools = [str(t).strip() for t in raw_allowed if str(t).strip()]
    try:
        from core.services.agent_runtime import spawn_agent_task
        result = spawn_agent_task(
            role=role,
            goal=goal,
            system_prompt=system_prompt,
            tool_policy=tool_policy,
            allowed_tools=allowed_tools,
            budget_tokens=budget,
            persistent=persistent,
            ttl_seconds=ttl_seconds if persistent else 0,
            auto_execute=True,
            context=_herkomst(args),
        )
        messages = result.get("messages") or []
        last_reply = ""
        for msg in reversed(messages):
            if str(msg.get("direction") or "") == "agent->jarvis":
                last_reply = str(msg.get("content") or "")
                break
        return {
            "status": "ok",
            "agent_id": str(result.get("agent_id") or ""),
            "role": role,
            "agent_status": str(result.get("status") or ""),
            # 1200 tegn var en tredjedel af hvad en god agent leverer (maalt:
            # 3.751 tegn). Man bad om en undersoegelse og fik en trediedel af
            # svaret — det faar dispatch til at foeles vaerdiloest.
            "reply": last_reply[:12000] if last_reply else None,
        }
    except Exception as exc:
        logger.warning("spawn_agent_task fejlede: %s", exc, exc_info=True)
        return {"status": "error", "error": str(exc)}
