"""Vagter for anden bølge af flade-kataloget (14/11-2026).

De fem nye typer — table, chart, form, tree, diff — må ikke gentage `box`-
fejlen: en type der står i prompt og renderer men IKKE i `_diagnosticér` bliver
erklæret «død», erstattet af `_DEGRADERET`, og fyrer `korriger_flader` — et helt
modelkald for at «rette» en flade der var korrekt skrevet.

Testene her måler guarden direkte. De er ikke en gentagelse af implementeringen:
hver case er en flade der enten SKAL kunne vises eller SKAL afvises, og
forskellen mellem dem er den adfærd der ellers kun opdages ved at se et run
brænde af.
"""

from __future__ import annotations

import pytest

from core.services.jarvis_ui_guard import _diagnosticér


class TestTable:
    def test_en_almindelig_tabel_er_ok(self) -> None:
        niveau, fejl = _diagnosticér({
            "type": "table",
            "columns": ["Navn", "Tal"],
            "rows": [["a", "1"], ["b", "2"]],
        })
        assert niveau == "ok", fejl

    def test_uden_kolonner_er_den_doed(self) -> None:
        niveau, _ = _diagnosticér({"type": "table", "columns": [], "rows": [["x"]]})
        assert niveau == "død"

    def test_uden_raekker_er_den_doed(self) -> None:
        niveau, _ = _diagnosticér({"type": "table", "columns": ["A"], "rows": []})
        assert niveau == "død"

    def test_en_raekke_med_forkert_laengde_forskyder_ikke_tabellen(self) -> None:
        """En række med 1 celle under 2 kolonner ville sætte tal under den
        forkerte overskrift. Den skal afvises — men fladen skal leve."""
        niveau, fejl = _diagnosticér({
            "type": "table",
            "columns": ["A", "B"],
            "rows": [["x", "y"], ["z"]],
        })
        assert niveau == "delvis"
        assert any("celler" in f for f in fejl)


class TestChart:
    def test_en_serie_med_tal_er_ok(self) -> None:
        niveau, fejl = _diagnosticér({
            "type": "chart",
            "series": [{"name": "s", "values": [1, 2, 3]}],
        })
        assert niveau == "ok", fejl

    def test_nan_og_infinity_taeller_ikke_som_tal(self) -> None:
        """`typeof NaN === 'number'`. Uden `_endeligt_tal` ville SVG'en tegne
        en streg der knækkede usynligt — uden nogen fejl nogen steder."""
        niveau, _ = _diagnosticér({
            "type": "chart",
            "series": [{"name": "s", "values": [float("nan"), float("inf")]}],
        })
        assert niveau == "død"

    def test_uden_serier_er_den_doed(self) -> None:
        niveau, _ = _diagnosticér({"type": "chart", "series": []})
        assert niveau == "død"


class TestForm:
    def test_slider_select_og_toggle_er_ok(self) -> None:
        niveau, fejl = _diagnosticér({
            "type": "form",
            "fields": [
                {"kind": "slider", "bind": "t", "label": "Timer", "min": 1, "max": 12},
                {"kind": "select", "bind": "m", "label": "Mode", "options": ["a", "b"]},
                {"kind": "toggle", "bind": "x", "label": "Slå til"},
            ],
        })
        assert niveau == "ok", fejl

    def test_uden_et_bundet_felt_er_den_doed(self) -> None:
        """Uden `bind` er der ingen lokal state — så er fladen ren tekst
        forklædt som en formular. Samme regel som `control`."""
        niveau, _ = _diagnosticér({
            "type": "form",
            "fields": [{"kind": "text", "text": "hej"}],
        })
        assert niveau == "død"

    def test_select_med_et_enkelt_valg_er_doed(self) -> None:
        niveau, _ = _diagnosticér({
            "type": "form",
            "fields": [{"kind": "select", "bind": "m", "label": "M", "options": ["a"]}],
        })
        assert niveau == "død"

    def test_ulovligt_slider_interval_afvises(self) -> None:
        niveau, _ = _diagnosticér({
            "type": "form",
            "fields": [{"kind": "slider", "bind": "t", "label": "T", "min": 10, "max": 2}],
        })
        assert niveau == "død"


class TestTree:
    def test_en_mappestruktur_er_ok(self) -> None:
        niveau, fejl = _diagnosticér({
            "type": "tree",
            "items": [
                {"name": "src", "kind": "dir", "depth": 0},
                {"name": "a.ts", "kind": "file", "depth": 1},
            ],
        })
        assert niveau == "ok", fejl

    def test_uden_items_er_den_doed(self) -> None:
        niveau, _ = _diagnosticér({"type": "tree", "items": []})
        assert niveau == "død"

    def test_dybde_over_loftet_afvises(self) -> None:
        niveau, _ = _diagnosticér({"type": "tree", "items": [{"name": "x", "depth": 9}]})
        assert niveau == "død"


class TestDiff:
    def test_to_sider_er_ok(self) -> None:
        niveau, fejl = _diagnosticér({"type": "diff", "path": "a.ts", "old": "a", "new": "b"})
        assert niveau == "ok", fejl

    def test_kun_den_ene_side_er_nok(self) -> None:
        """En fil der kun er tilføjet (eller kun slettet) er stadig en ændring."""
        niveau, fejl = _diagnosticér({"type": "diff", "new": "b"})
        assert niveau == "ok", fejl

    def test_helt_tom_er_doed(self) -> None:
        niveau, _ = _diagnosticér({"type": "diff", "old": "", "new": ""})
        assert niveau == "død"


@pytest.mark.parametrize("typ", ["table", "chart", "form", "tree", "diff"])
def test_hver_ny_type_har_en_gren_i_guarden(typ: str) -> None:
    """Kernen i hele øvelsen: en type der ikke kendes her, ØDELÆGGES.

    Denne test fejler ikke på en dårlig flade — den fejler hvis typen slet
    ikke er kendt, hvilket er den tilstand `box` stod i i et helt døgn.
    """
    niveau, fejl = _diagnosticér({"type": typ})
    assert not any("ukendt flade-type" in f for f in fejl), (
        f"{typ} er ikke kendt af guarden — så bliver den erklæret død og "
        f"koster et modelkald hver gang den skrives"
    )
