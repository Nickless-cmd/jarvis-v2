"""`vis_graf`: tegner, leverer, og er NAABAR.

De tre tests der betyder mest:

* `test_tool_use_id_foelger_med` — ankeret der bestemmer hvor i traaden grafen
  lander. Uden det havner den BAGEST, efter prosaen. Fejlen blev rettet i
  openrouter_image 13/9-2026 og glemt i pollinations indtil 28/9.
* `test_vaerktoejet_er_registreret_OG_i_dispatch` — et vaerktoej i kataloget uden
  en dispatch-post kan annonceres og ikke kaldes.
* `test_prompten_og_pinned_saettet_er_enige` — routeren sender 70-97 af ~494
  vaerktoejer. Beder prompten om et vaerktoej der ikke er pinned, skriver vi en
  anvisning vaerktoejssaettet ikke kan indfri. Det staar i pinned-filens eget
  `_doc`.
"""

from __future__ import annotations

import pytest

from core.tools.graf_tools import _exec_vis_graf


@pytest.fixture
def rig(monkeypatch, tmp_path):
    """Skriv til tmp, og fang de to leverings-kald."""
    import core.tools.graf_tools as G

    monkeypatch.setattr(G, "_graf_dir", lambda: tmp_path / "grafer")
    fanget: dict[str, object] = {"registreret": [], "noteret": []}
    monkeypatch.setattr(
        "core.services.attachment_service.register_generated_image",
        lambda **kw: (fanget["registreret"].append(kw), "att-1")[1],
    )
    monkeypatch.setattr(
        "core.services.published_files.note",
        lambda turn_id, **kw: fanget["noteret"].append((turn_id, kw)),
    )
    return fanget


_SPEC = {"serier": [{"navn": "hit", "y": [94.2, 93.7, 94.0]}], "titel": "cache"}


def test_den_tegner_og_leverer(rig, tmp_path):
    ud = _exec_vis_graf({**_SPEC, "_runtime_turn_id": "t1", "_runtime_tool_use_id": "tu-9"})
    assert ud["status"] == "ok" and ud["attachment_id"] == "att-1"
    assert ud["bytes"] > 1000
    sti = tmp_path / "grafer"
    filer = list(sti.iterdir())
    assert len(filer) == 1 and filer[0].suffix == ".png"
    assert filer[0].read_bytes()[:4] == b"\x89PNG"
    assert len(rig["registreret"]) == 1
    assert rig["registreret"][0]["mime_type"] == "image/png"


def test_tool_use_id_foelger_med(rig):
    """Ankeret. Uden det lander grafen bagest i traaden, efter prosaen."""
    _exec_vis_graf({**_SPEC, "_runtime_turn_id": "t1", "_runtime_tool_use_id": "tu-9"})
    assert len(rig["noteret"]) == 1
    turn_id, kw = rig["noteret"][0]
    assert turn_id == "t1"
    assert kw["tool_use_id"] == "tu-9", "ankeret mangler — grafen lander bagest"
    assert kw["attachment_id"] == "att-1"
    assert kw["mime_type"] == "image/png"


def test_svaret_beder_ham_IKKE_beskrive_billedet(rig):
    """Teksten er til ham. Uden den linje beskriver han grafen i prosa bagefter,
    og saa staar tallene to gange."""
    ud = _exec_vis_graf({**_SPEC, "_runtime_tool_use_id": "tu"})
    assert "konklusionen" in ud["text"].lower()


def test_en_daarlig_spec_siger_HVAD_der_er_galt(rig):
    ud = _exec_vis_graf({"serier": [{"y": [1, 2], "x": [1]}], "_runtime_tool_use_id": "t"})
    assert ud["status"] == "error"
    assert "1 x" in ud["error"] and "2 y" in ud["error"]
    assert rig["noteret"] == [], "en fejlet graf maa ikke laegges paa turen"


def test_en_fejlet_registrering_taber_ikke_filen(monkeypatch, tmp_path):
    """Filen er tegnet. En manglende vedhaeftning maa ikke gøre svaret til en fejl."""
    import core.tools.graf_tools as G

    monkeypatch.setattr(G, "_graf_dir", lambda: tmp_path / "g")

    def sprael(**kw):
        raise RuntimeError("attachment-tjenesten nede")

    monkeypatch.setattr("core.services.attachment_service.register_generated_image", sprael)
    monkeypatch.setattr("core.services.published_files.note", lambda *a, **k: None)
    ud = _exec_vis_graf({**_SPEC, "_runtime_tool_use_id": "t"})
    assert ud["status"] == "ok" and ud["attachment_id"] == ""
    assert list((tmp_path / "g").iterdir()), "filen blev ikke skrevet"


def test_vaerktoejet_er_registreret_OG_i_dispatch():
    import core.tools.simple_tools as st
    from core.tools.simple_tools import get_tool_definitions

    navne = {(d.get("function") or d).get("name") for d in (get_tool_definitions() or [])}
    assert "vis_graf" in navne, "vaerktoejet staar ikke i kataloget"
    tabeller = [v for v in vars(st).values()
                if isinstance(v, dict) and "pollinations_image" in v]
    assert tabeller, "dispatch-tabellen blev ikke fundet"
    assert any("vis_graf" in t for t in tabeller), (
        "annonceret men ikke kaldbar — et vaerktoej uden dispatch-post"
    )


def test_prompten_og_pinned_saettet_er_enige():
    """Beder prompten om et vaerktoej, SKAL det vaere pinned. Routeren sender
    70-97 af ~494, og et nyt uden kald-historik kommer ikke i always-core."""
    from core.services.prompt_sections.output_discipline import (
        _output_discipline_instruction,
    )
    from core.services.tool_tagger import get_pinned_set, invalidate_cache

    invalidate_cache()
    pinned = get_pinned_set()
    tekst = _output_discipline_instruction(strength="strong")
    assert "vis_graf" in tekst
    assert "vis_graf" in pinned, (
        "prompten beder om vis_graf, men det er ikke pinned — anvisningen kan "
        "ikke indfries (se _doc i state/tool_tags.pinned.json)"
    )
