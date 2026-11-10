"""The five-field model-facing Task facade over agent-contract-v1.

Everything that carries authority is derived from authenticated runtime state
and fixed profiles.  Prompt text never decides paths, tools, budget, target or
side-effect class.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import UTC, datetime, timedelta
from typing import Any

from core.runtime.config import PROJECT_ROOT
from core.services.agent_task_requirements import ufuldstaendige_vaerktoejer

logger = logging.getLogger(__name__)


_AGENT_ONLY_TOOLS = ("agent_note",)
# ``bash`` fjernes bevidst: den kører i containeren (eller på Bjørns maskine gennem
# operator-kanalen), ikke i agentens sandkasse. Målt 8/10-2026 valgte en kodeagent
# den usikre flade til at læse tre filer og udløste et godkendelses-kort for en `sed -n`.
_UDELADTE_TOOLS = frozenset({"bash"})
_READ_TYPES = frozenset({"researcher", "scout", "critic", "reviewer", "planner", "watcher"})
_WRITE_TYPES = frozenset({"executor", "builder", "coder", "code"})
_ROLE = {"scout": "researcher", "reviewer": "critic", "builder": "executor", "coder": "executor",
         "code": "executor"}


def _kendte_vaerktoejer() -> frozenset[str]:
    """Runtime-registerets værktøjsnavne. Tomt sæt hvis det ikke kan læses: vagten
    tilføjer kun en afvisning, så et manglende register må ikke afvise noget nyt."""
    try:
        from core.tools.simple_tools import _TOOL_HANDLERS
        return frozenset(_TOOL_HANDLERS)
    except Exception:  # noqa: BLE001 — vagten er additiv; uden register afviser den intet
        logger.warning("agent_task_facade: værktøjsregisteret kunne ikke læses", exc_info=True)
        return frozenset()


def _vaerktoejer_for(policy: str) -> list[str]:
    """Agentens værktøjer = policyens sæt + agent-kun-værktøjerne.

    Sættet UDLEDES af ``tool_policy``; det er ikke en literal her. Målt 10/11-2026:
    facaden gav en executor tre værktøjer (wt_bash, wt_write_file, agent_note) mens
    dens egen ``tool_policy: "worktree-write"`` lovede elleve — den kunne ikke engang
    ``read_file`` og måtte catte gennem wt_bash. Samme fejlform som
    ``_TOOL_USING_ROLES``: en håndholdt kopi der påstår noget andet end beslutningen.

    En tom liste er farligere end en bred: en agent uden værktøjer finder på sit
    output (målt 23/7-2026). Kan policyen ikke læses, annoncerer vi intet nyt.
    """
    try:
        from core.services.agent_runtime_base import tools_for_policy
        navne = [n for n in tools_for_policy(policy) if n not in _UDELADTE_TOOLS]
    except Exception:  # noqa: BLE001 — en agent uden værktøjer hallucinerer
        logger.warning("agent_task_facade: kunne ikke læse policy %r", policy, exc_info=True)
        navne = []
    if not navne:
        return []
    return [*navne, *[t for t in _AGENT_ONLY_TOOLS if t not in navne]]


def _session_scope(owner: str, session: str) -> tuple[str, str]:
    from core.runtime.db import _ensure_chat_session_workspace_columns, connect

    with connect() as conn:
        _ensure_chat_session_workspace_columns(conn)
        row = conn.execute(
            "SELECT owner_user_id, workspace_kind, workspace_root FROM chat_sessions WHERE session_id=?",
            (session,),
        ).fetchone()
    if row is None:
        return "", ""
    session_owner = str(row["owner_user_id"] or "")
    # 26/10-2026: en TOM owner er ikke "en anden ejer". Maalt efter genstart:
    # `current_user_id()` er tom i runtime-processen (ContextVar saettes i API'ets
    # middleware, ikke i runtime-turen), saa `Task` afviste HVERT kald med
    # "sessionen tilhoerer en anden ejer" — ogsaa fra ejerens egen session.
    # En tom owner kan ikke paaSTAA et ejerskab, men den kan heller ikke goere
    # vaerktoejet ubrugeligt: sessionens ejer er den autentificerede sandhed.
    # En IKKE-tom owner der afviger fra sessionen afvises stadig — det er den
    # eneste vej vaernet skal lukke.
    if owner and session_owner and session_owner != owner:
        raise ValueError("sessionen tilhoerer en anden ejer")
    kind, root = str(row["workspace_kind"] or ""), str(row["workspace_root"] or "")
    # Task er med vilje den samme dispatch-flade i chat og code. En almindelig
    # ejer-chat har intet klient-workspace, men Jarvis' eget server-repo er en
    # runtime-kapabilitet og maa ikke derfor blive til et tomt mandat: det gav
    # researcheren nul filvaerktoejer og afviste executoren. Et eksplicit
    # session-workspace vinder stadig; fallbacken gaetter aldrig ud fra prompten.
    if not kind and not root:
        return "repo", str(PROJECT_ROOT)
    # Desk may store the server root by its stable UI name. Resolve only the
    # repository name here; runtime-state/user-workspace roots are not code repos.
    if root == "repo":
        root = str(PROJECT_ROOT)
    return kind, root


def derive(*, owner_user_id: str, origin_session_id: str, parent_run_id: str,
           parent_agent_id: str, description: str, prompt: str, subagent_type: str,
           model: str, run_in_background: bool) -> dict[str, Any]:
    description, prompt = description.strip(), prompt.strip()
    kind = subagent_type.strip().lower()
    if not description or not prompt:
        raise ValueError("description og prompt er obligatoriske")
    if not kind:
        # Udledning maa kun NEDGRADERE. En udeladt type bliver den sikre side —
        # laeseretten — aldrig skrivning: skrivning kraever et bevidst valg,
        # praecis som never-escalate-kontrakten kraever. Anthropic loeser det
        # modsatte: deres udeladte type faar hele kataloget. Vi vaelger den anden
        # side af samme moent, fordi en agent der ikke kan skrive er harmloes.
        kind = "researcher"
    if kind not in _READ_TYPES | _WRITE_TYPES:
        raise ValueError("ukendt subagent_type; brug researcher, critic, planner, watcher eller executor")
    workspace_kind, workspace = _session_scope(owner_user_id, origin_session_id)
    workspace = os.path.realpath(workspace) if workspace else ""
    has_repo = bool(workspace and os.path.exists(os.path.join(workspace, ".git")))
    writes = kind in _WRITE_TYPES
    if writes and (not workspace or workspace_kind.lower() not in {"container", "local", "code", "repo", "git"}):
        raise ValueError("executor kraever et lokalt repo-workspace paa origin-sessionen")
    if writes and not has_repo:
        # Worktrees have a .git file, but the facade starts from the session's source repository.
        raise ValueError("executorens workspace er ikke et git-repository")

    # Fixed, countable limits. A child Task cannot fan out in this first complete slice.
    budget_tokens = 12_000 if writes else 8_000
    max_turns = 12 if writes else 8
    deadline = (datetime.now(UTC) + timedelta(minutes=45 if writes else 30)).isoformat()
    tools = _vaerktoejer_for("worktree-write" if writes else "read-only-runtime")
    if not workspace:
        tools = [t for t in tools if t in {"web_search", "web_fetch", "read_tool_result", "agent_note"}]
    mangler = ufuldstaendige_vaerktoejer(prompt, tools, _kendte_vaerktoejer())
    if mangler:
        # Afvis ved dispatch, ikke efter en kørsel: en agent kan ikke få et værktøj ud over sit
        # faste sæt, så opgaven ville blive accepteret, brænde tokens og fejle (4/11-2026).
        raise ValueError(
            f"opgaven kraever {', '.join('`' + n + '`' for n in mangler)}, som en {kind} ikke har "
            f"(den faar kun: {', '.join(tools)}). Udfoer det selv i stedet for at delegere det"
        )
    granted = "worktree-write" if writes else "read"
    original = "worktree-write" if has_repo else "read"
    canonical = {
        "owner": owner_user_id, "session": origin_session_id, "parent_run": parent_run_id,
        "parent_agent": parent_agent_id, "description": description, "prompt": prompt,
        "subagent_type": kind, "model": model.strip(), "background": bool(run_in_background),
    }
    idem = "task-" + hashlib.sha256(json.dumps(canonical, sort_keys=True).encode()).hexdigest()[:32]
    mandate_id = "mnd-" + hashlib.sha256(idem.encode()).hexdigest()[:16]
    scoped_prompt = prompt
    if workspace:
        visible_root = "/work" if writes else workspace
        scoped_prompt += (f"\n\nRuntime boundary: your workspace root is {visible_root}. "
                          "Use absolute paths inside that root; paths outside it are mechanically rejected.")
    return {
        "goal": scoped_prompt, "description": description, "role": _ROLE.get(kind, kind),
        "expected_result": description, "model": model.strip(), "writes": writes,
        "workspace": workspace if writes else "", "target": "runtime-container",
        "tool_policy": "worktree-write" if writes else "read-only-runtime",
        "allowed_tools": tools, "budget_tokens": budget_tokens, "max_turns": max_turns,
        "deadline_at": deadline, "idempotency_key": idem,
        "run_in_background": bool(run_in_background),
        "mandate": {
            "mandate_id": mandate_id, "owner_user_id": owner_user_id,
            "origin_session_id": origin_session_id, "parent_run_id": parent_run_id,
            "original_mandate_id": f"origin:{origin_session_id}", "target": "runtime-container",
            "workspace_roots": [workspace] if workspace else [], "allowed_tools": tools,
            "tool_policy": "worktree-write" if writes else "read-only-runtime",
            "granted_side_effect": granted, "original_side_effect": original,
            "budget_tokens": budget_tokens, "max_turns": max_turns, "max_depth": 0,
            "max_fanout": 0, "deadline_at": deadline, "expected_result": description,
            "return_address": f"agent-inbox:{owner_user_id}:{origin_session_id}:{parent_run_id}",
        },
    }


def execute(**fields: Any) -> dict[str, Any]:
    from core.services import agent_contract_service as service

    try:
        plan = derive(**fields)
    except ValueError as exc:  # facade validation is translated to the contract's stable error shape
        return service._err("INVALID_SCOPE", str(exc))
    mandate = plan.pop("mandate")
    background = bool(plan.pop("run_in_background"))
    result = service.dispatch_agent(
        owner_user_id=fields["owner_user_id"], origin_session_id=fields["origin_session_id"],
        parent_run_id=fields["parent_run_id"], parent_agent_id=fields["parent_agent_id"],
        mandate=mandate, **plan,
    )
    if background or result.get("status") != "accepted":
        return result
    waited = service.wait_agents(
        owner_user_id=fields["owner_user_id"], origin_session_id=fields["origin_session_id"],
        assignment_ids=[result["assignment_id"]], timeout_seconds=120, include_output=True,
        parent_run_id=fields["parent_run_id"], wake_if_run_ends=True,
    )
    return {**result, "foreground": waited}
