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
* De VEDVARENDE beskeder (styringer, hollow-promise-nudgen, hook-noter,
  baggrunds-shell-noter) gjorde noget vaerre: de aendrede hvilken besked der er
  den SIDSTE user-besked. ``build_lean_base_messages`` finder halen ved at
  lede efter netop den, saa fra det oejeblik fandt slankningen intet at skaere
  og gav den fulde hale tilbage — resten af turen. Ét run gik fra hale 5.859
  tegn til 26.838, og hit faldt fra 130.176 til 9.472 paa én runde: 120.704
  tokens tabt genkendelse.

## De to slags

``vedvarende`` gaelder fra det oejeblik de opstaar og resten af turen: en
styring brugeren skrev midtvejs, en note fra en baggrunds-shell. De skal med i
hver eneste foelgende runde, ellers ville historikken skifte mellem runder.

``runde`` gaelder KUN den runde de blev lavet til: et budget-varsel, et
batch-vink. De ryddes ved hver ny runde.

Begge haefter sig bagest, og de vedvarende staar foerst, fordi de er aeldst.
"""
from __future__ import annotations

from typing import Any


class RundeHale:
    """Turens hale. Ikke en liste, fordi de to slags har hver sin levetid."""

    __slots__ = ("_vedvarende", "_runde")

    def __init__(self) -> None:
        self._vedvarende: list[dict[str, Any]] = []
        self._runde: list[dict[str, Any]] = []

    def tilfoej_vedvarende(self, indhold: str, *, rolle: str = "user") -> None:
        """En besked der gaelder resten af turen. Tom tekst ignoreres —
        en tom besked ville forskyde historikken uden at sige noget."""
        tekst = str(indhold or "")
        if not tekst:
            return
        self._vedvarende.append({"role": rolle, "content": tekst})

    def tilfoej_runde(self, indhold: str, *, rolle: str = "user") -> None:
        """En besked der kun gaelder DENNE runde."""
        tekst = str(indhold or "")
        if not tekst:
            return
        self._runde.append({"role": rolle, "content": tekst})

    def ny_runde(self) -> None:
        """Ryd runde-beskederne. De vedvarende bliver."""
        self._runde.clear()

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

    def __len__(self) -> int:
        return len(self._vedvarende) + len(self._runde)
