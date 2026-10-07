"""Modelvendte agent-vaerktoejer over agent-contract-v1 (leverance F2).

Spec: docs/specs/2026-10-07-agentorkestrering-og-subagenter.md (5, 5.1, 7.3).

Tynde adaptere: ingen egen livscyklus, ingen skjult semantisk beslutning. Ejeren
tages fra den AUTENTIFICEREDE kontekst (`current_user_id`), aldrig fra et argument
modellen selv kan skrive; session og parent-run kommer fra runtimens injicerede
`_runtime_*`-felter. Vaerktoejerne annonceres kun naar kapabiliteten er taendt
(`approval_rollout_gate.may_advertise`), og er da fast i Jarvis' vaerktoejsflade.

`send_message_to_agent` og `list_agents` findes i forvejen med aeldre semantik:
her er kontrakt-bevidste udgaver, der falder tilbage til den gamle for agenter der ikke
er bundet til kontrakten (legacy_unscoped) eller naar kapabiliteten er slukket.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

#: De navne der er fast i Jarvis' standardflade naar motoren er aktiv (spec'ens syv + integration, F4d).
CONTRACT_TOOL_NAMES: tuple[str, ...] = (
    "dispatch_agent", "send_message_to_agent", "followup_agent", "list_agents",
    "wait_agents", "interrupt_agent", "close_agent", "integrate_agent_work",
)
#: Dem der KUN findes med kontrakten (de to andre har en aeldre udgave).
_NEW_ONLY: frozenset[str] = frozenset(
    {"dispatch_agent", "followup_agent", "wait_agents", "interrupt_agent", "close_agent",
     "integrate_agent_work"})


def _fn(name: str, description: str, properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {"type": "function", "function": {
        "name": name, "description": description,
        "parameters": {"type": "object", "properties": properties, "required": required}}}


_ID = {"type": "string", "description": "agent_id returned by dispatch_agent."}
_KEY = {"type": "string", "description": "Optional idempotency key: the same key with the same "
                                          "arguments returns the same accepted result."}

AGENT_CONTRACT_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    _fn("dispatch_agent",
        "Hand a bounded, independently checkable piece of work to a new agent and get its ids "
        "back immediately. The agent works in the background; acceptance is NOT a result. "
        "Use it when a sub-task can run in parallel, needs separate focus or large sources, "
        "benefits from an independent reviewer, or must be monitored over time. Do not use it "
        "for a short step you can finish directly.",
        {"goal": {"type": "string", "description": "The task, stated so it can be verified."},
         "description": {"type": "string", "description": "Short context for the agent."},
         "role": {"type": "string", "description": "researcher, critic, planner, executor, watcher ..."},
         "expected_result": {"type": "string", "description": "What a usable answer contains."},
         "tool_policy": {"type": "string", "description": "e.g. read-only-runtime. Omit for the role default."},
         "target": {"type": "string",
                    "description": "Where tools run: 'runtime-container' (default) or 'client:<stable_client_id>' "
                    "for ONE named connected client (operator_* tools only). The agent never falls back to "
                    "the container or to another client if that client disconnects."},
         "budget_tokens": {"type": "integer", "description": "Token budget; 0 = role default."},
         "max_turns": {"type": "integer", "description": "Tool/model step limit; 0 = default."},
         "model": {"type": "string", "description": "Optional model preference (provider/model). "
                   "The runtime validates it against the owner's allowed routes; it cannot unlock a "
                   "provider the owner may not use."},
         "model_required": {"type": "boolean", "description": "Treat `model` as a hard requirement: "
                            "the dispatch fails with MODEL_UNAVAILABLE instead of using another model."},
         "writes": {"type": "boolean", "description": "Code agent: it gets its OWN git worktree of `workspace` "
                    "and can write only there (sandboxed). The result is a diff; nothing is merged."},
         "workspace": {"type": "string", "description": "Repository path (required when writes is true)."},
         "idempotency_key": _KEY},
        ["goal"]),
    _fn("followup_agent",
        "Give an existing agent a NEW task (new assignment and run, same agent_id). Not allowed "
        "while it still has an active task or after close_agent.",
        {"agent_id": _ID, "goal": {"type": "string"},
         "expected_result": {"type": "string"}, "budget_tokens": {"type": "integer"},
         "idempotency_key": _KEY},
        ["agent_id", "goal"]),
    _fn("wait_agents",
        "Wait for agent assignments. With timeout_seconds (max 120) it blocks briefly. If still "
        "unmet and wake_if_run_ends is true, a wait contract is registered so a new run is "
        "started in this session when the condition is met. Use only when your NEXT step "
        "depends on the result; results otherwise arrive in your inbox on their own.",
        {"assignment_ids": {"type": "array", "items": {"type": "string"}},
         "condition": {"type": "string", "enum": ["first_terminal", "all_terminal"]},
         "timeout_seconds": {"type": "number"}, "wake_if_run_ends": {"type": "boolean"},
         "include_output": {"type": "boolean",
                            "description": "Include each finished agent's full output (paged, 20000 chars)."},
         "output_offset": {"type": "integer", "description": "Character offset for paged output."}},
        ["assignment_ids"]),
    _fn("interrupt_agent",
        "Request a stop of an agent's current task. Returns stop_requested; it is cancelled "
        "only once confirmed.",
        {"agent_id": _ID, "note": {"type": "string"}}, ["agent_id"]),
    _fn("close_agent",
        "Gracefully close an agent identity: no new tasks; accepted work finishes.",
        {"agent_id": _ID}, ["agent_id"]),
    _fn("integrate_agent_work",
        "Ask for a code agent's finished work to be integrated. This ONLY creates an approval request bound to the "
        "exact diff; you can NOT approve it - a human decides in Desk. On approval the work is merged onto a NEW "
        "branch (integrate/<assignment>); no one's working tree is touched and the main branch is never moved.",
        {"assignment_id": {"type": "string", "description": "The assignment_id of the finished code agent."}},
        ["assignment_id"]),
]


def contract_tool_names_advertised() -> tuple[str, ...]:
    """De navne der skal fastnaeles i Jarvis' flade - tom naar kapabiliteten er slukket."""
    try:
        from core.services.agent_contract_service import capability_enabled
        return CONTRACT_TOOL_NAMES if capability_enabled() else ()
    except Exception:
        logger.warning("kunne ikke afgoere agent-kapabilitet - ingen faste agent-vaerktoejer",
                       exc_info=True)
        return ()


def hidden_contract_tools() -> frozenset[str]:
    """De rene kontrakt-vaerktoejer der SKAL skjules lige nu: alle naar motoren er slukket
    (fail-closed - kan kapabiliteten ikke laeses, er de skjult). Bruges af tool_scoping."""
    return frozenset() if contract_tool_names_advertised() else _NEW_ONLY


# --- adaptere ----------------------------------------------------------------------

def _principal(args: dict[str, Any]) -> tuple[str, str, str]:
    """(ejer, session, parent-run). Ejeren er den autentificerede kontekst - IKKE et argument."""
    try:
        from core.identity.workspace_context import current_user_id
        owner = str(current_user_id() or "").strip()
    except Exception:
        owner = ""
    return (owner, str(args.get("_runtime_session_id") or "").strip(),
            str(args.get("_runtime_turn_id") or "").strip())


def _svc():
    from core.services import agent_contract_service
    return agent_contract_service


def _exec_dispatch_agent(args: dict[str, Any]) -> dict[str, Any]:
    owner, session, run = _principal(args)
    return _svc().dispatch_agent(
        owner_user_id=owner, origin_session_id=session, parent_run_id=run,
        goal=str(args.get("goal") or ""), description=str(args.get("description") or ""),
        role=str(args.get("role") or "researcher") or "researcher",
        expected_result=str(args.get("expected_result") or ""),
        tool_policy=str(args.get("tool_policy") or ""),
        target=str(args.get("target") or "runtime-container"),
        budget_tokens=max(0, int(args.get("budget_tokens") or 0)),
        max_turns=max(0, int(args.get("max_turns") or 0)),
        model=str(args.get("model") or ""), idempotency_key=str(args.get("idempotency_key") or ""),
        writes=bool(args.get("writes")), workspace=str(args.get("workspace") or ""),
        model_required=bool(args.get("model_required")))


def _exec_followup_agent(args: dict[str, Any]) -> dict[str, Any]:
    owner, session, run = _principal(args)
    return _svc().followup_agent(
        owner_user_id=owner, origin_session_id=session, parent_run_id=run,
        agent_id=str(args.get("agent_id") or "").strip(), goal=str(args.get("goal") or ""),
        expected_result=str(args.get("expected_result") or ""),
        budget_tokens=max(0, int(args.get("budget_tokens") or 0)),
        idempotency_key=str(args.get("idempotency_key") or ""))


def _exec_wait_agents(args: dict[str, Any]) -> dict[str, Any]:
    owner, session, run = _principal(args)
    ids = args.get("assignment_ids")
    return _svc().wait_agents(
        owner_user_id=owner, origin_session_id=session, parent_run_id=run,
        assignment_ids=[str(x) for x in ids] if isinstance(ids, list) else [],
        condition=str(args.get("condition") or "all_terminal"),
        timeout_seconds=float(args.get("timeout_seconds") or 0),
        wake_if_run_ends=bool(args.get("wake_if_run_ends")),
        include_output=bool(args.get("include_output")),
        output_offset=max(0, int(args.get("output_offset") or 0)))


def _exec_interrupt_agent(args: dict[str, Any]) -> dict[str, Any]:
    owner, session, _ = _principal(args)
    return _svc().interrupt_agent(owner_user_id=owner, origin_session_id=session,
                                  agent_id=str(args.get("agent_id") or "").strip(),
                                  note=str(args.get("note") or ""))


def _exec_close_agent(args: dict[str, Any]) -> dict[str, Any]:
    owner, session, _ = _principal(args)
    return _svc().close_agent(owner_user_id=owner, origin_session_id=session,
                              agent_id=str(args.get("agent_id") or "").strip())


def _is_contract_bound(agent_id: str, owner: str) -> bool:
    try:
        return bool(owner) and _svc()._owned_agent(agent_id, owner) is not None
    except Exception:
        logger.warning("kunne ikke afgoere om %s er kontrakt-bundet", agent_id, exc_info=True)
        return False


def _exec_send_message_to_agent(args: dict[str, Any]) -> dict[str, Any]:
    """Kontrakt-udgaven for bundne agenter; den gamle (inline) for resten."""
    from core.tools.simple_tools_native import _exec_send_message_to_agent as legacy
    owner, session, run = _principal(args)
    agent_id = str(args.get("agent_id") or "").strip()
    if not (_svc().capability_enabled() and _is_contract_bound(agent_id, owner)):
        return legacy(args)
    return _svc().send_message(owner_user_id=owner, origin_session_id=session,
                               agent_id=agent_id, content=str(args.get("content") or ""),
                               parent_run_id=run)


def _exec_list_agents(args: dict[str, Any]) -> dict[str, Any]:
    """Naar motoren er taendt: ejerens kontrakt-agenter (+ de gamle under `legacy`)."""
    from core.tools.simple_tools_native import _exec_list_agents as legacy
    owner, session, _ = _principal(args)
    if not (_svc().capability_enabled() and owner):
        return legacy(args)
    out = _svc().list_agents(owner_user_id=owner, status=str(args.get("status_filter") or ""))
    old = legacy(args)
    if isinstance(old, dict) and old.get("status") == "ok":
        out["legacy_agents"] = old.get("agents", [])
    return out


def _exec_integrate_agent_work(args: dict[str, Any]) -> dict[str, Any]:
    owner, session, _ = _principal(args)
    return _svc().request_integration(owner_user_id=owner, origin_session_id=session,
                                      assignment_id=str(args.get("assignment_id") or "").strip())
