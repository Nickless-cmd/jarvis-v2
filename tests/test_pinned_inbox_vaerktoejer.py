"""Prompten må ikke bede om et værktøj Jarvis ikke har i hånden.

Bjørn 4/10-2026: «hans inbox kan være lang tid om at loade.»

Målingen fandt ikke en langsom indlæsning — den fandt en ekstra runde:

    tool_router.load_more_fired
      {"requested_names": ["inbox", "inbox_done", "inbox_drop"]}

`inbox_prompt_section` skriver «+N mere → kald `inbox`» i HVER tur, men
værktøjs-ruteren vælger per tur ud fra brugerens besked. Beder Bjørn om noget
helt andet, er `inbox` ikke valgt — og så skal Jarvis først kalde
`load_more_tools`. Det koster en runde, og værre: værktøjer står FØR
beskederne i prompten, så en hentning midt i turen busted prefix-cachen for
resten af turen (målt i huset: 92 % → 26 % hit).

Målt til sammenligning: visningen bygger på 16 ms, værktøjet svarer på 24 ms
varmt. Indlæsningen var aldrig problemet.

De tre skemaer fylder 417 tokens i det CACHEDE prefix — altså næsten intet
per tur, netop fordi de står før beskederne.
"""
from __future__ import annotations

import json
import pathlib
import re


def _pinned() -> set[str]:
    p = pathlib.Path("state/tool_tags.pinned.json")
    return set(json.loads(p.read_text()).get("pinned") or [])


def test_de_tre_indbakke_vaerktoejer_er_pinnede():
    mangler = {"inbox", "inbox_done", "inbox_drop"} - _pinned()
    assert not mangler, (
        f"{sorted(mangler)} er ikke pinnede — Jarvis skal hente dem midt i "
        "turen, hvilket koster en runde OG prefix-cachen")


def test_alle_tre_hoerer_sammen():
    """`inbox` alene raekker ikke: gaten frigives KUN med `inbox_done` eller
    `inbox_drop`, saa et blik uden dem ville foere til en ny hentning."""
    p = _pinned()
    assert ("inbox" in p) == ("inbox_done" in p) == ("inbox_drop" in p), (
        "de tre er pinnet hver for sig — saa henter han stadig midt i turen")


def test_prompt_sektionen_peger_KUN_paa_pinnede_vaerktoejer():
    """Kilde-vagt om selve reglen: hvert vaerktoejsnavn prompt-sektionen
    naevner i backticks skal staa i det pinnede saet.

    Uden den kan en fremtidig linje — «kald `inbox_snooze`» — gentage praecis
    den fejl der blev maalt her: en anvisning i den staaende prompt til noget
    der ikke er i haanden.
    """
    kilde = pathlib.Path("core/services/inbox_prompt_section.py").read_text()
    # Kun strenge der FAKTISK naar prompten — docstrings og kommentarer
    # naevner navne som forklaring, ikke som anvisning.
    linjer = [x for x in kilde.splitlines()
              if ("linjer.append(" in x or "hoved.append(" in x or '"  +' in x)]
    tekst = "\n".join(linjer)
    navne = {m for m in re.findall(r"`([a-z_]+)`", tekst)}
    # `inbox_done(id)` / `inbox_drop(id, reason)` skrives med parentes.
    navne |= {m for m in re.findall(r"`([a-z_]+)\(", tekst)}
    ukendte = {n for n in navne if n.startswith("inbox")} - _pinned()
    assert not ukendte, (
        f"prompt-sektionen beder om {sorted(ukendte)}, som ikke er pinnede")
