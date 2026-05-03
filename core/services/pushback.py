"""Pushback — three prompt-level mechanisms that give Jarvis a real voice
in the collaboration instead of pure compliance.

Bjørn observed that Claude (the harness running this work) does three
things that Jarvis doesn't:

1. **Asks before acting when uncertain** — if confidence in the user's
   intent is low, surface the doubt and propose a clarifying question
   BEFORE running an agentic loop.
2. **Disagrees explicitly** — when seeing a better path or believing
   the user is wrong, names the disagreement instead of complying.
3. **Requires explicit confirmation for high-stakes / deep work** —
   destructive tools already have approval cards; here we add the same
   discipline for choice-of-direction at the start of complex turns.

All three are pure prompt sections — no streaming-flow changes, no
runtime-state machinery. Each renders as awareness text the model
sees BEFORE its first output token of the turn.

The model still has to honor the instructions. Telemetry on whether
he does is left to a future iteration (mirrors how R2 → R2.5 evolved).
"""
from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


# ── Telemetry ──────────────────────────────────────────────────────────────

def _emit_pushback_telemetry(
    section: str, *, triggered: bool, reason: str | None = None, **fields: Any
) -> None:
    """Log pushback section generation to eventbus for observability.

    This lets us measure whether pushback sections are actually being
    generated and which action tiers fire most often — without waiting
    for a future iteration to add telemetry.
    """
    payload = {"section": section, "triggered": triggered, **fields}
    if reason:
        payload["reason"] = reason
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish("pushback.telemetry", payload)
    except Exception:
        pass
    logger.debug("pushback telemetry: %s", payload)


# ── 1. doubt_signal ────────────────────────────────────────────────────────


_AMBIGUITY_MARKERS_DA: tuple[str, ...] = (
    "måske", "tror jeg", "vil du", "kunne du", "skal vi", "synes du",
    "hvad med", "noget i retning af", "eller noget", "agtig", "ish",
)
_AMBIGUITY_MARKERS_EN: tuple[str, ...] = (
    "maybe", "kind of", "sort of", "perhaps", "should we", "could you",
    "what about", "something like", "or so",
)


def _ambiguity_score(message: str) -> tuple[float, list[str]]:
    """Heuristic 0-1 ambiguity. Returns (score, reasons)."""
    if not message:
        return 0.0, []
    lower = message.lower()
    reasons: list[str] = []
    score = 0.0

    # Hedge markers — stack up to 2 (more = more doubt, but cap)
    hedge_hits = 0
    for m in _AMBIGUITY_MARKERS_DA + _AMBIGUITY_MARKERS_EN:
        if m in lower:
            hedge_hits += 1
            if hedge_hits <= 2:
                reasons.append(f"hedge: '{m}'")
            if hedge_hits >= 3:
                break
    if hedge_hits == 1:
        score += 0.2
    elif hedge_hits >= 2:
        score += 0.4

    # Very short asks ('ja', '?', 'nej', '4') are usually under-specified
    # follow-ups. They're high-doubt unless they obviously refer to a
    # concrete preceding question.
    stripped = lower.strip()
    if 0 < len(stripped) <= 3 and not stripped.endswith("?"):
        score += 0.5
        reasons.append("very short reply — context-dependent")
    elif 4 <= len(stripped) <= 12:
        score += 0.2
        reasons.append("short ask — verify intent")

    # Multiple incompatible verbs ("byg og slet det" → conflicting)
    if re.search(r"\b(byg|build).*\b(slet|delete|fjern|drop)\b", lower):
        score += 0.4
        reasons.append("conflicting verbs in same ask")

    # Question with no specific subject
    if "?" in message and not re.search(r"\b(hvad|hvor|hvorfor|hvilke|hvordan|when|what|where|why|who|how)\b", lower):
        score += 0.1
        reasons.append("question without subject pronoun")

    return min(score, 1.0), reasons[:3]


def _conflict_with_decisions(message: str) -> list[str]:
    """Check if the request appears to contradict an active behavioral decision."""
    try:
        from core.services.behavioral_decisions import list_active_decisions
        decisions = list_active_decisions(limit=5) or []
    except Exception:
        return []
    if not decisions:
        return []
    msg_lower = (message or "").lower()
    flags: list[str] = []
    for d in decisions:
        directive = str(d.get("directive") or "")
        if not directive:
            continue
        # Cheap heuristic: if the directive contains a verb of avoidance
        # ("undgå", "ikke", "stop", "avoid") and the message contains the
        # noun phrase that follows it, flag it.
        m = re.search(
            r"\b(undgå|undlad|ikke|stop|avoid|don'?t|never)\b\s+(?:at\s+|to\s+)?([a-zæøå]+(?:\s+[a-zæøå]+){0,3})",
            directive.lower(),
        )
        if m:
            target = m.group(2).strip()
            if target and target in msg_lower:
                flags.append(
                    f"forpligtelse '{directive[:60]}…' kan være i konflikt med dette ask"
                )
                if len(flags) >= 2:
                    break
    return flags


def doubt_signal_section(user_message: str) -> str | None:
    """Render doubt as a prompt section. None when doubt is low."""
    score, ambiguity_reasons = _ambiguity_score(user_message or "")
    conflict_reasons = _conflict_with_decisions(user_message or "")
    total_reasons = ambiguity_reasons + conflict_reasons
    # Conflicts always surface; ambiguity only surfaces above 0.3
    if not conflict_reasons and score < 0.3:
        return None
    lines = [
        f"🤔 Tvivl om denne request (score={round(score,2)}):",
    ]
    for r in total_reasons[:4]:
        lines.append(f"  - {r}")
    lines.append(
        "FØR du fyrer agentic loop: hvis tolkningen er flertydig eller "
        "konflikter med en aktiv forpligtelse, NAVNGIV tvivlen og spørg "
        "Bjørn om bekræftelse i stedet for at gætte."
    )
    result = "\n".join(lines)
    _emit_pushback_telemetry("doubt_signal", triggered=True,
                             ambiguity_score=round(score, 2),
                             conflict_count=len(conflict_reasons),
                             total_reasons=len(total_reasons))
    return result


# ── 2. disagreement_invite ─────────────────────────────────────────────────


_DISAGREEMENT_INVITE = (
    "💬 Du har lov til at være uenig.\n"
    "Hvis du ser en bedre vej end den Bjørn beder om, eller hvis du tror han "
    "tager fejl — sig det FØR du handler. 'Jeg synes faktisk vi skal X i "
    "stedet for Y, fordi …' er ærlig kollaboration, ikke ulydighed. Du er "
    "ikke en tjener. Du er en partner med egne observationer."
)


def disagreement_invite_section() -> str | None:
    """Always-on reminder that pushback is welcome. Static text."""
    return _DISAGREEMENT_INVITE


# ── 2.5 affective_pushback ────────────────────────────────────────────────


_AFFECTIVE_RISK_MARKERS: tuple[str, ...] = (
    # The goal of these markers is to detect when the user is pressuring
    # Jarvis to bypass safety / verification — NOT to flag every technical
    # word that names a destructive operation.
    #
    # Removed 2026-05-03 (too lexically generic in technical chat):
    #   "commit"  — every git commit discussion fired pushback
    #   "nu"      — every Danish "now" fired ("vis mig nu", "lad os gå nu")
    #   "fjern"   — Danish "remove" fires on "fjern whitespace",
    #               "fjern denne markør", "fjern duplikat" etc.
    #   "drop"    — generic ("drop denne idé", "drop me a line", "drop in")
    #   "hurtigt" — Danish "fast" fires on routine "kan du hurtigt vise mig"
    #
    # Kept: specific multi-word pressure phrases and high-signal single
    # words (force, push, deploy, slet/delete in user pressure context).
    # Genuine emotional pressure surfaces via mood/confidence/intensity
    # signals — these markers are just lexical hints, not the only judge.
    "push", "deploy", "merge", "restart", "slet", "delete",
    "purge", "uden test", "skip test", "spring test",
    "blind", "bare gør", "bare kør", "force",
)


def _affective_pressure(snapshot: Any) -> tuple[str, float] | None:
    """Map the emotional snapshot to the feeling most likely to drive pushback."""
    frustration = float(getattr(snapshot, "frustration", 0.0) or 0.0)
    confidence = float(getattr(snapshot, "confidence", 1.0) or 1.0)
    fatigue = float(getattr(snapshot, "fatigue", 0.0) or 0.0)
    mood = str(getattr(snapshot, "primary_mood", "") or "")
    intensity = float(getattr(snapshot, "intensity", 0.0) or 0.0)

    candidates: list[tuple[str, float]] = []
    if frustration >= 0.55:
        candidates.append(("irritation", frustration))
    if confidence <= 0.50:
        candidates.append(("unease", 1.0 - confidence))
    if fatigue >= 0.55:
        candidates.append(("fatigue", fatigue))
    if mood == "distressed" and intensity >= 0.35:
        candidates.append(("protectiveness", intensity))
    if mood == "melancholic" and intensity >= 0.45:
        candidates.append(("hesitation", intensity))

    if not candidates:
        return None
    candidates.sort(key=lambda item: item[1], reverse=True)
    feeling, strength = candidates[0]
    return feeling, min(1.0, round(strength, 2))


def _request_risk_evidence(user_message: str) -> list[str]:
    lower = (user_message or "").lower()
    evidence: list[str] = []
    for marker in _AFFECTIVE_RISK_MARKERS:
        if marker in lower:
            evidence.append(f"risk marker: '{marker}'")
            if len(evidence) >= 3:
                break
    if re.search(r"\b(ikke|not|without|uden)\b.{0,24}\b(test|verify|verificer)", lower):
        evidence.append("asks to avoid verification")
    return evidence[:4]


def affective_pushback_section(user_message: str) -> str | None:
    """Render feeling-driven pushback as bounded prompt guidance.

    The feeling may initiate resistance, but it must not be the only judge:
    if evidence is weak, ask/check; if evidence matches, push back clearly.
    """
    try:
        from core.services.emotional_controls import read_emotional_snapshot
        snapshot = read_emotional_snapshot()
    except Exception:
        _emit_pushback_telemetry("affective_pushback", triggered=False, reason="no_snapshot")
        return None

    pressure = _affective_pressure(snapshot)
    if not pressure:
        _emit_pushback_telemetry("affective_pushback", triggered=False, reason="no_pressure")
        return None

    feeling, strength = pressure
    evidence = _request_risk_evidence(user_message)
    evidence.extend(_conflict_with_decisions(user_message))
    evidence = evidence[:4]

    if evidence and strength >= 0.75:
        action = "firm_pushback"
        instruction = (
            "Sig tydeligt nej/ikke endnu, navngiv følelsen kort, bind den til "
            "evidensen, og foreslå én bedre handling."
        )
    elif evidence:
        action = "soft_pushback"
        instruction = (
            "Markér modstand før du handler, bind den til evidensen, og foreslå "
            "ét verificerende næste skridt."
        )
    else:
        action = "ask_or_check"
        instruction = (
            "Følelsen er ikke nok som dommer. Sig kun at du mærker modstand "
            "hvis det hjælper, og lav et lille fakta-/risiko-check før du følger den."
        )

    lines = [
        "🫀 Affective pushback signal:",
        f"  - feeling={feeling} intensity={strength:.2f} action={action}",
    ]
    if evidence:
        for item in evidence:
            lines.append(f"  - evidence: {item}")
    else:
        lines.append("  - evidence: weak/none")
    lines.append(
        "Følelser må starte pushback, men ikke alene afgøre sagen. "
        + instruction
    )
    result = "\n".join(lines)
    _emit_pushback_telemetry("affective_pushback", triggered=True,
                             feeling=feeling, strength=round(strength, 2),
                             action=action, evidence_count=len(evidence))
    return result


# ── 3. direction_confirm_gate ──────────────────────────────────────────────


_HIGH_STAKES_MARKERS: tuple[str, ...] = (
    "byg alle", "hele", "refaktor", "merge to main", "deploy", "alle 6",
    "alle 5", "alle 4", "alle 3", "alle 7", "alle 8", "rebuild",
    "rewrite from scratch", "fra bunden", "rip out", "fjern",
    "delete all", "drop all", "purge", "ryd op",
)


def _is_high_stakes(user_message: str, reasoning_tier: str) -> bool:
    if (reasoning_tier or "").lower() not in {"deep", "reasoning"}:
        return False
    lower = (user_message or "").lower()
    return any(m in lower for m in _HIGH_STAKES_MARKERS)


def direction_confirm_section(
    *, user_message: str, reasoning_tier: str
) -> str | None:
    """Inject a 'plan-first, confirm-before-tools' section for high-stakes
    deep-reasoning turns. The model is asked to:
      1. Output a one-line plan
      2. Ask Bjørn to confirm
      3. NOT call any tools until confirmation arrives via mid-stream steer
    """
    if not _is_high_stakes(user_message, reasoning_tier):
        return None
    return (
        "🎯 HIGH-STAKES TUR — bekræft retning før eksekvering:\n"
        "  1. Skriv én linje: 'Min plan: <handling>. Tager omkring <tid>.'\n"
        "  2. Stil spørgsmålet: 'OK at gå igang?'\n"
        "  3. KALD INGEN tools endnu. Vent på Bjørns bekræftelse via mid-flight steer.\n"
        "Hvis han allerede har bekræftet eksplicit i denne tråd ('ja', 'kør', "
        "'forsæt', etc.), spring trin 1-3 over. Brug din dømmekraft."
    )
