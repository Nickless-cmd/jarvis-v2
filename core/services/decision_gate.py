"""Decision gate — pre-execution decision conflict detection.

Cross-checks a user request against active behavioral decisions
BEFORE execution, not just in the prompt. If a tool call would
contradict an active decision, the gate blocks it and surfaces
the conflict for user confirmation.

This gives decisions "teeth" — they can actually prevent actions
that violate commitments, not just be text in the prompt.
"""
from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


# Tools whose results are used to check decisions (not blocked themselves).
_META_TOOLS = frozenset({
    "decision_list", "decision_get", "decision_review",
    "list_proposals", "list_plans", "todo_list",
})


def check_decision_gate(
    tool_name: str,
    tool_args: dict[str, Any] | None = None,
    user_message: str = "",
) -> tuple[bool, str | None]:
    """Check if a tool call conflicts with active decisions.

    Returns (allowed, reason). If allowed=False, the call is blocked
    and the reason should be surfaced to the user.

    Logic:
    1. Meta/decision tools are always allowed.
    2. Load active decisions.
    3. For each decision, check if the tool call + args would violate it.
    4. If conflict found → block with reason.
    5. Otherwise → allow.
    """
    if tool_name in _META_TOOLS:
        return True, None
    if ejeren_har_sagt_alligevel(user_message):
        return True, None

    try:
        from core.services.behavioral_decisions import list_active_decisions
        # ALLE aktive, ikke de foerste ti (7/9-2026). Der er 45 aktive, saa 35
        # blev aldrig tjekket — samme fejl som anmelderens limit=20 mod 45.
        # Sikkert foerst nu, hvor maalet skal fylde noget: med den gamle
        # matcher ville flere beslutninger bare give flere falske blokeringer.
        decisions = list_active_decisions(limit=_ALLE_AKTIVE) or []
    except Exception as _exc:
        # Fail-open synlighed (audit 2026-07-04): kan gaten ikke læse aktive beslutninger
        # tillader den handlingen — men det MÅ ikke være tavst, ellers kan Jarvis bryde
        # egne forpligtelser uden spor. Flag fail-open FØR return. Self-safe: incident-
        # loggen kaster aldrig, og fail-open-adfærden (return True, None) er uændret.
        try:
            from core.runtime.db_central_incidents import record_central_incident
            record_central_incident(
                cluster="commit", nerve="decision_gate", kind="fail_open",
                severity="error",
                message=f"check_decision_gate kunne ikke læse beslutninger → fail-OPEN "
                        f"for tool={tool_name}: {type(_exc).__name__}: {_exc}"[:300],
            )
        except Exception:
            pass
        return True, None

    if not decisions:
        return True, None

    # Build a combined context string from tool name + args + user message
    context = _build_context(tool_name, tool_args, user_message)

    conflicts: list[str] = []
    for d in decisions:
        directive = str(d.get("directive") or "").strip()
        if not directive:
            continue
        conflict = _detect_conflict(directive, context, d)
        if conflict:
            decision_id = str(d.get("decision_id") or "unknown")
            conflicts.append(f"[{decision_id[:8]}] {directive[:60]} — {conflict}")

    if not conflicts:
        return True, None

    # Multiple conflicts: surface the top 2
    top = conflicts[:2]
    reason = (
        f"DECISION GATE: {len(conflicts)} aktiv(e) forpligtelse(r) i konflikt. "
        + " | ".join(top)
        + " — Sig 'alligevel' for at gennemtvinge."
    )

    # Emit telemetry
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish("decision_gate.conflict", {
            "tool_name": tool_name,
            "conflict_count": len(conflicts),
            "conflicts": conflicts[:3],
        })
    except Exception:
        pass

    return False, reason


# Grader af blok (Commit-cluster, 2026-06-22): en konflikt med en HØJ-prioritets-
# beslutning hård-blokerer (RED); en konflikt med kun lav-prioritets-beslutninger blød-
# advarer men tillader (YELLOW). Tærskel = 50 (= create_decision-default), så nuværende
# blokerings-adfærd bevares for normale beslutninger; kun eksplicit lav-prioritet softer.
_HARD_BLOCK_PRIORITY = 50
_ALLE_AKTIVE = 500

# Adherence-gradering (22/10-2026).
#
# Målt i den levende base: 116 aktive beslutninger, 12 under 40 % adherence, 36
# aldrig målt. Gaten læste ALDRIG `adherence_score` — så en beslutning jeg bryder
# 88 % af gangene blokerede præcis lige hårdt som en jeg holder 100 %. Værst:
# den beslutning jeg bryder mest (0,12 — «den afsluttende tekstblok er ALTID
# sidste handling») har prioritet 92, altså den HÅRDESTE blok. Gaten råbte højest
# om netop det jeg ikke kunne finde ud af, og det gjorde blokeringen til støj jeg
# lærte at køre igennem — hvilket er den modsatte af hvad en gate skal gøre.
#
# Graderingen vender ikke blokken: en konflikt med en lav-adherence beslutning
# bliver SOFT (advarsel, kører) i stedet for HARD (blok). Beslutningen er stadig
# aktiv og stadig synlig — men en forpligtelse jeg ikke kan holde som skrevet skal
# omformuleres, ikke gennemtvinges. Det er samme bånd som `enforcement_section`
# beskriver: «navngiv bruddet; omformulér hvis beslutningen ikke kan opfyldes som
# skrevet».
#
# `None` (aldrig målt) graderes som FØR — vi straffer ikke en beslutning for at
# mangle data. Det er de 36 «aldrig målt» der skal klassificeres, ikke gættes på.
_LAV_ADHERENCE = 0.4


_OVERSTYRING = re.compile(r"(?<!\w)alligevel(?!\w)", re.IGNORECASE)


def ejeren_har_sagt_alligevel(user_message: str) -> bool:
    """Har BRUGEREN sagt «alligevel» i sin egen besked?

    Gaten har hele tiden skrevet «Sig \'alligevel\' for at gennemtvinge» — og
    INTET sted i koden laeste det ord. Jarvis proevede fire gange og meldte
    «uden effekt»; han havde ret, der var ingen effekt at faa. Samme familie som
    godkendelses-ringen: en port der anviser en udvej der ikke findes.

    Ordet skal komme fra BRUGERENS besked, ikke fra vaerktoejs-argumenterne.
    Modellen skriver selv sine argumenter, saa en overstyring der kunne staa dér
    ville vaere selv-udstedt — praecis den fejl ejer-godkendelsen allerede har
    kostet os én gang.
    """
    return bool(_OVERSTYRING.search(str(user_message or "")))


def evaluate_decision_conflict(
    tool_name: str,
    tool_args: dict[str, Any] | None = None,
    user_message: str = "",
) -> tuple[str, str | None]:
    """Graderet decision-conflict. Returnerer (severity, reason):
      'hard' → RED (blokér; konflikt med beslutning ≥ tærskel-prioritet)
      'soft' → YELLOW (advar men tillad; kun lav-prioritets-konflikt)
      'none' → GREEN (ingen konflikt)
    """
    if tool_name in _META_TOOLS:
        return "none", None
    if ejeren_har_sagt_alligevel(user_message):
        return "none", None
    try:
        from core.services.behavioral_decisions import list_active_decisions
        # ALLE aktive, ikke de foerste ti (7/9-2026). Der er 45 aktive, saa 35
        # blev aldrig tjekket — samme fejl som anmelderens limit=20 mod 45.
        # Sikkert foerst nu, hvor maalet skal fylde noget: med den gamle
        # matcher ville flere beslutninger bare give flere falske blokeringer.
        decisions = list_active_decisions(limit=_ALLE_AKTIVE) or []
    except Exception as _exc:
        # Fail-open synlighed (audit 2026-07-04): graderet-varianten fejler også STILLE til
        # 'none' (GREEN) → Jarvis kan bryde en forpligtelse uden spor. Flag FØR return.
        # Self-safe: incident-loggen kaster aldrig; fail-open-adfærden ('none', None) uændret.
        try:
            from core.runtime.db_central_incidents import record_central_incident
            record_central_incident(
                cluster="commit", nerve="decision_gate", kind="fail_open",
                severity="error",
                message=f"evaluate_decision_conflict kunne ikke læse beslutninger → "
                        f"fail-OPEN for tool={tool_name}: {type(_exc).__name__}: {_exc}"[:300],
            )
        except Exception:
            pass
        return "none", None
    if not decisions:
        return "none", None

    context = _build_context(tool_name, tool_args, user_message)
    conflicts: list[str] = []
    max_priority = 0
    # Adherence for de beslutninger der FAKTISK er i konflikt — ikke for alle
    # aktive. En lav score på en urelateret beslutning må ikke gøre en ægte
    # konflikt blød. `None` = aldrig målt, og det graderes som før.
    konflikt_adherence: list[float] = []
    for d in decisions:
        directive = str(d.get("directive") or "").strip()
        if not directive:
            continue
        if _detect_conflict(directive, context, d):
            decision_id = str(d.get("decision_id") or "unknown")
            conflicts.append(f"[{decision_id[:8]}] {directive[:60]}")
            max_priority = max(max_priority, int(d.get("priority") or 0))
            _adh = d.get("adherence_score")
            if _adh is not None:
                try:
                    konflikt_adherence.append(float(_adh))
                except (TypeError, ValueError):  # ikke et tal = «aldrig målt», graderes som før
                    pass

    if not conflicts:
        return "none", None

    severity = "hard" if max_priority >= _HARD_BLOCK_PRIORITY else "soft"
    # Adherence-gradering: er HVER konflikt-beslutning under tærsklen, er der
    # ingen reel forpligtelse tilbage at håndhæve — kun en der ikke holder som
    # skrevet. Den advarer stadig, men blokerer ikke. Se `_LAV_ADHERENCE`.
    _svag = bool(konflikt_adherence) and all(
        a < _LAV_ADHERENCE for a in konflikt_adherence
    )
    if severity == "hard" and _svag:
        severity = "soft"
    top = " | ".join(conflicts[:2])
    if severity == "hard":
        reason = (f"DECISION GATE (blok): {len(conflicts)} forpligtelse(r) i konflikt "
                  f"— {top} — Sig 'alligevel' for at gennemtvinge.")
    else:
        _lav = (
            f" (lav adherence {min(konflikt_adherence):.0%} — omformulér beslutningen "
            f"hvis den ikke kan holdes som skrevet)"
            if _svag else ""
        )
        reason = (f"DECISION GATE (blød advarsel): tangerer {len(conflicts)} lav-prioritets-"
                  f"forpligtelse(r) — {top}. Kører, men vær opmærksom.{_lav}")
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish("decision_gate.conflict", {
            "tool_name": tool_name, "severity": severity,
            "conflict_count": len(conflicts), "max_priority": max_priority,
            "lav_adherence": _svag,
        })
    except Exception:
        pass
    return severity, reason


def _build_context(
    tool_name: str,
    tool_args: dict[str, Any] | None,
    user_message: str,
) -> str:
    """Build a context string for conflict detection."""
    parts = [tool_name]
    if tool_args:
        for key in ("path", "command", "content", "text", "old_text", "new_text"):
            val = tool_args.get(key)
            if val:
                parts.append(str(val)[:200])
    if user_message:
        parts.append(user_message[:300])
    return " ".join(parts).lower()


# Hvor stor en del af direktivet maalet mindst skal fylde (7/9-2026).
#
# Regex'en griber ordene efter «ikke/undgaa/stop», men den kan ikke se om de er
# et FORBUD eller bare en vending inde i en laengere saetning. dec_c428 lyder
# «Foer jeg konkluderer at noget er doedt, aldrig kaldes, eller ikke findes —
# verificér at ...» (500+ tegn). Regex'en tog ordet «findes» og gjorde det til
# et forbud, saa gaten haard-blokerede ENHVER hukommelses-skrivning der indeholdt
# ordet. Maalt: «der findes en god kagegrimasse i koekkenet» blev blokeret.
#
# Ratio frem for ordliste, samme princip som `_is_self_bound` i Smiths stige: en
# ordliste udskyder bare det naeste ord. Et aegte forbud fylder det meste af sin
# saetning («undgaa at bruge bash til filredigering» → 0,74); et tilfaeldigt ord
# inde i et langt direktiv goer ikke («findes» i dec_c428 → 0,012).
_MIN_MAAL_ANDEL = 0.15


def _helt_ord(maal: str, tekst: str) -> bool:
    """Delstreng var for loest: «findes» ramte ogsaa «genfindes» og «befindes»."""
    return re.search(r"(?<!\w)%s(?!\w)" % re.escape(maal), tekst) is not None


def _detect_conflict(directive: str, context: str, decision: dict) -> str | None:
    """Detect if the context conflicts with a decision directive.

    Uses heuristic pattern matching:
    - If directive says "undgå/ikke/stop/avoid X" and context contains X → conflict
    - If directive says "altid/always X" and context suggests NOT doing X → conflict

    Maalet skal fylde mindst `_MIN_MAAL_ANDEL` af direktivet og matche som helt
    ord — se konstanten for hvorfor.
    """
    directive_lower = directive.lower()
    context_lower = context.lower()

    # Pattern: avoidance directive — "undgå X", "ikke X", "stop X"
    avoid_match = re.search(
        r"\b(undgå|undlad|ikke|stop|avoid|don'?t|never)\b\s+(?:at\s+|to\s+)?([a-zæøå]+(?:\s+[a-zæøå]+){0,4})",
        directive_lower,
    )
    if avoid_match:
        target = avoid_match.group(2).strip()
        if (target
                and len(target) / max(1, len(directive_lower)) >= _MIN_MAAL_ANDEL
                and _helt_ord(target, context_lower)):
            return f"handling matcher '{target}' som forpligtelsen siger at undgå"

    # Pattern: imperative directive — "altid X" and context suggests skipping
    always_match = re.search(
        r"\b(altid|always|skal altid|must always)\b\s+(?:at\s+)?([a-zæøå]+(?:\s+[a-zæøå]+){0,3})",
        directive_lower,
    )
    if always_match:
        target = always_match.group(2).strip()
        # Check if the context explicitly skips/avoids the target
        skip_patterns = [f"uden {target}", f"skip {target}", f"spring {target}", f"ikke {target}"]
        for sp in skip_patterns:
            if sp in context_lower:
                return f"context foreslår at springe '{target}' over som forpligtelsen kræver"

    return None