"""`mermaid_render` — server-side mermaid → SVG.

Målt 7/10-2026: mermaid kan IKKE rende i ren node. Den kræver `document`,
`CSSStyleSheet` og en layout-motor til `getBBox()`. jsdom har ingen layout, så
hver shim avler den næste fejl (seks forsøg, sidste viewBox 26 px i stedet for
115). Playwrights chromium-binær rendrede korrekt i første forsøg — derfor er
vejen en browser, og disse tests holder den der.

Testene dækker de led der kan knække tavst: at binærerne findes, at
tilgængeligheds-tjekket siger sandt når de gør, og at en tom eller for stor
kilde afvises med en læsbar fejl i stedet for at kaste ukendt.
"""
from __future__ import annotations

import pytest

from core.services.mermaid_render import (
    MAX_KILDE_BYTES,
    MermaidFejl,
    find_chrome,
    find_mermaid,
    render,
    tilgaengelig,
)

#: Rendering kraever Playwrights chromium. Den ligger i
#: `~/.cache/ms-playwright/chromium-1208` paa CT105 og typisk INGEN andre
#: steder — heller ikke paa udviklermaskinen.
#:
#: Foer 7/10-2026 fejlede de tests bare dér. Otte roede i hver koersel betyder
#: at suiten ikke kan bruges som vagt paa den maskine man udvikler paa, og det
#: er ikke en teoretisk pris: samme dag laa 16 AEGTE fejl usete blandt dem.
#:
#: Et skip er ikke det samme som at opgive kravet. Kravet om at binaeren ER
#: installeret hoerer til den vaert der serverer mermaid, og det hoerer i et
#: deploy-tjek — ikke i en unittest der koerer alle mulige steder. Her maales i
#: stedet det der KAN maales overalt: at `tilgaengelig()` fortaeller sandheden.
KRAEVER_CHROMIUM = pytest.mark.skipif(
    find_chrome() is None,
    reason="Playwrights chromium findes ikke paa denne vaert "
           "(se CHROME_STIER) — rendering kan ikke proeves her",
)


def test_tilgaengelig_fortaeller_sandheden_om_binaeren():
    """Vaert-uafhaengig: begge udfald paastaas, saa opdagelsen selv er vogtet.

    Den gamle udgave var `assert find_chrome() is not None` — altsaa et
    DEPLOY-tjek forklaedt som en unittest. Den sagde intet om hvorvidt koden
    virker; kun om maskinen var den rigtige. Her maales i stedet at
    `tilgaengelig()` ikke kan lyve nogen af vejene.
    """
    sti = find_chrome()
    klar, grund = tilgaengelig()
    if sti is None:
        assert klar is False
        assert "chromium" in grund.lower(), grund
    else:
        assert sti.is_file()
        # mermaid.js kan stadig mangle — saa skal grunden sige DET, ikke
        # chromium.
        if find_mermaid() is None:
            assert klar is False and "mermaid" in grund.lower(), grund
        else:
            assert klar is True, grund


def test_mermaid_js_findes():
    """Mermaid genbruges fra desk's node_modules — ikke en kopi til serveren."""
    sti = find_mermaid()
    assert sti is not None, "mermaid.js ikke fundet (se MERMAID_STIER)"
    assert sti.is_file()


@KRAEVER_CHROMIUM
def test_tilgaengelig_siger_klar_naar_binaererne_er_der():
    klar, grund = tilgaengelig()
    assert klar is True, f"rendereren er ikke klar: {grund}"


def test_tom_kilde_afvises():
    with pytest.raises(MermaidFejl, match="tom"):
        render("   ")


def test_for_stor_kilde_afvises():
    """Et diagram er en visning, ikke en applikation — samme ånd som widgeten."""
    with pytest.raises(MermaidFejl, match="bytes"):
        render("x" * (MAX_KILDE_BYTES + 1))


@KRAEVER_CHROMIUM
def test_gyldig_kilde_giver_svg():
    """Den ægte ende-til-ende-test: mermaid-syntaks ind, SVG ud."""
    svg = render("flowchart LR\n  A[En] --> B[To]")
    assert "<svg" in svg
    assert "viewBox" in svg


@KRAEVER_CHROMIUM
def test_ugyldig_kilde_giver_laesbar_fejl():
    """Dårlig syntaks skal give en MermaidFejl med en brugbar besked.

    KRAEVER chromium, selvom den «bestod» uden: `render` rejser samme
    `MermaidFejl` naar binaeren mangler, saa testen fangede sin egen
    forudsaetning i stedet for daarlig syntaks. En test der bestaar af den
    forkerte grund er vaerre end en der fejler.
    """
    with pytest.raises(MermaidFejl):
        render("flowchart TD\n  A[Start --> B")
