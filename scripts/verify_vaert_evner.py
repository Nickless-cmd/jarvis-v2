#!/usr/bin/env python
"""Vagt: de evner den SERVERENDE vært skal have, skal faktisk være der.

## Hvorfor (7/10-2026)

`tests/test_mermaid_render.py` havde en linje der lød

    assert find_chrome() is not None

Den fejlede i hver eneste kørsel på udviklermaskinen, fordi Playwrights
chromium kun ligger på CT105. Otte faste røde gør en suite ubrugelig som vagt
dér hvor man udvikler — og samme dag lå 16 ÆGTE fejl usete blandt dem, fordi
«det er bare mermaid» blev taget for givet.

Testene springer nu over hvor binæren mangler. Men kravet forsvandt ikke af
den grund: **mermaid SKAL kunne rendes på den vært der serverer den.** Det
krav hørte aldrig hjemme i en unittest, som kører alle mulige steder. Det
hører her.

## Formen er lånt, ikke opfundet

`--only-host` er samme flag og samme semantik som `verify_sqlite_schema.py`:
vagten håndhæver kun på den vært hvor sandheden bor, og siger pænt fra andre
steder. To gates der stiller samme slags krav bør stille det på samme måde.

## Hvorfor den IMPORTERER i stedet for at lede selv

`mermaid_render.tilgaengelig()` ER opslaget — den kender `CHROME_STIER` og
`MERMAID_STIER`. Et andet opslag her ville være den samme regel to steder, og
den ene er den man glemmer at rette. Vagten spørger derfor koden selv.

## Udvidelse

`EVNER` er listen. En ny evne skal bære sin egen begrundelse: hvad der går i
stykker uden den, så den der står med en rød vagt kan se om den betyder noget
for ham.
"""
from __future__ import annotations

import argparse
import socket
import sys
from collections.abc import Callable
from pathlib import Path

# Rod-stien, saa `core` kan importeres naar vagten koeres som et script.
# Uden den svarede tjekket «ModuleNotFoundError: No module named 'core'» —
# altsaa NEDE, men af den forkerte grund. En vagt der fejler paa sin egen
# opsaetning ligner en vagt der fanger noget, og det er vaerre end ingen vagt.
_ROD = Path(__file__).resolve().parent.parent
if str(_ROD) not in sys.path:
    sys.path.insert(0, str(_ROD))

#: Hver evne: navn, en funktion der svarer (ok, grund), og hvad der KNÆKKER
#: uden den. Den sidste er ikke pynt — en vagt uden konsekvens bliver slået fra.
EVNER: list[tuple[str, Callable[[], tuple[bool, str]], str]] = []


def _mermaid() -> tuple[bool, str]:
    from core.services.mermaid_render import tilgaengelig
    return tilgaengelig()


EVNER.append((
    "mermaid",
    _mermaid,
    "diagrammer kan ikke tegnes — mobilen viser rå kildekode i stedet, "
    "og `render_mermaid` fejler for hver eneste kalder",
))


def tjek() -> list[tuple[str, bool, str, str]]:
    """Kør alle evne-tjek. Returnér (navn, ok, grund, konsekvens) for hver.

    Self-safe pr. evne: kaster én, er DEN evne nede — de øvrige skal stadig
    svare. En vagt der ryger på den første fejl fortæller kun om én ting.
    """
    ud = []
    for navn, fn, konsekvens in EVNER:
        try:
            ok, grund = fn()
        except Exception as exc:
            ok, grund = False, f"tjekket kastede: {type(exc).__name__}: {exc}"
        ud.append((navn, bool(ok), str(grund), konsekvens))
    return ud


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only-host",
                        help="spring over medmindre dette er den serverende vært")
    args = parser.parse_args(argv)

    if args.only_host and socket.gethostname().lower() != args.only_host.lower():
        print(f"verify-vaert-evner: sprunget over paa {socket.gethostname()}; "
              f"den serverende vaert er {args.only_host}")
        return 0

    resultater = tjek()
    nede = [r for r in resultater if not r[1]]
    for navn, ok, grund, _ in resultater:
        print(f"  {'ok ' if ok else 'NEDE'}  {navn}: {grund}")
    if not nede:
        return 0

    print("\n❌ VAERT-EVNER — denne vaert serverer noget den ikke kan:\n")
    for navn, _, grund, konsekvens in nede:
        print(f"  {navn}: {grund}")
        print(f"      uden den: {konsekvens}\n")
    print("Installér det der mangler, eller sluk evnen bevidst et sted hvor")
    print("nogen kan se at den er slukket. En evne der er nede i tavshed er")
    print("den slags der foerst opdages naar en bruger spoerger hvorfor.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
