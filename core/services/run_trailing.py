"""Beskeder der hoerer EFTER historikken i en agentisk tur.

## Hvorfor de ikke maa ligge i base_messages

Beskedlisten bygges som ``base_messages + exchanges + hale``. Alt der laegges
paa ``base_messages`` havner derfor MIDT i prompten — foran hele den voksende
vaerktoejshistorik. DeepSeeks praefiks-cache genkender fra begyndelsen og
fremad, saa én besked indsat dér forskyder alt bagefter og braekker cachen paa
netop det sted.

Maalt paa CT105 28/9-2026, to gange:

* Per-runde-vinkene (budget, batch, tvungen afslutning) dukkede op og forsvandt
  igen. Ét run: 6.840 miss-tokens i snit i de ramte runder mod 1.109 i de
  oevrige — 27 % af hele runets miss, for tre beskeder paa 242 tegn.
* En STYRING i halen (rolle ``user``) gjorde noget vaerre: den aendrede hvilken
  besked der er den SIDSTE user-besked. ``build_lean_base_messages`` finder
  halen ved at lede efter netop den, saa fra det oejeblik fandt slankningen
  intet at skaere og gav den fulde hale tilbage — resten af turen. Ét run gik
  fra hale 5.859 tegn til 26.838, og hit faldt fra 130.176 til 9.472 paa én
  runde: 120.704 tokens tabt genkendelse. Styringer ligger nu i HISTORIKKEN
  (``ToolExchange.user_message``), ikke her — 7/10-2026.

## De tre slags

``vedvarende`` gaelder fra det oejeblik de opstaar og resten af turen. Den
bruges ikke af den agentiske loekke laengere (7/10-2026: alle fem kald-steder
gik til ``naeste``), men levetiden er aegte og staar aaben for en note der
virkelig skal blive ved.

## ARTEN — hvorfor levetiden ikke er nok (10/10-2026)

Levetiden siger HVOR LAENGE en note bliver. Den siger ikke HVAD den er — og
forskellen mellem de to er hele grunden til at turen nogle gange kører en runde
mere end den burde.

Målt 10/10-2026: batch-vinket stod i halen i runde 4 af et run, og runde 5
fulgte. Præcis én ekstra runde. Det er ikke en parameter der er skruet
forkert — **en note i halen kan kun nå modellen ved at køre modellen igen.**
Enhver note der lægges ved runde-SLUT koster +1 runde. Det er mekanikken.

Derfor bærer hver note nu en ART:

``forpligtelse`` — noten beskriver noget der SKAL ske, og turen er ikke
faerdig uden. De fem gater (hollow-promise, skill, baggrunds-shell, stop-hook,
stillingtagen) er forpligtelser: de fyrer fordi modellen gjorde noget
ufuldstaendigt, og de tvinger deres runde med ``tool_choice="required"``.
Runden er ikke spildt — den er arbejdet.

``raadgivning`` — noten er en observation om RYTME eller FORM, ikke et krav.
Batch-vinket og budget-varslet er raadgivning: de siger «du kunne gøre det
anderledes naeste gang», ikke «du mangler noget». En raadgivning maa derfor
ALDRIG vaere grunden til at turen fortsaetter — den rider med paa en runde der
sker alligevel. Er der ingen saadan runde, er den ikke vaerd at køre.

Skellet er ikke kosmetik. Uden det kan en raadgivning kun leveres ved at
koste en runde, og prisen betaler sig ikke: maalt 10/10 ramte syv runs
45-runde-loftet med 65-110 kald — ca. 1,8 kald pr. runde — efter tre uger hvor
batch-vinket har kostet en runde pr. tur uden at flytte tallet.

``naeste`` gaelder KUN den naeste runde: den rykker ind i ``runde`` naar
``ny_runde()`` kaldes, og forsvinder med den runde der foelger. Det er formen
for de fem gates i loekken (hollow-promise, skill, baggrunds-shell, stop-hook,
stillingtagen). De fyrer ved runde-SLUT, og noten skal praege praecis den runde
der kommer — ikke de naeste fyrre.

Hvorfor ikke ``runde`` til dem: ``ny_runde()`` rydder ved runde-START, og
gaterne fyrer ved runde-SLUT. En ``runde``-note ville altsaa blive slettet foer
den nogensinde blev sendt. ``naeste`` er den levetid der manglede mellem de to.

Maalt 7/10-2026, hollow-promise-noten alene: 426 fyringer over 356 ture, og
2.226 gen-sendinger i alt — 5,4 i snit pr. ramt tur, vaerst 40 i én tur. Noten
blev ikke appendet igen; den blev staaende i halen, og halen sendes hver runde.

``runde`` gaelder KUN den runde de blev lavet til: et budget-varsel, et
batch-vink. De ryddes ved hver ny runde.

Alle haefter sig bagest, og de staar i levetids-raekkefoelge: vedvarende
(aeldst), saa de naeste der er rykket ind i runden, saa rundens egne vink.
"""
from __future__ import annotations

from typing import Any


_RUNTIME_FRAME = "[RUNTIME — ikke en besked fra brugeren]\n"

#: Notens art. Se modul-docstringen: levetiden siger hvor laenge, arten siger
#: hvad. En ``raadgivning`` maa aldrig vaere grunden til at turen fortsaetter.
FORPLIGTELSE = "forpligtelse"
RAADGIVNING = "raadgivning"

#: De to arter der findes. Bruges af vagten i ``tilfoej_naeste``.
_ARTER = frozenset({FORPLIGTELSE, RAADGIVNING})


def runtime_instruction_message(text: str) -> dict[str, str]:
    """A model-facing runtime instruction with explicit non-user provenance."""
    return {"role": "system", "content": _RUNTIME_FRAME + str(text or "")}


class RundeHale:
    """Turens hale. Ikke en liste, fordi de tre slags har hver sin levetid."""

    __slots__ = ("_vedvarende", "_naeste", "_runde")

    def __init__(self) -> None:
        self._vedvarende: list[dict[str, Any]] = []
        self._naeste: list[dict[str, Any]] = []
        self._runde: list[dict[str, Any]] = []

    def tilfoej_vedvarende(
        self, indhold: str, *, rolle: str = "system", art: str = FORPLIGTELSE
    ) -> None:
        """En besked der gaelder resten af turen. Tom tekst ignoreres —
        en tom besked ville forskyde historikken uden at sige noget."""
        tekst = str(indhold or "")
        if not tekst:
            return
        if rolle == "system":
            tekst = _RUNTIME_FRAME + tekst
        self._vedvarende.append({"role": rolle, "content": tekst, "art": art})

    def tilfoej_naeste(
        self, indhold: str, *, rolle: str = "system", art: str = FORPLIGTELSE
    ) -> None:
        """En besked der gaelder KUN den naeste runde.

        Til noter fra de gates der fyrer ved runde-SLUT: de skal praege runden
        der kommer, og derefter vaere vaek. Laa de i ``runde``, ville
        ``ny_runde()`` slette dem ved runde-START — foer de blev sendt.

        ``art`` er som standard ``FORPLIGTELSE``: de fem gater er netop
        forpligtelser, og de tvinger deres runde med ``tool_choice="required"``.
        En ``RAADGIVNING`` her er en fejlklassificering — den ville koste en
        runde uden at kraeve den. Se modul-docstringen.
        """
        tekst = str(indhold or "")
        if not tekst:
            return
        if rolle == "system":
            tekst = _RUNTIME_FRAME + tekst
        self._naeste.append({"role": rolle, "content": tekst, "art": art})

    def tilfoej_runde(
        self, indhold: str, *, rolle: str = "system", art: str = RAADGIVNING
    ) -> None:
        """En besked der kun gaelder DENNE runde.

        ``art`` er som standard ``RAADGIVNING``: det er formen for de noter der
        ikke kraever noget — et budget-varsel, et batch-vink. De maa ikke vaere
        grunden til at turen fortsaetter.
        """
        tekst = str(indhold or "")
        if not tekst:
            return
        if rolle == "system":
            tekst = _RUNTIME_FRAME + tekst
        self._runde.append({"role": rolle, "content": tekst, "art": art})

    def ny_runde(self) -> None:
        """Ryd runde-beskederne; de vedvarende bliver, og de naeste rykker ind.

        De naeste laegges FOERST i den nye runde, saa de staar foer rundens egne
        vink — de er aeldst, og runden laeser dem som en note der kom foer
        vinket. Den gamle ``_runde``-liste erstattes (ikke clears), saa en
        kopi som pumpen allerede har bundet til et igangvaerende forsoeg ikke
        aendrer sig under den.
        """
        self._runde = list(self._naeste)
        self._naeste.clear()

    def som_liste(self) -> list[dict[str, Any]]:
        """Halen i afsendelses-raekkefoelge: vedvarende foerst, saa rundens.

        En KOPI, med vilje: pumpen binder den som default-argument for at et
        retry af samme runde sender byte-identisk. Gav vi den interne liste
        videre, ville en senere styring aendre en runde der allerede er sendt.
        """
        return [*self._vedvarende, *self._runde]

    @property
    def antal_vedvarende(self) -> int:
        return len(self._vedvarende)

    @property
    def antal_naeste(self) -> int:
        return len(self._naeste)

    @property
    def raadgivning_i_runden(self) -> int:
        """Hvor mange noter i den sendte hale der er raadgivning, ikke krav.

        Løkken kan bruge tallet til at se om en runde bærer en note der ikke
        kraever noget — og dermed ikke er grund til at fortsætte. Er tallet
        lig antallet af sendte noter, bærer runden intet krav.
        """
        return sum(
            1 for m in self.som_liste() if m.get("art") == RAADGIVNING
        )

    def __len__(self) -> int:
        return len(self._vedvarende) + len(self._naeste) + len(self._runde)

    def telemetri(self) -> dict[str, Any]:
        """Kompakt billede af halen, praecis som den sendes i denne runde.

        Halen blev sendt i HVER runde, men der fandtes intet tal paa hvad den
        bar. Den gamle fejl — hollow-promise-noten alene: 426 fyringer over 356
        ture og 2.226 gen-sendinger (5,4 i snit, vaerst 40 i én tur) — kunne
        derfor kun findes ved at grave i koden, ikke ved at laese driften.
        Uden dette kan en note der haenger igen heller ikke ses, foer nogen
        opdager det i svarene.

        ``naeste`` taelles med, men indgaar ikke i ``poster``: den er endnu ikke
        rykket ind i runden og sendes ikke foer ``ny_runde()``. At blande dem
        sammen ville vaere et tal der loj om hvad modellen faktisk fik.

        To slags tal, med vilje: ``tegn`` er hvad modellen FAAR (inkl.
        runtime-rammen), mens ``poster[].tegn`` er notens eget indhold uden
        rammen — saa det staar ved siden af den etiket det beskriver.

        Self-safe: halen er interne lister af dicts; intet her maa kunne kaste.
        """
        def _etiket(levetid: str, besked: dict[str, Any]) -> dict[str, Any]:
            tekst = str(besked.get("content") or "")
            # Runtime-rammen er konstant og siger intet om noten — skael den fra,
            # saa etiketten viser notens egne foerste ord.
            if tekst.startswith(_RUNTIME_FRAME):
                tekst = tekst[len(_RUNTIME_FRAME):]
            return {
                "levetid": levetid,
                "art": str(besked.get("art") or FORPLIGTELSE),
                "rolle": str(besked.get("role") or ""),
                "tegn": len(tekst),
                "label": tekst[:48],
            }

        poster = (
            [("vedvarende", m) for m in self._vedvarende]
            + [("runde", m) for m in self._runde]
        )
        sendt = self.som_liste()
        return {
            "vedvarende": len(self._vedvarende),
            "naeste": len(self._naeste),
            "runde": len(self._runde),
            "beskeder": len(sendt),
            "raadgivning": sum(1 for m in sendt if m.get("art") == RAADGIVNING),
            "tegn": sum(len(str(m.get("content") or "")) for m in sendt),
            "poster": [_etiket(levetid, m) for levetid, m in poster],
        }
