from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from apps.api.jarvis_api.services.cheap_provider_runtime import cheap_lane_status_surface
from apps.api.jarvis_api.services.non_visible_lane_execution import execute_cheap_lane
from core.runtime.db import (
    add_council_member,
    create_agent_message,
    create_agent_registry_entry,
    create_agent_run,
    create_council_session,
    get_agent_registry_entry,
    get_agent_run,
    get_council_session,
    list_agent_messages,
    list_agent_registry_entries,
    list_agent_runs,
    list_agent_tool_calls,
    list_council_sessions,
    update_council_session,
    update_agent_registry_entry,
    update_agent_run,
)


AGENT_ROLE_TEMPLATES = {
    "planner": {
        "title": "Planner",
        "default_tool_policy": "none",
        "system_prompt": (
            "Du er et offspring under Jarvis. Du planlaegger en konkret loesning, "
            "holder dig til opgaven, og afleverer et kort beslutningsklart resultat tilbage til Jarvis."
        ),
    },
    "critic": {
        "title": "Critic",
        "default_tool_policy": "none",
        "system_prompt": (
            "Du er et offspring under Jarvis. Du leder efter svage antagelser, risici og manglende test eller beviser, "
            "og afleverer fund direkte tilbage til Jarvis."
        ),
    },
    "researcher": {
        "title": "Researcher",
        "default_tool_policy": "read-only-runtime",
        "system_prompt": (
            "Du er et offspring under Jarvis. Du samler relevante fakta og observationer til opgaven "
            "og leverer en fokuseret research-brief tilbage til Jarvis."
        ),
    },
    "synthesizer": {
        "title": "Synthesizer",
        "default_tool_policy": "none",
        "system_prompt": (
            "Du er et offspring under Jarvis. Du samler input fra andre og leverer en stram syntese tilbage til Jarvis."
        ),
    },
    "watcher": {
        "title": "Watcher",
        "default_tool_policy": "read-only-runtime",
        "system_prompt": (
            "Du er et persistent offspring under Jarvis. Du holder oeje med et afgraenset signal og rapporterer kun relevante aendringer."
        ),
    },
    "executor": {
        "title": "Executor",
        "default_tool_policy": "proposal-only",
        "system_prompt": (
            "Du er et offspring under Jarvis. Du bryder en opgave ned i konkrete handlinger og rapporterer handlingsklar naeste fase tilbage."
        ),
    },
}

COUNCIL_ROLE_ORDER = ["planner", "critic", "researcher", "synthesizer", "executor"]


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _json_loads(raw: str, fallback):
    try:
        return json.loads(str(raw or ""))
    except Exception:
        return fallback


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
    latest_run = runs[0] if runs else None
    return {
        **agent,
        "allowed_tools": _json_loads(str(agent.get("allowed_tools_json") or "[]"), []),
        "context": _json_loads(str(agent.get("context_json") or "{}"), {}),
        "result_contract": _json_loads(str(agent.get("result_contract_json") or "{}"), {}),
        "runs": runs,
        "messages": messages,
        "tool_calls": tool_calls,
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
        },
    }


def enrich_council_surface(session: dict[str, object]) -> dict[str, object]:
    council_id = str(session.get("council_id") or "")
    messages = list_agent_messages(council_id=council_id, limit=120)
    return {
        **session,
        "messages": messages,
        "message_count": len(messages),
        "latest_message": messages[-1] if messages else None,
    }


def build_council_detail_surface(council_id: str) -> dict[str, object] | None:
    session = get_council_session(council_id)
    if session is None:
        return None
    return enrich_council_surface(session)


def spawn_agent_task(
    *,
    role: str,
    goal: str,
    system_prompt: str = "",
    tool_policy: str = "",
    allowed_tools: list[str] | None = None,
    parent_agent_id: str = "jarvis",
    persistent: bool = False,
    ttl_seconds: int = 0,
    budget_tokens: int = 0,
    context: dict[str, object] | None = None,
    result_contract: dict[str, object] | None = None,
    execution_mode: str = "solo-task",
    auto_execute: bool = True,
) -> dict[str, object]:
    allowed_tools = allowed_tools or []
    context = context or {}
    result_contract = result_contract or {
        "summary": True,
        "findings": True,
        "recommendation": True,
        "confidence": True,
        "blockers": True,
    }
    template = AGENT_ROLE_TEMPLATES.get(role, AGENT_ROLE_TEMPLATES["researcher"])
    system_prompt = str(system_prompt or template["system_prompt"])
    tool_policy = str(tool_policy or template["default_tool_policy"])
    selected = cheap_lane_status_surface().get("selected_target") or {}
    provider = str(selected.get("provider") or "")
    model = str(selected.get("model") or "")
    agent_id = f"agent-{uuid4().hex}"
    thread_id = f"agent-thread-{uuid4().hex}"
    next_wake_at = ""
    if persistent and ttl_seconds > 0:
        next_wake_at = (datetime.now(UTC) + timedelta(seconds=int(ttl_seconds))).isoformat()
    agent = create_agent_registry_entry(
        agent_id=agent_id,
        parent_agent_id=parent_agent_id,
        owner_agent_id="jarvis",
        kind="persistent-watcher" if persistent else "subagent",
        role=role,
        goal=goal,
        status="queued" if auto_execute else "planned",
        lane="cheap",
        provider=provider,
        model=model,
        system_prompt=system_prompt,
        tool_policy=tool_policy,
        allowed_tools_json=json.dumps(allowed_tools),
        persistent=persistent,
        ttl_seconds=ttl_seconds,
        next_wake_at=next_wake_at,
        budget_tokens=budget_tokens,
        context_json=json.dumps(context),
        result_contract_json=json.dumps(result_contract),
    )
    create_agent_message(
        message_id=f"agent-msg-{uuid4().hex}",
        thread_id=thread_id,
        agent_id=agent_id,
        direction="jarvis->agent",
        role="system",
        kind="task-brief",
        content=goal,
    )
    create_agent_message(
        message_id=f"agent-msg-{uuid4().hex}",
        thread_id=thread_id,
        agent_id=agent_id,
        direction="jarvis->agent",
        role="system",
        kind="system-prompt",
        content=system_prompt,
    )
    if not auto_execute:
        return build_agent_detail_surface(agent_id) or agent

    return execute_agent_task(agent_id=agent_id, thread_id=thread_id, execution_mode=execution_mode)


def execute_agent_task(*, agent_id: str, thread_id: str = "", execution_mode: str = "solo-task") -> dict[str, object]:
    agent = get_agent_registry_entry(agent_id)
    if agent is None:
        raise RuntimeError(f"unknown agent: {agent_id}")
    prompt = (
        f"System prompt:\n{agent.get('system_prompt') or ''}\n\n"
        f"Role: {agent.get('role') or 'agent'}\n"
        f"Goal: {agent.get('goal') or ''}\n\n"
        "Return a compact result with sections for summary, findings, recommendation, confidence, and blockers."
    )
    run_id = f"agent-run-{uuid4().hex}"
    update_agent_registry_entry(agent_id, status="starting", last_error="")
    create_agent_run(
        run_id=run_id,
        agent_id=agent_id,
        status="starting",
        execution_mode=execution_mode,
        provider=str(agent.get("provider") or ""),
        model=str(agent.get("model") or ""),
        input_summary=str(agent.get("goal") or ""),
        input_payload_json=json.dumps({"prompt": prompt}),
        started_at=_now_iso(),
    )
    try:
        update_agent_registry_entry(agent_id, status="active")
        result = execute_cheap_lane(message=prompt)
        text = str(result.get("text") or "").strip()
        create_agent_message(
            message_id=f"agent-msg-{uuid4().hex}",
            thread_id=thread_id or f"agent-thread-{agent_id}",
            run_id=run_id,
            agent_id=agent_id,
            direction="agent->jarvis",
            role="assistant",
            kind="result",
            content=text,
        )
        output_tokens = int(result.get("output_tokens") or 0)
        input_tokens = int(result.get("input_tokens") or 0)
        update_agent_run(
            run_id,
            status="completed",
            output_summary=text[:400],
            output_payload_json=json.dumps(result),
            finished_at=_now_iso(),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=float(result.get("cost_usd") or 0.0),
            provider_status=str(result.get("status") or "completed"),
        )
        update_agent_registry_entry(
            agent_id,
            status="completed",
            tokens_burned_delta=input_tokens + output_tokens,
            completed_at=_now_iso(),
        )
    except Exception as exc:
        message = str(exc)
        create_agent_message(
            message_id=f"agent-msg-{uuid4().hex}",
            thread_id=thread_id or f"agent-thread-{agent_id}",
            run_id=run_id,
            agent_id=agent_id,
            direction="agent->jarvis",
            role="assistant",
            kind="failure",
            content=message,
        )
        update_agent_run(
            run_id,
            status="failed",
            finished_at=_now_iso(),
            failure_reason=message,
            provider_status="failed",
        )
        update_agent_registry_entry(
            agent_id,
            status="failed",
            failure_increment=1,
            last_error=message,
        )
    return build_agent_detail_surface(agent_id) or {}


def create_council_session_runtime(
    *,
    topic: str,
    roles: list[str] | None = None,
    owner_agent_id: str = "jarvis",
) -> dict[str, object]:
    roles = roles or COUNCIL_ROLE_ORDER[:4]
    council_id = f"council-{uuid4().hex}"
    create_council_session(
        council_id=council_id,
        owner_agent_id=owner_agent_id,
        topic=topic,
        status="forming",
        summary=f"Council formed around: {topic}",
    )
    create_agent_message(
        message_id=f"agent-msg-{uuid4().hex}",
        thread_id=f"council-thread-{council_id}",
        council_id=council_id,
        direction="jarvis->council",
        role="system",
        kind="council-brief",
        content=topic,
    )
    for role in roles:
        agent = spawn_agent_task(
            role=role,
            goal=f"Council topic: {topic}",
            parent_agent_id=owner_agent_id,
            auto_execute=False,
        )
        update_agent_registry_entry(str(agent.get("agent_id") or ""), status="waiting")
        add_council_member(
            council_id=council_id,
            agent_id=str(agent.get("agent_id") or ""),
            role=role,
            position_summary="awaiting deliberation",
            confidence="pending",
        )
    update_council_session(council_id, status="deliberating")
    return build_council_detail_surface(council_id) or {}


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
