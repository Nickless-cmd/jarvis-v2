"""Værns-noterne — hvad Bjørn ser, og hvad modellen må se.

## Hvorfor filen findes

Bjørn 3/10-2026, stående regel: *«Alt der ikk er mig der har skrevet fra composer
skal mærkes som fra systemet»* — efter at han og Codex fandt værn der kostede
ekstra runder, fordi «hans tomt løfte værn kunne starte en ny runde i mit navn».

Målt samme dag: FEM værns-noter i `visible_runs.py` appender til `_a_parts`, og
`_a_parts` er — ifølge `compose_exchange_text`s egen docstring — *«assistant-turen
til næste rundes model-input»* OG det persisterede svar. Én liste tjener altså
både mennesket og modellen, og der var ingen adskillelse.

Fire af de fem er i jeg-form, og tre af dem bærer en invitation:

    _exhaust_note   «jeg prøvede igen … sig til, så fortsætter jeg»
    _stop_note      «Jeg stoppede her … Sig til, så tager jeg den derfra»
    _hp_note        «Sig til, så tager jeg den forfra»

Næste runde ser dermed en opfordring i første person, uadskillelig fra Bjørns
egne ord, og kan læse den som om den VAR givet. Det er dér en runde starter i
hans navn.

Og risikoen er ikke teoretisk. `interruption_notice.py` dokumenterer den målte
version af samme fejl: 45 stubs klumpet 16-8-7-4-2, og da tre laa i træk svarede
DeepSeek paa en almindelig prompt ved at skrive den SAMME sætning igen, ord for
ord. **Modellen efterlignede sin egen historik.**

## De tre klasser

Aksen er ikke hvad noten siger, men hvad den skal udrette:

1. **Skal handle** — runnet dør eller hænger uden den. `ingen_tekst_i_runder`
   er netop det: DeepSeek stopper tavst uden at sende noget, så nogen SKAL
   tvinge en fortsættelse. Bjørn 3/10: «en nødvendighed». Den bliver, men
   mærkes, så modellen ved at runden blev TVUNGET og ikke bedt om.
2. **Skal advare næste runde** — modellen skal vide det for ikke at gentage sig.
   Det tomme løfte hører her: i dag tvinges modellen i tavshed to gange og får
   først ord når det er for sent. Advarslen er derfor en TILFØJELSE, ikke en
   flytning — og den er i tredje person uden invitation.
3. **Kun til mennesket** — Bjørn skal forstå hvorfor; modellen vinder intet.
   Noten BLIVER i jeg-form med sin invitation, fordi det er den rigtige besked
   til et menneske, og filtreres ud af model-input.

## Hvor filtreringen sker

To lag, og begge er nødvendige:

* **Samme tur:** `_exchange_text()` i `visible_runs.py` kalder
  `fjern_menneske_noter(_a_parts)` før `compose_exchange_text`. Den funktion
  adskiller allerede «hvad der gemmes» fra «hvad modellen ser», i BEGGE
  retninger — den kan tilføje noget modellen ser uden at det gemmes. Derfor er
  den sømmen.
* **Følgende ture:** `transcript_sections` stripper fra den persisterede
  historik, præcis som `strip_interruption_notices` gør for afbrydelses-noten.

Teksterne står ÉT sted her, så skriveren og filteret ikke kan drive fra
hinanden — det er præcis hvordan et filter bliver stille virkningsløst.
"""
from __future__ import annotations

import logging
from typing import Final

logger = logging.getLogger(__name__)

#: 1 = runnet dør uden den · 2 = modellen skal advares · 3 = kun mennesket.
KLASSE_HANDLER: Final[int] = 1
KLASSE_ADVAR: Final[int] = 2
KLASSE_MENNESKE: Final[int] = 3

#: Mærkningen alt ikke-fra-composeren skal bære. Tre egenskaber gør den
#: virksom: den siger hvad den ER, hvad den IKKE er, og den forbyder eksplicit
#: at læse den som samtykke. Den sidste er vigtigst — uden den kan en
#: systembesked blive et «ja», og det var netop «Sig til»-fejlen.
SYSTEM_MAERKE: Final[str] = (
    "[SYSTEM — IKKE FRA BJØRN] Dette er en automatisk iagttagelse fra runtimen, "
    "IKKE en besked fra brugeren. Den må IKKE læses som samtykke, bekræftelse "
    "eller en anmodning om at gentage noget."
)


# ── Noterne. Teksterne er ORDRET som før 3/10, så det Bjørn ser er uændret ──

def forbindelsen_glippede() -> str:
    """P6 graceful-degrade: forbindelsen svigtede gentagne gange. Klasse 3."""
    return (
        "\n\n_(Forbindelsen blev ved med at glippe — "
        "jeg prøvede igen et par gange men måtte give op. "
        "Her er hvad jeg nåede; sig til, så fortsætter jeg.)_"
    )


def loekken_tvang_en_afslutning() -> str:
    """Løkken tvang en afslutning med et ventende tool-intent. Klasse 3."""
    return (
        "\n\n_(Jeg stoppede her fordi løkken tvang en "
        "afslutning — ikke fordi jeg var færdig. Sig til, "
        "så tager jeg den derfra.)_"
    )


def tool_call_loekke(runder: int) -> str:
    """Flere runder med værktøjskald og intet synligt svar. Klasse 3."""
    return (
        "⚠ Jeg faldt i et tool-call loop — "
        f"{int(runder)} runder uden synligt svar. "
        "Her er hvad jeg fandt:"
    )


def ingen_tekst_i_runder(runder: int) -> str:
    """Runder uden tekst overhovedet — KLASSE 1, den holder runnet i gang.

    Teksten er paa engelsk modsat resten af huset. Det er bevaret med vilje:
    den er uaendret siden den blev tilfoejet som en noedvendighed, og en
    oversaettelse her ville aendre hvad Bjoern ser i en commit om maerkning.
    Hoerer i sit eget spor.
    """
    return (
        f"⚠ I ran {int(runder)} rounds without producing text. "
        "Something went wrong — try again."
    )


# ── Klasse 2: advarslen der ikke fandtes ──

def tomt_loefte_advarsel() -> str:
    """Advarslen til NÆSTE runde om et tomt løfte. Klasse 2 — MÆRKET.

    I dag får modellen aldrig at vide med ord at den gav et tomt løfte:
    `note_detected` udsender et event, `next_round_tool_choice` tvinger et
    værktøjsvalg uden ord, og først når BEGGE tvungne forsøg fejlede taler
    `hollow_promise_note` — med «Sig til, så tager jeg den forfra».

    Modellen tvinges altså i tavshed to gange og får først ord når det er for
    sent. Denne advarsel er derfor en TILFØJELSE, ikke en flytning: den siger
    hvad der gik galt mens modellen stadig kan rette det.

    Tredje person, ingen invitation, og mærket.
    """
    return (
        f"\n\n{SYSTEM_MAERKE}\n"
        "Et værn observerede: forrige runde lovede en handling og kaldte nul "
        "værktøjer. Dette er en iagttagelse, ikke en anmodning — ingen har bedt "
        "om en gentagelse. Kald det værktøj der faktisk udfører arbejdet, eller "
        "sig tydeligt at du ikke kan."
    )


def systemmaerket(tekst: str) -> str:
    """Mærk en vilkårlig runtime-besked som fra systemet. Klasse 1 og 2."""
    t = str(tekst or "").strip()
    if not t:
        return ""
    return f"\n\n{SYSTEM_MAERKE}\n{t}"


# ── Genkendelse og filtrering ──

#: Kendetegn pr. klasse-3-note. Korte nok at taale smaa variationer
#: (tegnsaetning, en tilfoejet linje), snaevre nok til aldrig at ramme et aegte
#: svar. Samme afvejning som `interruption_notice._KENDETEGN`.
_MENNESKE_KENDETEGN: Final[tuple[str, ...]] = (
    "forbindelsen blev ved med at glippe",
    "stoppede her fordi løkken tvang",
    "faldt i et tool-call loop",
)

#: Klasse 1 genkendes ogsaa, men FJERNES IKKE — den skal naa modellen. Her kun
#: for at kunne maerke den og for at en test kan skelne de to klasser.
_HANDLER_KENDETEGN: Final[tuple[str, ...]] = (
    "rounds without producing text",
)

#: Det tomme loeftes MENNESKE-note bor i hollow_promise_round.py (klasse 2's
#: menneske-halvdel). Kendetegnet staar her, saa filteret daekker den ogsaa.
_MENNESKE_KENDETEGN_EKSTERNE: Final[tuple[str, ...]] = (
    "kaldte så ingen værktøjer",
)


def er_menneske_note(tekst: str) -> bool:
    """Er dette en klasse-3-note — altså til Bjørn og ikke til modellen?

    Self-safe → False ved tvivl. Fail-retningen er med vilje: en note der ikke
    genkendes bliver stående i model-input (status quo), mens en FALSK positiv
    ville fjerne et ægte svar. Bedre at filteret misser end at det spiser.
    """
    try:
        t = str(tekst or "").strip().lower()
        if not t or len(t) > 600:
            return False
        alle = _MENNESKE_KENDETEGN + _MENNESKE_KENDETEGN_EKSTERNE
        return any(k in t for k in alle)
    except Exception:
        logger.warning("guard_notices: kunne ikke vurdere note", exc_info=True)
        return False


def er_handler_note(tekst: str) -> bool:
    """Er dette en klasse-1-note? Den SKAL naa modellen; her kun til mærkning."""
    try:
        t = str(tekst or "").strip().lower()
        if not t or len(t) > 600:
            return False
        return any(k in t for k in _HANDLER_KENDETEGN)
    except Exception:
        logger.warning("guard_notices: kunne ikke vurdere handler-note", exc_info=True)
        return False


def fjern_menneske_noter(dele: list[str]) -> list[str]:
    """Fjern klasse-3-noter fra de dele der bliver model-input.

    `_a_parts` tjener BEGGE: den persisteres (Bjørn ser noten) og den bliver
    næste rundes model-input. Denne funktion kaldes KUN på vejen til modellen —
    listen selv røres aldrig, så det persisterede svar beholder noten.

    Self-safe → uændret liste ved fejl.
    """
    try:
        return [d for d in (dele or []) if not er_menneske_note(d)]
    except Exception:
        logger.warning("guard_notices: filtrering fejlede — sender uændret",
                       exc_info=True)
        return dele or []


def fjern_menneske_noter_fra_historik(historik: list) -> list:
    """Fjern klasse-3-noter fra den PERSISTEREDE historik modellen får.

    Samme formål som `strip_interruption_notices`, men på tværs af ture: en note
    der blev gemt i går må ikke blive et mønster modellen efterligner i dag.

    Kun ASSISTENT-beskeder, og kun hvis HELE beskeden er noten. En note der står
    sammen med et ægte svar bliver stående — at skære i en gemt besked ville
    ændre historikken, og det er værre end at lade noten stå.
    """
    try:
        ud = []
        for m in historik or []:
            rolle = (m.get("role") if isinstance(m, dict) else None) or ""
            indhold = (m.get("content") if isinstance(m, dict) else "") or ""
            if rolle == "assistant" and er_menneske_note(str(indhold)):
                continue
            ud.append(m)
        return ud
    except Exception:
        logger.warning("guard_notices: historik-filtrering fejlede", exc_info=True)
        return historik or []
