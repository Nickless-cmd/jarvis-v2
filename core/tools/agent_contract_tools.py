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
    "Task", "send_message_to_agent", "followup_agent", "list_agents",
    "wait_agents", "interrupt_agent", "close_agent", "integrate_agent_work",
    "convene_agent_council", "review_agent_work", "decide_agent_approval",
)
#: Dem der KUN findes med kontrakten (de to andre har en aeldre udgave).
#:
#: Reglen er UDLEDT, ikke talt: et navn i den fastgjorte flade skjules hvis det ikke har
#: sin egen definition uden for ``AGENT_CONTRACT_TOOL_DEFINITIONS``.
#: ``decide_agent_approval`` manglede her indtil 16/10-2026. Den er kontrakt-KUN — ingen
#: legacy-udgave — men stod synlig naar motoren var slukket, altsaa i den tilstand flaget
#: selv starter i (§12.4, fail-closed). Det er den ENE kontrakt-vaerktoej hvis formaal er
#: at fjerne et menneske fra godkendelses-loopet; den hoerer ikke i den tilstand.
#: ``test_contract_only_tools_are_the_hidden_set`` udleder reglen og fanger naeste.
_NEW_ONLY: frozenset[str] = frozenset(
    {"Task", "followup_agent", "wait_agents", "interrupt_agent", "close_agent",
     "integrate_agent_work", "convene_agent_council", "review_agent_work",
     "decide_agent_approval"})


def _fn(name: str, description: str, properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {"type": "function", "function": {
        "name": name, "description": description,
        "parameters": {"type": "object", "properties": properties, "required": required}}}


_ID = {"type": "string", "description": "agent_id returned by Task."}
_KEY = {"type": "string", "description": "Optional idempotency key: the same key with the same "
                                          "arguments returns the same accepted result."}

AGENT_CONTRACT_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    _fn("Task",
        "Delegate one bounded task. Runtime derives owner, parent, mandate, tools, target, "
        "workspace/sandbox, limits, idempotency, delivery contract and return address. The "
        "agent works freely inside that mechanical mandate. Use a writing subagent_type only "
        "for repository work; owner chat sessions use Jarvis' server repository when no "
        "explicit workspace is selected.",
        {"description": {"type": "string",
                         "description": "Short description of the usable deliverable."},
         "prompt": {"type": "string", "description": "Complete task instructions."},
         "subagent_type": {"type": "string",
                           "enum": ["researcher", "critic", "planner", "watcher", "executor"]},
         "model": {"type": "string",
                   "description": "Optional model preference; runtime validates allowed routes."},
         "run_in_background": {"type": "boolean",
                               "description": "True returns after acceptance; false waits up to 120 seconds."}},
        ["description", "prompt", "subagent_type"]),
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
    _fn("convene_agent_council",
        "Convene a council: one independent agent per member (each with its OWN assessment task but the SAME facts, "
        "in separate contexts) plus a synthesis that is created automatically when every member has finished. "
        "All-or-nothing: if there is no room for every member nothing is started. A member that fails counts as "
        "finished and the synthesis must name it. You are woken when the synthesis is ready - do not poll.",
        {"topic": {"type": "string", "description": "What the council decides or assesses."},
         "facts": {"type": "string", "description": "The shared factual basis every member gets."},
         "members": {"type": "array", "description": "2-6 members with DIFFERENT tasks.",
                     "items": {"type": "object", "properties": {
                         "role": {"type": "string", "description": "e.g. critic, planner, researcher, devils_advocate"},
                         "task": {"type": "string", "description": "This member's own assessment task."}},
                         "required": ["role", "task"]}},
         "budget_tokens": {"type": "integer", "description": "Token budget per member; 0 = role default."},
         "idempotency_key": _KEY},
        ["topic", "members"]),
    _fn("review_agent_work",
        "Start an independent, read-only reviewer for a FINISHED builder assignment. The reviewer gets your "
        "requirements, the builder's actual changes (diff, changed files) and artifacts - the builder's own "
        "conclusion is included only as a claim to verify. Do not treat the builder's word as the review.",
        {"builder_assignment_id": {"type": "string", "description": "The finished builder's assignment_id."},
         "requirements": {"type": "string", "description": "What the work must satisfy, verifiably."},
         "budget_tokens": {"type": "integer", "description": "Token budget; 0 = role default."},
         "idempotency_key": _KEY},
        ["builder_assignment_id", "requirements"]),
    _fn("decide_agent_approval",
        "Decide a tool-approval for an agent YOU started - no human in the loop. This is your own "
        "delegation, not your own action: you may approve an agent's OWN tool call, but NEVER an "
        "integration (a change to the house's code) and never an agent someone else started. Those "
        "still go to the human. The human's gate for YOUR OWN actions is unchanged.",
        {"approval_id": {"type": "string", "description": "The approval_id from your inbox."},
         "decision": {"type": "string", "enum": ["approve", "deny"]},
         "digest": {"type": "string",
                    "description": "The args_digest from the approval card - it binds the decision to "
                    "exactly this call; if the arguments changed, a new approval is required."},
         "note": {"type": "string", "description": "Optional reason, recorded in the audit trail."}},
        ["approval_id", "decision", "digest"]),
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
    # In a child worker there is no HTTP user context. The lease scope proves
    # which assignment is executing; model-supplied _runtime_* fields alone do
    # not. The worker stamps these values from the DB before executing a tool.
    scoped = _scoped_parent(args)
    if scoped:
        owner = scoped[1]
        return (owner, scoped[2], scoped[3])
    return (owner, str(args.get("_runtime_session_id") or "").strip(),
            str(args.get("_runtime_turn_id") or "").strip())


def _scoped_parent(args: dict[str, Any]) -> tuple[str, str, str, str] | None:
    """Return (agent, owner, session, run) for the current fenced child run."""
    from core.runtime.db_agent_lease import current_assignment_id
    assignment_id = current_assignment_id()
    agent_id = str(args.get("_runtime_agent_id") or "").strip()
    if not assignment_id or not agent_id:
        return None
    from core.runtime.db_agent_contract import _conn
    row = _conn().execute(
        "SELECT agent_id, owner_user_id, origin_session_id FROM agent_assignments "
        "WHERE assignment_id=? AND agent_id=?", (assignment_id, agent_id)).fetchone()
    if row is None:
        return None
    run = _conn().execute(
        "SELECT run_id FROM agent_runs WHERE assignment_id=? "
        "ORDER BY attempt_no DESC, created_at DESC LIMIT 1", (assignment_id,)).fetchone()
    if run is None:
        return None
    return (str(row["agent_id"]), str(row["owner_user_id"]),
            str(row["origin_session_id"]), str(run["run_id"]))


def _svc():
    from core.services import agent_contract_service
    return agent_contract_service


def _exec_dispatch_agent(args: dict[str, Any]) -> dict[str, Any]:
    owner, session, run = _principal(args)
    scoped = _scoped_parent(args)
    # 26/10-2026: `writes` og `tool_policy` er ikke laengere felter i skemaet.
    # En repo-sti ER en kodeagent — det er den ene beslutning, ikke to.
    workspace = str(args.get("workspace") or "")
    writes = bool(workspace)
    # Skemaet tilbyder ikke tool_policy laengere, men legacy-adapteren kan sende
    # den — og en repo-sti vinder altid, fordi det ER en kodeagent.
    tool_policy = "worktree-write" if writes else str(args.get("tool_policy") or "")
    # Legacy-adapteren (spawn_agent_task) sender ikke expected_result. Uden et
    # resultatkrav rapporterer agenten sin proces i stedet for sit fund — maalt
    # 26/10-2026: "Mange kandidater. Laes kerne." Falder vi tilbage til goal,
    # har agenten altid et krav om at LEVERE, ikke om at proeve.
    expected_result = str(args.get("expected_result") or "") or str(args.get("goal") or "")
    return _svc().dispatch_agent(
        owner_user_id=owner, origin_session_id=session, parent_run_id=run,
        parent_agent_id=scoped[0] if scoped else "jarvis",
        goal=str(args.get("goal") or ""), description=str(args.get("description") or ""),
        role=str(args.get("role") or "researcher") or "researcher",
        expected_result=expected_result,
        tool_policy=tool_policy,
        target=str(args.get("target") or "runtime-container"),
        budget_tokens=max(0, int(args.get("budget_tokens") or 0)),
        max_turns=max(0, int(args.get("max_turns") or 0)),
        model=str(args.get("model") or ""), idempotency_key=str(args.get("idempotency_key") or ""),
        writes=writes, workspace=workspace,
        model_required=bool(args.get("model_required")),
        context_mode=str(args.get("context_mode") or "fresh"),
        context_excerpt=str(args.get("context_excerpt") or ""),
        accept_fork_switch=bool(args.get("accept_fork_switch")),
        reasoning_effort=str(args.get("reasoning_effort") or ""))


def _exec_task(args: dict[str, Any]) -> dict[str, Any]:
    """Five model fields in; all authority-bearing fields come from runtime state."""
    owner, session, run = _principal(args)
    scoped = _scoped_parent(args)
    from core.services.agent_task_facade import execute

    return execute(
        owner_user_id=owner, origin_session_id=session, parent_run_id=run,
        parent_agent_id=scoped[0] if scoped else "jarvis",
        description=str(args.get("description") or ""), prompt=str(args.get("prompt") or ""),
        subagent_type=str(args.get("subagent_type") or ""), model=str(args.get("model") or ""),
        run_in_background=bool(args.get("run_in_background", True)),
    )


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


def _exec_convene_agent_council(args: dict[str, Any]) -> dict[str, Any]:
    owner, session, run = _principal(args)
    from core.services import agent_council
    return agent_council.convene(
        owner_user_id=owner, origin_session_id=session, parent_run_id=run, topic=str(args.get("topic") or ""),
        facts=str(args.get("facts") or ""), members=args.get("members") or [],
        budget_tokens=max(0, int(args.get("budget_tokens") or 0)),
        idempotency_key=str(args.get("idempotency_key") or ""))


def _exec_decide_agent_approval(args: dict[str, Any]) -> dict[str, Any]:
    """Jarvis afgoer en af SINE EGNE agenters vaerktoejskald (14/10-2026).

    Graensen haandhaeves i LAGERET, ikke her: kun ``parent_agent_id == "jarvis"`` og
    ``kind == "tool_call"``. En integration - en aendring af husets kode - afvises der og lander
    stadig hos Bjorn. Ingen ``_principal``: denne afgoerelse er ikke bundet til et assignment,
    den er bundet til hvem der STARTEDE agenten.
    """
    return _svc().decide_approval_as_parent(
        approval_id=str(args.get("approval_id") or "").strip(),
        decision=str(args.get("decision") or "").strip(),
        digest=str(args.get("digest") or "").strip(),
        note=str(args.get("note") or ""))


def _exec_review_agent_work(args: dict[str, Any]) -> dict[str, Any]:
    owner, session, run = _principal(args)
    from core.services import agent_council
    return agent_council.dispatch_review(
        owner_user_id=owner, origin_session_id=session, parent_run_id=run,
        builder_assignment_id=str(args.get("builder_assignment_id") or ""),
        requirements=str(args.get("requirements") or ""),
        budget_tokens=max(0, int(args.get("budget_tokens") or 0)),
        idempotency_key=str(args.get("idempotency_key") or ""))
