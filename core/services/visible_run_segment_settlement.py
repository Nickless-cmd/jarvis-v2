"""Ét sted hvor et unormalt segment-ophør bliver durabelt — før noget lukkes.

Opgave 3 i planen for varig genoptagelse. `visible_runs.py` havde sin egen
afslutning pr. udgang: provider-fejl, breaker, tavshed, tidsloft, opbrugte
forsøg, relay-tavshed, maks runder, tvungen slutrunde, en almindelig
undtagelse, `GeneratorExit` og en mislykket detached-spawn. Hver af dem
besluttede selv hvad turen blev til, og først bagefter — hvis overhovedet —
blev noget skrevet ned.

To ting kræver at det samles:

* **Rækkefølgen.** Den durable post skal ligge FØR den terminale SSE. Ellers
  kan processen dø i mellemrummet, og så har klienten set en afslutning som
  ingen journal kender.
* **Én ejer af fortsættelsen.** Når hver udgang selv kunne starte en
  fortsættelse, kunne to af dem gøre det for samme tur.

Modulet er bevidst tyndt: det oversætter kendsgerningerne til den
`TerminalEvidence` politikken allerede forstår, kalder koordinatoren fra
opgave 2, og giver kalderen både dommen og den besked der skal sendes.
Selve klassifikationen bor stadig ét sted (`visible_terminal_policy`).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from core.services.visible_run_recovery_coordinator import (
    FailureClass,
    RecoverySettlement,
    RecoverySettlementRequest,
    settle_segment,
)
from core.services.visible_run_terminal_recovery import has_incompletion_evidence
from core.services.visible_terminal_policy import (
    TerminalDecision,
    TerminalEvidence,
    TerminalState,
    has_pending_tool_intent,
    recovery_notice,
)

logger = logging.getLogger("uvicorn.error")


#: Hvilken slags fejl en exit-grund er. Klassen bruges til telemetri og til at
#: vælge hvem der må genoptage — den ændrer ALDRIG dommen, som stadig kommer
#: fra `classify_terminal`. Ukendte grunde er `RUNTIME`: det er den klasse der
#: hverken lover at en udbyder svigtede eller at processen døde.
_KLASSE_PRAEFIKS: tuple[tuple[str, FailureClass], ...] = (
    ("provider-", FailureClass.PROVIDER),
    ("relay_source_", FailureClass.WATCHDOG),
    ("round-", FailureClass.WATCHDOG),
    ("turn-", FailureClass.WATCHDOG),
    ("research-", FailureClass.RESEARCH),
    ("interrupted:", FailureClass.RUNTIME),
    ("early-exit-", FailureClass.RUNTIME),
)
_KLASSE_EKSAKT: dict[str, FailureClass] = {
    "shutdown": FailureClass.PROCESS,
    "user-cancelled": FailureClass.CANCELLATION,
    "user-steer-stop": FailureClass.CANCELLATION,
    "user-steer-stop-mid-stream": FailureClass.CANCELLATION,
    "breaker-open": FailureClass.PROVIDER,
    "provider-not-supported": FailureClass.PROVIDER,
    "budget-opbrugt": FailureClass.RUNTIME,
    "pending-tool-intent": FailureClass.RUNTIME,
    "forced-finalize-unverified": FailureClass.RUNTIME,
    "completed-truncated": FailureClass.PROVIDER,
}


def failure_class_for(exit_reason: str) -> FailureClass:
    """Grundens klasse. Ukendt → `RUNTIME`; vi gætter ikke på en udbyder."""
    value = str(exit_reason or "").strip().lower()
    if value in _KLASSE_EKSAKT:
        return _KLASSE_EKSAKT[value]
    # En timeout er vagthundens dom, ikke udbyderens. `provider-round-timeout`
    # begynder med `provider-`, men det var VORES ur der løb ud — udbyderen
    # nåede aldrig at svare hverken ja eller nej.
    if "timeout" in value or "idle" in value:
        return FailureClass.WATCHDOG
    for praefiks, klasse in _KLASSE_PRAEFIKS:
        if value.startswith(praefiks):
            return klasse
    return FailureClass.RUNTIME


@dataclass(frozen=True, slots=True)
class SegmentUdfald:
    """Dommen, den durable post, og hvad kalderen skal sende ud."""

    decision: TerminalDecision
    exit_reason: str
    event_name: str
    event_payload: dict[str, object]
    record: dict[str, object]
    dispatch_due: bool
    failure_class: FailureClass
    final_synthesis_required: bool = False
    #: Kunne journalen ikke skrives? Så er dette segment IKKE genoptageligt,
    #: og kalderen skal sige det højt frem for at love en fortsættelse.
    durable_write_failed: bool = False


def settle_user_stop(*, run_id: str, session_id: str = "", task_id: str = "",
                      reason: str = "user-cancelled") -> SegmentUdfald:
    """Brugeren trykkede stop. Det er endeligt — og skal skrives ned FØRST.

    Opgave 5 (17/9-2026). Før blev kørslen afbrudt, og journalen fik det at
    vide bagefter, hvis nogen nåede det. Et stop der ikke er skrevet ned, ser
    ud som en afbrudt tur — og en afbrudt tur bliver genoptaget. Brugeren ville
    altså se sit eget stop starte igen af sig selv.
    """
    return settle_segment_exit(
        run_id=run_id, session_id=session_id, task_id=task_id,
        exit_reason=reason, explicit_user_cancel=True,
        failure_class=FailureClass.CANCELLATION,
        summary="stoppet af brugeren",
    )


def settle_segment_exit(
    *,
    run_id: str,
    session_id: str,
    exit_reason: str,
    final_text: str = "",
    finish_reason: str = "",
    forced_finalize: bool = False,
    pending_tool_intent: bool = False,
    explicit_user_cancel: bool = False,
    waiting_for_user: bool = False,
    recovery_attempt: int = 0,
    recovery_limit: int = 3,
    task_id: str = "",
    summary: str = "",
    checkpoint_ref: str = "",
    generation: int | None = None,
    owner: str = "",
    final_synthesis_attempted: bool = False,
    failure_class: FailureClass | None = None,
) -> SegmentUdfald:
    """Gør segmentets ophør durabelt og sig hvad der skal sendes.

    Kaldes FØR den terminale SSE. Kaster aldrig: en journal der ikke kan
    skrives må ikke tage svaret med sig — men den må heller ikke lyve, så
    `durable_write_failed` sættes, og beskeden siger at der ikke fortsættes.
    """
    pending = bool(pending_tool_intent) or has_pending_tool_intent(final_text)
    evidence = TerminalEvidence(
        exit_reason=str(exit_reason or "completed"),
        finish_reason=str(finish_reason or ""),
        forced_finalize=bool(forced_finalize),
        pending_tool_intent=pending,
        explicit_user_cancel=bool(explicit_user_cancel),
        waiting_for_user=bool(waiting_for_user),
        incompletion_evidence=has_incompletion_evidence(final_text),
        recovery_attempt=int(recovery_attempt),
        recovery_limit=int(recovery_limit),
    )
    klasse = failure_class or failure_class_for(exit_reason)
    anmodning = RecoverySettlementRequest(
        task_id=str(task_id or run_id),
        run_id=str(run_id),
        session_id=str(session_id),
        evidence=evidence,
        failure_class=klasse,
        summary=str(summary or exit_reason or ""),
        checkpoint_ref=str(checkpoint_ref or ""),
        generation=generation,
        owner=str(owner or ""),
        final_synthesis_attempted=bool(final_synthesis_attempted),
    )
    try:
        settlement: RecoverySettlement = settle_segment(anmodning)
    except Exception:
        # Journalen svigtede. Dommen kan vi stadig give — men vi må IKKE love
        # en fortsættelse ingen har skrevet ned.
        logger.warning("segment-settlement kunne ikke skrives for run=%s", run_id,
                       exc_info=True)
        from core.services.visible_terminal_policy import classify_terminal
        dom = classify_terminal(evidence)
        grund = dom.reason or str(exit_reason or "")
        besked = recovery_notice(grund, continuing=False)
        besked["message"] = (
            f"{besked.get('message', '')} Genoptagelses-journalen kunne ikke skrives, "
            "så segmentet fortsætter ikke af sig selv."
        ).strip()
        return SegmentUdfald(
            decision=TerminalDecision(TerminalState.FAILED_TERMINAL, grund,
                                      False, True, "failed_terminal"),
            exit_reason=f"failed-terminal:{grund}",
            event_name="run_recovery",
            event_payload={"type": "run_recovery", **besked},
            record={},
            dispatch_due=False,
            failure_class=klasse,
            durable_write_failed=True,
        )

    dom = settlement.decision
    grund = dom.reason or str(exit_reason or "")
    if dom.state is TerminalState.RECOVERING:
        return SegmentUdfald(
            decision=dom, exit_reason=grund, event_name="run_recovery",
            event_payload={"type": "run_recovery", **settlement.notice},
            record=settlement.record, dispatch_due=settlement.dispatch_due,
            failure_class=klasse,
            final_synthesis_required=settlement.final_synthesis_required,
        )
    if dom.state is TerminalState.FAILED_TERMINAL:
        return SegmentUdfald(
            decision=dom, exit_reason=f"failed-terminal:{grund}",
            event_name="run_recovery",
            event_payload={"type": "run_recovery", **settlement.notice},
            record=settlement.record, dispatch_due=False, failure_class=klasse,
        )
    return SegmentUdfald(
        decision=dom, exit_reason=str(exit_reason or "completed"),
        event_name="", event_payload={}, record=settlement.record,
        dispatch_due=False, failure_class=klasse,
    )
