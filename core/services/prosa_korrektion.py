"""Ret prosa-opremsninger FØR svaret vises — ikke som et flag bagefter.

Baggrund (målt 25/10-2026, Bjørn): «den første.. og i gør commits skal vises
ordenligt og ikk som en lang besked men med den rigtige opstilling.. vi arbejder
næsten kun i git og det er vigtig sådan ting står ordenligt... men det gælder
osse for andre ting end git.. oplevelsen gør det hele».

Han pegede på det samme svar to gange: først som «den svageste første sektion»,
derefter som «en prosa med en linje til Commit e4036a383 … er rodet». Guarden
fra samme dag (``prosa_struktur_guard``) SÅ fejlen — den skrev den bare i
``central_incidents`` som ``severity="info"``. Et flag ingen læser er ikke en
kontrol, det er en log. Rækkefølgen var forkert igen: kontrollen kørte efter
svaret var formuleret, så dens eneste mulighed var at konstatere fejlen.

Denne modul er den manglende runde, og den er bygget som ``flade_korrektion``:
tag den færdige tekst, spørg guarden hvad der er galt, bed modellen rette KUN
de ramte afsnit — én gang, med et hårdt loft. Kan den ikke, står teksten
uændret.

Designvalg der ikke er tilfældige:

* **Kun de ramte afsnit sendes.** Et svar på 20.000 tegn med ét smøre-afsnit
  skal ikke koste et helt nyt svar, og modellen skal ikke have mere at
  ødelægge end nødvendigt.
* **Én runde, ikke en løkke.** En korrektion der fejler, fejler.
* **Fail-open.** Kan modellen ikke kaldes, eller svarer den ubrugeligt,
  returneres den oprindelige tekst. Et svar må aldrig gå tabt på at forsøge at
  forbedre det.
* **Korridoren er snæver.** Modellen må kun returnere de erstattede afsnit,
  ikke hele svaret. Det gør det mekanisk at sætte dem tilbage — og umuligt for
  den at tabe prosa undervejs.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

#: Loft for hvor mange afsnit der sendes til korrektion i én runde. Et svar
#: med ti smøre-afsnit er ikke et format-problem, det er et nyt svar.
_MAX_AFSNIT = 4

#: Loft for hvor meget tekst der sendes. Samme princip som flade-korrektionen:
#: kun det nødvendige vindue, ikke hele svaret.
_MAX_KONTEKST = 6000

_KORREKTIONS_INSTRUKS = """\
Dit svar er allerede skrevet og vist for brugeren. Nogle afsnit under en \
overskrift opremser flere parallelle ting som løbende prosa, hvor de skulle \
have stået som punktopstilling. Brugeren skal kunne skimme svaret.

Ret KUN de afsnit der er listet nedenfor. Regler:

1. Returnér præcis ÉT afsnit pr. nummer, i samme rækkefølge, adskilt af en \
linje med kun `---`. Skriv INGEN overskrift, ingen indledning, ingen \
afslutning, ingen forklaring.
2. Hvert afsnit skal være en punktopstilling: én linje pr. selvstændigt led, \
med `- ` foran. Bær hvert led over ORDRET — samme ord, samme tal, samme \
hash, samme sti. Ændr ikke indholdet, kun opstillingen.
3. Har et led en naturlig etiket (fx «Commit», «Filen», «Tests»), sæt den \
foran med en tankestreg: `- Commit — e4036a383, kl. 12:38:27, pushet`.
4. Er et afsnit allerede velstruktureret, returnér det uændret.
5. Opfind aldrig et led, et tal eller en etiket der ikke stod i afsnittet. \
Kan et afsnit ikke deles uden at opfinde data, returnér det uændret.
"""


def _baerende_tokens(tekst: str) -> list[str]:
    """De ord i et afsnit der ikke må forsvinde: tal, hashes og stier.

    Målt 25/10-2026: en model der svarer med fire tomme punkter består enhver
    liste-kontrol, men erstatter et afsnit med ingenting. Det er den slags
    korrektion der gør et svar værre — og den er usynlig hvis man kun måler
    formen. Hashes, klokkeslæt, filstier og rene tal er det konkrete indhold;
    prosa-ord kan omformuleres, de kan ikke.
    """
    tokens: list[str] = []
    for raa in re.findall(r"[A-Za-z0-9_./:-]{4,}", tekst):
        kerne = raa.strip(".,;:")
        if not kerne:
            continue
        # Kun det der bærer fakta: cifre, eller en sti/hash med både bogstav og tal.
        har_ciffer = any(c.isdigit() for c in kerne)
        if not har_ciffer:
            continue
        if kerne not in tokens:
            tokens.append(kerne)
    return tokens


def _afsnit_tekst(tekst: str, punkt) -> str:
    """Find det rå afsnit i teksten som ``punkt`` peger på.

    ``ProsaPunkt.uddrag`` er normaliseret (linjer slået sammen), så det kan
    ikke bruges til at klippe i originalen. Vi leder i stedet efter den
    sammenhængende blok hvis normaliserede form matcher uddraget.
    """
    maal = " ".join(punkt.uddrag.split())
    linjer = tekst.split("\n")
    for start in range(len(linjer)):
        for slut in range(start + 1, min(start + 40, len(linjer)) + 1):
            kandidat = " ".join(" ".join(linjer[start:slut]).split())
            if kandidat == maal:
                return "\n".join(linjer[start:slut])
            if len(kandidat) > len(maal) + 40:
                break
    return ""


def _del_svar(tekst: str, dele: list[str]) -> str:
    """Sæt de returnerede afsnit tilbage i teksten, ét ad gangen.

    Hvert afsnit erstattes ved at finde dets oprindelige form og bytte det ud.
    Kan et afsnit ikke findes, springes det over — en korrektion der ikke kan
    placeres må ikke flytte rundt på resten af svaret.
    """
    nyt = tekst
    for original, erstatning in dele:
        if not original or not erstatning:
            continue
        if original not in nyt:
            logger.debug("prosa_korrektion: afsnittet kunne ikke genfindes — sprunget over")
            continue
        nyt = nyt.replace(original, erstatning, 1)
    return nyt


def korriger_prosa(
    tekst: str,
    fejl: list[str],
    *,
    stream_followup,
    provider: str,
    model: str,
    base_messages: list[dict],
    run_id: str = "",
    session_id: str = "",
) -> str:
    """Bed modellen rette prosa-opremsninger. Returnerer ny tekst.

    ``stream_followup`` er ``stream_visible_followup`` (injektionspunktet der
    gør funktionen testbar uden netværk). Returnerer den OPRINDELIGE tekst ved
    enhver fejl — en korrektion der ikke kan gennemføres må ikke koste svaret.
    """
    if not tekst or not fejl:
        return tekst

    try:
        from core.services.prosa_struktur_guard import find_prosa_punkter
    except Exception:
        logger.debug("prosa_korrektion: kunne ikke importere guarden", exc_info=True)
        return tekst

    punkter = find_prosa_punkter(tekst)[:_MAX_AFSNIT]
    if not punkter:
        return tekst

    par: list[tuple[str, str]] = []
    for punkt in punkter:
        original = _afsnit_tekst(tekst, punkt)
        if original:
            par.append((original, punkt))
    if not par:
        logger.debug("prosa_korrektion: ingen afsnit kunne genfindes i teksten")
        return tekst

    opgave_dele: list[str] = []
    for nr, (original, punkt) in enumerate(par, start=1):
        opgave_dele.append(
            f"Afsnit {nr} (under «{punkt.overskrift}», {punkt.antal_led} led):\n"
            f"{original}"
        )
    opgave = "\n\n".join(opgave_dele)[:_MAX_KONTEKST]

    trailing = [
        {"role": "user", "content": _KORREKTIONS_INSTRUKS + "\n\n" + opgave},
    ]

    try:
        from core.services.visible_followup_events import (
            FollowupDelta,
            FollowupDone,
            FollowupFailed,
        )
    except Exception:
        logger.debug("prosa_korrektion: kunne ikke importere events", exc_info=True)
        return tekst

    dele: list[str] = []
    try:
        for event in stream_followup(
            provider=provider,
            model=model,
            base_messages=base_messages,
            exchanges=[],
            tool_definitions=None,
            round_index=0,
            thinking_mode="fast",
            run_id=run_id,
            session_id=session_id,
            trailing_messages=trailing,
        ):
            if isinstance(event, FollowupDelta):
                dele.append(event.delta)
            elif isinstance(event, FollowupDone):
                if event.text and not dele:
                    dele.append(event.text)
                break
            elif isinstance(event, FollowupFailed):
                logger.debug("prosa_korrektion: runden fejlede: %s", event.error)
                return tekst
    except Exception:
        logger.debug("prosa_korrektion: kaldet fejlede", exc_info=True)
        return tekst

    svar = "".join(dele).strip()
    if not svar:
        return tekst

    # Modellen svarer med ÉT afsnit pr. nummer, adskilt af `---`. Færre dele
    # end afsnit betyder at den har tabt et — så er svaret ikke til at stole på.
    # (Målt 25/10-2026: med kun ét afsnit findes ingen separator, så split på
    # `\n---` giver én del — det er korrekt, ikke en fejl.)
    stykker = [s.strip() for s in svar.split("\n---") if s.strip()]
    if len(stykker) != len(par):
        logger.debug(
            "prosa_korrektion: forventede %d afsnit, fik %d — forkastet",
            len(par), len(stykker),
        )
        return tekst

    erstatninger: list[tuple[str, str]] = []
    for (original, _punkt), stykke in zip(par, stykker):
        # Kun punktopstilling tæller som en korrektion. Returnerer modellen
        # prosa igen, er der intet vundet — og vi rører ikke teksten.
        if not any(l.lstrip().startswith(("- ", "* ")) for l in stykke.split("\n")):
            logger.debug("prosa_korrektion: svaret var ikke en liste — forkastet")
            return tekst
        # Indholdet skal bæres over. Målt 25/10-2026: en model der svarer med
        # fire tomme punkter består liste-kontrollen, men erstatter et afsnit
        # med ingenting. Hvert bærende token (tal, hash, sti) skal stadig stå
        # der — ellers er korrektionen et tab, ikke en forbedring.
        for token in _baerende_tokens(original):
            if token not in stykke:
                logger.debug(
                    "prosa_korrektion: «%s» forsvandt i korrektionen — forkastet", token,
                )
                return tekst
        erstatninger.append((original, stykke))

    nyt = _del_svar(tekst, erstatninger)
    if nyt == tekst:
        return tekst

    # Kontrollér at korrektionen faktisk hjalp. Ellers er den bare en anden fejl.
    try:
        from core.services.prosa_struktur_guard import fejl_i_prosa as _fejl_efter
    except Exception:  # import kan fejle i en delt proces; uden kontrollen er korrektionen stadig brugbar
        return nyt
    if len(_fejl_efter(nyt)) >= len(fejl):
        logger.debug("prosa_korrektion: korrektionen hjalp ikke — forkastet")
        return tekst
    return nyt
