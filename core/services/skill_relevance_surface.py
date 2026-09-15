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

# KALIBRERET 15/9-2026 paa 200 af hans egne beskeder.
#
# De gamle tal (0,30 og 0,50) stammede fra HuggingFace-embedderen. Den lokale
# (all-MiniLM-L6-v2 via Ollama, skiftet 12/9) har et helt andet interval: ALLE
# scorer ligger mellem 0,59 og 0,80. Taersklerne laa altsaa under hele feltet,
# saa «STAERKT match» betoed i praksis «altid» — 42% af hans ture fik ét.
#
# Grundlag: et match regnes som rigtigt naar beskeden indeholder skillets eget
# domaeneord («regneark» → xlsx, «pdf» → pdf). Det er en PROXY og ikke en
# haandlabel, n=17 rigtige mod 82 oevrige — svagt bevis, men aegte data, og
# kurvens form er robust over for label-stoej:
#
#   taerskel   rigtige beholdt   stoej igennem   praecision
#     0,50        100%              100%            17%
#     0,75         70%               15%            48%
#     0,77         52%                4%            69%   ← knaek
#     0,78          5%                2%            33%   ← klippe
#
# Praecision vejer tungest her (jf. reference_model_quality_benchmark: opdigt
# er vaerre end at overse). Et forkert STAERKT match koster en hel
# SKILL.md-laesning og en begrundelse; et overset rigtigt koster at han loeser
# opgaven selv — hvilket han beviseligt kan.
_THRESHOLD = 0.70
_PRIMARY_THRESHOLD = 0.77
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


def _navnet_staar_i(skill_navn: str, besked: str) -> bool:
    """Staar skillets eget navn i beskeden?

    Bindestreger taeller som mellemrum, saa «excel-automation» ogsaa rammes af
    «brug excel automation». Kraever mindst 3 tegn, saa korte navne ikke rammer
    tilfaeldige stavelser.
    """
    n = str(skill_navn or "").strip().lower()
    b = f" {str(besked or '').lower()} "
    if len(n) < 3:
        return False
    if f" {n} " in b or n in b.replace("-", " "):
        return True
    # Sammensat navn: alle led skal staa der, ikke noedvendigvis samlet.
    led = [x for x in n.replace("-", " ").split() if len(x) >= 3]
    return bool(led) and all(f" {x}" in b for x in led)


def _naevner_mekanismen(besked: str) -> bool:
    """Beder brugeren udtrykkeligt om et skill? Saa er beskeden aldrig smaasnak."""
    lav = f" {str(besked or '').lower()} "
    return any(f"{o}" in lav for o in _SKILL_ORD)


def sidst_foreslaaede() -> list[str]:
    """Hvilke skills blev foreslaaet i den seneste prompt-bygning.

    Laeser samme memo som beskaereren. Bruges til at maerke en invokering med
    om runtimen havde foreslaaet skillet, eller han fandt det selv — uden det
    kan kaeden matched → surfaced → invoked ikke laegges sammen bagefter.
    """
    return list(_SIDSTE[1])


#: Ture ingen bruger har startet. Maalt paa 478 ture over 14 dage:
#:   recurring 249 · heartbeat 111 · dream 53 · wakeup 34 · autonomous 31
#:
#: `autonomous` er IKKE med: det er den origin hans egne beskeder faar naar de
#: kommer ind via en kanal-gateway (Telegram, Discord). Navnet er forvirrende,
#: og netop den forvirring kostede en fejl samme dag — se `_er_autonom_tur`.
#:
#: `wakeup` er heller ikke med: den genoptager HANS afbrudte arbejde, saa der
#: er en opgave bag den.
_SELVSTARTEDE_ORIGINS = frozenset({"recurring", "heartbeat", "dream"})


def _er_selvstartet_tur() -> bool:
    """Startede maskinen sig selv, uden nogen opgave fra ham?

    Fejlretningen: kender vi ikke origin, siger vi NEJ. En ukendt tur skal
    beholde sine skills — det er hans ture der betyder noget.
    """
    try:
        # Koerslens egen origin foerst: gatens globale deles af alle koersler i
        # processen og husker den SENESTE autonome — en hjerteslags-tur kl. 16
        # ville ellers undtage hans brugertur kl. 16:05. Har koerslen sat sin
        # identitet, gaelder dens origin, OGSAA naar den er tom (= brugertur).
        from core.services.run_autonomy_context import current_origin, current_run_id
        from core.services.run_closure_gate import aktuel_origin

        origin = current_origin() if current_run_id() else aktuel_origin()
        return origin.strip().lower() in _SELVSTARTEDE_ORIGINS
    except Exception:
        logger.debug("kunne ikke laese turens origin", exc_info=True)
        return False


def _er_autonom_tur() -> bool:
    """Koerer vi en autonom tur lige nu?

    ## Hvorfor (15/9-2026)

    Maalt over tre timer: skill-fladen fyrede TRE gange, og alle tre var
    autonome ture — 12:15:59, 13:18:43, 14:00:43:

        autonomous-e  «Begge bekraeftet. Dream note verificeret…»
        autonomous-d  «Data samlet. DB er sund (integrity OK)…»
        autonomous-3  «hjemme. Her er den korte rapport…»

    Der var ingen bruger der spurgte om noget. Fladen foreslog deep-research,
    code-review og git-advanced til hans egne baggrundsture, og nul af dem
    blev brugt — hvilket var KORREKT adfaerd, ikke en fejl.

    Det kostede ~55 ms matcher-opslag og en plads ud af de 48 paa hver eneste
    baggrundstur. Bjoern: «Autonome undtaget».

    Run-id'et saettes af `run_closure_gate._on_run_started`, som kun lytter paa
    `runtime.autonomous_run_started` — saa et `autonomous-`-praefiks er et
    positivt bevis. Er det tomt (synlig tur, eller vi ved det ikke), koerer vi
    som foer: tvivlen falder ud til at BEHOLDE skills for hans egne ture.
    """
    try:
        from core.services.session_context_resolve import aktivt_run_id

        return str(aktivt_run_id("")).startswith("autonomous-")
    except Exception:
        logger.debug("kunne ikke afgoere om turen er autonom", exc_info=True)
        return False


def _traef(besked: str) -> list[dict]:
    """Selve opslaget. Adskilt saa baade sektionen og memoen bruger samme vej."""
    if not _enabled():
        return []
    # Selvstartede ture (hjerteslag, gentagne opgaver, drømme) faar ingen
    # skill-flade. Afgjort paa koerslens ORIGIN, ikke paa `autonomous-`-
    # praefikset: kanal-gatewayen for Telegram og Discord giver ogsaa hans egne
    # beskeder det praefiks (maalt 15/9: aftensmads-samtalen 15:54 og 16:02),
    # saa den foerste udgave tog skills fra alt han skrev derfra.
    if _er_selvstartet_tur():
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
        # EKSPLICIT NAVN SLAAR SCOREN (15/9-2026). Skriver han selv skillets
        # navn, er det det staerkeste signal der findes — staerkere end nogen
        # embedding. «brug pdf skill» gav 0,76, altsaa under den kalibrerede
        # taerskel paa 0,77, og ville ellers blive et tilbud i stedet for en
        # instruks. Det er den samme pointe Codex noterede: et eksplicit oenske
        # skal resolves deterministisk, ikke semantisk.
        if score >= _PRIMARY_THRESHOLD or _navnet_staar_i(navn, besked):
            har_primaer = True
            linjer.append(
                "  • %s (%.2f) — STÆRKT match: brug skillets format som det "
                "primære for dit svar" % (navn, score)
            )
        else:
            linjer.append("  • %s (%.2f)" % (navn, score))

    # STAERKT match og svagt match skal ikke lyde ens (15/9-2026).
    #
    # Maalt paa en aegte tur: «lav et regneark over deepseek-forbruget» gav
    # xlsx 0,78 — STAERKT match. Fladen stod i prompten (498 tegn),
    # `skill_invoke` var faestnet i vaerktoejssaettet, og han brugte 47
    # bash-kald i stedet. Han loeste opgaven KORREKT uden skillet.
    #
    # Aarsagen stod i vores egen formulering: «Vil du ikke, saa lad vaere».
    # Et match paa 0,78 blev praesenteret med samme vaegt som et paa 0,31 —
    # som et tilbud han udtrykkeligt fik lov at afslaa. For en opgave han
    # allerede kan loese, er det rationelle valg saa at lade vaere.
    #
    # Bjoern: «Stram formulering».
    #
    # BEMAERK hvorfor dette ikke er det ritual der fejlede: de to pensionerede
    # beslutninger kraevede `skill_suggest` FOER hver opgave — en handling uden
    # synlig gevinst, med efterlevelse 0,10 og 0,00. Her har runtimen allerede
    # fundet svaret for DENNE opgave; der bedes om at laese det, ikke om at
    # lede. Og et fravalg skal begrundes, ikke blokeres: en haard blokering
    # ville goere et forkert match til en blindgyde.
    if har_primaer:
        linjer.append(
            "Det stærke match er skrevet til præcis denne opgave og indeholder "
            "ting du ikke ved på forhånd. Kald skill_invoke(\"<navn>\") og læs "
            "HELE SKILL.md før du svarer. Vælger du det fra, så skriv kort "
            "hvorfor i dit svar — et fravalg må ikke være tavst."
        )
    else:
        linjer.append(
            "Ingen af dem er et stærkt match — de er et tilbud, ikke et "
            "krav. Vil du bruge et: skill_invoke(\"<navn>\") og læs HELE "
            "SKILL.md før du skriver svaret."
        )
    linjer.append(
        "Sig aldrig at du brugte et skill uden faktisk at have invokeret det."
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
