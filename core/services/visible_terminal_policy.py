"""Single source of truth for visible task terminal decisions.

Provider attempts and SSE segments may end without the user's task being done.
This module deliberately contains no I/O so every exit path can ask the same
question before it emits ``completed`` or schedules recovery.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Final
import re


class TerminalState(str, Enum):
    COMPLETED = "completed"
    WAITING_FOR_USER = "waiting_for_user"
    RECOVERING = "recovering"
    CANCELLED = "cancelled"
    FAILED_TERMINAL = "failed_terminal"


@dataclass(frozen=True, slots=True)
class TerminalEvidence:
    exit_reason: str = "completed"
    finish_reason: str = ""
    forced_finalize: bool = False
    pending_tool_intent: bool = False
    explicit_user_cancel: bool = False
    waiting_for_user: bool = False
    incompletion_evidence: bool = False
    recovery_attempt: int = 0
    recovery_limit: int = 3


@dataclass(frozen=True, slots=True)
class TerminalDecision:
    state: TerminalState
    reason: str
    should_continue: bool
    notify: bool
    stop_reason: str


_DSML_TOOL_INTENT_RE = re.compile(
    r"<｜｜DSML｜｜\s*(?:tool_calls|calls)\s*>|"
    r"<｜｜DSML｜｜\s*invoke\b",
    re.IGNORECASE,
)


def has_pending_tool_intent(text: str | None) -> bool:
    return bool(text and _DSML_TOOL_INTENT_RE.search(str(text)))


def is_non_retryable_recovery_reason(reason: str | None) -> bool:
    """Reject retries for deterministic request and local-code failures."""
    value = str(reason or "")
    return bool(re.search(
        r"\bhttp\s+400\b|\b400 bad request\b|\bname\s+['\"]?[^'\"]+['\"]?\s+is not defined\b",
        value, re.I,
    ))


def is_recoverable_exit_reason(reason: str | None) -> bool:
    value = str(reason or "").strip().lower()
    if is_non_retryable_recovery_reason(value):
        return False
    if not value or value == "completed":
        return False
    if value in {"user-cancelled", "user-steer-stop", "user-steer-stop-mid-stream"}:
        return False
    # En model der ikke HAR en followup-adapter, får den ikke af at prøve igen.
    # Grunden stod på listen fra før der fandtes en dispatcher, hvor
    # «genoptagelig» kun var en besked på skærmen. Med varig genoptagelse (17/9-
    # 2026) blev den til en handling: samme tur startes igen med samme
    # `provider_override`, rammer nøjagtig samme mur, og bruger tre forsøg plus
    # en slutrunde på et udfald der er afgjort på forhånd. Det er ikke en
    # midlertidig fejl, det er en egenskab ved den valgte model — så turen
    # lukkes med det svar der ER, og `recovery_notice` siger hvorfor.
    if value == "provider-not-supported":
        return False
    return (
        value == "budget-opbrugt"
        or value in {"shutdown", "completed-truncated",
                     "pending-tool-intent", "forced-finalize-unverified"}
        or value.startswith("interrupted:")
        or value.startswith("early-exit-")
        or value.startswith("provider-")
        or value.startswith("round-")
        or value.startswith("turn-")
        or value.startswith("research-")
        or value.startswith("runtime-")
        or value.startswith("unhandled:")
        or value.startswith("relay_")
        # Breakeren åbnede og der var ingen fallback tilbage. Turen er IKKE
        # færdig — den blev stoppet af et værn. Uden den her blev et
        # «breaker-open»-segment lukket som `end_turn`, altså som et helt svar
        # (fundet 17/9-2026 da fejlklasserne blev kørt igennem).
        or value == "breaker-open"
    )


#: Grunde hvor et skrevet svar IKKE er bevis for at opgaven er færdig.
#:
#: Fælles for dem: afslutningen blev TVUNGEN eller AFKORTET — den var ikke
#: modellens eget valg. Runnet skriver et svar i alle fire tilfælde (det ER hvad
#: en afslutning gør), men svaret er ikke opgaven løst, og `recovery_notice`
#: lover derfor «Jarvis fortsætter automatisk fra sit checkpoint».
SVAR_ER_IKKE_BEVIS: Final[frozenset[str]] = frozenset({
    "forced-finalize-unverified",
    "completed-truncated",
    "budget-opbrugt",
    "breaker-open",
})


def svar_beviser_faerdig(reason: str | None) -> bool:
    """Er et svar fra et run med denne grund BEVIS for at opgaven er færdig?

    Nej for de grunde hvor afslutningen blev fremtvunget eller afkortet: der
    skriver runnet et svar, men svaret er ikke beviset — det er netop dét
    `recovery_notice` lover at fortsætte forbi.

    Ja for alt andet, inklusive `shutdown` og `pending-tool-intent`, hvor runnet
    nåede at afslutte sin egen tur, og svaret derfor ER svaret.

    Grænsen er målt, ikke gættet. 10/10-2026 gav et `pending-tool-intent`-run et
    KOMPLET svar, og en genoptagelse oveni gav Bjørn to svar på én besked — den
    grund hører derfor ikke her. 14/10-2026 blev `visible-c1bafe9b` tvunget til
    slutrunde efter 18 runder, skrev sit svar, og blev droppet af netop
    `_runnet_har_svaret`: tre gange på én dag i én samtale, hver gang med et
    varsel der lovede en fortsættelse der aldrig kom.
    """
    value = str(reason or "").strip().lower()
    if not value:
        return True
    return value not in SVAR_ER_IKKE_BEVIS


def classify_terminal(evidence: TerminalEvidence) -> TerminalDecision:
    reason = str(evidence.exit_reason or "").strip() or "unknown"
    if evidence.explicit_user_cancel or reason in {
        "user-cancelled", "user-steer-stop", "user-steer-stop-mid-stream",
    }:
        return TerminalDecision(
            TerminalState.CANCELLED, reason, False, False, "cancelled")
    if evidence.waiting_for_user:
        return TerminalDecision(
            TerminalState.WAITING_FOR_USER, reason, False, True, "waiting_for_user")
    if is_non_retryable_recovery_reason(reason):
        return TerminalDecision(
            TerminalState.FAILED_TERMINAL, reason, False, True, "failed_terminal")

    recovery_reason = ""
    if evidence.pending_tool_intent:
        recovery_reason = "pending-tool-intent"
    elif evidence.forced_finalize and evidence.incompletion_evidence:
        recovery_reason = "forced-finalize-unverified"
    elif str(evidence.finish_reason or "").strip().lower() == "length":
        recovery_reason = "completed-truncated"
    elif is_recoverable_exit_reason(reason):
        recovery_reason = reason
    elif evidence.forced_finalize and reason != "completed":
        recovery_reason = reason

    if recovery_reason:
        if int(evidence.recovery_attempt) >= max(0, int(evidence.recovery_limit)):
            return TerminalDecision(
                TerminalState.FAILED_TERMINAL, recovery_reason,
                False, True, "failed_terminal")
        return TerminalDecision(
            TerminalState.RECOVERING, recovery_reason,
            True, True, "recovering")

    return TerminalDecision(
        TerminalState.COMPLETED, reason, False, False, "end_turn")


def recovery_notice(reason: str, *, continuing: bool = True) -> dict[str, object]:
    descriptions = {
        "budget-opbrugt": "Arbejdsvinduets rundebudget blev brugt.",
        "pending-tool-intent": "Jarvis havde stadig et vaerktoejskald klar.",
        "completed-truncated": "Modellens svar blev afkortet.",
        "shutdown": "Jarvis-runtime genstarter.",
        "provider-not-supported": "Den valgte model kunne ikke fortsaette vaerktoejssporet.",
        "forced-finalize-unverified": "En tvungen slutrunde manglede bevis for at opgaven var faerdig.",
        "relay_source_idle_timeout": "Svar-kilden var tavs ud over det haarde sikkerhedsloft.",
        "relay_source_closed": "Svar-kilden lukkede uden en normal afslutning.",
        # 24/9-2026: uden disse faldt begge tilbage paa standardteksten, og den
        # lover «checkpointet er bevaret» om noget der netop ER opgivet.
        "genoptagelses-vinduet udloeb": (
            "Opgaven naaede aldrig at blive genoptaget inden for et doegn."),
        # 3/10-2026: genoptagelsen blev FORSOEGT og budgettet brugt op (typisk
        # `shutdown` midt i et forsoeg). Uden denne faldt den tilbage paa
        # standardteksten, der lover at checkpointet kan genoptages — om
        # netop det der er opgivet.
        "genoptagelses-forsoegene-opbrugt": (
            "Forsoegene paa at genoptage opgaven blev brugt op."),
    }
    raa = str(reason or "")
    if raa.startswith("opgivet efter aftale"):
        return {
            "state": "failed_terminal",
            "reason": raa,
            "message": "Opgaven blev opgivet efter aftale. Skriv den igen hvis "
                       "den stadig skal laves.",
            "continuing": False,
        }
    detail = descriptions.get(raa, "Det aktuelle run-segment sluttede foer opgaven.")
    if raa == "shutdown" and continuing:
        action = "Checkpointet er bevaret til genoptagelse efter genstart."
    elif raa in {"genoptagelses-vinduet udloeb", "genoptagelses-forsoegene-opbrugt"}:
        # Begge er OPGIVET: der er intet at vente paa. Beskeden skal sige hvad
        # han kan goere i stedet — ikke love at checkpointet kan genoptages.
        action = "Skriv den igen hvis den stadig skal laves."
    else:
        action = "Jarvis fortsaetter automatisk fra sit checkpoint." if continuing else (
            "Checkpointet er bevaret, men automatisk recovery er opbrugt.")
    return {
        "state": "recovering" if continuing else "failed_terminal",
        "reason": str(reason or "unknown"),
        "message": f"{detail} {action}",
        "continuing": bool(continuing),
    }
