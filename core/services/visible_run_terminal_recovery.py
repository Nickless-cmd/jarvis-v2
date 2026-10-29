"""Resolve whether an agentic run segment completed or needs recovery."""
from __future__ import annotations

from dataclasses import dataclass
import re

from core.services.visible_terminal_policy import (
    TerminalDecision,
    TerminalEvidence,
    TerminalState,
    classify_terminal,
    has_pending_tool_intent,
    recovery_notice,
)


#: Negationen må ikke krydse en sætningsgrænse.
#:
#: Målt 29/10-2026 på et rigtigt svar (8.710 tegn, komplet, sluttede med et
#: spørgsmål til Bjørn): dommen matchede `«ikke er min.» + «Verificeret»` —
#: altså en negation i ÉN sætning og ordet «Verificeret» som overskrift i det
#: NÆSTE afsnit — og læste det som «ikke verificeret». `re.DOTALL` gjorde at
#: prik og linjeskift talte som ét vilkårligt tegn.
#:
#: Konsekvensen var ikke kosmetisk: `forced_finalize` + `incompletion_evidence`
#: → `forced-finalize-unverified` → `SVAR_ER_IKKE_BEVIS` → RECOVERING. Svaret
#: blev vist for Bjørn, og turen blev derefter genoptaget oveni, så han ikke
#: nåede at svare før den næste mig skrev igen.
#:
#: Samme fejlklasse som `_CONTINUING_ACTION_RE` nedenfor blev rettet for
#: 26/10-2026: en vagt der læser tekst på tværs af sætninger svarer om noget
#: andet end det den måler. Reglen er derfor den samme i begge: `[^.!?\n]`.
#: En ægte uafsluttethed («det er ikke færdigt endnu») står i samme sætning.
_NEGATED_COMPLETION_RE = re.compile(
    r"\b(?:ikke|ej|aldrig|not|never)\b[^.!?\n]{0,32}"
    r"\b(?:færdig(?:t)?|afsluttet|fuldført|implementeret|rettet|løst|verificeret|"
    r"completed|finished|done|fixed|implemented|verified)\b",
    re.IGNORECASE,
)


#: Kun MINE egne løfter om fortsat arbejde tæller som uafsluttethed.
#:
#: Målt 26/10-2026: den gamle form krævede kun verbet + «nu», uden subjekt.
#: Derfor matchede den beskrivelser af et VÆRKTØJ der kører — «Kanalen er åben,
#: så `bash` kører nu på CheifOne», «Kommandoen kører nu i baggrunden» — og
#: gjorde et FÆRDIGT svar til `forced-finalize-unverified`. 124 runs bar det
#: spor; 65 af dem var terminalt opgivet i de sidste 14 dage, hver efter at
#: brugeren havde fået sit svar. Jo mere ærligt svaret beskrev hvad der ikke
#: virkede, jo større var chancen for at turen blev stemplet fejlet.
#:
#: Førsteperson er nu påkrævet, i begge ordstillinger («jeg … samler nu» og
#: «samler nu … jeg»), og må ikke krydse en sætningsgrænse.
_FP = r"\b(?:jeg|vi)\b"
_VERB = (r"\b(?:samler|fortsætter|fortsaetter|undersøger|undersoeger|tester|"
         r"implementerer|retter|kører|koerer|afventer)\s+(?:nu|stadig|videre)\b")
_CONTINUING_ACTION_RE = re.compile(
    rf"{_FP}[^.!?\n]{{0,60}}?{_VERB}|{_VERB}[^.!?\n]{{0,40}}?{_FP}",
    re.IGNORECASE,
)


def has_incompletion_evidence(text: str | None) -> bool:
    """Explicit unfinished work; absence of a completion keyword is not proof."""
    value = str(text or "")
    if not value.strip():
        return True
    return bool(
        _NEGATED_COMPLETION_RE.search(value)
        or _CONTINUING_ACTION_RE.search(value)
    )


@dataclass(frozen=True, slots=True)
class AgenticExitResolution:
    decision: TerminalDecision
    exit_reason: str
    event_name: str
    event_payload: dict[str, object]


def resolve_agentic_exit(
    *,
    exit_reason: str,
    final_text: str,
    finish_reason: str = "",
    forced_finalize: bool = False,
    pending_tool_intent: bool = False,
    recovery_attempt: int = 0,
    recovery_limit: int = 3,
) -> AgenticExitResolution:
    pending = bool(pending_tool_intent) or has_pending_tool_intent(final_text)
    decision = classify_terminal(TerminalEvidence(
        exit_reason=exit_reason,
        finish_reason=finish_reason,
        forced_finalize=forced_finalize,
        pending_tool_intent=pending,
        incompletion_evidence=has_incompletion_evidence(final_text),
        recovery_attempt=recovery_attempt,
        recovery_limit=recovery_limit,
    ))
    normalized = str(exit_reason or "completed")
    if decision.state is TerminalState.RECOVERING:
        normalized = decision.reason
        return AgenticExitResolution(
            decision, normalized, "run_recovery",
            {"type": "run_recovery", **recovery_notice(normalized, continuing=True)},
        )
    if decision.state is TerminalState.FAILED_TERMINAL:
        normalized = f"failed-terminal:{decision.reason}"
        return AgenticExitResolution(
            decision, normalized, "run_recovery",
            {"type": "run_recovery", **recovery_notice(decision.reason, continuing=False)},
        )
    return AgenticExitResolution(decision, normalized, "", {})
