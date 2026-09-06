"""Slå skills op FOR ham i stedet for at bede ham huske at slå op.

To af hans adfærdsbeslutninger var blandt de allerlaveste på adherence:

    0,00  «Kald altid skill_gate(query=...) som det allerførste step»
    0,10  «Før enhver research/analyse/faktatjek-opgave — kør skill_suggest()»

Mønsteret i de beslutninger han bryder, er tydeligt: det er **ritualer** — gør
altid dette præcis dér. De beslutninger han holder, handler om holdning og
dømmekraft. Et ritual der skal huskes hver gang, hører ikke hjemme som en
hensigt i prompten; det hører hjemme i runtimen.

Så runtimen slår op nu. Matcher noget, står det i prompten som en kendsgerning
— han skal ikke længere huske at spørge for at få noget at vide.

Bemærk hvad dette IKKE gør: det invokerer ingenting. Auto-invokering ville
udvide injektions-fladen (modellen kan skrive en SKILL.md og dermed styre hvad
der foreslås den næste tur), og den flade er bevidst ejer-gated via
``skill_autosurface`` med master-kontakt default OFF. Vi flytter kun OPSLAGET,
ikke beslutningen. Han vælger stadig selv om han bruger det.

Prisen er målt: matcheren koster ~750 ms. Den submittes derfor i prompt-
assemblyens fase 1-trådpulje, hvor den forsvinder bag memory_selection (~1500
ms) og frame (~940 ms). Korte beskeder springes helt over — «hej» matcher
alligevel ingenting.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Fra beslutningen selv: ≥0,3 → læs skillet; ≥0,5 → brug det som primært format.
_THRESHOLD = 0.30
_PRIMARY_THRESHOLD = 0.50
_MAX_SUGGESTIONS = 3

# Under denne længde er en besked småsnak eller en kvittering. Sparer et embed-
# kald pr. tur på præcis de ture hvor der alligevel aldrig er et match.
_MIN_MESSAGE_CHARS = 15


def _enabled() -> bool:
    """Kill-switch. Self-safe: kan config ikke læses, slår vi op."""
    try:
        from core.runtime.settings import load_settings
        return bool(load_settings().extra.get("skill_relevance_surface_enabled", True))
    except Exception:
        return True


def relevant_skills_section(user_message: str) -> str:
    """Prompt-sektion med de skills der matcher turens opgave. "" hvis ingen.

    Kaster aldrig — en fejlende matcher må ikke kunne vælte prompt-bygningen.
    """
    besked = str(user_message or "").strip()
    if not besked or len(besked) < _MIN_MESSAGE_CHARS:
        return ""
    if not _enabled():
        return ""

    try:
        from core.tools.skill_engine_tools import _suggest_skills_for_query
        traef = _suggest_skills_for_query(
            query=besked, threshold=_THRESHOLD, max_results=_MAX_SUGGESTIONS,
        ) or []
    except Exception as exc:
        logger.debug("skill_relevance_surface: opslag fejlede: %s", exc)
        return ""

    if not traef:
        return ""

    linjer = [
        "[SKILLS DER MATCHER DENNE OPGAVE]",
        "Runtimen har allerede slået op for dig — du skal ikke kalde "
        "skill_suggest eller skill_gate først.",
    ]
    har_primaer = False
    for s in traef:
        navn = str(s.get("name") or "").strip()
        if not navn:
            continue
        try:
            score = float(s.get("score") or 0.0)
        except Exception:
            score = 0.0
        if score >= _PRIMARY_THRESHOLD:
            har_primaer = True
            linjer.append(
                "  • %s (%.2f) — STÆRKT match: brug skillets format som det "
                "primære for dit svar" % (navn, score)
            )
        else:
            linjer.append("  • %s (%.2f)" % (navn, score))

    linjer.append(
        "Vil du bruge et af dem: skill_invoke(\"<navn>\") og læs HELE SKILL.md "
        "før du skriver svaret. Vil du ikke, så lad være — men sig aldrig at du "
        "brugte et skill uden faktisk at have invokeret det."
    )
    if not har_primaer:
        linjer.append(
            "Ingen af dem er et stærkt match (<0,50) — de er et tilbud, ikke et krav."
        )
    return "\n".join(linjer)


def build_skill_relevance_surface(user_message: str = "") -> dict[str, object]:
    """Observationsflade — hvad opslaget ville sige om denne besked."""
    tekst = relevant_skills_section(user_message)
    return {
        "active": _enabled(),
        "message_chars": len(str(user_message or "").strip()),
        "skipped_short": len(str(user_message or "").strip()) < _MIN_MESSAGE_CHARS,
        "threshold": _THRESHOLD,
        "primary_threshold": _PRIMARY_THRESHOLD,
        "matched": bool(tekst),
        "section_chars": len(tekst),
    }
