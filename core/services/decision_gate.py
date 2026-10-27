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

    # Match the decision against the action Jarvis is about to execute. The
    # user's message is only authority for the explicit "alligevel" override;
    # including it here lets a negated request such as "ingen researcher"
    # falsely block an executor (and every unrelated tool call in the turn).
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

# En ALDRIG MÅLT beslutning med et mønster af brud er svag i PRAKSIS (22/10-2026).
# `adherence_score` kræver en review-dom, og 36 aktive beslutninger har aldrig
# fået en. Brud-historikken findes derimod: `decision.breach_detected` fyrer og
# `decision_breach_recent` skrives. Den bruges her som signal — ikke som et
# opdigtet tal — så de aldrig målte bliver klassificeret i stedet for gættet på.
_ALDRI_MAALT_BRUD_TAERSKEL = 3


def _aldrig_maalt_er_svag(decision_id: str, brud: dict) -> bool:
    """Har en beslutning uden måling et brud-mønster i vinduet?"""
    try:
        from core.services.decision_breach_reader import BRUD_TAERSKEL_LAV as taerskel
    except Exception:  # læseren er valgfri — den lokale tærskel er identisk
        taerskel = _ALDRI_MAALT_BRUD_TAERSKEL
    s = (brud or {}).get(str(decision_id)) or {}
    return int(s.get("count") or 0) >= taerskel


def directive_har_maal(directive: str) -> bool:
    """Kan `_detect_conflict` overhovedet finde et mål i dette direktiv?

    Bruges af `decision_breach_reader.classify` til at afgøre om en beslutning
    er EKSEKVERBAR: et direktiv uden et mål gaten kan matche kan ikke håndhæves
    før eksekvering, uanset hvor vigtigt det lyder. Samme to mønstre og samme
    andels-krav som matcheren — ellers ville klassifikationen lyve om gaten.
    """
    directive_lower = str(directive or "").lower()
    for mønster in (_AVOID_RE, _ALWAYS_RE):
        m = mønster.search(directive_lower)
        if not m:
            continue
        target = (m.group(2) or "").strip()
        if target and len(target) / max(1, len(directive_lower)) >= _MIN_MAAL_ANDEL:
            return True
    return False


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
    # Én svagheds-dom pr. konflikt. Før var `None` (aldrig målt) automatisk
    # «ikke svag» — men en beslutning der aldrig er blevet MÅLT kan godt være
    # svag i praksis: brud-historikken er et adfærdssignal. Se
    # `decision_breach_reader` (22/10-2026).
    konflikt_svag: list[bool] = []
    konflikt_adherence: list[float] = []
    konflikt_brud: list[int] = []
    _brud: dict = {}
    _breach_stats = None
    try:
        from core.services.decision_breach_reader import breach_stats as _breach_stats
    except Exception:  # læseren er valgfri — gaten skal virke uden den
        _breach_stats = None
    if _breach_stats is not None:
        try:
            _brud = _breach_stats()
        except Exception:  # korrupt state-fil må ikke gøre gaten tandløs
            _brud = {}
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
                    _a = float(_adh)
                    konflikt_adherence.append(_a)
                    konflikt_svag.append(_a < _LAV_ADHERENCE)
                except (TypeError, ValueError):  # ikke et tal = «aldrig målt»
                    konflikt_svag.append(_aldrig_maalt_er_svag(decision_id, _brud))
                    konflikt_brud.append(
                        int((_brud.get(decision_id) or {}).get("count") or 0)
                    )
            else:
                konflikt_svag.append(_aldrig_maalt_er_svag(decision_id, _brud))
                konflikt_brud.append(
                    int((_brud.get(decision_id) or {}).get("count") or 0)
                )

    if not conflicts:
        return "none", None

    severity = "hard" if max_priority >= _HARD_BLOCK_PRIORITY else "soft"
    # Adherence-gradering: er HVER konflikt-beslutning svag, er der ingen reel
    # forpligtelse tilbage at håndhæve — kun en der ikke holder som skrevet.
    # Den advarer stadig, men blokerer ikke. Se `_LAV_ADHERENCE`.
    _svag = bool(konflikt_svag) and all(konflikt_svag)
    if severity == "hard" and _svag:
        severity = "soft"
    top = " | ".join(conflicts[:2])
    if severity == "hard":
        reason = (f"DECISION GATE (blok): {len(conflicts)} forpligtelse(r) i konflikt "
                  f"— {top} — Sig 'alligevel' for at gennemtvinge.")
    else:
        if konflikt_adherence:
            _lav = (f" (lav adherence {min(konflikt_adherence):.0%} — omformulér "
                    f"beslutningen hvis den ikke kan holdes som skrevet)")
        elif _svag:
            _antal = sum(konflikt_brud)
            _lav = (f" (aldrig målt, men {_antal} brud i vinduet — omformulér "
                    f"beslutningen hvis den ikke kan holdes som skrevet)")
        else:
            _lav = ""
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
    """Build conflict context from the proposed action, not the whole request.

    ``user_message`` remains in the signature for call-site compatibility and
    is deliberately ignored here. It is evaluated separately by
    :func:`ejeren_har_sagt_alligevel`, where only the owner can authorize an
    override. Task fields are included so decisions can distinguish a real
    researcher dispatch from an executor dispatch.
    """
    parts = [tool_name]
    if tool_args:
        for key in (
            "path", "command", "content", "text", "old_text", "new_text",
            "description", "prompt", "subagent_type", "goal", "query", "role",
        ):
            val = tool_args.get(key)
            if val:
                parts.append(str(val)[:200])
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

# 24/10-2026: samme princip, men maalt paa det ENKELTE ord i maalet. En frase
# som «bash til filredigering» staar aldrig ordret i et vaerktoejskald, saa
# frase-kravet alene gjorde gaten tandloes. Ord-kravet er lavere end
# frase-kravet, fordi et ord paa 4+ tegn i et kort direktiv ER baerende
# («bash» i «brug aldrig bash til filredigering» → 0,10). Til gengaeld kraeves
# mindst 4 tegn, saa «til», «jeg» og «det» aldrig bliver et maal.
_MIN_ORD_ANDEL = 0.08

# De to mønstre står som modul-konstanter, fordi `directive_har_maal` skal
# bruge PRÆCIS de samme som matcheren. Kopierede man dem, ville
# klassifikationen kunne sige «eksekverbar» om et direktiv gaten ikke fanger.
# 24/10-2026: «aldrig» manglede i forbuds-mønstret, mens «altid» var med i det
# paabydende. Asymmetrien var utilsigtet og kostede maalt: af 135 aktive
# beslutninger kunne gaten haandhaeve 8 — resten var ren prompt-tekst. Et forbud
# skrevet paa dansk skrives naturligt med ALDRIG («skriv aldrig til repo-roden»),
# saa det var praecis den formulering gaten var blind for. Maalt direkte:
# «Skriv ALDRIG til repo-roden» → tandloes, «Skriv ikke til repo-roden» → gatebar.
# Andels-kravet nedenfor er uaendret og holder stadig falske positive ude: et
# tilfaeldigt «aldrig» inde i et langt direktiv fylder under 15 % og afvises.
_AVOID_RE = re.compile(
    r"\b(undgå|undlad|ikke|aldrig|stop|avoid|don'?t|never)\b\s+(?:at\s+|to\s+)?([a-zæøå]+(?:\s+[a-zæøå]+){0,4})"
)
_ALWAYS_RE = re.compile(
    r"\b(altid|always|skal altid|must always)\b\s+(?:at\s+)?([a-zæøå]+(?:\s+[a-zæøå]+){0,3})"
)


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
    avoid_match = _AVOID_RE.search(directive_lower)
    if avoid_match:
        target = avoid_match.group(2).strip()
        if (target
                and len(target) / max(1, len(directive_lower)) >= _MIN_MAAL_ANDEL
                and _helt_ord(target, context_lower)):
            return f"handling matcher '{target}' som forpligtelsen siger at undgå"
        # 24/10-2026: frasen alene var for streng. «Brug ALDRIG bash til
        # filredigering» udtraekker «bash til filredigering», og den frase staar
        # aldrig ordret i et vaerktoejskald — saa gaten var tandloes i praksis
        # (maalt: 9 blokeringer i hele sin levetid). Nu proeves OGSAA det
        # baerende ord alene, men kun naar det fylder nok til at vaere et reelt
        # maal og ikke en tilfaeldig vending. Det er samme andels-krav, bare
        # maalt paa ordet i stedet for frasen.
        if target:
            for ord_ in target.split():
                if (len(ord_) >= 4
                        and len(ord_) / max(1, len(directive_lower)) >= _MIN_ORD_ANDEL
                        and _helt_ord(ord_, context_lower)):
                    return f"handling matcher '{ord_}' som forpligtelsen siger at undgå"

    # Pattern: imperative directive — "altid X" and context suggests skipping
    always_match = _ALWAYS_RE.search(directive_lower)
    if always_match:
        target = always_match.group(2).strip()
        # Check if the context explicitly skips/avoids the target
        skip_patterns = [f"uden {target}", f"skip {target}", f"spring {target}", f"ikke {target}"]
        for sp in skip_patterns:
            if sp in context_lower:
                return f"context foreslår at springe '{target}' over som forpligtelsen kræver"

    return None
