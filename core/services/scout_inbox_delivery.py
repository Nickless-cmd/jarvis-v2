"""Deliver terminal scout runs to Jarvis' durable inbox."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)
_SCOUT_POLICIES = frozenset({"read-only-runtime", "read-only-workstation"})


def record_scout_completion(surface: dict[str, object]) -> bool:
    """Store one non-gating inbox item per finished scout.

    The authenticated user is captured when the scout is spawned. An absent
    user is never guessed from a global owner or the current background thread.
    """
    if (str(surface.get("role") or "") != "researcher"
            or str(surface.get("tool_policy") or "") not in _SCOUT_POLICIES):
        return False
    status = str(surface.get("status") or "")
    if status not in {"completed", "failed", "blocked", "expired"}:
        return False
    context = surface.get("context") or {}
    if not isinstance(context, dict):
        return False
    user_id = str(context.get("user_id") or "").strip()
    agent_id = str(surface.get("agent_id") or "").strip()
    run = surface.get("latest_run") or {}
    if not isinstance(run, dict):
        return False
    run_id = str(run.get("run_id") or "").strip()
    if not user_id or not agent_id or not run_id:
        logger.warning("scout-resultat mangler bruger/run-id: %s", agent_id)
        return False
    goal = " ".join(str(surface.get("goal") or "").split())[:180]
    summary = " ".join(str(run.get("output_summary") or surface.get("last_error")
                           or "").split())[:450]
    label = "Scout færdig" if status == "completed" else "Scout fejlede"
    # 27/10-2026: her stod «Hent hele svaret med get_agent(agent_id=…)» — men der
    # findes intet `get_agent`-vaerktoej (grep over core/ og apps/ gav nul). Pekeren
    # var doed, og `output_sti` blev aldrig sat, saa posten havde ingen vej til
    # leverancen. Maalt paa `run-4316279150ea47ba`: beskrivelsen bar 702 tegn af en
    # tekst paa 2439, og `DAEKNING`-linjen — kontraktens egen noegle — stod i halen
    # der blev klippet. Artefakten ligger derimod paa disk, og stien kan bygges af
    # de to id'er funktionen allerede har.
    artefakt_sti = f"state/agent-artifacts/{agent_id}/{run_id}/final.txt"
    description = (f"{label}: {goal or agent_id}. {summary} "
                   f"Kørsel: {run_id}. "
                   f"Hele svaret: {artefakt_sti}")
    from core.services.inbox_state import registrer_kilde
    result = registrer_kilde(
        # The live background-job projection uses agent_id too. Sharing its
        # identity prevents a failed scout from appearing twice in the inbox.
        bruger_id=user_id, kildetype="agent_result", kilde_id=agent_id,
        kilde_ejer="jarvis", beskrivelse=description,
    )
    return str(result.get("status") or "") == "ok"
