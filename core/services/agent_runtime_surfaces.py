"""Agent runtime — read surfaces (agent + council/swarm projections).

Split out of ``agent_runtime`` (behavior-preserving). Pure read/build
surfaces over the agent registry, runs, messages, schedules, tool-calls,
and council sessions/members. No mutations.

Re-exported via ``core.services.agent_runtime`` for backward compatibility.
"""

from __future__ import annotations

from core.services.agent_runtime_base import (
    AGENT_ROLE_TEMPLATES,
    COUNCIL_ROLE_ORDER,
    _json_loads,
    _now_iso,
    cheap_lane_status_surface,
    get_agent_registry_entry,
    get_council_session,
    list_agent_messages,
    list_agent_registry_entries,
    list_agent_runs,
    list_agent_schedules,
    list_agent_tool_calls,
    list_council_members,
    list_council_sessions,
)


def build_agent_runtime_surface(limit: int = 100) -> dict[str, object]:
    registry = list_agent_registry_entries(limit=limit)
    cheap_lane = cheap_lane_status_surface()
    active = [item for item in registry if item["status"] in {"queued", "starting", "active", "waiting", "blocked", "scheduled"}]
    completed = [item for item in registry if item["status"] == "completed"]
    failed = [item for item in registry if item["status"] == "failed"]
    expired = [item for item in registry if item["status"] == "expired"]
    persistent = [item for item in registry if item["persistent"]]
    return {
        "fetched_at": _now_iso(),
        "cheap_lane": cheap_lane,
        "templates": [
            {
                "role": role,
                "title": template["title"],
                "default_tool_policy": template["default_tool_policy"],
            }
            for role, template in AGENT_ROLE_TEMPLATES.items()
        ],
        "agents": [enrich_agent_surface(item) for item in registry],
        "summary": {
            "agent_count": len(registry),
            "active_count": len(active),
            "completed_count": len(completed),
            "failed_count": len(failed),
            "expired_count": len(expired),
            "persistent_count": len(persistent),
            "token_burn_total": sum(int(item.get("tokens_burned") or 0) for item in registry),
        },
    }


def enrich_agent_surface(agent: dict[str, object]) -> dict[str, object]:
    agent_id = str(agent.get("agent_id") or "")
    runs = list_agent_runs(agent_id=agent_id, limit=20)
    messages = list_agent_messages(agent_id=agent_id, limit=40)
    tool_calls = list_agent_tool_calls(agent_id=agent_id, limit=20)
    schedules = list_agent_schedules(agent_id=agent_id, limit=20)
    latest_run = runs[0] if runs else None
    return {
        **agent,
        "allowed_tools": _json_loads(str(agent.get("allowed_tools_json") or "[]"), []),
        "schedule": _json_loads(str(agent.get("schedule_json") or "{}"), {}),
        "context": _json_loads(str(agent.get("context_json") or "{}"), {}),
        "result_contract": _json_loads(str(agent.get("result_contract_json") or "{}"), {}),
        "runs": runs,
        "messages": messages,
        "tool_calls": tool_calls,
        "schedules": schedules,
        "latest_schedule": schedules[0] if schedules else None,
        "latest_run": latest_run,
        "message_count": len(messages),
        "tool_call_count": len(tool_calls),
        "latest_message": messages[-1] if messages else None,
        "latest_tool_call": tool_calls[0] if tool_calls else None,
        "progress_label": _progress_label(agent=agent, latest_run=latest_run),
    }


def build_agent_detail_surface(agent_id: str) -> dict[str, object] | None:
    agent = get_agent_registry_entry(agent_id)
    if agent is None:
        return None
    return enrich_agent_surface(agent)


def build_council_surface(limit: int = 40) -> dict[str, object]:
    sessions = list_council_sessions(limit=limit)
    return {
        "fetched_at": _now_iso(),
        "roster": [
            {
                "role": role,
                "title": AGENT_ROLE_TEMPLATES[role]["title"],
                "default_tool_policy": AGENT_ROLE_TEMPLATES[role]["default_tool_policy"],
                "status": "available",
            }
            for role in COUNCIL_ROLE_ORDER
        ],
        "sessions": [enrich_council_surface(item) for item in sessions],
        "summary": {
            "session_count": len(sessions),
            "active_count": sum(1 for item in sessions if item.get("status") in {"forming", "deliberating", "merging", "reporting"}),
            "closed_count": sum(1 for item in sessions if item.get("status") == "closed"),
            "council_count": sum(1 for item in sessions if item.get("mode") == "council"),
            "swarm_count": sum(1 for item in sessions if item.get("mode") == "swarm"),
        },
    }


def enrich_council_surface(session: dict[str, object]) -> dict[str, object]:
    council_id = str(session.get("council_id") or "")
    messages = list_agent_messages(council_id=council_id, limit=120)
    members = list_council_members(council_id=council_id)
    return {
        **session,
        "members": members,
        "messages": messages,
        "message_count": len(messages),
        "latest_message": messages[-1] if messages else None,
    }


def build_council_detail_surface(council_id: str) -> dict[str, object] | None:
    session = get_council_session(council_id)
    if session is None:
        return None
    return enrich_council_surface(session)


def _progress_label(*, agent: dict[str, object], latest_run: dict[str, object] | None) -> str:
    status = str(agent.get("status") or "unknown")
    if latest_run and str(latest_run.get("status") or "") == "completed":
        return "completed"
    if status in {"queued", "starting"}:
        return "booting"
    if status in {"active", "waiting"}:
        return "running"
    if status == "scheduled":
        return "scheduled"
    if status == "failed":
        return "failed"
    if status == "expired":
        return "expired"
    return status
