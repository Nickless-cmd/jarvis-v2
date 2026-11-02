"""Kontekst-proveniens: hvad var FAKTISK i den prompt der blev bygget.

2/11-2026. Bjørn målte at `memcite` blev godkendt uden kontrol af om memory
overhovedet var i den aktuelle modelkontekst. Kontrakten skrev i sin kommentar
at «det er runtime der afgjorde at den var i konteksten» — men runtime afgjorde
intet. Markøren blev godkendt, fordi der ikke fandtes nogen at spørge.

Det her er den nogen: `prompt_contract` registrerer, når den bygger
`[HUKOMMELSE]`-gruppen, hvor mange linjer den faktisk lagde ind. Citation-
kontrakten spørger derefter registeret — ikke sin egen antagelse.

## Hvorfor en probe og ikke et flag

Rækkefølgen er bindende og var årsagen til at kæden var død i går:

* `visible_runs` laver `FirstPassOutputFilter` ved run-start, **før** prompten
  findes.
* Prompten bygges inde i `pump_first_pass`, altså **efter** filteret.

Et boolsk flag sat ved instansiering ville derfor være `False` for evigt. En
probe, der aflæses ved opslaget, rammer den rækkefølge der faktisk gælder.

## Hvorfor TTL

Uden en udløbsgrænse kunne en tur fra i går godkende en `memcite` i dag, fordi
sessionen er den samme. Sandheden skal være frisk. 10 minutter er rigeligt til
en prompt-bygning og et svar, og kort nok til at en gammel registrering ikke
kan lække ind i en ny tur.

Kun stdlib — modulet importeres fra prompt-bygningen, som er den varmeste sti
i hele runtime.
"""

from __future__ import annotations

import threading
import time

#: Hvor længe en registrering regnes som frisk.
TTL_SEKUNDER = 600.0

#: session_id → (monotonic-tidsstempel, antal memory-linjer).
_REGISTER: dict[str, tuple[float, int]] = {}
_LAAS = threading.Lock()


def marker_memory_i_kontekst(session_id: str, antal_linjer: int) -> None:
    """Registrér at `[HUKOMMELSE]` blev bygget med `antal_linjer` linjer.

    Kaldes fra `prompt_contract` dér hvor gruppen dannes. `antal_linjer = 0`
    betyder eksplicit «ingen memory i denne prompt» — det er en sandhed, ikke
    en manglende registrering, og den skal kunne slå en tidligere tur ud.
    """
    if not session_id:
        return
    with _LAAS:
        _REGISTER[session_id] = (time.monotonic(), max(0, int(antal_linjer)))


def memory_i_kontekst(session_id: str) -> bool:
    """Var der memory-linjer i den seneste byggede prompt for sessionen?

    Ukendt session, tom session eller udløbet registrering → `False`. Det er
    fail-closed og bevidst: en `memcite` er en påstand om at svaret bygger på
    hukommelse, og uden et friskt spor er påstanden udokumenteret.
    """
    if not session_id:
        return False
    with _LAAS:
        post = _REGISTER.get(session_id)
        if post is None:
            return False
        tid, antal = post
        if (time.monotonic() - tid) > TTL_SEKUNDER:
            _REGISTER.pop(session_id, None)
            return False
        return antal > 0


def ryd_register() -> None:
    """Tøm registeret. Kun til tests — ellers lever det som en lille dict."""
    with _LAAS:
        _REGISTER.clear()


__all__ = [
    "TTL_SEKUNDER",
    "marker_memory_i_kontekst",
    "memory_i_kontekst",
    "ryd_register",
]
