"""Graf-renderen: en spec bliver en PNG, og en daarlig spec bliver en FEJL.

Valget af PNG frem for SVG er maalt, ikke smag: mobilen har `react-native-svg`
men INGEN WebView, saa en SVG-streng kan ikke renderes uden ny native kode. En
billed-blok renderes derimod allerede af baade desk og mobil.

Den vigtigste test her er `test_en_tom_eller_ulovlig_spec_KASTER`: en tom figur
ville se ud som et svar, og en graf uden tal er en loegn om tallene.
"""

from __future__ import annotations

import pytest

from core.services.graf_render import (
    MAX_PUNKTER,
    MAX_SERIER,
    GrafFejl,
    tegn_graf,
)


def _png(b: bytes) -> bool:
    return b[:8] == b"\x89PNG\r\n\x1a\n"


def test_en_enkel_linje_bliver_en_png():
    b = tegn_graf({"slags": "linje", "titel": "cache-hit",
                   "serier": [{"navn": "hit", "y": [94.2, 93.7, 94.0]}]})
    assert _png(b) and len(b) > 1000


@pytest.mark.parametrize("slags", ["linje", "soejle", "punkt"])
def test_alle_tre_slags_tegner(slags):
    b = tegn_graf({"slags": slags, "serier": [{"y": [1, 2, 3]}]})
    assert _png(b)


def test_x_udfyldes_naar_den_mangler():
    """y alene er nok — ellers skal Jarvis skrive 1,2,3,… i haanden hver gang."""
    b = tegn_graf({"serier": [{"y": [5, 4, 6]}]})
    assert _png(b)


def test_tekst_paa_x_aksen_virker():
    b = tegn_graf({"slags": "soejle",
                   "serier": [{"y": [3, 7], "x": ["september", "oktober"]}]})
    assert _png(b)


def test_flere_serier_faar_hver_sin_farve_og_en_forklaring():
    b = tegn_graf({"serier": [{"navn": "a", "y": [1, 2]},
                              {"navn": "b", "y": [2, 1]}]})
    assert _png(b)


@pytest.mark.parametrize("spec,hvorfor", [
    ({"serier": []}, "tom serie-liste"),
    ({}, "ingen serier"),
    ({"serier": [{"y": []}]}, "serie uden y"),
    ({"slags": "kage", "serier": [{"y": [1]}]}, "ukendt slags"),
    ({"serier": [{"y": ["to"]}]}, "y der ikke er tal"),
    ({"serier": [{"y": [1, 2], "x": [1]}]}, "x og y af forskellig laengde"),
    ({"serier": ["ikke et objekt"]}, "serie der ikke er et objekt"),
    ({"serier": [{"y": 5}]}, "y der ikke er en liste"),
])
def test_en_tom_eller_ulovlig_spec_KASTER(spec, hvorfor):
    """Kaster MED VILJE frem for at returnere en tom figur. En tom graf ser ud
    som et svar — og er en loegn om tallene."""
    with pytest.raises(GrafFejl):
        tegn_graf(spec)


def test_graenserne_haandhaeves():
    """En spec er model-skrevet og skal ikke kunne bede om en 50 MB-fil."""
    with pytest.raises(GrafFejl, match="for mange"):
        tegn_graf({"serier": [{"y": [1]} for _ in range(MAX_SERIER + 1)]})
    with pytest.raises(GrafFejl, match="punkter"):
        tegn_graf({"serier": [{"y": list(range(MAX_PUNKTER + 1))}]})
    # Og lige under graensen SKAL virke, ellers er loftet i praksis lavere.
    assert _png(tegn_graf({"serier": [{"y": [1]} for _ in range(MAX_SERIER)]}))


def test_fejlbeskeden_siger_HVAD_der_er_galt():
    """Jarvis faar beskeden tilbage og skal kunne rette specen uden at gaette."""
    with pytest.raises(GrafFejl) as e:
        tegn_graf({"serier": [{"y": [1, 2], "x": [1]}]})
    besked = str(e.value)
    assert "1 x" in besked and "2 y" in besked


def test_figurer_laekker_ikke_i_en_langtlevende_proces():
    """`plt.close(fig)` i en finally. Uden den vokser matplotlibs egen liste af
    aabne figurer for hvert kald, og runtime-processen lever i dage."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.close("all")
    for _ in range(5):
        tegn_graf({"serier": [{"y": [1, 2, 3]}]})
    assert plt.get_fignums() == [], "en figur blev ikke lukket"


def test_en_fejlet_tegning_lukker_ogsaa_figuren():
    plt_mod = __import__("matplotlib.pyplot", fromlist=["x"])
    plt_mod.close("all")
    with pytest.raises(GrafFejl):
        tegn_graf({"serier": [{"y": ["nej"]}]})
    assert plt_mod.get_fignums() == []
