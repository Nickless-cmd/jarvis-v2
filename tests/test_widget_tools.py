"""`vis_widget`: pakker, gemmer som VEDHAEFTNING, og laegger den i traaden.

Den vigtigste test er `test_uden_attachment_id_er_det_en_FEJL`. En widget uden
vedhaeftning kan ingen klient hente, og en post paa turen ville love en flade
der ikke kan vises — en tom rude i stedet for en fejl han kan handle paa.

`test_html_rejser_IKKE_i_resultatet` daekker det andet valg: resultater
afkortes (`block.resultAfkortet`) og lander i transkriptet, saa en widget i
resultatet ville baade blive skaaret midt over og koste sin plads i hver
senere prompt.
"""

from __future__ import annotations

import pytest

from core.tools.widget_tools import _exec_vis_widget

_FRAG = "<table><tr><td>94,2</td></tr></table>"


@pytest.fixture
def rig(monkeypatch, tmp_path):
    import core.tools.widget_tools as W

    monkeypatch.setattr(W, "_widget_dir", lambda: tmp_path / "widgets")
    fanget: dict[str, list] = {"registreret": [], "noteret": []}
    monkeypatch.setattr(
        "core.services.attachment_service.register_generated_media",
        lambda **kw: (fanget["registreret"].append(kw), "att-w1")[1],
    )
    monkeypatch.setattr(
        "core.services.published_files.note",
        lambda turn_id, **kw: fanget["noteret"].append((turn_id, kw)),
    )
    return fanget


def test_den_pakker_gemmer_og_leverer(rig, tmp_path):
    ud = _exec_vis_widget({"html": _FRAG, "titel": "cache",
                           "_runtime_turn_id": "t1", "_runtime_tool_use_id": "tu-3"})
    assert ud["status"] == "ok" and ud["attachment_id"] == "att-w1"
    filer = list((tmp_path / "widgets").iterdir())
    assert len(filer) == 1 and filer[0].suffix == ".html"
    doc = filer[0].read_text(encoding="utf-8")
    # Serverens CSP SKAL staa i den gemte fil — det er det lag begge klienter deler.
    assert "default-src 'none'" in doc and _FRAG in doc
    assert rig["registreret"][0]["mime_type"] == "text/html"


def test_html_rejser_IKKE_i_resultatet(rig):
    """Resultatet maa kun baere en reference. HTML i resultatet ville blive
    afkortet OG lande i hver senere prompt."""
    ud = _exec_vis_widget({"html": _FRAG, "_runtime_tool_use_id": "tu"})
    assert _FRAG not in str(ud)
    assert "<table" not in str(ud)
    assert ud["attachment_id"] == "att-w1"


def test_tool_use_id_foelger_med(rig):
    _exec_vis_widget({"html": _FRAG, "_runtime_turn_id": "t1", "_runtime_tool_use_id": "tu-3"})
    turn_id, kw = rig["noteret"][0]
    assert turn_id == "t1"
    assert kw["tool_use_id"] == "tu-3", "ankeret mangler — fladen lander bagest"
    assert kw["mime_type"] == "text/html"


def test_uden_attachment_id_er_det_en_FEJL(monkeypatch, tmp_path):
    """Ingen klient kan hente en widget uden vedhaeftning. En post paa turen
    ville love en flade der ikke kan vises."""
    import core.tools.widget_tools as W

    monkeypatch.setattr(W, "_widget_dir", lambda: tmp_path / "w")
    monkeypatch.setattr(
        "core.services.attachment_service.register_generated_media",
        lambda **kw: "",
    )
    noteret: list = []
    monkeypatch.setattr("core.services.published_files.note",
                        lambda *a, **k: noteret.append(1))
    ud = _exec_vis_widget({"html": _FRAG, "_runtime_tool_use_id": "tu"})
    assert ud["status"] == "error" and "kan derfor ikke vises" in ud["error"]
    assert noteret == [], "intet maa laegges paa turen naar fladen ikke kan vises"


@pytest.mark.parametrize("html,maerke", [
    ("", "tom"),
    ("<!doctype html><html><body>x</body></html>", "FRAGMENT"),
    ("x" * (256 * 1024 + 1), "hoejst"),
])
def test_en_daarlig_html_siger_HVAD_der_er_galt(rig, html, maerke):
    ud = _exec_vis_widget({"html": html, "_runtime_tool_use_id": "tu"})
    assert ud["status"] == "error" and maerke in ud["error"]
    assert rig["noteret"] == []


def test_vaerktoejet_er_registreret_OG_i_dispatch():
    import core.tools.simple_tools as st
    from core.tools.simple_tools import get_tool_definitions

    navne = {(d.get("function") or d).get("name") for d in (get_tool_definitions() or [])}
    assert "vis_widget" in navne
    tabeller = [v for v in vars(st).values()
                if isinstance(v, dict) and "vis_graf" in v]
    assert any("vis_widget" in t for t in tabeller), "annonceret men ikke kaldbar"


def test_prompten_og_pinned_saettet_er_enige():
    from core.services.prompt_sections.output_discipline import (
        _output_discipline_instruction,
    )
    from core.services.tool_tagger import get_pinned_set, invalidate_cache

    invalidate_cache()
    tekst = _output_discipline_instruction(strength="strong")
    assert "vis_widget" in tekst
    assert "vis_widget" in get_pinned_set(), (
        "prompten beder om vis_widget, men det er ikke pinned — routeren sender "
        "70-97 af ~494 vaerktoejer"
    )
