"""agent-contract-v1: den ene motor bag dispatch og styring af agenter (leverance F1).

Spec: docs/specs/2026-10-07-agentorkestrering-og-subagenter.md (5, 12.2, 12.3).

Modelvaerktoejer, Desk/API og planlagte aktiveringer kalder DISSE funktioner; ingen
af dem har sin egen livscyklus. Ejer, oprindelsessession og parent-run gives
udefra af adapteren (fra den autentificerede anmodningskontekst) og valideres her
- aldrig fra modeltekst. Ethvert muterende kald returnerer identitet og
accept-status: accept er ikke gennemfoerelse.

Interim: agentens model-/vaerktoejsloekke koeres endnu i en baggrundstraad i denne
proces (`_run_in_background`). Spec'ens krav om en isoleret workerproces (§12.1)
hoerer til leverance C og aendrer ikke denne kontrakt.
"""
from __future__ import annotations

import contextvars
import hashlib
import json
import logging
import threading
import time
from typing import Any, Callable

from core.runtime import db_agent_contract as c
from core.runtime.db_agent_contract import ASSIGNMENT_TERMINAL, CONTRACT_VERSION, ContractError

logger = logging.getLogger(__name__)

CAPABILITY_FLAG = "agent_contract.enabled"
PROMPT_VERSION = "orchestrator-v1"

# Startprofilen, §12.3.
MAX_ACTIVE_GLOBAL = 12
MAX_ACTIVE_PER_OWNER = 8
MAX_ACTIVE_PER_PARENT = 6
MAX_WAIT_SECONDS = 120.0
_POLL_SECONDS = 0.5

_SUPPORTED_TARGETS = ("runtime-container",)


# --- kapabilitet ---------------------------------------------------------------

def capability_enabled() -> bool:
    """Fail-CLOSED: enhver laesefejl er `False`. Starter slukket (§12.4)."""
    try:
        from core.runtime.db_core import get_runtime_state_bool
        return bool(get_runtime_state_bool(CAPABILITY_FLAG, False))
    except Exception:
        logger.warning("kunne ikke laese %s - behandles som slukket", CAPABILITY_FLAG,
                       exc_info=True)
        return False


def set_capability(enabled: bool, *, role: str = "") -> bool:
    """Taend/sluk. At TAENDE er en ejerbeslutning; at slukke (kill switch) er altid tilladt."""
    if enabled and role != "owner":
        return capability_enabled()
    from core.runtime.db_core import set_runtime_state_value
    set_runtime_state_value(CAPABILITY_FLAG, bool(enabled))
    return bool(enabled)


def capability_status() -> dict[str, Any]:
    """Faelles sandhed for admission, vaerktoejsudvalg, prompt og Desk."""
    on = capability_enabled()
    return {"enabled": on, "contract_version": CONTRACT_VERSION, "prompt_version": PROMPT_VERSION,
            "reason": "" if on else "agent-kontrakten er slukket (kill switch / ikke udrullet)",
            "targets": list(_SUPPORTED_TARGETS)}


# --- fejl og hjaelpere -----------------------------------------------------------

def _err(code: str, detail: str = "", phase: str = "admission") -> dict[str, Any]:
    return {"status": "error", "code": code, "phase": phase, "error": detail or code,
            "contract_version": CONTRACT_VERSION}


def _guard(owner: str, session: str) -> dict[str, Any] | None:
    if not capability_enabled():
        return _err("POLICY_DENIED", "agent-kontrakten er slukket", "admission")
    if not (owner or "").strip() or not (session or "").strip():
        return _err("INVALID_SCOPE", "ejer og session mangler")
    return None


def _owned_agent(agent_id: str, owner: str) -> dict[str, Any] | None:
    """Agenten, men KUN hvis den tilhoerer ejeren. En andens agent er `None`."""
    row = c._conn().execute(
        "SELECT * FROM agent_registry WHERE agent_id=? AND owner_user_id=?",
        (agent_id, owner)).fetchone()
    return None if row is None else {k: row[k] for k in row.keys()}


def _run_in_background(fn: Callable[[], Any]) -> None:
    """Start agentens loekke uden at blokere kalderen. Kontekst foelger med."""
    ctx = contextvars.copy_context()

    def _target() -> None:
        try:
            ctx.run(fn)
        except Exception:
            logger.warning("baggrundskoersel af agent fejlede", exc_info=True)

    threading.Thread(target=_target, daemon=True, name="agent-contract-run").start()


def _start_execution(agent_id: str) -> None:
    def _go() -> None:
        from core.services.agent_runtime_spawn import execute_agent_task
        execute_agent_task(agent_id=agent_id)
    _run_in_background(_go)


def _signal_feed() -> None:
    """Meld nye/aendrede agentreferencer til Desk. Best effort: supervisor-tikket gensender (G)."""
    try:
        from core.runtime.db_agent_feed import signal_changes
        signal_changes()
    except Exception:
        logger.warning("feed-signal kunne ikke udsendes nu", exc_info=True)


def _digest(**parts: Any) -> str:
    return hashlib.sha256(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()


def _accept_view(acc: dict[str, Any]) -> dict[str, Any]:
    return {"status": "accepted", "agent_id": acc["agent_id"], "assignment_id": acc["assignment_id"],
            "run_id": acc.get("run_id", ""), "assignment_status": acc.get("status", "queued"),
            "replayed": bool(acc.get("replayed")), "contract_version": CONTRACT_VERSION}


def _capacity_error(owner: str, parent: str) -> dict[str, Any] | None:
    if c.count_open_assignments() >= MAX_ACTIVE_GLOBAL:
        return _err("CAPACITY", f"globalt loft {MAX_ACTIVE_GLOBAL} aktive agentruns")
    if c.count_open_assignments(owner_user_id=owner) >= MAX_ACTIVE_PER_OWNER:
        return _err("CAPACITY", f"loft {MAX_ACTIVE_PER_OWNER} aktive agentruns pr. ejer")
    if c.count_open_assignments(parent_agent_id=parent) >= MAX_ACTIVE_PER_PARENT:
        return _err("CAPACITY", f"loft {MAX_ACTIVE_PER_PARENT} direkte boern pr. parent")
    return None


# --- operationer -----------------------------------------------------------------

def dispatch_agent(
    *, owner_user_id: str, origin_session_id: str, goal: str, parent_run_id: str = "",
    parent_agent_id: str = "jarvis", role: str = "researcher", description: str = "",
    tool_policy: str = "", allowed_tools: list[str] | None = None,
    target: str = "runtime-container", budget_tokens: int = 0, max_turns: int = 0,
    expected_result: str = "", model: str = "", idempotency_key: str = "",
    writes: bool = False, workspace: str = "", model_required: bool = False,
) -> dict[str, Any]:
    """Accepter en afgraenset opgave til en ny agent og returner id'er STRAKS.

    ``model`` er en praeference, ``model_required=True`` et haardt krav (D, spec 7.1). Ruten fastlaegges
    FOER agenten oprettes; findes ingen tilladt rute, svares ``MODEL_UNAVAILABLE`` og intet er oprettet.

    ``writes=True`` + ``workspace`` giver en kodeagent: den faar sit eget git-worktree (reserveret FOER
    den er accepteret) og kan kun skrive dér, gennem en sandbox (C5). Faar worktree'et ikke plads, er
    intet oprettet."""
    if (bad := _guard(owner_user_id, origin_session_id)):
        return bad
    goal = (goal or "").strip()
    if not goal:
        return _err("INVALID_SCOPE", "goal mangler")
    wt_tools = tool_policy == "worktree-write" or any(str(t).startswith("wt_") for t in (allowed_tools or []))
    if writes:
        if not (workspace or "").strip():
            return _err("INVALID_SCOPE", "writes kraever et workspace (repo-sti)")
        if allowed_tools or (tool_policy and tool_policy != "worktree-write"):
            return _err("INVALID_SCOPE", "en kodeagent har den faste politik worktree-write")
        tool_policy = "worktree-write"
    elif wt_tools or (workspace or "").strip():
        return _err("INVALID_SCOPE", "worktree-vaerktoejer og workspace kraever writes=true")
    if target not in _SUPPORTED_TARGETS:
        return _err("CLIENT_OFFLINE" if target.startswith("client:") else "INVALID_SCOPE",
                    f"target {target!r} understoettes ikke endnu (kun {_SUPPORTED_TARGETS})")
    digest = _digest(goal=goal, role=role, description=description, tool_policy=tool_policy,
                     allowed_tools=allowed_tools or [], target=target, budget=budget_tokens,
                     turns=max_turns, expected=expected_result, model=model, model_required=model_required,
                     parent=parent_agent_id, parent_run=parent_run_id, writes=writes, workspace=workspace)
    prior = c.find_assignment_by_key(owner_user_id=owner_user_id, origin_session_id=origin_session_id,
                                     operation="dispatch", idempotency_key=idempotency_key)
    if prior is not None:
        if prior["request_digest"] != digest:
            return _err("IDEMPOTENCY_CONFLICT", idempotency_key)
        return {**_accept_view({"agent_id": prior["agent_id"], "assignment_id": prior["assignment_id"],
                                "status": prior["status"], "replayed": True})}
    if (full := _capacity_error(owner_user_id, parent_agent_id)):
        return full
    from core.services.agent_model_policy import ModelUnavailable, decide_route
    try:
        route = decide_route(owner_user_id=owner_user_id, requested_model=model, hard=model_required,
                             role=role, budget_tokens=budget_tokens)
    except ModelUnavailable as exc:
        logger.info("dispatch afvist: ingen tilladt model (%s)", exc.detail)
        return {**_err("MODEL_UNAVAILABLE", exc.detail, "admission"), "reasons": exc.reasons}
    from core.services.agent_runtime_spawn import spawn_agent_task
    try:
        spawned = spawn_agent_task(
            role=role, goal=goal if not description else f"{description}\n\n{goal}",
            tool_policy=tool_policy, allowed_tools=allowed_tools or None,
            parent_agent_id=parent_agent_id, budget_tokens=budget_tokens, max_turns=max_turns,
            auto_execute=False, provider=route["provider"], model=route["model"], respekter_model=True,
            context={"user_id": owner_user_id, "parent_session_id": origin_session_id,
                     "parent_run_id": parent_run_id},
            contract={"idempotency_key": idempotency_key, "request_digest": digest,
                       "target": target, "expected_result": expected_result},
        )
    except Exception as exc:
        logger.warning("dispatch_agent: spawn fejlede", exc_info=True)
        return _err("INVALID_SCOPE", str(exc)[:200], "admission")
    agent_id = str(spawned.get("agent_id") or "")
    a = c.open_assignment_for_agent(agent_id)
    if a is None:
        return _err("INVALID_SCOPE", "agenten blev ikke bundet til kontrakten", "admission")
    try:
        from core.runtime import db_agent_route
        db_agent_route.record_decision(assignment_id=a["assignment_id"], agent_id=agent_id,
                                       owner_user_id=owner_user_id, decision=route, attempt=1)
    except Exception as exc:
        logger.warning("rute-proveniens kunne ikke gemmes - agenten afvises", exc_info=True)
        c.discard_unstarted_assignment(agent_id=agent_id, owner_user_id=owner_user_id)
        return _err("INVALID_SCOPE", f"rute kunne ikke gemmes: {type(exc).__name__}"[:120])
    worktree: dict[str, Any] | None = None
    if writes:
        from core.services.agent_worktrees import provision
        try:
            worktree = provision(owner_user_id=owner_user_id, assignment_id=a["assignment_id"],
                                 repo_path=workspace)
        except ContractError as exc:
            c.discard_unstarted_assignment(agent_id=agent_id, owner_user_id=owner_user_id)
            return _err(exc.code, exc.detail)
        except Exception as exc:
            logger.warning("worktree kunne ikke reserveres", exc_info=True)
            c.discard_unstarted_assignment(agent_id=agent_id, owner_user_id=owner_user_id)
            return _err("INVALID_SCOPE", f"worktree: {type(exc).__name__}"[:120])
    _start_execution(agent_id)
    _signal_feed()
    run = c._conn().execute("SELECT run_id FROM agent_runs WHERE assignment_id=? "
                            "ORDER BY attempt_no LIMIT 1", (a["assignment_id"],)).fetchone()
    view = _accept_view({"agent_id": agent_id, "assignment_id": a["assignment_id"],
                         "run_id": run["run_id"] if run else "", "status": a["status"]})
    view["route"] = {"route_source": route["route_source"], "provider": route["provider"],
                     "model": route["model"]}
    if worktree is not None:
        view["worktree"] = {"worktree_id": worktree["worktree_id"], "branch": worktree["branch"],
                            "base_commit": worktree["base_commit"]}
    return view


def followup_agent(
    *, owner_user_id: str, origin_session_id: str, agent_id: str, goal: str,
    parent_run_id: str = "", budget_tokens: int = 0, expected_result: str = "",
    idempotency_key: str = "", operation: str = "followup",
) -> dict[str, Any]:
    """Ny opgave til SAMME agent-id: nyt assignment, nyt run. Ikke til en lukket agent."""
    if (bad := _guard(owner_user_id, origin_session_id)):
        return bad
    goal = (goal or "").strip()
    if not goal:
        return _err("INVALID_SCOPE", "goal mangler")
    agent = _owned_agent(agent_id, owner_user_id)
    if agent is None:
        return _err("INVALID_SCOPE", "ukendt agent")
    if agent["lifecycle_status"] in ("closing", "closed"):
        return _err("POLICY_DENIED", f"agenten er {agent['lifecycle_status']}")
    digest = _digest(agent=agent_id, goal=goal, budget=budget_tokens, expected=expected_result,
                     parent_run=parent_run_id)
    prior = c.find_assignment_by_key(owner_user_id=owner_user_id, origin_session_id=origin_session_id,
                                     operation=operation, idempotency_key=idempotency_key)
    if prior is not None:
        if prior["request_digest"] != digest:
            return _err("IDEMPOTENCY_CONFLICT", idempotency_key)
        return _accept_view({"agent_id": prior["agent_id"], "assignment_id": prior["assignment_id"],
                             "status": prior["status"], "replayed": True})
    if (full := _capacity_error(owner_user_id, agent["parent_agent_id"] or "jarvis")):
        return full
    try:
        acc = c.accept_assignment(
            agent_id=agent_id, owner_user_id=owner_user_id, origin_session_id=origin_session_id,
            goal=goal, parent_agent_id=agent["parent_agent_id"] or "jarvis",
            parent_run_id=parent_run_id, expected_result=expected_result,
            budget={"tokens": budget_tokens}, created_by="jarvis", operation=operation,
            idempotency_key=idempotency_key, request_digest=digest)
    except ContractError as exc:
        logger.info("followup_agent afvist for %s: %s", agent_id, exc)
        return _err(exc.code, exc.detail)
    from core.runtime.db_agent_runtime import create_agent_message, update_agent_registry_entry
    from uuid import uuid4
    create_agent_message(message_id=f"agent-msg-{uuid4().hex}", thread_id=f"agent-thread-{agent_id}",
                         agent_id=agent_id, direction="jarvis->agent", role="system",
                         kind="task-brief", content=goal)
    update_agent_registry_entry(agent_id, status="queued", last_error="")
    _start_execution(agent_id)
    _signal_feed()
    return _accept_view(acc)


def send_message(
    *, owner_user_id: str, origin_session_id: str, agent_id: str, content: str,
    sender: str = "jarvis", parent_run_id: str = "", idempotency_key: str = "",
) -> dict[str, Any]:
    """Information/styring til barnets aktuelle opgave, eller - er barnet ledigt - en
    beskedudloest ny opgave. Returnerer et besked-id; levering er IKKE bevist (§6)."""
    if (bad := _guard(owner_user_id, origin_session_id)):
        return bad
    content = (content or "").strip()
    if not content:
        return _err("INVALID_SCOPE", "content mangler")
    agent = _owned_agent(agent_id, owner_user_id)
    if agent is None:
        return _err("INVALID_SCOPE", "ukendt agent")
    if agent["lifecycle_status"] == "closed":
        return _err("POLICY_DENIED", "agenten er lukket")
    open_a = c.open_assignment_for_agent(agent_id)
    if open_a is None:
        out = followup_agent(owner_user_id=owner_user_id, origin_session_id=origin_session_id,
                             agent_id=agent_id, goal=content, parent_run_id=parent_run_id,
                             idempotency_key=idempotency_key, operation="message")
        return {**out, "triggered_assignment": out.get("status") == "accepted"}
    from uuid import uuid4
    from core.runtime.db_agent_runtime import create_agent_message
    mid = f"agent-msg-{uuid4().hex}"
    create_agent_message(message_id=mid, thread_id=f"agent-thread-{agent_id}", agent_id=agent_id,
                         direction="jarvis->agent", role="user", kind="parent-message",
                         content=f"[{sender}]\n{content}")
    return {"status": "accepted", "message_id": mid, "agent_id": agent_id,
            "assignment_id": open_a["assignment_id"], "delivery": "accepted",
            "note": "gemt til agentens naeste tur; levering til en igangvaerende tur er ikke bevist",
            "contract_version": CONTRACT_VERSION}


def interrupt_agent(*, owner_user_id: str, origin_session_id: str, agent_id: str,
                    note: str = "") -> dict[str, Any]:
    """Anmod om stop af den aktuelle tur. `stop_requested`, aldrig et lovet `cancelled`."""
    if (bad := _guard(owner_user_id, origin_session_id)):
        return bad
    if _owned_agent(agent_id, owner_user_id) is None:
        return _err("INVALID_SCOPE", "ukendt agent")
    open_a = c.open_assignment_for_agent(agent_id)
    if open_a is None:
        return {"status": "noop", "agent_id": agent_id, "detail": "ingen aktiv opgave",
                "contract_version": CONTRACT_VERSION}
    from core.services.agent_runtime_spawn import cancel_agent
    cancel_agent(agent_id, note=note or "interrupt_agent")
    return {"status": "stop_requested", "agent_id": agent_id,
            "assignment_id": open_a["assignment_id"], "contract_version": CONTRACT_VERSION}


def close_agent(*, owner_user_id: str, origin_session_id: str, agent_id: str) -> dict[str, Any]:
    """Graceful lukning: `closing` straks (afviser nye opgaver); `closed` naar eget run og
    boern er terminale. Accepterede runs afbrydes ikke."""
    if (bad := _guard(owner_user_id, origin_session_id)):
        return bad
    if _owned_agent(agent_id, owner_user_id) is None:
        return _err("INVALID_SCOPE", "ukendt agent")
    c.set_lifecycle(agent_id=agent_id, owner_user_id=owner_user_id, lifecycle_status="closing")
    return {"status": "accepted", "agent_id": agent_id,
            "lifecycle_status": settle_closing(agent_id, owner_user_id),
            "contract_version": CONTRACT_VERSION}


def settle_closing(agent_id: str, owner_user_id: str) -> str:
    """`closing` -> `closed`, naar agentens eget assignment og alle boerns er terminale."""
    conn = c._conn()
    row = conn.execute("SELECT lifecycle_status FROM agent_registry WHERE agent_id=? "
                       "AND owner_user_id=?", (agent_id, owner_user_id)).fetchone()
    if row is None:
        return ""
    if row["lifecycle_status"] != "closing":
        return str(row["lifecycle_status"])
    busy = conn.execute(
        "SELECT 1 FROM agent_assignments WHERE status IN ('queued','active','waiting') AND "
        "(agent_id=? OR parent_agent_id=?) LIMIT 1", (agent_id, agent_id)).fetchone()
    if busy is None:
        c.set_lifecycle(agent_id=agent_id, owner_user_id=owner_user_id, lifecycle_status="closed")
        return "closed"
    return "closing"


def list_agents(*, owner_user_id: str, origin_session_id: str = "", status: str = "",
                limit: int = 50) -> dict[str, Any]:
    """Ejerens agenter (aldrig en andens): status, rolle, target, ubehandlede resultater."""
    owner = (owner_user_id or "").strip()
    if not owner:
        return _err("INVALID_SCOPE", "ejer mangler")
    q = ("SELECT r.agent_id, r.role, r.status AS agent_status, r.lifecycle_status, "
         "r.parent_agent_id, a.assignment_id, a.status AS assignment_status, a.target, "
         "a.goal, a.updated_at, "
         "(SELECT COUNT(*) FROM agent_result_outbox o WHERE o.assignment_id=a.assignment_id "
         " AND o.delivery_status != 'acknowledged') AS unprocessed "
         "FROM agent_registry r LEFT JOIN agent_assignments a ON a.assignment_id = "
         "(SELECT assignment_id FROM agent_assignments WHERE agent_id=r.agent_id "
         " ORDER BY created_at DESC LIMIT 1) WHERE r.owner_user_id=?")
    args: list[Any] = [owner]
    if origin_session_id:
        q += " AND r.owner_session_id=?"
        args.append(origin_session_id)
    if status:
        q += " AND a.status=?"
        args.append(status)
    q += " ORDER BY a.updated_at DESC LIMIT ?"
    args.append(max(1, min(int(limit), 200)))
    rows = [{k: r[k] for k in r.keys()} for r in c._conn().execute(q, args).fetchall()]
    for r in rows:
        r["goal"] = str(r.get("goal") or "")[:160]
    return {"status": "ok", "agents": rows, "count": len(rows), "contract_version": CONTRACT_VERSION}


def wait_agents(
    *, owner_user_id: str, origin_session_id: str, assignment_ids: list[str],
    condition: str = "all_terminal", timeout_seconds: float = 0.0,
    wake_if_run_ends: bool = False, parent_run_id: str = "",
    include_output: bool = False, output_offset: int = 0,
) -> dict[str, Any]:
    """Vent paa assignments. `timeout_seconds` blokerer kortvarigt (max 120 s); er betingelsen
    stadig ikke opfyldt og `wake_if_run_ends` er sat, registreres en ventekontrakt (B2), saa et
    naeste run vaekkes naar den er opfyldt - uden at parenten skal polle."""
    if (bad := _guard(owner_user_id, origin_session_id)):
        return bad
    ids = sorted({str(a).strip() for a in (assignment_ids or []) if str(a).strip()})
    if not ids or condition not in ("first_terminal", "all_terminal"):
        return _err("INVALID_SCOPE", "assignment_ids/condition ugyldig")
    deadline = time.monotonic() + max(0.0, min(float(timeout_seconds or 0), MAX_WAIT_SECONDS))

    def snapshot() -> tuple[list[dict[str, Any]], bool]:
        marks = ",".join("?" * len(ids))
        rows = c._conn().execute(
            f"SELECT assignment_id, agent_id, status, outcome_json FROM agent_assignments "
            f"WHERE assignment_id IN ({marks}) AND owner_user_id=? AND origin_session_id=?",
            [*ids, owner_user_id, origin_session_id]).fetchall()
        view = [{"assignment_id": r["assignment_id"], "agent_id": r["agent_id"],
                 "status": r["status"],
                 "terminal": r["status"] in ASSIGNMENT_TERMINAL} for r in rows]
        done = sum(1 for v in view if v["terminal"])
        ok = done >= 1 if condition == "first_terminal" else (len(view) == len(ids) and done == len(ids))
        return view, ok

    view, ok = snapshot()
    if len(view) != len(ids):
        return _err("INVALID_SCOPE", "assignment tilhoerer ikke ejer/session")
    while not ok and time.monotonic() < deadline:
        time.sleep(_POLL_SECONDS)
        view, ok = snapshot()
    if include_output:
        _attach_outputs(view, owner_user_id, int(output_offset or 0))
    out: dict[str, Any] = {"status": "ok", "satisfied": ok, "condition": condition,
                           "assignments": view, "contract_version": CONTRACT_VERSION}
    if not ok and wake_if_run_ends:
        try:
            from core.runtime.db_agent_wait import register_wait
            ct = register_wait(owner_user_id=owner_user_id, origin_session_id=origin_session_id,
                               parent_run_id=parent_run_id, assignment_ids=ids, condition=condition)
            out["wait_contract"] = {"contract_id": ct["contract_id"], "status": ct["status"]}
        except ContractError as exc:
            out["wait_contract_error"] = {"code": exc.code, "detail": exc.detail}
    return out


def _attach_outputs(view: list[dict[str, Any]], owner_user_id: str, offset: int) -> None:
    """Fuldt output (``final.txt``) for terminale assignments, via den ejer-kontrollerede
    artefaktreference. En manglende/korrupt/udloebet artefakt faar en praecis status."""
    from core.runtime import db_agent_artifacts as art

    for v in view:
        if not v["terminal"]:
            continue
        row = c._conn().execute("SELECT outcome_json FROM agent_assignments WHERE assignment_id=?",
                                (v["assignment_id"],)).fetchone()
        try:
            payload = json.loads(row["outcome_json"] or "{}") if row else {}
        except ValueError:
            payload = {}
        ref = str(payload.get("artifact_ref") or "")
        v["summary"] = str(payload.get("summary") or "")
        if not ref:
            v["output"] = {"status": "NO_ARTIFACT", "detail": str(payload.get("artifact_error") or "")}
            continue
        run_id = ref.partition("/")[0]
        v["output"] = art.read_artifact(owner_user_id=owner_user_id, ref=f"{run_id}/final.txt",
                                        offset=offset)
        v["result_ref"] = ref


def supervise() -> list[dict[str, Any]]:
    """Supervisor-taek: udloeb approvals, genoptag parkerede agenter hvis approval er afgjort, overtag udloebne
    leases og genstart sikre forsoeg. Kan koeres fra begge processer; atomiske DB-claims afgoer hvem der handler."""
    from core.runtime import db_agent_approvals as appr
    from core.runtime.db_agent_lease import reconcile_expired_leases
    from core.services.agent_parking import resume_decided

    appr.expire_due()
    try:
        from core.services.agent_approval_notify import ensure_wakes
        ensure_wakes()
    except Exception:
        logger.warning("ensure_wakes fejlede", exc_info=True)
    resumed = resume_decided(_start_execution)
    try:
        from core.services.agent_integration import run_pending
        run_pending()
    except Exception:
        logger.warning("godkendte integrationer kunne ikke udfoeres", exc_info=True)
    done = reconcile_expired_leases()
    try:
        from core.runtime.db_agent_feed import signal_changes
        signal_changes()      # G: crash mellem commit og push taber ikke notifikationen
    except Exception:
        logger.warning("feed-signaler kunne ikke udsendes", exc_info=True)
    for d in done:
        if d.get("action") == "retry":
            _start_execution(d["agent_id"])
    return done + [{"action": "resumed_after_approval", **r} for r in resumed]


# --- approvals (F4) -----------------------------------------------------------------------------------

def approval_view(r: dict[str, Any]) -> dict[str, Any]:
    """Det en klient/en model maa se: sikker visning + digest, ALDRIG de raa argumenter."""
    keys = ("approval_id", "kind", "status", "agent_id", "assignment_id", "run_id", "parent_run_id",
            "origin_session_id", "target", "tool_name", "safe_view", "args_digest", "risk_class",
            "requested_by", "created_at", "expires_at", "decided_at", "decided_by", "decision_note")
    return {k: r.get(k) for k in keys}


def list_approvals(*, owner_user_id: str, status: str = "", origin_session_id: str = "") -> dict[str, Any]:
    from core.runtime import db_agent_approvals as appr

    if not (owner_user_id or "").strip():
        return _err("INVALID_SCOPE", "ejer mangler")
    rows = appr.list_for_owner(owner_user_id=owner_user_id, status=status, origin_session_id=origin_session_id)
    return {"status": "ok", "approvals": [approval_view(r) for r in rows], "count": len(rows),
            "contract_version": CONTRACT_VERSION}


def decide_approval(*, approval_id: str, decision: str, actor_user_id: str, actor_kind: str, digest: str,
                    note: str = "") -> dict[str, Any]:
    """Afgoer en approval (kun et menneske, jf. db_agent_approvals.decide) og genoptager straks det parkerede
    barn. Virker ogsaa naar motoren er slukket: accepteret arbejde og dets approvals kan altid afgoeres."""
    from core.runtime import db_agent_approvals as appr
    from core.services.agent_parking import resume_decided

    try:
        r = appr.decide(approval_id=approval_id, decision=decision, actor_user_id=actor_user_id,
                        actor_kind=actor_kind, digest=digest, note=note)
    except ContractError as exc:
        logger.info("approval %s: afgoerelsen blev afvist (%s)", approval_id, exc.code)
        return _err(exc.code, exc.detail, "approval")
    try:
        from core.services.agent_approval_notify import cancel_wake
        cancel_wake(r, f"approvalen er {r['status']}")
    except Exception:
        logger.warning("kunne ikke aflyse vaekning for %s", approval_id, exc_info=True)
    resume_decided(_start_execution)
    integration = None
    if r.get("kind") == "integration" and r["status"] == "approved":
        from core.services.agent_integration import execute_approved
        integration = execute_approved(r)
    out = {"status": "ok", "approval": approval_view(r), "contract_version": CONTRACT_VERSION}
    if integration is not None:
        out["integration"] = {k: integration.get(k) for k in ("status", "integrate_branch", "commit", "summary",
                                                              "error_code", "conflicts")}
    return out


def request_integration(*, owner_user_id: str, origin_session_id: str, assignment_id: str) -> dict[str, Any]:
    """Jarvis beder om integration af et kodeassignments arbejde. Opretter KUN en approval - han kan ikke
    godkende den. Virker ikke naar motoren er slukket (en ny handling); afgoerelsen virker altid."""
    if (bad := _guard(owner_user_id, origin_session_id)):
        return bad
    from core.services.agent_integration import request_integration as _request
    try:
        r = _request(owner_user_id=owner_user_id, origin_session_id=origin_session_id,
                     assignment_id=(assignment_id or "").strip())
    except ContractError as exc:
        logger.info("integration kunne ikke anmodes for %s: %s", assignment_id, exc)
        return _err(exc.code, exc.detail)
    try:
        from core.services.agent_approval_notify import on_requested
        on_requested(r)
    except Exception:
        logger.warning("kunne ikke notificere om integrations-approval %s", r["approval_id"], exc_info=True)
    return {"status": "approval_requested", "approval": approval_view(r),
            "note": "Venter paa brugerens godkendelse i Desk. Du kan ikke godkende den selv.",
            "contract_version": CONTRACT_VERSION}
