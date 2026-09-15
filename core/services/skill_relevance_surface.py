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

# ...med ÉN undtagelse (15/9-2026). «brug pdf skill» er 14 tegn — ét under
# taersklen — og er samtidig den mest eksplicitte skill-anmodning der findes.
# Naevner beskeden mekanismen, er den aldrig smaasnak, uanset laengde.
#
# Prisen er maalt: af 1.527 brugerbeskeder paa 30 dage var 294 under 15 tegn,
# og NUL af dem naevnte «skill». Undtagelsen koster altsaa reelt ingenting.
#
# Bemaerk forskellen fra `_MEKANIK_ORD` i matcheren: dér kan ordet «skill» ikke
# BEVISE et match. Her siger det bare at vi skal se efter. At spoerge og at
# bevise er ikke det samme.
_SKILL_ORD = ("skill", "skills", "skillet", "skillene")


def _enabled() -> bool:
    """Kill-switch. Self-safe: kan config ikke læses, slår vi op."""
    try:
        from core.runtime.settings import load_settings
        return bool(load_settings().extra.get("skill_relevance_surface_enabled", True))
    except Exception:
        return True


# Ét opslag, to forbrugere (15/9-2026).
#
# Prompten naevner `skill_invoke("<navn>")`, men MAALT samme dag: af kataloget
# paa 471 vaerktoejer har 24 «skill» i navnet, og INGEN af dem overlever
# beskaeringen til de 48 i den synlige lane — heller ikke naar brugeren
# bogstaveligt skriver «brug pdf skill».
#
# Runtimen bad altsaa modellen om at kalde noget der ikke laa i kaldet. Den
# eneste vej var `load_more_tools`, som ER blandt de 48 — men prompten naevner
# den ikke, saa modellen skulle gaette. Den gjorde det rationelle i stedet:
# fandt filen med `explore` og laeste SKILL.md i haanden.
#
# Beskaereren har brug for at vide det SAMME som prompten. Den kunne koere
# matcheren selv, men det ville koste ~55 ms to gange og kunne give to
# forskellige svar. Derfor deles ét resultat.
_SIDSTE: tuple[str, list[str]] = ("", [])


def matchede_skills(user_message: str) -> list[str]:
    """Navnene paa de skills der matcher denne besked. Tom liste hvis ingen.

    Memoiseret paa beskeden, saa beskaereren og prompt-sektionen faar SAMME
    svar uden at betale for opslaget to gange. Kun ét trin huskes: turene
    kommer én ad gangen, og et ubegraenset lager ville vokse i en proces der
    koerer i ugevis.

    Kaster aldrig — en fejlende matcher maa hverken vaelte prompten eller
    vaerktoejsvalget.
    """
    global _SIDSTE
    besked = str(user_message or "").strip()
    if not besked:
        return []
    if _SIDSTE[0] == besked:
        return list(_SIDSTE[1])
    navne = [str(t.get("name") or "") for t in _traef(besked) if t.get("name")]
    _SIDSTE = (besked, navne)
    return list(navne)


def _naevner_mekanismen(besked: str) -> bool:
    """Beder brugeren udtrykkeligt om et skill? Saa er beskeden aldrig smaasnak."""
    lav = f" {str(besked or '').lower()} "
    return any(f"{o}" in lav for o in _SKILL_ORD)


def _traef(besked: str) -> list[dict]:
    """Selve opslaget. Adskilt saa baade sektionen og memoen bruger samme vej."""
    if not _enabled():
        return []
    if len(besked) < _MIN_MESSAGE_CHARS and not _naevner_mekanismen(besked):
        return []
    try:
        from core.tools.skill_engine_tools import _suggest_skills_for_query
        return _suggest_skills_for_query(
            query=besked, threshold=_THRESHOLD, max_results=_MAX_SUGGESTIONS,
        ) or []
    except Exception as exc:
        logger.debug("skill_relevance_surface: opslag fejlede: %s", exc)
        return []


def relevant_skills_section(user_message: str) -> str:
    """Prompt-sektion med de skills der matcher turens opgave. "" hvis ingen.

    Kaster aldrig — en fejlende matcher må ikke kunne vælte prompt-bygningen.
    """
    try:
        from core.services.research_prompt_context import research_prompt_section
        research = research_prompt_section()
    except Exception:
        research = ""
    besked = str(user_message or "").strip()
    if not besked:
        return research
    if len(besked) < _MIN_MESSAGE_CHARS and not _naevner_mekanismen(besked):
        return research
    if not _enabled():
        return research

    traef = _traef(besked)
    # Fyld memoen, saa beskaereren faar samme svar uden et nyt opslag.
    global _SIDSTE
    _SIDSTE = (besked, [str(x.get("name") or "") for x in traef if x.get("name")])

    if not traef:
        return research

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
    ordinary = "\n".join(linjer)
    return f"{research}\n\n{ordinary}" if research else ordinary


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
