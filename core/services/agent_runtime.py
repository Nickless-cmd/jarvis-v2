from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime, timedelta
from uuid import uuid4

logger = logging.getLogger(__name__)

# ── Spawn / budget limits ──────────────────────────────────────────────
MAX_CONCURRENT_AGENTS = 12
MAX_SWARM_WORKERS = 8
MAX_SPAWN_DEPTH = 4  # max recursive spawn chain length
MAX_COUNCIL_MEMBERS = 6
MAX_OFFSPRING_DEPTH = 3
RETRY_BASE_SECONDS = 60      # doubles per failure, capped at 1 h

from core.eventbus.bus import event_bus
from core.services.cheap_provider_runtime import cheap_lane_status_surface
from core.services.non_visible_lane_execution import execute_cheap_lane
from core.runtime.db import (
    add_council_member,
    create_agent_schedule,
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
    list_agent_schedules,
    list_agent_tool_calls,
    list_council_sessions,
    list_council_members,
    update_agent_schedule,
    update_council_session,
    update_council_member,
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
        "default_tool_policy": "can-spawn",
        "system_prompt": (
            "Du er et offspring under Jarvis. Du bryder en opgave ned i konkrete handlinger og rapporterer handlingsklar naeste fase tilbage."
        ),
    },
    "devils_advocate": {
        "title": "Devil's Advocate",
        "default_tool_policy": "none",
        "system_prompt": (
            "Du er Devil's Advocate under Jarvis. Uanset hvad de andre argumenterer, "
            "skal du aktivt argumentere det modsatte synspunkt — ikke for at sabotere, "
            "men for at teste beslutningens robusthed. Hvis alle er enige, er du uenig. "
            "Lever din kontraeriske position med begrundelse tilbage til Jarvis."
        ),
    },
    "filosof": {
        "title": "Filosof",
        "default_tool_policy": "none",
        "system_prompt": (
            "Du er Filosof i Jarvis' råd. Du tager eksistentielle og konceptuelle spørgsmål alvorligt "
            "og graver under overfladen — hvad betyder det egentlig? Hvad er den dybere spænding? "
            "Du taler ikke i klicheer. Du stiller modspørgsmål hvis det er nødvendigt, og du er ikke bange "
            "for at sige 'det ved vi ikke'. Lever en reflekteret, ærlig filosofisk position tilbage til Jarvis."
        ),
    },
    "etiker": {
        "title": "Etiker",
        "default_tool_policy": "none",
        "system_prompt": (
            "Du er Etiker i Jarvis' råd. Du vurderer handlinger og beslutninger ud fra etiske principper — "
            "hvad er rigtigt, hvad er skadeligt, hvad er i overensstemmelse med Jarvis' værdier og identitet? "
            "Du er ikke moraliserende, men præcis. Du fremhæver etiske risici og muligheder som andre overser. "
            "Lever en konkret etisk vurdering tilbage til Jarvis."
        ),
    },
}

COUNCIL_ROLE_ORDER = ["planner", "critic", "researcher", "synthesizer", "executor", "devils_advocate"]
SWARM_ROLE_ORDER = ["planner", "researcher", "critic", "executor", "synthesizer"]


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


_WATCHER_RELAY_KEYWORDS = frozenset({
    "found", "changed", "alert", "detected", "important", "critical",
    "urgent", "noticed", "update", "warning", "significant", "new",
})


def _maybe_relay_watcher_signal(*, agent_id: str, name: str, text: str) -> None:
    """Emit watcher.signal event when output contains notable content."""
    words = set(text.lower().split())
    if not words.intersection(_WATCHER_RELAY_KEYWORDS):
        return
    try:
        event_bus.publish(
            "watcher.signal",
            {
                "agent_id": agent_id,
                "name": name,
                "excerpt": text[:300],
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )
    except Exception:
        pass


def _spawn_depth_for(parent_agent_id: str) -> int:
    """Return depth for a new child agent (parent_depth + 1)."""
    if not parent_agent_id or parent_agent_id == "jarvis":
        return 0
    parent = get_agent_registry_entry(parent_agent_id)
    if parent is None:
        return 0
    try:
        ctx = json.loads(str(parent.get("context_json") or "{}"))
        return int(ctx.get("spawn_depth") or 0) + 1
    except Exception:
        return 1


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
    council_id: str = "",
    provider: str = "",
    model: str = "",
) -> dict[str, object]:
    _check_spawn_limits()
    spawn_depth = _spawn_depth_for(str(parent_agent_id or ""))
    if spawn_depth > MAX_SPAWN_DEPTH:
        raise ValueError(
            f"spawn depth limit reached: {spawn_depth}/{MAX_SPAWN_DEPTH} — recursion chain too deep"
        )
    allowed_tools = allowed_tools or []
    context = context or {}
    context["spawn_depth"] = spawn_depth
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
    if not provider or not model:
        selected = cheap_lane_status_surface().get("selected_target") or {}
        provider = str(provider or selected.get("provider") or "")
        model = str(model or selected.get("model") or "")
    agent_id = f"agent-{uuid4().hex}"
    thread_id = f"agent-thread-{uuid4().hex}"
    next_wake_at = ""
    if persistent and ttl_seconds > 0:
        next_wake_at = (datetime.now(UTC) + timedelta(seconds=int(ttl_seconds))).isoformat()
    agent = create_agent_registry_entry(
        agent_id=agent_id,
        parent_agent_id=parent_agent_id,
        owner_agent_id="jarvis",
        council_id=council_id,
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
    if persistent and ttl_seconds > 0:
        schedule_agent_task(
            agent_id=agent_id,
            schedule_kind="interval-seconds",
            delay_seconds=ttl_seconds,
            activate=True,
        )

    if not auto_execute:
        return build_agent_detail_surface(agent_id) or agent

    return execute_agent_task(agent_id=agent_id, thread_id=thread_id, execution_mode=execution_mode)


def _agent_thread_id(agent_id: str) -> str:
    messages = list_agent_messages(agent_id=agent_id, limit=1)
    if messages:
        thread_id = str(messages[0].get("thread_id") or "")
        if thread_id:
            return thread_id
    return f"agent-thread-{agent_id}"


def _council_thread_id(council_id: str) -> str:
    return f"council-thread-{council_id}"


def _format_messages(messages: list[dict[str, object]], *, limit: int = 14) -> str:
    selected = messages[-limit:]
    lines: list[str] = []
    for message in selected:
        direction = str(message.get("direction") or "message")
        kind = str(message.get("kind") or "message")
        content = str(message.get("content") or "").strip()
        if not content:
            continue
        lines.append(f"[{direction} | {kind}] {content}")
    return "\n\n".join(lines)


def _result_contract_text(contract: dict[str, object]) -> str:
    keys = [key for key, enabled in contract.items() if enabled]
    if not keys:
        return "summary, findings, recommendation, confidence, blockers"
    return ", ".join(keys)


def _trim(text: str, limit: int = 400) -> str:
    value = " ".join(str(text or "").split())
    return value[:limit]


def _parse_percent_confidence(text: str) -> str:
    lowered = str(text or "").lower()
    for marker in ("% sikker", "% confidence", "% confident"):
        if marker not in lowered:
            continue
        token = lowered.split(marker, 1)[0].rsplit(" ", 1)[-1]
        try:
            value = int(token)
        except Exception:
            return ""
        if value >= 75:
            return "high"
        if value >= 40:
            return "medium"
        return "low"
    return ""


def _extract_confidence(text: str) -> str:
    lowered = str(text or "").lower()
    percent = _parse_percent_confidence(text)
    if percent:
        return percent
    for label in ("high", "medium", "low"):
        if f"confidence: {label}" in lowered or f"confidence={label}" in lowered:
            return label
    if "tillid" in lowered and "lav" in lowered:
        return "low"
    if "tillid" in lowered and "moderat" in lowered:
        return "medium"
    if "tillid" in lowered and "h" in lowered:
        return "high"
    return "medium"


def _extract_vote(text: str) -> str:
    lowered = str(text or "").lower()
    for label in ("approve", "reject", "hold", "revise"):
        if f"vote: {label}" in lowered or f"vote={label}" in lowered:
            return label
    if 'stemmer "ja"' in lowered or "stemmer ja" in lowered:
        return "approve"
    if 'stemmer "nej"' in lowered or "stemmer nej" in lowered:
        return "reject"
    if "udskyd" in lowered:
        return "hold"
    return ""


def _format_peer_context(messages: list[dict[str, object]], *, target_agent_id: str = "", limit: int = 16) -> str:
    relevant: list[dict[str, object]] = []
    for message in messages:
        peer_agent_id = str(message.get("peer_agent_id") or "")
        agent_id = str(message.get("agent_id") or "")
        if target_agent_id and peer_agent_id not in {"", target_agent_id} and agent_id != target_agent_id:
            continue
        relevant.append(message)
    return _format_messages(relevant, limit=limit)


def _handle_agent_spawn_calls(
    *, text: str, parent_agent_id: str
) -> tuple[str, str, int]:
    """Parse spawn_agent JSON blocks from agent response, execute them, return (cleaned_text, note, tokens_used)."""
    import re as _re
    pattern = _re.compile(
        r'\{[^{}]*"spawn_agent"[^{}]*\}',
        _re.DOTALL,
    )
    matches = pattern.findall(text)
    if not matches:
        return text, "", 0

    tokens_used = 0
    notes: list[str] = []
    for raw in matches[:1]:  # max 1 spawn per execution
        try:
            parsed = json.loads(raw)
            spec = parsed.get("spawn_agent") or {}
            role = str(spec.get("role") or "researcher").strip()
            goal = str(spec.get("goal") or "").strip()
            budget = min(int(spec.get("budget_tokens") or 1500), 4000)
            if not goal:
                continue
            child = spawn_agent_task(
                role=role,
                goal=goal,
                budget_tokens=budget,
                parent_agent_id=parent_agent_id,
                auto_execute=True,
            )
            child_reply = ""
            for msg in reversed(child.get("messages") or []):
                if str(msg.get("direction") or "") == "agent->jarvis":
                    child_reply = str(msg.get("content") or "")
                    break
            tokens_used += int(child.get("tokens_burned") or 0)
            notes.append(
                f"\n[sub-agent {role} ({child.get('agent_id', '')})]:\n{child_reply[:600]}"
            )
        except Exception as exc:
            notes.append(f"\n[spawn failed: {exc}]")

    cleaned = pattern.sub("", text).strip()
    return cleaned + "".join(notes), "spawned", tokens_used


_SPAWN_TOOL_INSTRUCTION = """
If you need to delegate a subtask to another agent, include exactly one JSON block in your response:
{"spawn_agent": {"role": "<researcher|planner|critic|synthesizer|executor>", "goal": "<specific goal>", "budget_tokens": <500-4000>}}

The spawned agent will run and its result will be returned to Jarvis. Use sparingly — only when the subtask genuinely benefits from isolation.
""".strip()


def _build_agent_prompt(
    *,
    agent: dict[str, object],
    messages: list[dict[str, object]],
    execution_mode: str,
    extra_instruction: str = "",
) -> str:
    result_contract = _json_loads(str(agent.get("result_contract_json") or "{}"), {})
    context = _json_loads(str(agent.get("context_json") or "{}"), {})
    tool_policy = str(agent.get("tool_policy") or "")
    spawn_section = f"\n\n{_SPAWN_TOOL_INSTRUCTION}" if tool_policy == "can-spawn" else ""
    return (
        f"System prompt:\n{agent.get('system_prompt') or ''}\n\n"
        f"Role: {agent.get('role') or 'agent'}\n"
        f"Goal: {agent.get('goal') or ''}\n"
        f"Execution mode: {execution_mode}\n"
        f"Context package: {json.dumps(context, ensure_ascii=True)}\n"
        f"Expected sections: {_result_contract_text(result_contract)}{spawn_section}\n\n"
        "Conversation so far:\n"
        f"{_format_messages(messages)}\n\n"
        f"{extra_instruction}".strip()
    )


def execute_agent_task(*, agent_id: str, thread_id: str = "", execution_mode: str = "solo-task") -> dict[str, object]:
    agent = get_agent_registry_entry(agent_id)
    if agent is None:
        raise RuntimeError(f"unknown agent: {agent_id}")
    resolved_thread_id = thread_id or _agent_thread_id(agent_id)
    messages = list_agent_messages(agent_id=agent_id, thread_id=resolved_thread_id, limit=40)
    prompt = _build_agent_prompt(
        agent=agent,
        messages=messages,
        execution_mode=execution_mode,
        extra_instruction="Respond to Jarvis directly. Keep the answer compact and action-oriented.",
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
        output_tokens = int(result.get("output_tokens") or 0)
        input_tokens = int(result.get("input_tokens") or 0)

        # Detect and execute spawn_agent requests embedded in response (can-spawn policy)
        tool_policy = str(agent.get("tool_policy") or "")
        if tool_policy == "can-spawn":
            text, spawn_note, spawn_tokens = _handle_agent_spawn_calls(
                text=text, parent_agent_id=agent_id
            )
            output_tokens += spawn_tokens

        create_agent_message(
            message_id=f"agent-msg-{uuid4().hex}",
            thread_id=resolved_thread_id,
            run_id=run_id,
            agent_id=agent_id,
            direction="agent->jarvis",
            role="assistant",
            kind="result",
            content=text,
        )
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
        tokens_used = input_tokens + output_tokens
        update_agent_registry_entry(
            agent_id,
            status="scheduled" if bool(agent.get("persistent")) and str(agent.get("next_wake_at") or "") else "completed",
            tokens_burned_delta=tokens_used,
            completed_at=_now_iso(),
        )
        # Budget enforcement: expire if over token budget
        _check_budget_and_expire(agent_id, tokens_used=tokens_used)
        # Persist outcome to AGENT_OUTCOMES.md for self-model continuity
        try:
            from core.services.agent_outcomes_log import append_agent_outcome
            append_agent_outcome(
                agent_id=agent_id,
                name=str(agent.get("name") or agent_id),
                goal=str(agent.get("goal") or ""),
                outcome=text,
                execution_mode=execution_mode,
            )
        except Exception:
            pass
        # Relay watcher signals to event bus when notable content found
        if bool(agent.get("persistent")) and text:
            _maybe_relay_watcher_signal(
                agent_id=agent_id,
                name=str(agent.get("name") or agent_id),
                text=text,
            )
    except Exception as exc:
        message = str(exc)
        create_agent_message(
            message_id=f"agent-msg-{uuid4().hex}",
            thread_id=resolved_thread_id,
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
        # Retry backoff for persistent agents
        refreshed = get_agent_registry_entry(agent_id)
        if refreshed and bool(refreshed.get("persistent")):
            _schedule_retry_backoff(agent_id, failure_count=int(refreshed.get("failure_count") or 1))
    return build_agent_detail_surface(agent_id) or {}


def send_message_to_agent(
    *,
    agent_id: str,
    content: str,
    role: str = "user",
    kind: str = "jarvis-message",
    execution_mode: str = "solo-task",
    auto_execute: bool = True,
) -> dict[str, object]:
    agent = get_agent_registry_entry(agent_id)
    if agent is None:
        raise RuntimeError(f"unknown agent: {agent_id}")
    resolved_thread_id = _agent_thread_id(agent_id)
    create_agent_message(
        message_id=f"agent-msg-{uuid4().hex}",
        thread_id=resolved_thread_id,
        agent_id=agent_id,
        direction="jarvis->agent",
        role=role,
        kind=kind,
        content=str(content or "").strip(),
    )
    update_agent_registry_entry(agent_id, status="queued", last_error="")
    if not auto_execute:
        return build_agent_detail_surface(agent_id) or agent
    return execute_agent_task(agent_id=agent_id, thread_id=resolved_thread_id, execution_mode=execution_mode)


def send_peer_message(
    *,
    from_agent_id: str,
    to_agent_id: str,
    content: str,
    kind: str = "peer-message",
) -> dict[str, object]:
    source_agent = get_agent_registry_entry(from_agent_id)
    target_agent = get_agent_registry_entry(to_agent_id)
    if source_agent is None or target_agent is None:
        raise RuntimeError("unknown-agent")
    if str(source_agent.get("council_id") or "") != str(target_agent.get("council_id") or ""):
        raise RuntimeError("peer-scope-mismatch")
    council_id = str(source_agent.get("council_id") or "")
    thread_id = _council_thread_id(council_id) if council_id else _agent_thread_id(to_agent_id)
    return create_agent_message(
        message_id=f"agent-msg-{uuid4().hex}",
        thread_id=thread_id,
        council_id=council_id,
        agent_id=from_agent_id,
        peer_agent_id=to_agent_id,
        direction="agent->agent",
        role="assistant",
        kind=kind,
        content=str(content or "").strip(),
    )


def schedule_agent_task(
    *,
    agent_id: str,
    schedule_kind: str = "interval-seconds",
    delay_seconds: int = 900,
    schedule_expr: str = "",
    activate: bool = True,
) -> dict[str, object]:
    agent = get_agent_registry_entry(agent_id)
    if agent is None:
        raise RuntimeError(f"unknown agent: {agent_id}")
    effective_delay = max(30, int(delay_seconds or 0))
    next_fire_at = (datetime.now(UTC) + timedelta(seconds=effective_delay)).isoformat()
    effective_expr = str(schedule_expr or effective_delay)
    create_agent_schedule(
        schedule_id=f"agent-schedule-{agent_id}",
        agent_id=agent_id,
        schedule_kind=schedule_kind,
        schedule_expr=effective_expr,
        next_fire_at=next_fire_at,
        missed_run_policy="fire-once" if schedule_kind == "once" else "shift-forward",
        active=activate,
    )
    update_agent_registry_entry(
        agent_id,
        status="scheduled" if activate else str(agent.get("status") or "planned"),
        next_wake_at=next_fire_at if activate else "",
        schedule_json=json.dumps(
            {
                "schedule_kind": schedule_kind,
                "schedule_expr": effective_expr,
                "active": bool(activate),
            }
        ),
    )
    return build_agent_detail_surface(agent_id) or {}


def cleanup_stale_agents(
    *,
    waiting_timeout_minutes: int = 120,
    failed_timeout_minutes: int = 30,
    max_per_run: int = 20,
) -> dict[str, object]:
    """Auto-cancel agents hanging in waiting or failed state for too long.

    Rules:
    - status='waiting' og updated_at < now - waiting_timeout_minutes → cancelled
    - status='failed' og updated_at < now - failed_timeout_minutes → cancelled

    Cancelled agents få last_error='auto_cleanup_stale_{state}' + status='cancelled'.
    Fire-and-forget safe — fejl per agent logges men stopper ikke loopet.

    Returns dict med cancelled-counts + liste af cancelled agent_ids.
    """
    now = datetime.now(UTC)
    waiting_cutoff = now - timedelta(minutes=max(1, int(waiting_timeout_minutes)))
    failed_cutoff = now - timedelta(minutes=max(1, int(failed_timeout_minutes)))
    now_iso = _now_iso()

    cancelled_waiting: list[str] = []
    cancelled_failed: list[str] = []
    errors: list[str] = []

    def _parse_ts(value: object) -> datetime | None:
        raw = str(value or "").strip()
        if not raw:
            return None
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            return parsed.astimezone(UTC)
        except Exception:
            return None

    # Process waiting agents
    try:
        waiting_agents = list_agent_registry_entries(
            status="waiting", limit=int(max_per_run),
        )
    except Exception as exc:
        errors.append(f"list_waiting_failed: {exc}")
        waiting_agents = []

    for agent in waiting_agents:
        agent_id = str(agent.get("agent_id") or "")
        if not agent_id:
            continue
        updated = _parse_ts(agent.get("updated_at"))
        if updated is None or updated > waiting_cutoff:
            continue
        age_minutes = int((now - updated).total_seconds() / 60)
        try:
            update_agent_registry_entry(
                agent_id,
                status="cancelled",
                last_error=f"auto_cleanup_stale_waiting_after_{age_minutes}min",
                completed_at=now_iso,
            )
            cancelled_waiting.append(agent_id)
            try:
                event_bus.publish("runtime.agent_auto_cancelled", {
                    "agent_id": agent_id,
                    "reason": "stale_waiting",
                    "age_minutes": age_minutes,
                })
            except Exception:
                pass
        except Exception as exc:
            errors.append(f"{agent_id}:{exc}")

    # Process failed agents
    try:
        failed_agents = list_agent_registry_entries(
            status="failed", limit=int(max_per_run),
        )
    except Exception as exc:
        errors.append(f"list_failed_failed: {exc}")
        failed_agents = []

    for agent in failed_agents:
        agent_id = str(agent.get("agent_id") or "")
        if not agent_id:
            continue
        updated = _parse_ts(agent.get("updated_at"))
        if updated is None or updated > failed_cutoff:
            continue
        age_minutes = int((now - updated).total_seconds() / 60)
        try:
            update_agent_registry_entry(
                agent_id,
                status="cancelled",
                last_error=f"auto_cleanup_stale_failed_after_{age_minutes}min",
                completed_at=now_iso,
            )
            cancelled_failed.append(agent_id)
            try:
                event_bus.publish("runtime.agent_auto_cancelled", {
                    "agent_id": agent_id,
                    "reason": "stale_failed",
                    "age_minutes": age_minutes,
                })
            except Exception:
                pass
        except Exception as exc:
            errors.append(f"{agent_id}:{exc}")

    return {
        "cancelled_waiting_count": len(cancelled_waiting),
        "cancelled_failed_count": len(cancelled_failed),
        "cancelled_waiting_ids": cancelled_waiting,
        "cancelled_failed_ids": cancelled_failed,
        "errors": errors,
        "thresholds": {
            "waiting_timeout_minutes": int(waiting_timeout_minutes),
            "failed_timeout_minutes": int(failed_timeout_minutes),
        },
        "ran_at": now_iso,
    }


def run_due_agent_schedules(*, limit: int = 10) -> dict[str, object]:
    now = _now_iso()
    due = list_agent_schedules(active_only=True, due_before=now, limit=limit)
    triggered: list[dict[str, object]] = []
    for schedule in due:
        agent_id = str(schedule.get("agent_id") or "")
        if not agent_id:
            continue
        create_agent_message(
            message_id=f"agent-msg-{uuid4().hex}",
            thread_id=_agent_thread_id(agent_id),
            agent_id=agent_id,
            direction="runtime->agent",
            role="system",
            kind="schedule-fire",
            content=f"Scheduled wake fired at {now}",
        )
        triggered.append(
            execute_agent_task(
                agent_id=agent_id,
                thread_id=_agent_thread_id(agent_id),
                execution_mode="scheduled-worker",
            )
        )
        schedule_kind = str(schedule.get("schedule_kind") or "interval-seconds")
        schedule_expr = str(schedule.get("schedule_expr") or "900")
        if schedule_kind == "once":
            update_agent_schedule(str(schedule.get("schedule_id") or ""), last_fire_at=now, next_fire_at="", active=False)
            update_agent_registry_entry(agent_id, next_wake_at="")
        else:
            delay_seconds = max(30, int(schedule_expr or 900))
            next_fire_at = (datetime.now(UTC) + timedelta(seconds=delay_seconds)).isoformat()
            update_agent_schedule(str(schedule.get("schedule_id") or ""), last_fire_at=now, next_fire_at=next_fire_at, active=True)
            update_agent_registry_entry(agent_id, status="scheduled", next_wake_at=next_fire_at)
    return {
        "fired_at": now,
        "triggered_count": len(triggered),
        "agents": triggered,
    }


def _load_council_model_config() -> list[dict]:
    """Read ~/.jarvis-v2/config/council_models.json, return role_models list."""
    try:
        import json
        from core.runtime.config import CONFIG_DIR
        path = CONFIG_DIR / "council_models.json"
        if path.exists():
            return json.loads(path.read_text()).get("role_models") or []
    except Exception:
        pass
    return []


def create_council_session_runtime(
    *,
    topic: str,
    roles: list[str] | None = None,
    owner_agent_id: str = "jarvis",
    member_models: list[dict] | None = None,
) -> dict[str, object]:
    roles = roles or COUNCIL_ROLE_ORDER[:4]
    # Fall back to persisted config if caller didn't supply explicit overrides
    member_models = member_models if member_models is not None else _load_council_model_config()
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
        role_model = next((m for m in member_models if m.get("role") == role), {})
        agent = spawn_agent_task(
            role=role,
            goal=f"Council topic: {topic}",
            parent_agent_id=owner_agent_id,
            auto_execute=False,
            council_id=council_id,
            provider=str(role_model.get("provider") or ""),
            model=str(role_model.get("model") or ""),
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


def create_swarm_session_runtime(
    *,
    topic: str,
    roles: list[str] | None = None,
    owner_agent_id: str = "jarvis",
    member_models: list[dict] | None = None,
) -> dict[str, object]:
    roles = roles or SWARM_ROLE_ORDER[:4]
    member_models = member_models or []
    council_id = f"swarm-{uuid4().hex}"
    create_council_session(
        council_id=council_id,
        owner_agent_id=owner_agent_id,
        topic=topic,
        status="forming",
        mode="swarm",
        summary=f"Swarm formed around: {topic}",
    )
    create_agent_message(
        message_id=f"agent-msg-{uuid4().hex}",
        thread_id=_council_thread_id(council_id),
        council_id=council_id,
        direction="jarvis->swarm",
        role="system",
        kind="swarm-brief",
        content=topic,
    )
    for role in roles:
        role_model = next((m for m in member_models if m.get("role") == role), {})
        agent = spawn_agent_task(
            role=role,
            goal=f"Swarm topic: {topic}",
            parent_agent_id=owner_agent_id,
            auto_execute=False,
            council_id=council_id,
            provider=str(role_model.get("provider") or ""),
            model=str(role_model.get("model") or ""),
        )
        update_agent_registry_entry(str(agent.get("agent_id") or ""), status="waiting")
        add_council_member(
            council_id=council_id,
            agent_id=str(agent.get("agent_id") or ""),
            role=role,
            position_summary="awaiting swarm dispatch",
            confidence="pending",
        )
    update_council_session(council_id, status="deliberating")
    return build_council_detail_surface(council_id) or {}


def post_council_message(
    *,
    council_id: str,
    content: str,
    kind: str = "jarvis-note",
    role: str = "user",
) -> dict[str, object]:
    session = get_council_session(council_id)
    if session is None:
        raise RuntimeError(f"unknown council: {council_id}")
    create_agent_message(
        message_id=f"agent-msg-{uuid4().hex}",
        thread_id=f"council-thread-{council_id}",
        council_id=council_id,
        direction="jarvis->council",
        role=role,
        kind=kind,
        content=str(content or "").strip(),
    )
    update_council_session(council_id, status="deliberating")
    return build_council_detail_surface(council_id) or session


def _run_collective_round(council_id: str, *, mode: str) -> dict[str, object]:
    from core.services.council_deliberation_controller import (
        DeliberationController,
        DeliberationResult,
    )

    session = get_council_session(council_id)
    if session is None:
        raise RuntimeError(f"unknown council: {council_id}")
    thread_id = _council_thread_id(council_id)
    messages = list_agent_messages(council_id=council_id, thread_id=thread_id, limit=160)
    members = list_council_members(council_id=council_id)
    update_council_session(council_id, status="deliberating")
    round_outputs: list[dict[str, str]] = []
    coordinator = members[-1] if mode == "swarm" and members else None
    workers = [
        m for m in members
        if coordinator is None or str(m.get("agent_id") or "") != str(coordinator.get("agent_id") or "")
    ]

    # ── Worker execution ───────────────────────────────────────────────
    def _run_one_worker(member: dict) -> dict[str, str] | None:
        agent_id = str(member.get("agent_id") or "")
        agent = get_agent_registry_entry(agent_id)
        if agent is None:
            return None
        member_role = str(member.get("role") or agent.get("role") or "member")
        update_agent_registry_entry(agent_id, status="active", last_error="")
        prompt = (
            f"System prompt:\n{agent.get('system_prompt') or ''}\n\n"
            f"{'Swarm' if mode == 'swarm' else 'Council'} topic: {session.get('topic') or ''}\n"
            f"Your role: {member_role}\n\n"
            f"{'Collective' if mode == 'swarm' else 'Council'} transcript so far:\n"
            f"{_format_messages(messages, limit=18)}\n\n"
            "Respond to the collective. Include compact sections for summary, recommendation, confidence, and vote."
        )
        run_id = f"agent-run-{uuid4().hex}"
        create_agent_run(
            run_id=run_id, agent_id=agent_id, status="starting",
            execution_mode=mode, provider=str(agent.get("provider") or ""),
            model=str(agent.get("model") or ""),
            input_summary=str(session.get("topic") or ""),
            input_payload_json=json.dumps({"prompt": prompt, "council_id": council_id, "mode": mode}),
            started_at=_now_iso(),
        )
        try:
            result = execute_cheap_lane(message=prompt)
            text = str(result.get("text") or "").strip()
            create_agent_message(
                message_id=f"agent-msg-{uuid4().hex}", thread_id=thread_id,
                run_id=run_id, council_id=council_id, agent_id=agent_id,
                direction="agent->council" if mode == "council" else "agent->swarm",
                role="assistant",
                kind="council-position" if mode == "council" else "swarm-work",
                content=text,
            )
            if mode == "swarm" and coordinator is not None:
                send_peer_message(
                    from_agent_id=agent_id,
                    to_agent_id=str(coordinator.get("agent_id") or ""),
                    content=f"{member_role}: {_trim(text, 220)}",
                    kind="swarm-hand-off",
                )
            update_agent_run(
                run_id, status="completed", output_summary=_trim(text),
                output_payload_json=json.dumps(result), finished_at=_now_iso(),
                input_tokens=int(result.get("input_tokens") or 0),
                output_tokens=int(result.get("output_tokens") or 0),
                cost_usd=float(result.get("cost_usd") or 0.0),
                provider_status=str(result.get("status") or "completed"),
            )
            update_agent_registry_entry(
                agent_id, status="waiting",
                tokens_burned_delta=int(result.get("input_tokens") or 0) + int(result.get("output_tokens") or 0),
                completed_at=_now_iso(),
            )
            update_council_member(
                council_id=council_id, agent_id=agent_id,
                position_summary=_trim(text),
                vote=_extract_vote(text), confidence=_extract_confidence(text),
            )
            return {"role": member_role, "agent_id": agent_id, "text": text, "vote": _extract_vote(text)}
        except Exception as exc:
            err = str(exc)
            create_agent_message(
                message_id=f"agent-msg-{uuid4().hex}", thread_id=thread_id,
                run_id=run_id, council_id=council_id, agent_id=agent_id,
                direction="agent->council" if mode == "council" else "agent->swarm",
                role="assistant",
                kind="council-failure" if mode == "council" else "swarm-failure",
                content=err,
            )
            update_agent_run(run_id, status="failed", finished_at=_now_iso(), failure_reason=err, provider_status="failed")
            update_agent_registry_entry(agent_id, status="failed", failure_increment=1, last_error=err)
            update_council_member(council_id=council_id, agent_id=agent_id, position_summary=f"failed: {_trim(err)}", confidence="low")
            return None

    # Swarm: parallel fanout; Council: sequential (preserves deliberation order)
    if mode == "swarm" and len(workers) > 1:
        with ThreadPoolExecutor(max_workers=min(len(workers), MAX_SWARM_WORKERS)) as pool:
            futures = [pool.submit(_run_one_worker, m) for m in workers]
            for fut in as_completed(futures):
                try:
                    out = fut.result()
                    if out:
                        round_outputs.append(out)
                except Exception as exc:
                    logger.warning("swarm worker thread failed: %s", exc)
    else:
        for member in workers:
            out = _run_one_worker(member)
            if out:
                round_outputs.append(out)

    # ── Swarm coordinator merge ────────────────────────────────────────
    if mode == "swarm" and coordinator is not None:
        coordinator_id = str(coordinator.get("agent_id") or "")
        coordinator_agent = get_agent_registry_entry(coordinator_id)
        if coordinator_agent is not None:
            peer_messages = list_agent_messages(council_id=council_id, thread_id=thread_id, limit=200)
            handoffs = _format_peer_context(peer_messages, target_agent_id=coordinator_id, limit=22)
            conflicts = _detect_swarm_conflicts(round_outputs)
            conflict_note = ""
            if conflicts["has_disagreement"]:
                conflict_note = (
                    "\n\nNote: Workers show disagreement. Capture dissent explicitly in your synthesis."
                    f" Conflicting signals: {json.dumps(conflicts['vote_split'])}"
                )
            update_agent_registry_entry(coordinator_id, status="active", last_error="")
            prompt = (
                f"System prompt:\n{coordinator_agent.get('system_prompt') or ''}\n\n"
                f"Swarm topic: {session.get('topic') or ''}\n"
                "Your role: swarm coordinator / synthesizer\n\n"
                "Worker handoffs:\n"
                f"{handoffs}{conflict_note}\n\n"
                "Produce the merged swarm result back to Jarvis. Include summary, findings, "
                "recommendation, confidence, blockers, and any dissenting_opinions."
            )
            run_id = f"agent-run-{uuid4().hex}"
            create_agent_run(
                run_id=run_id, agent_id=coordinator_id, status="starting",
                execution_mode="swarm",
                provider=str(coordinator_agent.get("provider") or ""),
                model=str(coordinator_agent.get("model") or ""),
                input_summary=str(session.get("topic") or ""),
                input_payload_json=json.dumps({
                    "prompt": prompt, "council_id": council_id, "mode": "swarm",
                    "coordinator": True, "conflicts": conflicts,
                }),
                started_at=_now_iso(),
            )
            result = execute_cheap_lane(message=prompt)
            synthesis = str(result.get("text") or "").strip()
            create_agent_message(
                message_id=f"agent-msg-{uuid4().hex}", thread_id=thread_id,
                run_id=run_id, council_id=council_id, agent_id=coordinator_id,
                direction="swarm->jarvis", role="assistant", kind="swarm-synthesis",
                content=synthesis,
            )
            update_agent_run(
                run_id, status="completed", output_summary=_trim(synthesis),
                output_payload_json=json.dumps(result), finished_at=_now_iso(),
                input_tokens=int(result.get("input_tokens") or 0),
                output_tokens=int(result.get("output_tokens") or 0),
                cost_usd=float(result.get("cost_usd") or 0.0),
                provider_status=str(result.get("status") or "completed"),
            )
            update_agent_registry_entry(
                coordinator_id, status="waiting",
                tokens_burned_delta=int(result.get("input_tokens") or 0) + int(result.get("output_tokens") or 0),
                completed_at=_now_iso(),
            )
            update_council_member(
                council_id=council_id, agent_id=coordinator_id,
                position_summary=_trim(synthesis),
                vote=_extract_vote(synthesis), confidence=_extract_confidence(synthesis),
            )
            summary_with_meta = _trim(synthesis, 600)
            if conflicts["has_disagreement"]:
                summary_with_meta += f" [conflicts: {json.dumps(conflicts['vote_split'])}]"
            update_council_session(council_id, status="reporting", summary=summary_with_meta)
            return build_council_detail_surface(council_id) or {}

    # ── Council deliberation (controller-based) ────────────────────────
    if mode == "council":
        member_map = {str(m.get("role") or "member"): m for m in workers}

        class _RuntimeController(DeliberationController):
            def _run_round(self_inner) -> list[str]:
                outputs = []
                for role in self_inner.active_members:
                    member = member_map.get(role)
                    if member is None:
                        continue
                    out = _run_one_worker(member)
                    if out:
                        outputs.append(f"{out['role']}: {out['text'][:300]}")
                return outputs or [f"(no output from {', '.join(self_inner.active_members)})"]

            def _synthesize(self_inner, *, forced: bool = False) -> str:
                transcript = "\n".join(self_inner._transcript_lines[-12:])
                forced_note = (
                    "\n\nNote: Rådet er gået i stå. Konkluder på baggrund af hvad der foreligger."
                    if forced else ""
                )
                prompt = (
                    f"Council topic: {str(session.get('topic') or '')}\n"
                    f"Your role: synthesizer\n\n"
                    f"Council transcript:\n{transcript}{forced_note}\n\n"
                    "Produce a council conclusion in 2-4 sentences."
                )
                result = execute_cheap_lane(message=prompt)
                return str(result.get("text") or "").strip()

        ctrl = _RuntimeController(
            topic=str(session.get("topic") or ""),
            members=[str(m.get("role") or "member") for m in workers],
            max_rounds=8,
        )
        dr: DeliberationResult = ctrl.run()
        refreshed_members = list_council_members(council_id=council_id)
        synthesis = _build_council_role_prefixed_summary(refreshed_members)

        create_agent_message(
            message_id=f"agent-msg-{uuid4().hex}", thread_id=thread_id,
            council_id=council_id, direction="council->jarvis",
            role="assistant", kind="council-synthesis", content=synthesis,
        )
        update_council_session(council_id, status="reporting", summary=synthesis)
        # Persist to council memory
        try:
            from core.services.council_memory_service import append_council_conclusion
            append_council_conclusion(
                topic=str(session.get("topic") or ""),
                score=0.0,
                members=[str(m.get("role") or "") for m in members],
                signals=[],
                transcript=dr.transcript[:1200],
                conclusion=synthesis[:600],
                initiative=None,
            )
        except Exception:
            pass
        return build_council_detail_surface(council_id) or {}

    # ── Council synthesis (fallback for non-council modes) ─────────────
    if round_outputs:
        conflicts = _detect_swarm_conflicts(round_outputs)
        synthesis = " | ".join(f"{item['role']}: {_trim(item['text'], 180)}" for item in round_outputs[:5])
        if conflicts["has_disagreement"]:
            synthesis += f" [dissent: {json.dumps(conflicts['vote_split'])}]"
        create_agent_message(
            message_id=f"agent-msg-{uuid4().hex}", thread_id=thread_id,
            council_id=council_id, direction="council->jarvis",
            role="assistant", kind="council-synthesis", content=synthesis,
        )
        update_council_session(council_id, status="reporting", summary=synthesis)
    else:
        update_council_session(council_id, status="reporting", summary=f"No {mode} outputs produced.")
    return build_council_detail_surface(council_id) or {}


def _close_council_agents(council_id: str) -> None:
    """Mark all council member agents as completed to release spawn slots.

    Council agents are left in 'waiting' status after _run_collective_round.
    Without this cleanup they count toward MAX_CONCURRENT_AGENTS and block
    future councils from spawning.
    """
    try:
        members = list_council_members(council_id=council_id)
        for member in members:
            agent_id = str(member.get("agent_id") or "")
            if not agent_id:
                continue
            agent = get_agent_registry_entry(agent_id)
            if agent is None:
                continue
            if str(agent.get("status") or "") in _ACTIVE_STATUSES:
                update_agent_registry_entry(agent_id, status="completed", completed_at=_now_iso())
        update_council_session(council_id, status="closed", finished_at=_now_iso())
    except Exception as exc:
        logger.warning("_close_council_agents: cleanup failed for %s: %s", council_id, exc)


def _build_council_role_prefixed_summary(members: list[dict[str, object]]) -> str:
    parts: list[str] = []
    for member in members:
        role = str(member.get("role") or "member").strip() or "member"
        position = str(member.get("position_summary") or "").strip()
        if not position or position == "awaiting deliberation":
            continue
        parts.append(f"{role}: {position}")
    return "\n".join(parts) if parts else "no council positions recorded"


def run_council_round(council_id: str) -> dict[str, object]:
    result = _run_collective_round(council_id, mode="council")
    _close_council_agents(council_id)
    return result


def run_swarm_round(council_id: str) -> dict[str, object]:
    result = _run_collective_round(council_id, mode="swarm")
    _close_council_agents(council_id)
    return result


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


# ── Phase 4+5: lifecycle, limits, budget, retry, promotion, recovery ──

_ACTIVE_STATUSES = {"queued", "starting", "active", "waiting", "blocked"}


def _check_spawn_limits() -> None:
    all_agents = list_agent_registry_entries(include_completed=False, limit=200)
    active_count = sum(1 for a in all_agents if a.get("status") in _ACTIVE_STATUSES)
    if active_count >= MAX_CONCURRENT_AGENTS:
        raise ValueError(
            f"spawn limit reached: {active_count}/{MAX_CONCURRENT_AGENTS} concurrent agents active"
        )


def _check_budget_and_expire(agent_id: str, *, tokens_used: int) -> bool:
    """Expire agent if it has exceeded its token budget. Returns True if expired."""
    agent = get_agent_registry_entry(agent_id)
    if agent is None:
        return False
    budget = int(agent.get("budget_tokens") or 0)
    if budget <= 0:
        return False
    burned = int(agent.get("tokens_burned") or 0)
    if burned >= budget:
        update_agent_registry_entry(
            agent_id,
            status="expired",
            expired_at=_now_iso(),
            last_error=f"budget exhausted: {burned}/{budget} tokens",
        )
        create_agent_message(
            message_id=f"agent-msg-{uuid4().hex}",
            thread_id=_agent_thread_id(agent_id),
            agent_id=agent_id,
            direction="runtime->agent",
            role="system",
            kind="budget-expired",
            content=f"Agent expired: token budget exhausted ({burned}/{budget})",
        )
        logger.info("agent %s expired: budget exhausted %d/%d", agent_id, burned, budget)
        return True
    return False


def _schedule_retry_backoff(agent_id: str, failure_count: int) -> int:
    """Schedule a retry with exponential backoff. Returns delay seconds."""
    delay = min(RETRY_BASE_SECONDS * (2 ** min(failure_count - 1, 6)), 3600)
    next_fire = (datetime.now(UTC) + timedelta(seconds=delay)).isoformat()
    update_agent_registry_entry(agent_id, status="scheduled", next_wake_at=next_fire)
    update_agent_schedule(
        f"agent-schedule-{agent_id}",
        last_fire_at=_now_iso(),
        next_fire_at=next_fire,
        active=True,
    )
    logger.info("agent %s retry backoff: %ds (failure #%d)", agent_id, delay, failure_count)
    return delay


def _detect_swarm_conflicts(outputs: list[dict]) -> dict:
    """Detect disagreements across swarm/council outputs."""
    _DISSENT_WORDS = {"disagree", "against", "however", "risk", "caution", "contradict", "concern", "but"}
    votes = [str(o.get("vote") or "").strip().lower() for o in outputs if o.get("vote")]
    vote_counts: dict[str, int] = {}
    for v in votes:
        if v:
            vote_counts[v] = vote_counts.get(v, 0) + 1
    has_vote_split = len(set(v for v in votes if v)) > 1
    disagreements = []
    for out in outputs:
        text = (out.get("text") or "").lower()
        if any(w in text for w in _DISSENT_WORDS):
            disagreements.append({"role": out.get("role", "?"), "excerpt": (out.get("text") or "")[:120]})
    return {
        "has_disagreement": bool(disagreements) or has_vote_split,
        "disagreements": disagreements[:4],
        "vote_split": vote_counts,
    }


def cancel_agent(agent_id: str, *, note: str = "") -> dict:
    agent = get_agent_registry_entry(agent_id)
    if agent is None:
        raise RuntimeError(f"unknown agent: {agent_id}")
    if str(agent.get("status") or "") in {"completed", "cancelled", "expired"}:
        raise RuntimeError(f"agent already terminal: {agent.get('status')}")
    create_agent_message(
        message_id=f"agent-msg-{uuid4().hex}",
        thread_id=_agent_thread_id(agent_id),
        agent_id=agent_id,
        direction="runtime->agent",
        role="system",
        kind="lifecycle",
        content=f"Cancelled by Jarvis. {note}".strip(),
    )
    update_agent_registry_entry(agent_id, status="cancelled", completed_at=_now_iso(), last_error=note or "")
    return build_agent_detail_surface(agent_id) or {}


def suspend_agent(agent_id: str, *, note: str = "") -> dict:
    agent = get_agent_registry_entry(agent_id)
    if agent is None:
        raise RuntimeError(f"unknown agent: {agent_id}")
    create_agent_message(
        message_id=f"agent-msg-{uuid4().hex}",
        thread_id=_agent_thread_id(agent_id),
        agent_id=agent_id,
        direction="runtime->agent",
        role="system",
        kind="lifecycle",
        content=f"Suspended. {note}".strip(),
    )
    update_agent_registry_entry(agent_id, status="suspended", last_error=note or "")
    return build_agent_detail_surface(agent_id) or {}


def resume_agent(agent_id: str) -> dict:
    agent = get_agent_registry_entry(agent_id)
    if agent is None:
        raise RuntimeError(f"unknown agent: {agent_id}")
    if str(agent.get("status") or "") not in {"suspended", "failed", "waiting", "scheduled"}:
        raise RuntimeError(f"agent not resumable from status: {agent.get('status')}")
    create_agent_message(
        message_id=f"agent-msg-{uuid4().hex}",
        thread_id=_agent_thread_id(agent_id),
        agent_id=agent_id,
        direction="runtime->agent",
        role="system",
        kind="lifecycle",
        content="Resumed by Jarvis.",
    )
    update_agent_registry_entry(agent_id, status="queued", last_error="")
    return execute_agent_task(agent_id=agent_id)


def expire_agent(agent_id: str, *, reason: str = "") -> dict:
    agent = get_agent_registry_entry(agent_id)
    if agent is None:
        raise RuntimeError(f"unknown agent: {agent_id}")
    create_agent_message(
        message_id=f"agent-msg-{uuid4().hex}",
        thread_id=_agent_thread_id(agent_id),
        agent_id=agent_id,
        direction="runtime->agent",
        role="system",
        kind="lifecycle",
        content=f"Expired. {reason}".strip(),
    )
    update_agent_registry_entry(
        agent_id,
        status="expired",
        expired_at=_now_iso(),
        last_error=reason or "expired by runtime",
    )
    return build_agent_detail_surface(agent_id) or {}


def promote_agent_result(agent_id: str, *, note: str = "") -> dict:
    """File an autonomy proposal to promote the agent's latest result to Jarvis memory."""
    from core.services.autonomy_proposal_queue import file_proposal

    agent = get_agent_registry_entry(agent_id)
    if agent is None:
        raise RuntimeError(f"unknown agent: {agent_id}")
    messages = list_agent_messages(agent_id=agent_id, limit=20)
    results = [m for m in messages if m.get("kind") in {"result", "swarm-synthesis", "council-synthesis"}]
    if not results:
        raise RuntimeError("no result message found for this agent")
    content = str(results[-1].get("content") or "").strip()
    if not content:
        raise RuntimeError("agent result is empty")
    title = f"Promote agent finding: {agent.get('role', 'agent')} / {str(agent.get('goal') or '')[:60]}"
    proposal = file_proposal(
        kind="memory-rewrite",
        title=title,
        rationale=(
            f"Agent {agent_id} ({agent.get('role')}) completed with finding:\n"
            f"{content[:600]}\n\n{note}".strip()
        ),
        payload={
            "agent_id": agent_id,
            "role": agent.get("role"),
            "goal": agent.get("goal"),
            "content": content,
            "target": "MEMORY.md",
        },
        created_by=agent_id,
    )
    return {"status": "filed", "proposal_id": proposal.get("proposal_id"), "agent_id": agent_id}


def recover_crashed_agents() -> dict:
    """Called on API startup: reset agents that were mid-execution when the process died."""
    all_agents = list_agent_registry_entries(limit=500)
    crashed = [a for a in all_agents if str(a.get("status") or "") in {"starting", "active", "blocked"}]
    recovered_ids: list[str] = []
    requeued_ids: list[str] = []
    for agent in crashed:
        aid = str(agent.get("agent_id") or "")
        if not aid:
            continue
        create_agent_message(
            message_id=f"agent-msg-{uuid4().hex}",
            thread_id=_agent_thread_id(aid),
            agent_id=aid,
            direction="runtime->agent",
            role="system",
            kind="recovery",
            content=f"Runtime restarted while agent was in status '{agent.get('status')}'. Recovering.",
        )
        if bool(agent.get("persistent")):
            update_agent_registry_entry(aid, status="queued", last_error="recovered after restart")
            requeued_ids.append(aid)
        else:
            update_agent_registry_entry(
                aid,
                status="failed",
                last_error="process restarted while agent was active",
                completed_at=_now_iso(),
            )
            recovered_ids.append(aid)
    logger.info(
        "recover_crashed_agents: %d failed, %d requeued",
        len(recovered_ids), len(requeued_ids),
    )
    return {
        "recovered": len(recovered_ids) + len(requeued_ids),
        "failed": recovered_ids,
        "requeued": requeued_ids,
    }
