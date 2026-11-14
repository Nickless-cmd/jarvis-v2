"""Vagter for fladekatalog-udvidelsen (14/11-2026).

Den vigtigste test her er ``test_box_er_ikke_ukendt``. Baggrunden er målt:
``box`` landede i renderer og prompt, men IKKE i ``_diagnosticér``. En ukendt
type er ikke en passiv forglemmelse — guarden erklærer den «død», erstatter
blokken med ``_DEGRADERET`` og fyrer ``korriger_flader``, altså et helt
modelkald for at «rette» en flade der var korrekt skrevet. Funktionen
forsvinder, fladen ser rigtig ud i loggen, og intet siger det.

Derfor måler hver test både at den gode variant accepteres OG at den tomme
afvises: en guard der siger ja til alt vogter ingenting.
"""

from __future__ import annotations

import pytest

from core.services.jarvis_ui_guard import _diagnosticér, normalisér


def test_box_er_ikke_ukendt() -> None:
    """Uden denne gren blev hver box degraderet og kostede et modelkald."""
    niveau, fejl = _diagnosticér(
        {"type": "box", "children": [{"type": "callout", "title": "a", "body": "b"}]}
    )
    assert niveau == "ok", fejl


def test_box_uden_boern_er_doed() -> None:
    assert _diagnosticér({"type": "box", "children": []})[0] == "død"


def test_box_i_dybde_fire_afvises() -> None:
    """Rendereren afviser dybde 4; guarden skal måle det samme tal."""
    node: dict = {"type": "callout", "title": "x", "body": "y"}
    for _ in range(4):
        node = {"type": "box", "children": [node]}
    assert _diagnosticér(node)[0] == "død"


@pytest.mark.parametrize(
    "data",
    [
        {"type": "keyvalue", "items": [{"key": "PID", "value": "123"}]},
        {"type": "progress", "items": [{"label": "Disk", "value": 7, "max": 10}]},
        {"type": "quote", "text": "Hej"},
        {"type": "code", "path": "a.py", "code": "x = 1"},
        {
            "type": "tabs",
            "tabs": [
                {"label": "A", "children": [{"type": "callout", "title": "x", "body": "y"}]},
                {"label": "B", "children": [{"type": "callout", "title": "z", "body": "w"}]},
            ],
        },
    ],
)
def test_ny_type_accepteres(data: dict) -> None:
    niveau, fejl = _diagnosticér(data)
    assert niveau == "ok", fejl


@pytest.mark.parametrize(
    "data",
    [
        {"type": "keyvalue", "items": [{"key": "PID"}]},
        {"type": "progress", "items": [{"label": "D", "value": 7, "max": 0}]},
        {"type": "quote", "source": "x"},
        {"type": "code", "path": "a.py"},
        {
            "type": "tabs",
            "tabs": [{"label": "A", "children": [{"type": "callout", "title": "x", "body": "y"}]}],
        },
    ],
)
def test_toem_type_er_doed(data: dict) -> None:
    """En type uden indhold skal afvises — ellers vogter guarden ingenting."""
    assert _diagnosticér(data)[0] == "død"


def test_progress_med_nan_afvises() -> None:
    """``NaN`` er et tal for Python, men giver en bjælke med ``width: NaN%``."""
    niveau, _ = _diagnosticér(
        {"type": "progress", "items": [{"label": "D", "value": float("nan"), "max": 10}]}
    )
    assert niveau == "død"


def test_box_overlever_normalisering() -> None:
    """Den ægte vej: en korrekt box må ikke erstattes af den grå linje."""
    tekst = (
        '```jarvis-ui\n{"type":"box","title":"S","children":'
        '[{"type":"callout","title":"a","body":"b"}]}\n```'
    )
    ud = normalisér(tekst)
    assert "callout" in ud
    assert "kunne ikke vises" not in ud
