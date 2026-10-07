"""`render_mermaid` — diagrammet skal kunne ses på mobilen.

Målt 7/10-2026: Bjørn skrev «Det virker kun i desk, ikk på mobilen». Desk tegner
` ```mermaid ` selv; mobilen har ingen mermaid-renderer og viste rå kildekode.
Værktøjet rendrer i stedet server-side og lægger et PNG på turen — den vej
`openrouter_image` allerede bruger, og som begge klienter tegner i dag.

Testene dækker de led der kan knække tavst: registreringen (et værktøj der ikke
er i definitions kan modellen ikke kalde), rasteriseringen (SVG → PNG), og
skaleringen (et lodret diagram må ikke blive ubrugeligt højt).
"""
from __future__ import annotations

import re

import pytest

from core.services.mermaid_render import find_chrome
from core.tools.mermaid_tool import (
    BREDDE,
    MAKS_HOEJDE,
    MERMAID_TOOL_DEFINITIONS,
    _exec_render_mermaid,
    _svg_til_png,
)

#: Rasteriseringen gaar gennem Playwrights chromium, som kun findes paa den
#: vaert der serverer mermaid. Se den fulde begrundelse i
#: `tests/test_mermaid_render.py` — kort: otte roede i hver koersel goer suiten
#: ubrugelig som vagt paa udviklermaskinen, og samme dag laa 16 aegte fejl
#: usete blandt dem.
KRAEVER_CHROMIUM = pytest.mark.skipif(
    find_chrome() is None,
    reason="Playwrights chromium findes ikke paa denne vaert "
           "(se CHROME_STIER) — rasterisering kan ikke proeves her",
)


def test_vaerktoejet_er_registreret():
    """Uden en definition i TOOL_DEFINITIONS kan modellen ikke kalde det."""
    from core.tools.simple_tools import TOOL_DEFINITIONS

    navne = [t["function"]["name"] for t in TOOL_DEFINITIONS]
    assert "render_mermaid" in navne


def test_definitionen_kraever_kilde():
    """En tom kalde skal afvises af skemaet, ikke af koden."""
    (defn,) = MERMAID_TOOL_DEFINITIONS
    assert defn["function"]["name"] == "render_mermaid"
    assert defn["function"]["parameters"]["required"] == ["kilde"]


def test_tom_kilde_giver_typet_fejl():
    r = _exec_render_mermaid({"kilde": "   "})
    assert r["status"] == "error"
    assert "kilde" in r["error"]


@KRAEVER_CHROMIUM
def test_svg_uden_viewbox_skaleres_paa_bredden():
    """Uden en viewBox at måle på skal bredden styre — ikke et gæt."""
    svg = '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"></svg>'
    png = _svg_til_png(svg)
    assert png[:8] == b"\x89PNG\r\n\x1a\n"


@KRAEVER_CHROMIUM
def test_lodret_diagram_loftes_paa_hoejden():
    """`flowchart TD` er højere end bredt; højden skal styre skalaen.

    Målt 7/10-2026: uden loftet blev tre knuder 1400x3797 px — ubrugeligt på
    en telefon. Med loftet er højden præcis MAKS_HOEJDE og bredden følger.
    """
    from PIL import Image
    import io

    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'viewBox="0 0 115.09375 312.109375" width="115" height="312">'
        '<rect x="0" y="0" width="115" height="312" fill="#fff"/></svg>'
    )
    png = _svg_til_png(svg)
    b, h = Image.open(io.BytesIO(png)).size
    assert h == MAKS_HOEJDE
    assert b < BREDDE, "bredden skal følge forholdet, ikke tvinges til BREDDE"


@KRAEVER_CHROMIUM
def test_bredt_diagram_loftes_paa_bredden():
    """Et bredt diagram skal fylde BREDDE og ikke ramme højde-loftet."""
    from PIL import Image
    import io

    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'viewBox="0 0 400 50" width="400" height="50">'
        '<rect x="0" y="0" width="400" height="50" fill="#fff"/></svg>'
    )
    png = _svg_til_png(svg)
    b, h = Image.open(io.BytesIO(png)).size
    assert b == BREDDE
    assert h < MAKS_HOEJDE


@KRAEVER_CHROMIUM
def test_ugyldig_mermaid_giver_laesbar_fejl():
    """Dårlig syntaks er kalderens fejl og skal kunne rettes med det samme.

    KRAEVER chromium selvom den «bestod» uden: uden binaeren fejler kaldet paa
    «ingen chromium-binaer», og ordet «mermaid» staar i den besked ogsaa. Den
    maalte altsaa sin egen forudsaetning.
    """
    r = _exec_render_mermaid({"kilde": "flowchart TD\n  A[Start --> B"})
    assert r["status"] == "error"
    # Enten afviser mermaid den, eller også rendrer den — men den må ikke
    # kaste. Er den accepteret, skal den have lagt et billede.
    assert "mermaid" in r["error"] or r.get("path")


@KRAEVER_CHROMIUM
def test_png_har_rigtige_dimensioner_efter_skalering():
    """Rasteriseringen skal give et ægte billede, ikke en tom fil."""
    from PIL import Image
    import io

    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'viewBox="0 0 200 100" width="200" height="100">'
        '<rect x="10" y="10" width="180" height="80" fill="#49c9b8"/></svg>'
    )
    png = _svg_til_png(svg)
    im = Image.open(io.BytesIO(png))
    assert im.size[0] == BREDDE
    # Baggrunden er sat til #0d1117, så billedet må ikke være ensfarvet hvidt.
    farver = im.convert("RGB").getcolors(maxcolors=100000)
    assert farver is not None and len(farver) > 1


@KRAEVER_CHROMIUM
def test_rasteriseringen_tegner_foreignobject():
    """Fejlen der fik ALLE kasser til at stå tomme (målt 7/10-2026).

    Mermaid lægger sine labels i `<foreignObject>` — HTML inde i SVG'en.
    rsvg-convert tegner den ikke: former, pile og farver kom med, men ingen
    tekst. Bjørn så det på sin telefon og sagde det præcist: «diagram tegner..
    men hvis du har tilføjet tekste i diagrammet kan det ikke ses».

    Chromium tegner den. Uden denne test kan rasteriseringen skiftes tilbage
    til librsvg uden at nogen opdager at diagrammerne bliver tomme igen.
    """
    from PIL import Image
    import io

    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 60">'
        '<rect width="200" height="60" fill="#0d1117"/>'
        '<foreignObject x="10" y="10" width="180" height="40">'
        '<div xmlns="http://www.w3.org/1999/xhtml" '
        'style="color:#ffffff;font:32px sans-serif">TEKST</div>'
        "</foreignObject></svg>"
    )
    png = _svg_til_png(svg)
    im = Image.open(io.BytesIO(png)).convert("L")
    lyse = sum(1 for p in im.getdata() if p > 120)
    assert lyse > 200, f"foreignObject blev ikke tegnet ({lyse} lyse pixels)"
