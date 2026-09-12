"""Fjern runtime'ens interne markører fra den tekst brugeren ser.

## Hvorfor den findes

Gaterne taler til Jarvis i hans egen tur. `decision_signal_staging` lægger
noten i `_exchange_text()` — assistent-turen som modellen får tilbage næste
runde — og holder den ude af `_a_parts`, så både det persisterede svar og
resolution-tjekket forbliver rene. Det virker efter hensigten.

Men noten står dermed i modellens *egne forrige ord*. Målt 12/9-2026 på
runtime: 82 af 2.830 ture (2,9 %) indeholdt markøren i det synlige svar — med
**3.924 forekomster** fordelt på de 82, altså ~48 gentagelser pr. ramt besked.
Ingen kodesti skriver dem dertil; alle otte `_a_parts.append`-steder er enten
modellens tekst eller en eksplicit vagt-besked. Modellen efterligner det
mønster den ser i sin egen hale — samme mekanik som afbrydelses-stubben i
`interruption_notice_parroting`.

Derfor kan kilden alene ikke bære garantien. En model kan efterligne hvad som
helst den ser, og signalet *skal* blive ved med at nå Jarvis. Så vagten sidder
hvor garantien kan gives: mellem teksten og skærmen.

## Hvorfor en scanner og ikke et regex

Markøren indeholder sine egne klammer:

    [decision-signal: interceptor (verification: [interceptor:verification] R2 …)]

Et ikke-grådigt `\\[decision-signal:.*?\\]` stopper ved det INDRE `]` og
efterlader « R2 blød surface — uverificerede mutationer)]» på skærmen — altså
netop den støj vi fjerner, minus sit navn. Et grådigt `.*\\]` æder alt frem til
det sidste `]` i hele beskeden. Klammetælling er den eneste form der klarer
begge, og den er kort nok til at læse.
"""
from __future__ import annotations

import re

# Præfikser der markerer en intern note. Alt fra præfikset til dets balancerede
# slut-klamme fjernes. Holdt som en liste fordi gaterne er flere organer, og
# den næste der får en stemme skal kunne tilføjes ét sted.
INTERNE_PRAEFIKSER: tuple[str, ...] = (
    "[decision-signal:",
    "[interceptor:",
)

# Længste note vi tror på. En «[» der IKKE er en note må ikke kunne holde
# ubegrænset tekst tilbage i strømmen — så hellere slippe den igennem end at
# tie resten af svaret ihjel.
MAKS_NOTE = 600


def _slut_paa_note(tekst: str, start: int) -> int | None:
    """Indeks EFTER den klamme der lukker noten der begynder på `start`.

    None hvis noten ikke er lukket inden for `MAKS_NOTE` — så ved kalderen at
    der enten mangler tekst (strøm) eller at det ikke var en note (færdig tekst).
    """
    dybde = 0
    for i in range(start, min(len(tekst), start + MAKS_NOTE)):
        c = tekst[i]
        if c == "[":
            dybde += 1
        elif c == "]":
            dybde -= 1
            if dybde == 0:
                return i + 1
    return None


def _foerste_markoer(tekst: str, fra: int = 0) -> int:
    """Indeks på den tidligste interne markør fra `fra`, eller -1."""
    fund = [tekst.find(p, fra) for p in INTERNE_PRAEFIKSER]
    fund = [i for i in fund if i >= 0]
    return min(fund) if fund else -1


def fjern_interne_markoerer(tekst: str) -> str:
    """Teksten uden runtime-noter, med tomme linjer ryddet op efter sig.

    En uafsluttet markør i halen fjernes OGSÅ: bliver et svar klippet midt i en
    note, er en halv note lige så meget støj som en hel.
    """
    if not tekst:
        return tekst
    # Faerdig tekst er bare en strøm der slutter med det samme. At bygge den
    # paa samme funktion er det eneste der garanterer at det brugeren SER under
    # streaming, og det der GEMMES bagefter, er den samme tekst — to
    # implementeringer ville droppe ud af sync ved foerste saerlige tilfaelde.
    klar, hale = fjern_interne_markoerer_stroem(tekst)
    if _foerste_markoer(hale) >= 0:
        hale = hale[: _foerste_markoer(hale)]  # uafsluttet note i halen er støj
    return _ryd_tomrum(klar + hale)


def _ryd_tomrum(tekst: str) -> str:
    """Noten stod i sit eget afsnit. Fjerner man den, står der tre tomme
    linjer tilbage — et hul der ligner en fejl i svaret."""
    tekst = re.sub(r"[ \t]+\n", "\n", tekst)
    tekst = re.sub(r"\n{3,}", "\n\n", tekst)
    return tekst.strip()


def _uden_markoerord(tekst: str) -> str:
    """Teksten med selve markoer-ordene fjernet, men indholdet bevaret."""
    for p in INTERNE_PRAEFIKSER:
        tekst = tekst.replace(p, "")
    return tekst


class StroemSkrubber:
    """Samme fjernelse, men på en strøm hvor markøren kan være delt over flere
    deltaer.

    En note ankommer sjældent i ét stykke. Derfor holdes en hale tilbage så
    snart den kan være begyndelsen på en markør, og slippes først når det er
    afgjort. Garantien er: ingen delvis markør forlader nogensinde skrubberen.
    """

    def __init__(self) -> None:
        self._hale = ""

    def foed(self, stykke: str) -> str:
        """Den del af `stykke` der trygt kan sendes videre nu."""
        self._hale += stykke or ""
        klar, self._hale = fjern_interne_markoerer_stroem(self._hale)
        if len(self._hale) > MAKS_NOTE:
            # Loftet. En aegte note er ~110 tegn og ALTID lukket; en «[» der
            # holder 600+ tegn er ikke en note, men den kan tie resten af
            # svaret ihjel saa laenge vi venter paa en lukkeklamme der aldrig
            # kommer. Saa slippes indholdet — kun selve markoer-ordet falder
            # vaek, for det er det Bjoern ikke skal se.
            frigivet = _uden_markoerord(self._hale)
            self._hale = ""
            return klar + frigivet
        return klar

    def skyl(self) -> str:
        """Resten, når strømmen er slut. Uafsluttede noter ryger."""
        rest = fjern_interne_markoerer(self._hale)
        self._hale = ""
        return rest


def fjern_interne_markoerer_stroem(buffer: str) -> tuple[str, str]:
    """(klar-til-udsendelse, hale-der-skal-holdes-tilbage).

    ## Den ene invariant der baerer det hele

    **Tomrum sendes aldrig ud foer vi ved hvad der foelger.** Alt andet falder
    ud af den. En note staar i sit eget afsnit, saa naar den klippes vaek, skal
    de to blanke linjer omkring den blive til én — og det kan kun afgoeres naar
    teksten efter noten er ankommet. Holder vi afsluttende tomrum tilbage, er
    den blanke linje stadig i bufferen naar noten dukker op i naeste delta.

    Foerste udgave gjorde det rekursivt og sendte `foer` af sted undervejs.
    Resultatet afhang saa af HVOR strømmen knaekkede: maalt gav chunk=5
    «abcdef» og chunk=3 én linje for lidt. Denne udgave klipper alle hele
    noter ud af bufferen foerst, og afgoer FOERST derefter hvor lidt der trygt
    kan sendes.
    """
    while True:
        j = _foerste_markoer(buffer)
        if j < 0:
            break
        slut = _slut_paa_note(buffer, j)
        if slut is None:
            break  # uafsluttet note — resten af bufferen holdes tilbage
        # Ingen syntese af afsnitsbrud. Foerste udgave skrev et "\n\n" naar
        # noten blev klippet ud, men naar `efter` endnu var tom, ankom kildens
        # EGEN blanke linje bagefter og lagde sig oven i det syntetiske — to
        # noter efter hinanden gav «\n\n\n» midt i svaret (maalt v. chunk 32
        # og 40). Tomrummet faar lov at staa som det er og klappes sammen
        # nedenfor; det kan lade sig goere fordi afsluttende tomrum aldrig
        # sendes ud, og derfor stadig er til stede naar resten ankommer.
        buffer = buffer[:j] + buffer[slut:]

    buffer = _klap_tomrum_sammen(buffer)
    j = _foerste_markoer(buffer)
    if j >= 0:
        # Uafsluttet note: hold den og tomrummet foran den tilbage.
        krop = buffer[:j]
    else:
        # Kunne halen vaere begyndelsen paa en markoer? «[dec» er ikke en
        # markoer endnu, men sender vi den, kan vi ikke traekke den tilbage.
        hold = _muligt_praefiks(buffer)
        krop = buffer[: len(buffer) - len(hold)]
    skaering = len(krop.rstrip())
    return buffer[:skaering], buffer[skaering:]


def _klap_tomrum_sammen(tekst: str) -> str:
    """Tre eller flere linjeskift bliver til ét afsnitsbrud.

    Koeres paa HELE bufferen hver gang, ogsaa paa den hale der endnu ikke er
    sendt — derfor kan et hul der opstaar hen over to deltaer stadig naa at
    lukke sig. Roerer kun tomrum, aldrig tegn.
    """
    tekst = re.sub(r"[ \t]+\n", "\n", tekst)
    return re.sub(r"\n{3,}", "\n\n", tekst)


def _muligt_praefiks(buffer: str) -> str:
    """Den slut-stump der kunne være starten på en markør — ellers «»."""
    for p in INTERNE_PRAEFIKSER:
        for n in range(min(len(p) - 1, len(buffer)), 0, -1):
            if buffer.endswith(p[:n]):
                return buffer[-n:]
    return ""
