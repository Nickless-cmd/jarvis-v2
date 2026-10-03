"""Delta-sporet: hvor i kæden bliver streamen klumpet? (3/10-2026)

## Spørgsmålet

Bjørn: «kan du måle om det er modelen der er for hurtigt og det er derfor det
virker som om synteser og svar bliver dumpet ind? streaming burde glide».

Codex målte samme dag på en kørende tur: 36 tekstbidder, 2.274 tegn, ~27
sekunder. Nogle kom under 10 ms fra hinanden; det længste ophold var 9,4
sekunder. Desk brugte imens 90-150 % CPU. Hans egen konklusion var ærlig:

> «Målingen startede midt i runnet … Derfor kan jeg ikke skille modellens egen
> hastighed præcist fra serverens afsendelse og desks visning endnu.»

Det er netop det, der skal afgøres FØR nogen retter noget. En klump kan opstå
tre steder, og de kræver tre forskellige rettelser.

## Hvad sporet gør

To målepunkter i den samme tur:

    ind    hver delta vi modtager FRA udbyderen  (visible_model_adapters)
    ud     hver frame vi sender MOD desk         (chat_stream_v2's relay)

Og så er svaret et simpelt sammenligning:

* er **ind** allerede klumpet → det er modellen/udbyderen, ikke os
* er **ind** jævn og **ud** klumpet → det er vores egen kæde imellem
* er **begge** jævne, og desk klumper alligevel → det er desks visning

Uden begge punkter er enhver konklusion et gæt — og det var præcis grunden
til at Codex ikke kunne afslutte målingen.

## Hvorfor en opsummering og ikke en linje per delta

36 linjer per tur ville drukne journalen og ændre det, der måles: en print per
delta koster selv tid. Sporet samler derfor i hukommelsen og skriver ÉN linje
per målepunkt når turen slutter, med den fordeling der afgør sagen — median,
p95 og det største hul. Et gennemsnit ville skjule netop de 9,4 sekunder.

Slukket som standard. Tænd med::

    touch /tmp/jarvis-delta-trace

Så skriver hver synlig tur to linjer til stderr::

    DELTA-SPOR ind run=visible-1a2b n=36 tegn=2274 varighed=26.8s
               median=112ms p95=1840ms max=9412ms@17
    DELTA-SPOR ud  run=visible-1a2b n=41 tegn=2274 varighed=26.9s
               median=118ms p95=1851ms max=9409ms@19

`max=...@17` siger HVILKEN delta hullet lå før, så den kan findes igen.

Samme mønster som `turn_trace`: sentinel-gated, self-safe, no-op når slukket.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from typing import Final

logger = logging.getLogger(__name__)

_SENTINEL: Final[str] = "/tmp/jarvis-delta-trace"
#: Et run med flere tusind deltaer må ikke kunne æde hukommelse. 5.000 er langt
#: over enhver observeret tur (Codex målte 36) og koster under 100 kB.
_MAKS: Final[int] = 5000
#: Hvor mange runs vi holder styr på ad gangen. En tur rydder sig selv ved
#: `afslut`, men et run der dør uden terminal må ikke lække for evigt.
_MAKS_RUNS: Final[int] = 32

_laas = threading.Lock()
#: {(punkt, run_id): [(monotonic, tegn), ...]}
_spor: dict[tuple[str, str], list[tuple[float, int]]] = {}


def taendt() -> bool:
    """Er sporet slået til? Enhver tvivl → nej, så det aldrig koster noget."""
    try:
        return os.path.exists(_SENTINEL)
    except Exception:  # kan filsystemet ikke laeses, maaler vi ikke — et spor
        # maa aldrig blive en grund til at en tur fejler.
        return False


def noter(punkt: str, run_id: str, tegn: int) -> None:
    """Registrér én delta. No-op når sporet er slukket.

    `punkt` er «ind» (fra udbyderen) eller «ud» (mod desk). Kaster aldrig.
    """
    if not taendt():
        return
    try:
        rid = str(run_id or "")[:48]
        if not rid:
            return
        n = time.monotonic()
        with _laas:
            if len(_spor) > _MAKS_RUNS:
                _spor.clear()
            raekke = _spor.setdefault((str(punkt)[:8], rid), [])
            if len(raekke) < _MAKS:
                raekke.append((n, max(0, int(tegn))))
    except Exception:
        logger.debug("delta-spor: kunne ikke notere", exc_info=True)


def _fordeling(huller: list[int]) -> tuple[int, int, int, int]:
    """(median, p95, max, indeks-for-max) i millisekunder."""
    if not huller:
        return 0, 0, 0, 0
    sorteret = sorted(huller)
    median = sorteret[len(sorteret) // 2]
    p95 = sorteret[min(len(sorteret) - 1, int(len(sorteret) * 0.95))]
    stoerst = max(huller)
    return median, p95, stoerst, huller.index(stoerst) + 1


def afslut(run_id: str) -> dict[str, dict[str, float | int]]:
    """Skriv opsummeringen for et run og ryd det. No-op når slukket.

    Returnerer tallene, så en test kan hævde dem uden at læse stderr.
    """
    if not taendt():
        return {}
    svar: dict[str, dict[str, float | int]] = {}
    try:
        rid = str(run_id or "")[:48]
        with _laas:
            noegler = [k for k in _spor if k[1] == rid]
            data = {k[0]: _spor.pop(k) for k in noegler}
        for punkt in ("ind", "ud"):
            raekke = data.get(punkt) or []
            if len(raekke) < 2:
                continue
            # `round`, ikke `int`: flydende tal gav 49 ms for et hul paa 0,05 s,
            # fordi 100,05 - 100,0 = 0,04999999999999716. En afkortning goer
            # altsaa hvert eneste hul en anelse MINDRE end det var — og en
            # maaling der systematisk underdriver er vaerre end ingen.
            huller = [round((raekke[i][0] - raekke[i - 1][0]) * 1000)
                      for i in range(1, len(raekke))]
            median, p95, stoerst, hvor = _fordeling(huller)
            varighed = raekke[-1][0] - raekke[0][0]
            tal = {
                "n": len(raekke), "tegn": sum(t for _m, t in raekke),
                "varighed_s": round(varighed, 1), "median_ms": median,
                "p95_ms": p95, "max_ms": stoerst, "max_ved": hvor,
            }
            svar[punkt] = tal
            import sys as _s
            print(
                f"DELTA-SPOR {punkt:<3} run={rid} n={tal['n']} "
                f"tegn={tal['tegn']} varighed={tal['varighed_s']}s "
                f"median={median}ms p95={p95}ms max={stoerst}ms@{hvor}",
                file=_s.stderr, flush=True)
    except Exception:
        logger.warning("delta-spor: opsummeringen fejlede", exc_info=True)
    return svar
