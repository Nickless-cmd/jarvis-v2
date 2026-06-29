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


def note_round_retry(run_id: str, round_num: int, attempt: int, reason: str = "",
                     *, outcome: str = "", **data: Any) -> None:
    """RUND-NIVEAU RETRY (spec §4.1/S7): en forbigående runde-fejl blev retry'et
    i stedet for at dræbe turen — og om retry'en FAKTISK reddede den eller bare
    udskød døden.

    ``outcome`` ∈ {recovered, exhausted}:
      - ``recovered``  — retry'en lykkedes; turen overlevede et mid-turn-blip.
      - ``exhausted``  — total/runde-budget opbrugt; vi faldt til interruption
                         (men med checkpointed partial + ærlig note, aldrig tomt).

    Distinkte signaler så Centralen kan se om rund-retry redder (recovered-rate
    op) eller bare maskerer en haltende provider (exhausted-rate op). Self-safe."""
    _observe("round_retry", run_id, round_num=int(round_num or 0),
             attempt=int(attempt or 0), reason=str(reason or "")[:200],
             outcome=str(outcome or ""), **data)


def note_loop_complete(run_id: str, *, rounds: int = 0, exit_reason: str = "",
                       provider: str = "", model: str = "") -> None:
    """Followup-loopet sluttede → observe runder kørt + exit-grund (completed/
    interrupted/user-cancelled/...). Grundlag for 'hvor dyb er loopen typisk?'."""
    _observe("followup_loop_complete", run_id, rounds=int(rounds or 0),
             exit_reason=str(exit_reason or ""), provider=str(provider or ""),
             model=str(model or ""))


def note_empty_completion(run_id: str, *, provider: str = "", model: str = "",
                          rounds: int = 0, tools_executed: int = 0,
                          session_id: str = "", path: str = "") -> None:
    """TAVS CUT-OFF: loopet sluttede 'completed' men producerede INTET synligt svar.
    Provider-AGNOSTISK — fejlen bor i loopets håndtering af en tom sidste runde, ikke i
    nogen providers wire-format. Var fuldstændig usynlig: status=completed, ingen fejl
    → klienten så et tavst hæng bruger oplever som "afbrudt".

    `path` mærker HVOR runnet døde tomt (agentic_block | unified_checkpoint | …) så vi
    kan se hvilken terminal-sti der knækker. Ved gentagelse BUMPES den stående incident
    (recurrence + sti + tid) i stedet for at dedup'e den væk — så panelet viser et LIVE,
    hyppigt problem (Bjørn 29. jun: 'centralen fanger det ikke' = dedup skjulte frekvensen)."""
    _observe("empty_completion", run_id, provider=str(provider or ""),
             model=str(model or ""), rounds=int(rounds or 0),
             tools_executed=int(tools_executed or 0),
             session_id=str(session_id or ""), path=str(path or ""))
    try:
        from core.runtime.db_central_incidents import (
            record_central_incident, has_open_incident, bump_open_incident)
        _p = str(path or "ukendt-sti")
        if has_open_incident(cluster=_CLUSTER, nerve="empty_completion"):
            # Gentagelse → refresh + tæl op (ikke usynlig dedup).
            bump_open_incident(
                cluster=_CLUSTER, nerve="empty_completion",
                run_id=str(run_id or ""), session_id=str(session_id or ""),
                note=f"sti={_p} {provider}/{model}")
        else:
            record_central_incident(
                cluster=_CLUSTER, nerve="empty_completion", kind="silent_cutoff",
                severity="error", run_id=str(run_id or ""),
                session_id=str(session_id or ""),
                message=(f"Tavs cut-off [sti={_p}]: {int(tools_executed or 0)} "
                         f"værktøj(er) kørt, men intet svar (status=completed) — "
                         f"{provider}/{model}, {int(rounds or 0)} runde(r). "
                         f"Provider-agnostisk."))
    except Exception:
        pass


def note_resend(run_id: str, *, provider: str = "", model: str = "",
                recovered: bool = False) -> None:
    """RESEND-PÅ-TOM (Bjørn option 1): runtimen fangede en transient tom completion
    og gen-spurgte modellen ÉN gang. recovered=True hvis gen-forsøget gav et svar.
    Telemetri — viser hvor ofte tomme svar er transiente (og kureres) vs vedholdende."""
    _observe("resend", run_id, provider=str(provider or ""),
             model=str(model or ""), recovered=bool(recovered))


def note_leak(run_id: str, *, provider: str = "", model: str = "",
              chars: int = 0, reason: str = "") -> None:
    """LEAK/DUMP: modellen echoede et råt (kæmpe) tool-result som prosa-svar i stedet
    for at opsummere (Bjørns 27KB-dumps). Synlig + dedup'et incident."""
    _observe("leak", run_id, provider=str(provider or ""), model=str(model or ""),
             chars=int(chars or 0), reason=str(reason or ""))
    try:
        from core.runtime.db_central_incidents import (
            record_central_incident, has_open_incident)
        if not has_open_incident(cluster=_CLUSTER, nerve="leak"):
            record_central_incident(
                cluster=_CLUSTER, nerve="leak", kind="tool_result_dump",
                severity="warn", run_id=str(run_id or ""),
                message=(f"Leak/dump: råt tool-result som svar ({chars} tegn) — "
                         f"{provider}/{model}: {reason}"))
    except Exception:
        pass


def note_degeneration(run_id: str, *, provider: str = "", model: str = "",
                      reason: str = "", chars: int = 0) -> None:
    """MODEL-LOOP: streaming-laget fangede en runaway-repetition og dræbte den ved
    kilden (var 147KB skrald der forgiftede sessionen). Synlig nerve + dedup'et incident."""
    _observe("degeneration", run_id, provider=str(provider or ""),
             model=str(model or ""), reason=str(reason or ""), chars=int(chars or 0))
    try:
        from core.runtime.db_central_incidents import (
            record_central_incident, has_open_incident)
        if not has_open_incident(cluster=_CLUSTER, nerve="degeneration"):
            record_central_incident(
                cluster=_CLUSTER, nerve="degeneration", kind="runaway_repetition",
                severity="error", run_id=str(run_id or ""),
                message=(f"Model-repetitions-løkke dræbt ved kilden ({chars} tegn) — "
                         f"{provider}/{model}: {reason}. Var 147KB-skrald-klassen."))
    except Exception:
        pass


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
