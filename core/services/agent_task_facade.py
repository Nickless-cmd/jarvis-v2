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

# Budgettet var en literal (12_000/8_000), og den passede ikke til virkeligheden.
# Maalt 10/11-2026 paa hele registret: 8 af 30 agenter siden 1/11 doede af
# `budget exhausted` — og en laesende agent der DOEDE brugte 32.962 tokens hvor en
# der LYKKEDES brugte 19.302. De doede var altsaa ikke daarligere; de var midt i
# mere arbejde, og hele koerslen var spildt. Median-forbruget for den laesende
# rolle er 12.961 — 62 % over det gamle loft paa 8.000, som aldrig har passet.
#
# Defaulten er nu p90 af det MAALTE forbrug pr. rolle, saa ni af ti koersler kan
# fuldfoere. Et loft der ikke rammes koster nul; et loft der rammes koster hele
# koerslen. Turn-loftet er uroert: nul fuldfoerte koersler har nogensinde ramt det.
_BUDGET_DEFAULT: dict[str, int] = {
    "researcher": 60_000,   # p90 maalt 57.403
    "critic": 16_000,       # p90 maalt 14.273
    "planner": 16_000,      # p90 maalt 12.792
    "watcher": 16_000,      # ingen maalinger — samme niveau som critic/planner
    "executor": 32_000,     # p90 maalt 27.745
}
#: Ukendt rolle: critic/planner-niveau — ikke det gamle 8.000, som ingen rolle passer i.
_BUDGET_FALLBACK = 16_000
def _budget_for(role: str, requested: int) -> int:
    """Rollens maalte default — og et oenske der kun maa SAENKE den.

    Budgettet er ikke en autoritet men en graense, og en graense en agent selv kan
    haeve er ikke en graense. Derfor: defaulten kommer fra maalingen, og et
    model-suppleret tal kan kun traekke forbruget NED (fx «denne opgave er lille»).
    Det er samme regel som never-escalate — udledning maa kun nedgradere.
    """
    default = _BUDGET_DEFAULT.get(str(role or "").strip().lower(), _BUDGET_FALLBACK)
    try:
        wanted = int(requested or 0)
    except (TypeError, ValueError):
        wanted = 0
    if wanted <= 0:
        return default
    return min(wanted, default)


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
           model: str, run_in_background: bool, budget_tokens: int = 0,
           team_id: str = "", member_index: int = 0) -> dict[str, Any]:
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
    # 10/11-2026: typen er et NAVN, ikke en port. Foer kastede en ukendt type
    # ValueError, saa en opgave der hed «explore» eller «verification-cost» blev
    # afvist for sit navn — maalt: `explore`/`explorer` findes i agent_registry
    # men i ingen af listerne her. Navnet gaar nu videre som rollenavn; kun
    # laese/skrive-afgoerelsen er mekanisk, og den falder ALTID mod laeseret.
    # Et ukendt navn kan derfor aldrig give skriveret — kun et bevidst valg af
    # en skrivende type kan, praecis som never-escalate kraever.
    workspace_kind, workspace = _session_scope(owner_user_id, origin_session_id)
    workspace = os.path.realpath(workspace) if workspace else ""
    has_repo = bool(workspace and os.path.exists(os.path.join(workspace, ".git")))
    writes = kind in _WRITE_TYPES
    # 10/11-2026: `workstation` manglede i saettet, og det blokerede HVER executor startet
    # fra en Desk-session — maalt: sessionens workspace_kind er "workstation" med
    # workspace_root = serverens eget repo, saa `derive()` afviste med "executor kraever et
    # lokalt repo-workspace" selv om stien ER et git-repo. Rettelsen er ikke en lempelse:
    # `has_repo`-tjekket lige nedenfor er det der afgoer, og en member-workspace der peger
    # paa en anden maskine findes ikke paa serveren og afvises derfor stadig.
    if writes and (not workspace or workspace_kind.lower() not in
                   {"container", "local", "code", "repo", "git", "workstation"}):
        raise ValueError("executor kraever et lokalt repo-workspace paa origin-sessionen")
    if writes and not has_repo:
        # Worktrees have a .git file, but the facade starts from the session's source repository.
        raise ValueError("executorens workspace er ikke et git-repository")

    # Fixed, countable limits. A child Task cannot fan out in this first complete slice.
    role = _ROLE.get(kind, kind)
    budget_tokens = _budget_for(role, budget_tokens)
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
    # Team-felterne tilfoejes KUN naar de er sat. Laa de der ubetinget, fik hver
    # enkelt-agent en ny ``idem`` og dermed et nyt ``mandate_id`` — og enhver replay af
    # allerede accepteret arbejde ville braekke. Er ``team_id`` tom, er ``canonical``
    # byte-identisk med foer; det er bevist af en test der holder hashen som literal.
    if str(team_id or "").strip():
        canonical["team_id"] = str(team_id).strip()
        canonical["member_index"] = int(member_index)
    idem = "task-" + hashlib.sha256(json.dumps(canonical, sort_keys=True).encode()).hexdigest()[:32]
    mandate_id = "mnd-" + hashlib.sha256(idem.encode()).hexdigest()[:16]
    scoped_prompt = prompt
    if workspace:
        visible_root = "/work" if writes else workspace
        scoped_prompt += (f"\n\nRuntime boundary: your workspace root is {visible_root}. "
                          "Use absolute paths inside that root; paths outside it are mechanically rejected.")
    return {
        "goal": scoped_prompt, "description": description, "role": role,
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


def derive_team_id(*, owner_user_id: str, origin_session_id: str, parent_run_id: str,
                   description: str, prompt: str, team_name: str,
                   members: list[dict[str, Any]]) -> str:
    """Deterministisk ``team_id``, saa et gentaget ``Task(team=...)`` rammer den samme raekke.

    Ren funktion: ingen DB, ingen I/O — kan kaldes foer noget er dispatchet.
    """
    # Medlemmerne hashes i den bestilte raekkefoelge, ikke sorteret: ombyttede medlemmer er
    # en anden bestilling (et andet team), ikke en retry af den foerste.
    # Kun role+task indgaar, saa et senere tilfoejet felt ikke aendrer eksisterende id'er.
    canonical = {
        "owner_user_id": owner_user_id, "origin_session_id": origin_session_id,
        "parent_run_id": parent_run_id, "description": description, "prompt": prompt,
        "team_name": team_name,
        "members": [{"role": m.get("role"), "task": m.get("task")} for m in members],
    }
    return "team-" + hashlib.sha256(json.dumps(canonical, sort_keys=True).encode()).hexdigest()[:16]


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
