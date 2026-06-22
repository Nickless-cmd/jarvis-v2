"""Followup-cluster — gør den agentiske followup-loop synlig i Den Intelligente Central.

Followup-loopet (visible_runs.py: ``for _agentic_round in range(_AGENTIC_MAX_ROUNDS)``)
er hvor Jarvis kalder værktøjer, får resultater og fortsætter — runde efter runde. Det er
også hvor de sværeste fejl bor: provider-followup der 400'er (copilot thinking-bug),
tomme tool-runder, loops der aldrig konvergerer. Før var KUN budget (loop.tool_budget) og
exit-grunden i en logger.info — ingen kunne pege på HVILKEN runde der fejlede og HVORFOR,
eller hvor mange runder en model i snit bruger.

Observe pr. loop-livscyklus: round-start (provider/model/exchange-dybde), round-failure
(provider-fejl pr. runde — det copilot-400 Bjørn jager), og loop-complete (runder kørt +
exit-grund). Metadata-only. Grundlag for adaptiv læring: er en provider/model ustabil i
followup, og hvor mange runder koster den typisk?

SELV-SIKKER: kaster ALDRIG ind i den hotte followup-loop.
"""
from __future__ import annotations

from typing import Any

_CLUSTER = "loop"


def _observe(nerve: str, run_id: str, **data: Any) -> None:
    try:
        from core.services.central_core import central
        central().observe({"cluster": _CLUSTER, "nerve": nerve,
                           "run_id": str(run_id or ""), **data})
    except Exception:
        pass


def note_round(run_id: str, round_num: int, provider: str = "", model: str = "",
               *, exchanges: int = 0) -> None:
    """En agentisk followup-runde startede. Metadata-only."""
    _observe("followup_round", run_id, round_num=int(round_num or 0),
             provider=str(provider or ""), model=str(model or ""),
             exchanges=int(exchanges or 0))


def note_round_failed(run_id: str, round_num: int, provider: str = "",
                      error: str = "", **data: Any) -> None:
    """En followup-runde fejlede (provider-fejl) → synlig. Det er her copilot-400 /
    thinking-bug / tomme svar lever — nu pollbar i Centralen i stedet for kun i logs."""
    _observe("followup_failed", run_id, round_num=int(round_num or 0),
             provider=str(provider or ""), error=str(error or "")[:200], **data)


def note_loop_complete(run_id: str, *, rounds: int = 0, exit_reason: str = "",
                       provider: str = "", model: str = "") -> None:
    """Followup-loopet sluttede → observe runder kørt + exit-grund (completed/
    interrupted/user-cancelled/...). Grundlag for 'hvor dyb er loopen typisk?'."""
    _observe("followup_loop_complete", run_id, rounds=int(rounds or 0),
             exit_reason=str(exit_reason or ""), provider=str(provider or ""),
             model=str(model or ""))


def followup_summary(*, window: int = 500) -> dict[str, Any]:
    """Read-only: nylig followup-loop-aktivitet (til MC). Self-safe."""
    rounds = 0
    failures = 0
    loops = 0
    total_rounds = 0
    try:
        from core.services import central_trace
        for r in central_trace.sink().recent(limit=window):
            if r.cluster != _CLUSTER:
                continue
            if r.nerve == "followup_round":
                rounds += 1
            elif r.nerve == "followup_failed":
                failures += 1
            elif r.nerve == "followup_loop_complete":
                loops += 1
                total_rounds += int((r.payload or {}).get("rounds") or 0)
    except Exception:
        pass
    avg = round(total_rounds / loops, 1) if loops else 0.0
    return {"followup_rounds": rounds, "followup_failures": failures,
            "followup_loops": loops, "avg_rounds_per_loop": avg}
