"""`box.retning` (raekke|grid): server accepterer, begge klienter rendrer, CSS findes.

Klient-parserne er TSX og kan ikke køres i node her, så kontrakten tjekkes mod
kilden: parse-grenen, render-grenen og at klassen findes i den CSS komponenten bruger.
Fjernes `retning` ét sted, fejler mindst én test.
"""
from __future__ import annotations

import pathlib

from core.services.jarvis_ui_guard import _diagnosticér

_ROD = pathlib.Path(__file__).resolve().parent.parent
_DESK_TSX = (_ROD / "apps/jarvis-desk/src/components/rich/NativeRichBlock.tsx").read_text()
_MOBIL_TSX = (_ROD / "apps/mobile/src/components/NativeRichBlock.tsx").read_text()
_CSS = (_ROD / "apps/jarvis-desk/src/styles/app.css").read_text()
_BARN = [{"type": "callout", "title": "a", "body": "b"}]


def test_guard_accepterer_raekke_og_grid() -> None:
    for r in ("raekke", "grid"):
        assert _diagnosticér({"type": "box", "retning": r, "children": _BARN})[0] == "ok"


def test_guard_afviser_ikke_ukendt_retning() -> None:
    assert _diagnosticér({"type": "box", "retning": "diagonal", "children": _BARN})[0] == "ok"
    assert _diagnosticér({"type": "box", "retning": 7, "children": _BARN})[0] == "ok"


def test_desk_parser_ukendt_retning_falder_til_kolonne() -> None:
    assert "r === 'raekke' || r === 'grid' ? r : 'kolonne'" in _DESK_TSX
    # render: kolonne giver ingen modifier-klasse, raekke/grid giver
    assert "native-box-boern--${spec.retning}" in _DESK_TSX


def test_mobil_parser_og_render() -> None:
    assert "r === 'raekke' || r === 'grid' ? r : 'kolonne'" in _MOBIL_TSX
    assert "spec.retning === 'raekke' && styles.boxRaekke" in _MOBIL_TSX
    assert "boxRaekke: { flexDirection: 'row'" in _MOBIL_TSX
    assert "boxGrid: { flexDirection: 'row'" in _MOBIL_TSX


def test_css_klasser_findes_i_filen_desk_importerer() -> None:
    app = (_ROD / "apps/jarvis-desk/src/App.tsx").read_text()
    assert "./styles/app.css" in app
    assert ".native-box-boern--raekke {" in _CSS and ".native-box-boern--grid {" in _CSS
    assert "flex-direction: row" in _CSS.split(".native-box-boern--raekke {")[1].split("}")[0]
    assert "display: grid" in _CSS.split(".native-box-boern--grid {")[1].split("}")[0]
