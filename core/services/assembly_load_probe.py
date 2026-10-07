"""Hvad lavede maskinen MENS prompten blev samlet?

Bjørn 4/10-2026, efter at jeg havde taget fejl tre gange i træk om den samme
måling: «mål hvad de 120 tråde laver under en assembly».

## Hvorfor den findes

`prompt-assembly-timing` skriver allerede `total_ms` for hver tur. Men et
sekundtal uden sin sammenhæng kan ikke skelne **«assemblyen er blevet tung»**
fra **«boksen var optaget»** — og jeg forvekslede netop de to:

    samme kald, samme parametre, load 1,47  →  2,0 s
    samme kald, samme parametre, load 7,56  →  9,6 s

Jeg målte det første på en tom boks, holdt det op mod live-tal fra en travl,
og kaldte forskellen et fund. Tre forsøg, tre gange samme sammenblanding.
Dataene kunne ikke svare, fordi de ikke bar konteksten.

Nu gør de. Felterne skrives på den linje der i forvejen findes, så næste
måling kan filtrere på «kun ture hvor boksen var rolig» i stedet for at nogen
skal huske hvordan der så ud.

## Hvad `cpu_pr_sek` fortæller

Det vigtigste felt, og det er et FORHOLD, ikke en varighed: processens samlede
CPU-tid delt med vægur-tiden.

* **Nær 0** — assemblyen ventede. På I/O, på en lås, eller på GIL'en mens en
  anden tråd regnede.
* **Nær 1** — én tråd regnede for fuld kraft; det er ægte arbejde.
* **Over 1** — flere tråde regnede samtidig i processen, altså noget andet
  end assemblyen selv var i gang.

Målt kontrolleret 4/10: 0,44 kerner samtidigt Python-arbejde firedoblede en
assembly fra 2,0 til 8,67 s. Mætning af CPU var det ikke — det var
GIL-serialisering. Præcis den tilstand er `cpu_pr_sek` lav OG `traade` høj,
og det kan man nu se i stedet for at udlede det.

## Kontrakt

Som `turn_tail_timing`: kaster aldrig, holder kun et lille dict, og et
måleinstrument der kan ødelægge det det måler er værre end ingen måling.
Hvert felt falder for sig — kan `loadavg` ikke læses, mangler kun det ene.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any

logger = logging.getLogger(__name__)

#: Felter vi ikke kunne læse udelades HELT frem for at stå som 0. Et nul i
#: `load1` ville se ud som en tom maskine — altså det modsatte af sandheden.
_UKENDT = object()


def _proces_cpu_sek() -> float | None:
    """Processens samlede CPU-tid (alle tråde) i sekunder.

    `/proc/self/stat` frem for `time.process_time()`: den sidste tæller KUN
    den kaldende tråds CPU i nogle implementeringer, og det er hele pointen
    her at fange hvad de ANDRE tråde lavede.
    """
    try:
        with open("/proc/self/stat", encoding="ascii") as f:
            # Feltet efter ')' er `state`; utime/stime er nr. 12 og 13 i
            # proc(5), altså indeks 11 og 12 efter den opsplitning.
            felter = f.read().rsplit(") ", 1)[1].split()
        hz = os.sysconf("SC_CLK_TCK") or 100
        return (int(felter[11]) + int(felter[12])) / float(hz)
    except Exception as exc:  # noqa: BLE001
        logger.debug("assembly_load_probe: kunne ikke laese proces-cpu: %s", exc)
        return None


def start() -> dict[str, Any]:
    """Åbn en måling. Returnerer en uigennemsigtig nøgle til `afslut`."""
    return {"t": time.monotonic(), "cpu": _proces_cpu_sek()}


def afslut(start_token: dict[str, Any] | None) -> str:
    """Luk målingen og returnér felterne som ÉN streng til log-linjen.

    En streng og ikke et dict, fordi kalderen er en `print` i en fil på 4.900
    linjer: jo mindre den skal vide om formen, jo mindre kan drive fra
    hinanden. Tom streng ved enhver tvivl — linjen skal stadig kunne skrives.
    """
    try:
        if not isinstance(start_token, dict):
            return ""
        ud: list[str] = []
        vaegur = max(time.monotonic() - float(start_token.get("t") or 0.0), 1e-6)

        cpu_foer = start_token.get("cpu")
        cpu_efter = _proces_cpu_sek()
        if cpu_foer is not None and cpu_efter is not None:
            brugt = max(cpu_efter - cpu_foer, 0.0)
            ud.append(f"cpu_ms={int(brugt * 1000)}")
            # Forholdet er det bærende tal — se modulets hoved.
            ud.append(f"cpu_pr_sek={brugt / vaegur:.2f}")

        try:
            ud.append(f"traade={threading.active_count()}")
        except Exception:  # noqa: BLE001 — et traad-tal maa ikke vaelte linjen
            pass
        try:
            ud.append(f"load1={os.getloadavg()[0]:.2f}")
        except Exception:  # noqa: BLE001 — findes ikke paa alle platforme
            pass
        try:
            ud.append(f"kerner={os.cpu_count() or 0}")
        except Exception:  # noqa: BLE001 — samme
            pass
        return " ".join(ud)
    except Exception as exc:  # noqa: BLE001
        logger.debug("assembly_load_probe: maalingen fejlede: %s", exc)
        return ""


__all__ = ["start", "afslut"]
