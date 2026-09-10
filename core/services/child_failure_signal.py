"""Et barn der doer, skal kunne SES — Fase 5.

«provider removal/new-start rejection and child failure are observable.»

## Hvad der manglede

Maalt 10/9-2026: barnets skaebne bliver PAENT registreret — `agent_registry`
faar status, `last_error` og et tidsstempel, og der skrives en `agent_message`.
Men NUL nerver og NUL incidents. Data laa i basen; ingen overflade viste den,
og ingen ville opdage at raten steg.

Det er samme klasse som cut-off-signalet der kun gik i en flygtig ring-buffer:
registreret, aldrig set. Panelet viste derfor aldrig noget.

## Hvad tallene sagde

96 boern uden raad. Explore's egne (budget 0): 61 gennemfoerte, 3 ryddet op som
staaende efter ~47 timer, 1 tabt til en procesgenstart. De 17 udloebne har alle
budget > 0 og kommer altsaa fra `spawn_agent_task`, ikke fra explore — og de
braender langt over deres budget foer de stoppes (10.749 mod 4.000 i det
groveste tilfaelde), fordi tjekket sker EFTER forbruget, ikke foer.

Raterne er lave nu. Pointen er at kunne se hvis de holder op med at vaere det.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Hvor alvorligt er det? Et opbrugt budget er en graense der VIRKER; et barn
# der doer af en genstart er noget andet.
#
# Vaerdierne er husets egne — `db_central_incidents._SEVERITIES` kender kun
# («info», «error», «severe»). Foerste udgave brugte «warning», som faldt
# STILLE igennem til «error», saa skelnen forsvandt paa vej i basen. Testen
# fangede det ikke, fordi den maalte hvad jeg SENDTE og ikke hvad der blev
# GEMT. Verificeret paa produktionen bagefter.
_ALVOR = {"expired": "info", "cancelled": "info", "failed": "error"}


def note_child_ended(agent_id: str, *, status: str, role: str = "",
                     provider: str = "", model: str = "",
                     error: str = "", parent_run_id: str = "") -> None:
    """Sig hoejt at et barn endte uden at levere. Kaster ALDRIG.

    Kaldes kun for de udfald der IKKE er «completed» — et vellykket barn er
    ikke en haendelse.
    """
    st = str(status or "").strip().lower()
    if st in ("", "completed"):
        return
    try:
        from core.services.central_core import central
        central().observe({
            "cluster": "agents", "nerve": "child_ended",
            "agent_id": str(agent_id or ""), "status": st,
            "role": str(role or ""), "provider": str(provider or ""),
            "model": str(model or ""), "error": str(error or "")[:200],
            "parent_run_id": str(parent_run_id or ""),
        })
    except Exception:
        pass

    # Og som RIGTIG incident: observe() alene bor i en flygtig ring-buffer pr.
    # proces og er vaek ved genstart — praecis grunden til at cut-offs aldrig
    # naaede panelet. dedup: en stribe ens fejl bumper en taeller frem for at
    # oversvoemme.
    try:
        from core.runtime.db_central_incidents import record_central_incident
        record_central_incident(
            cluster="agents", nerve="child_ended",
            kind=st, severity=_ALVOR.get(st, "warning"),
            message=(f"barn endte som {st}: role={role or '?'} "
                     f"provider={provider or '?'}/{model or '?'} "
                     f"{str(error or '')[:120]}"),
            run_id=str(parent_run_id or ""),
            session_id="",
            dedup=True,
        )
    except Exception:
        logger.debug("child_failure_signal: kunne ikke skrive incident",
                     exc_info=True)


def note_from_registry(agent: dict[str, Any] | None) -> None:
    """Bekvem indgang naar man allerede har registry-raekken."""
    if not isinstance(agent, dict):
        return
    note_child_ended(
        str(agent.get("agent_id") or ""),
        status=str(agent.get("status") or ""),
        role=str(agent.get("role") or ""),
        provider=str(agent.get("provider") or ""),
        model=str(agent.get("model") or ""),
        error=str(agent.get("last_error") or ""),
        parent_run_id=str((agent.get("context") or {}).get("parent_run_id") or "")
        if isinstance(agent.get("context"), dict) else "",
    )
