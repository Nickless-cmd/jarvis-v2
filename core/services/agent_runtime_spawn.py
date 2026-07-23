"""Agent runtime — spawn, execution, messaging, scheduling & lifecycle.

Split out of ``agent_runtime`` (behavior-preserving). Owns the single-agent
lifecycle: spawning, prompt-building, execution (including the guarded tool
loop hand-off), Jarvis<->agent and peer messaging, scheduling, stale-cleanup,
budget/retry enforcement, and terminal lifecycle transitions
(cancel/suspend/resume/expire/promote/recover).

Re-exported via ``core.services.agent_runtime`` for backward compatibility.
"""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.services.agent_runtime_base import (
    AGENT_ROLE_TEMPLATES,
    MAX_AGENT_TURNS,
    MAX_CONCURRENT_AGENTS,
    MAX_SPAWN_DEPTH,
    RETRY_BASE_SECONDS,
    _ACTIVE_STATUSES,
    _facade,
    _json_loads,
    _now_iso,
    _role_needs_tools,
    _run_agent_tool_loop,
    agent_tools_enabled,
    cheap_lane_status_surface,
    create_agent_message,
    create_agent_registry_entry,
    create_agent_run,
    create_agent_schedule,
    event_bus,
    get_agent_registry_entry,
    list_agent_messages,
    list_agent_registry_entries,
    list_agent_schedules,
    logger,
    update_agent_registry_entry,
    update_agent_run,
    update_agent_schedule,
)
from core.services.agent_runtime_surfaces import (
    build_agent_detail_surface,
    build_council_detail_surface,  # re-export convenience (council callers)
)


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


_WATCHER_RELAY_KEYWORDS = frozenset({
    "found", "changed", "alert", "detected", "important", "critical",
    "urgent", "noticed", "update", "warning", "significant", "new",
})


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
    max_turns: int = 0,
    context: dict[str, object] | None = None,
    result_contract: dict[str, object] | None = None,
    execution_mode: str = "solo-task",
    auto_execute: bool = True,
    council_id: str = "",
    provider: str = "",
    model: str = "",
) -> dict[str, object]:
    _check_spawn_limits()
    if max_turns <= 0:
        max_turns = MAX_AGENT_TURNS
    spawn_depth = _spawn_depth_for(str(parent_agent_id or ""))
    if spawn_depth > MAX_SPAWN_DEPTH:
        raise ValueError(
            f"spawn depth limit reached: {spawn_depth}/{MAX_SPAWN_DEPTH} — recursion chain too deep"
        )
    allowed_tools = allowed_tools or []
    # Fase 2 Task 3: strictest-mode inheritance — never-escalate ceiling. A
    # child agent's effective tool allowlist is the requested tools
    # intersected with the parent's own allowlist, so a child can never gain
    # a tool its parent lacks. The root parent ("jarvis") has no ceiling
    # (full catalog) — everything else spawns FROM some existing agent whose
    # own allowlist already bounds it.
    if str(parent_agent_id or "jarvis") != "jarvis":
        parent_entry = get_agent_registry_entry(str(parent_agent_id))
        parent_allowed = None
        if parent_entry is not None:
            parent_allowed = _json_loads(str(parent_entry.get("allowed_tools_json") or "[]"), [])
        if isinstance(parent_allowed, list) and parent_allowed:
            allowed_tools = [t for t in allowed_tools if t in set(parent_allowed)]
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
    # Layer 2 (Scout Memory): inject role's learned skills.md if present
    try:
        from core.services.agent_skill_library import get_skills
        skills_info = get_skills(role)
        if skills_info.get("exists") and skills_info.get("content"):
            skills_text = str(skills_info["content"])[:3000]
            system_prompt = (
                f"{system_prompt}\n\n"
                "## Lærte mønstre (cross-session skills.md)\n"
                f"{skills_text}\n"
                "Brug `append_skill_observation` ved completion hvis du opdager "
                "et nyt mønster der er værd at huske."
            )
    except Exception:
        pass

    # Layer 3 (Scout Memory): inject relevant cross-agent observations
    try:
        from core.services.cross_agent_memory import cross_agent_recall_section
        cross_agent_text = cross_agent_recall_section(role=role, query=goal)
        if cross_agent_text:
            system_prompt = (
                f"{system_prompt}\n\n{cross_agent_text}\n"
                "Disse observationer kommer fra andre agenter der har arbejdet med "
                "lignende emner. Brug dem som baggrund — verificér selv før du regner med dem."
            )
    except Exception:
        pass
    if not provider or not model:
        # Task-aware routing: classify goal → tier, look up role's tier-specific
        # provider/model from council_models.json. Falls through to flat
        # role-default if config has no tiers, or to cheap_lane defaults
        # below if no role match.
        try:
            from core.services.role_model_resolver import resolve_role_model
            resolved = resolve_role_model(role=role, goal=goal)
            provider = str(provider or resolved.get("provider") or "")
            model = str(model or resolved.get("model") or "")
        except Exception:
            pass
    if not provider or not model:
        # Fallback: cheap_lane current default.
        selected = cheap_lane_status_surface().get("selected_target") or {}
        provider = str(provider or selected.get("provider") or "")
        model = str(model or selected.get("model") or "")
    agent_id = f"agent-{uuid4().hex}"
    thread_id = f"agent-thread-{uuid4().hex}"
    # Agents-cluster: agent-spawn synligt i Centralen (pool/swarm/council). Self-safe.
    try:
        from core.services.agents import note_agent_spawn
        note_agent_spawn(agent_id, role, parent=str(parent_agent_id or ""),
                         council_id=str(council_id or ""), mode=str(execution_mode or ""))
    except Exception:
        pass
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
        max_turns=max_turns,
        context_json=json.dumps(context),
        result_contract_json=json.dumps(result_contract),
    )
    # Per-agent transcript: metadata sidecar + lifecycle event + sidechain
    try:
        from core.services.agent_transcript import write_meta, write_lifecycle, write_sidechain
        write_meta(agent_id, {
            "agent_id": agent_id,
            "role": role,
            "goal": goal,
            "parent_agent_id": parent_agent_id,
            "provider": provider,
            "model": model,
            "tool_policy": tool_policy,
            "allowed_tools": allowed_tools,
            "persistent": persistent,
            "ttl_seconds": ttl_seconds,
            "max_turns": max_turns,
            "execution_mode": execution_mode,
        })
        write_lifecycle(agent_id, "spawned", note=f"role={role}")
        write_sidechain(agent_id, role, goal)
    except Exception:
        pass  # transcript er non-critical
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
            # Budget-strangle-fix (2026-07-23, Bjørn "A"): default var 1500 tokens
            # cap 4000 → agenten brændte budgettet på et par tool-kald og nåede
            # ALDRIG at skrive et afsluttende svar → "completed" men tomt last_reply.
            # 0 = ubegrænset (kun max_turns=20 som sikkerhedsnet, jf.
            # _check_budget_and_expire). Kør til opgaven er løst, som Claudes egne
            # agenter — respektér kun et EKSPLICIT budget hvis kalderen sætter et.
            budget = int(spec.get("budget_tokens") or 0)
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
{"spawn_agent": {"role": "<researcher|planner|critic|synthesizer|executor>", "goal": "<specific, self-contained goal>"}}

The spawned agent runs to completion (bounded by a turn limit) and returns its written result to Jarvis — you do NOT need to set a token budget; omit it and let the agent finish its work. Give it a sharp, self-contained goal with enough context to act without you. Use sparingly — only when the subtask genuinely benefits from isolation.
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
    # maxTurns check: skip execution if agent has exhausted its turn budget
    max_turns = int(agent.get("max_turns") or 0)
    turns_completed = int(agent.get("turns_completed") or 0)
    if max_turns > 0 and turns_completed >= max_turns:
        update_agent_registry_entry(
            agent_id,
            status="completed",
            completed_at=_now_iso(),
        )
        surface = build_agent_detail_surface(agent_id) or {"agent_id": agent_id}
        surface["status"] = "completed"
        surface["note"] = f"max_turns exhausted: {turns_completed}/{max_turns}"
        return surface
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
    # Per-agent transcript: log prompt before model call
    try:
        from core.services.agent_transcript import write_prompt, write_lifecycle
        write_prompt(agent_id, prompt, run_id=run_id)
        write_lifecycle(agent_id, "started", note=f"run_id={run_id}")
    except Exception:
        pass
    result: dict[str, object] = {}  # A4: readable on the failure seam too
    _t0 = time.monotonic()
    _result_noted = False  # agent_result skal fyre PRÆCIS én gang pr. dispatch
    try:
        update_agent_registry_entry(agent_id, status="active")
        _needs_tools = _role_needs_tools(str(agent.get("role") or ""))
        # Axis 3: give the agent hands only when the reversible flag is ON.
        # OFF (default) → unchanged text-only path. Self-safe: any failure in
        # the tool-loop dispatch degrades to the legacy call.
        if agent_tools_enabled():
            try:
                result = _run_agent_tool_loop(
                    agent=agent, prompt=prompt, requires_tools=_needs_tools,
                )
            except Exception:
                result = _facade().execute_with_role_or_fallback(
                    message=prompt,
                    provider=str(agent.get("provider") or ""),
                    model=str(agent.get("model") or ""),
                    requires_tools=_needs_tools,
                    lane="agent",
                )
        else:
            result = _facade().execute_with_role_or_fallback(
                message=prompt,
                provider=str(agent.get("provider") or ""),
                model=str(agent.get("model") or ""),
                requires_tools=_needs_tools,
                lane="agent",
            )
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
        # Per-agent transcript: log result
        try:
            from core.services.agent_transcript import write_result
            write_result(agent_id, text, run_id=run_id,
                         input_tokens=input_tokens, output_tokens=output_tokens,
                         cost_usd=float(result.get("cost_usd") or 0.0))
        except Exception:
            pass
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
        # Agents-cluster: dispatch-udfald SYNLIGT i Centralen (robusthedskonvolut +
        # envelope-tidsserier). Self-safe — kaster aldrig ind i dispatch-stien.
        _dispatch_status = str(result.get("status") or "completed")
        try:
            from core.services.agents import note_agent_blocked, note_agent_result
            note_agent_result(
                agent_id, _dispatch_status,
                tokens_in=input_tokens, tokens_out=output_tokens,
                cost_usd=float(result.get("cost_usd") or 0.0),
                duration_ms=int((time.monotonic() - _t0) * 1000),
                tool_calls=int(result.get("tool_calls") or 0),
                role=str(agent.get("role") or ""), run_id=str(run_id or ""),
                provider=str(agent.get("provider") or ""),
                model=str(agent.get("model") or ""),
            )
            _result_noted = True
            if _dispatch_status in ("blocked", "needs_context"):
                note_agent_blocked(
                    agent_id, _dispatch_status,
                    reason=str(result.get("text") or "")[:160],
                    role=str(agent.get("role") or ""),
                )
        except Exception:
            pass
        tokens_used = input_tokens + output_tokens
        # A4b: cost is now logged at the execution chokepoint
        # (execute_with_role_or_fallback / execute_cheap_lane_via_pool) with
        # lane="agent" threaded through — NOT here at the dispatch seam. Logging
        # here as well double-counted every dispatch that fell back to the pool
        # (lane="agent" + lane="cheap" for the same tokens). Seam log removed.
        update_agent_registry_entry(
            agent_id,
            status="scheduled" if bool(agent.get("persistent")) and str(agent.get("next_wake_at") or "") else "completed",
            tokens_burned_delta=tokens_used,
            turns_completed_delta=1,
            completed_at=_now_iso(),
        )
        # Budget enforcement: expire if over token budget
        _check_budget_and_expire(agent_id, tokens_used=tokens_used)
        # maxTurns enforcement: expire if turn limit reached
        _check_max_turns_and_expire(agent_id)
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
        # Per-agent transcript: log completion
        try:
            from core.services.agent_transcript import write_lifecycle
            write_lifecycle(agent_id, "completed", note=f"tokens={input_tokens + output_tokens}")
        except Exception:
            pass
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
        # Per-agent transcript: log failure
        try:
            from core.services.agent_transcript import write_failure, write_lifecycle
            write_failure(agent_id, message, run_id=run_id)
            write_lifecycle(agent_id, "failed", note=message[:200])
        except Exception:
            pass
        update_agent_run(
            run_id,
            status="failed",
            finished_at=_now_iso(),
            failure_reason=message,
            provider_status="failed",
        )
        # A4b: no cost log at the dispatch seam — the execution chokepoint owns
        # cost logging now (lane threaded). On a failure that reached a provider,
        # the pool/primary-direct site already logged; a failure before any model
        # call has no usage to log. Removed to kill the agent→pool double-count.
        update_agent_registry_entry(
            agent_id,
            status="failed",
            failure_increment=1,
            last_error=message,
        )
        # Agents-cluster: agent-fejl SYNLIG i Centralen (var blind — note_agent_error
        # var defineret men aldrig kaldt, så ALLE spawn/exec-fejl smuttede forbi). Self-safe.
        try:
            from core.services.agents import note_agent_error
            note_agent_error(agent_id, exc, run_id=str(run_id or ""))
        except Exception:
            pass
        # Agents-cluster: dispatch-udfald (fejl-stien) — agent_result skal fyre PRÆCIS
        # én gang pr. dispatch. _result_noted-vagten forhindrer dobbelt-fyring hvis
        # succes-stien nåede at note men senere efterbehandling kastede. Self-safe.
        if not _result_noted:
            try:
                from core.services.agents import note_agent_result
                note_agent_result(
                    agent_id, "failed",
                    tokens_in=int(result.get("input_tokens") or 0),
                    tokens_out=int(result.get("output_tokens") or 0),
                    cost_usd=float(result.get("cost_usd") or 0.0),
                    duration_ms=int((time.monotonic() - _t0) * 1000),
                    tool_calls=int(result.get("tool_calls") or 0),
                    role=str(agent.get("role") or ""), run_id=str(run_id or ""),
                    provider=str(agent.get("provider") or ""),
                    model=str(agent.get("model") or ""),
                    error=message[:160],
                )
                _result_noted = True
            except Exception:
                pass
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


def _council_thread_id(council_id: str) -> str:
    return f"council-thread-{council_id}"


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
    active_timeout_minutes: int = 90,
    starting_timeout_minutes: int = 15,
    blocked_timeout_minutes: int = 120,
    max_per_run: int = 20,
) -> dict[str, object]:
    """Auto-cancel agents hanging in non-terminal states for too long.

    Rules:
    - status='waiting'  + updated_at < now - waiting_timeout_minutes  → cancelled
    - status='failed'   + updated_at < now - failed_timeout_minutes   → cancelled
    - status='active'   + updated_at < now - active_timeout_minutes   → cancelled
    - status='starting' + updated_at < now - starting_timeout_minutes → cancelled
    - status='blocked'  + updated_at < now - blocked_timeout_minutes  → cancelled

    The original implementation only handled waiting/failed; an agent that
    crashed silently mid-execution (LLM hang, thread death, etc.) would
    sit in 'active' forever and count toward MAX_CONCURRENT_AGENTS, eating
    a slot until process restart. 2026-04-29: extended to cover the three
    other non-terminal states with conservative timeouts so genuinely
    long-running work isn't killed.

    Defaults:
        active=90min   — long enough for legit multi-step work, short
                         enough to free slots when an agent has truly hung
        starting=15min — a real agent should leave 'starting' fast; if
                         it's stuck here it's almost certainly broken
        blocked=120min — same as waiting; might be holding for human
                         approval or external resource

    Cancelled agents get last_error='auto_cleanup_stale_{state}' +
    status='cancelled'. Fire-and-forget safe.

    Returns dict with cancelled counts + lists of cancelled agent_ids.
    """
    now = datetime.now(UTC)
    waiting_cutoff = now - timedelta(minutes=max(1, int(waiting_timeout_minutes)))
    failed_cutoff = now - timedelta(minutes=max(1, int(failed_timeout_minutes)))
    active_cutoff = now - timedelta(minutes=max(1, int(active_timeout_minutes)))
    starting_cutoff = now - timedelta(minutes=max(1, int(starting_timeout_minutes)))
    blocked_cutoff = now - timedelta(minutes=max(1, int(blocked_timeout_minutes)))
    now_iso = _now_iso()

    cancelled_waiting: list[str] = []
    cancelled_failed: list[str] = []
    cancelled_active: list[str] = []
    cancelled_starting: list[str] = []
    cancelled_blocked: list[str] = []
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

    # Process active/starting/blocked agents — silent-crash recovery
    for state, cutoff, sink in (
        ("active", active_cutoff, cancelled_active),
        ("starting", starting_cutoff, cancelled_starting),
        ("blocked", blocked_cutoff, cancelled_blocked),
    ):
        try:
            agents = list_agent_registry_entries(status=state, limit=int(max_per_run))
        except Exception as exc:
            errors.append(f"list_{state}_failed: {exc}")
            continue
        for agent in agents:
            agent_id = str(agent.get("agent_id") or "")
            if not agent_id:
                continue
            updated = _parse_ts(agent.get("updated_at"))
            if updated is None or updated > cutoff:
                continue
            age_minutes = int((now - updated).total_seconds() / 60)
            try:
                update_agent_registry_entry(
                    agent_id,
                    status="cancelled",
                    last_error=f"auto_cleanup_stale_{state}_after_{age_minutes}min",
                    completed_at=now_iso,
                )
                sink.append(agent_id)
                try:
                    event_bus.publish("runtime.agent_auto_cancelled", {
                        "agent_id": agent_id,
                        "reason": f"stale_{state}",
                        "age_minutes": age_minutes,
                    })
                except Exception:
                    pass
            except Exception as exc:
                errors.append(f"{agent_id}:{exc}")

    return {
        "cancelled_waiting_count": len(cancelled_waiting),
        "cancelled_failed_count": len(cancelled_failed),
        "cancelled_active_count": len(cancelled_active),
        "cancelled_starting_count": len(cancelled_starting),
        "cancelled_blocked_count": len(cancelled_blocked),
        "cancelled_waiting_ids": cancelled_waiting,
        "cancelled_failed_ids": cancelled_failed,
        "cancelled_active_ids": cancelled_active,
        "cancelled_starting_ids": cancelled_starting,
        "cancelled_blocked_ids": cancelled_blocked,
        "errors": errors,
        "thresholds": {
            "waiting_timeout_minutes": int(waiting_timeout_minutes),
            "failed_timeout_minutes": int(failed_timeout_minutes),
            "active_timeout_minutes": int(active_timeout_minutes),
            "starting_timeout_minutes": int(starting_timeout_minutes),
            "blocked_timeout_minutes": int(blocked_timeout_minutes),
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


# ── Phase 4+5: lifecycle, limits, budget, retry, promotion, recovery ──


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


def _check_max_turns_and_expire(agent_id: str) -> bool:
    """Expire agent if it has reached its max_turns limit. Returns True if expired."""
    agent = get_agent_registry_entry(agent_id)
    if agent is None:
        return False
    max_turns = int(agent.get("max_turns") or 0)
    if max_turns <= 0:
        return False
    completed = int(agent.get("turns_completed") or 0)
    if completed >= max_turns:
        update_agent_registry_entry(
            agent_id,
            status="expired",
            expired_at=_now_iso(),
            last_error=f"max_turns reached: {completed}/{max_turns}",
        )
        create_agent_message(
            message_id=f"agent-msg-{uuid4().hex}",
            thread_id=_agent_thread_id(agent_id),
            agent_id=agent_id,
            direction="runtime->agent",
            role="system",
            kind="max-turns-reached",
            content=f"Agent expired: max turns reached ({completed}/{max_turns})",
        )
        logger.info("agent %s expired: max_turns %d/%d", agent_id, completed, max_turns)
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
