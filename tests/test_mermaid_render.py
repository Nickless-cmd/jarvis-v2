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


def test_chromium_binaeren_findes():
    """Uden en browser kan intet rendes — det skal fejle højt, ikke tavst."""
    sti = find_chrome()
    assert sti is not None, "ingen chromium-binær fundet (se CHROME_STIER)"
    assert sti.is_file()


def test_mermaid_js_findes():
    """Mermaid genbruges fra desk's node_modules — ikke en kopi til serveren."""
    sti = find_mermaid()
    assert sti is not None, "mermaid.js ikke fundet (se MERMAID_STIER)"
    assert sti.is_file()


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


def test_gyldig_kilde_giver_svg():
    """Den ægte ende-til-ende-test: mermaid-syntaks ind, SVG ud."""
    svg = render("flowchart LR\n  A[En] --> B[To]")
    assert "<svg" in svg
    assert "viewBox" in svg


def test_ugyldig_kilde_giver_laesbar_fejl():
    """Dårlig syntaks skal give en MermaidFejl med en brugbar besked."""
    with pytest.raises(MermaidFejl):
        render("flowchart TD\n  A[Start --> B")
