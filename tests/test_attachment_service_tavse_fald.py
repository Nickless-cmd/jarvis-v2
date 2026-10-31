"""Vagter for de 7 tavse fald i attachment_service.py (31/10-2026).

Fejlformen der blev rettet: et ``except`` returnerede en vaerdi der er
IDENTISK med den legitime tilstand.

- ``get_attachment`` returnerer ``None`` = baade «findes ikke» og «DB brudt».
- ``list_attachments`` returnerer ``[]`` = baade «ingen» og «listen kunne
  ikke laeses».
- ``read_attachment_content``s binaer-gren returnerede ``status: ok`` med en
  TOM preview naar laesningen fejlede — saa en ulaeselig fil saa ud som en
  tom fil.

Hver vagt beviser TO ting:
  1. fejlen efterlader et spor (WARNING paa modul-loggeren), og
  2. returvaerdien er stadig den fail-soft vaerdi kalderne forventer.

Plus én stoej-vagt: normal drift maa IKKE logge, ellers drukner de aegte
fejl i normal-adfaerd.
"""
from __future__ import annotations

import logging


import core.services.attachment_service as att

LOGGER = "core.services.attachment_service"


def _advarsler(caplog) -> list[str]:
    """Kun WARNING+ fra dette modul — ikke pytest's egen stoej."""
    return [
        r.getMessage()
        for r in caplog.records
        if r.name == LOGGER and r.levelno >= logging.WARNING
    ]


def _braek(*_a, **_k):
    raise RuntimeError("db nede")


# ── get_attachment / list_attachments ────────────────────────────────────


def test_get_attachment_logger_men_returnerer_none(monkeypatch, caplog):
    """DB-fejl giver stadig None — men efterlader et spor."""
    monkeypatch.setattr(att, "_db_get", _braek)
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        assert att.get_attachment("att-1") is None
    assert any("att-1" in m for m in _advarsler(caplog)), (
        "et brudt opslag efterlod intet spor — kalderen ser en manglende fil"
    )


def test_list_attachments_logger_men_returnerer_tom(monkeypatch, caplog):
    """DB-fejl giver stadig [] — men efterlader et spor."""
    monkeypatch.setattr(att, "_db_list", _braek)
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        assert att.list_attachments("sess-1") == []
    assert any("sess-1" in m for m in _advarsler(caplog)), (
        "en brudt liste efterlod intet spor — sessionen ser tom ud"
    )


def test_normal_opslag_logger_ikke(monkeypatch, caplog):
    """STOEJ-VAGT: et vellykket opslag maa ikke skrive en advarsel."""
    monkeypatch.setattr(att, "_db_get", lambda _id: {"attachment_id": "a"})
    monkeypatch.setattr(att, "_db_list", lambda _s, _l: [{"attachment_id": "a"}])
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        assert att.get_attachment("a") == {"attachment_id": "a"}
        assert att.list_attachments("s") == [{"attachment_id": "a"}]
    assert _advarsler(caplog) == [], "normal drift sto ejede i loggen"


# ── _vision_model ────────────────────────────────────────────────────────


def test_vision_model_logger_naar_config_fejler(monkeypatch, caplog):
    """Config-fejl falder videre — men man skal kunne se hvorfor."""
    import core.runtime.secrets as secrets

    def _kast(_key):
        raise RuntimeError("runtime.json ulaeselig")

    monkeypatch.setattr(secrets, "read_runtime_key", _kast)
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        model = att._vision_model()
    assert model, "skal stadig give et modelnavn (fail-soft)"
    assert any("vision_model_name" in m for m in _advarsler(caplog)), (
        "en ulaeselig config efterlod intet spor"
    )


def test_vision_model_logger_naar_begge_fejler(monkeypatch, caplog):
    """Baade config og standard fejler → hardkodet fallback, med spor."""
    import core.runtime.secrets as secrets
    import core.services.visual_memory as vm

    def _kast(_key):
        raise RuntimeError("nope")

    monkeypatch.setattr(secrets, "read_runtime_key", _kast)
    monkeypatch.delattr(vm, "_DEFAULT_MODEL", raising=False)
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        model = att._vision_model()
    assert model == "qwen2.5vl:3b"
    assert any("hardkodet" in m for m in _advarsler(caplog)), (
        "den hardkodede fallback efterlod intet spor"
    )


# ── read_attachment_content: binaer-grenen ───────────────────────────────


def test_binaer_ulaeselig_fil_logger_og_markerer_preview(monkeypatch, caplog):
    """Den vigtigste: en ulaeselig fil maa ikke se ud som en tom fil."""
    monkeypatch.setattr(
        att,
        "_db_get",
        lambda _id: {
            "attachment_id": "bin-1",
            "mime_type": "application/octet-stream",
            "local_path": "/findes/ikke/overhovedet.bin",
            "filename": "noget.bin",
            "size_bytes": 1234,
        },
    )
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        svar = att.read_attachment_content("bin-1")
    assert svar["status"] == "ok", "kontrakten er uaendret"
    assert "utilgaengelig" in svar["content"], (
        "tom preview blev rapporteret som en tom fil"
    )
    assert _advarsler(caplog), "en ulaeselig fil efterlod intet spor"


def test_binaer_laeselig_fil_logger_ikke(monkeypatch, caplog, tmp_path):
    """STOEJ-VAGT: en fil der KAN laeses maa ikke markeres eller logge."""
    fil = tmp_path / "ok.bin"
    fil.write_bytes(b"\x00\x01\x02\x03")
    monkeypatch.setattr(
        att,
        "_db_get",
        lambda _id: {
            "attachment_id": "bin-2",
            "mime_type": "application/octet-stream",
            "local_path": str(fil),
            "filename": "ok.bin",
            "size_bytes": 4,
        },
    )
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        svar = att.read_attachment_content("bin-2")
    assert svar["status"] == "ok"
    assert "00010203" in svar["content"], "previewen mangler den rigtige hex"
    assert "utilgaengelig" not in svar["content"], "en laeselig fil blev markeret"
    assert _advarsler(caplog) == [], "normal laesning sto ejede i loggen"


# ── read_attachment_content: tekst-grenen ────────────────────────────────


def test_tekst_ulaeselig_logger(monkeypatch, caplog):
    """Tekst-grenen returnerede allerede error — men uden et spor."""
    monkeypatch.setattr(
        att,
        "_db_get",
        lambda _id: {
            "attachment_id": "txt-1",
            "mime_type": "text/plain",
            "local_path": "/findes/ikke/tekst.txt",
            "filename": "tekst.txt",
            "size_bytes": 10,
        },
    )
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        svar = att.read_attachment_content("txt-1")
    assert svar["status"] == "error", "kontrakten er uaendret"
    assert _advarsler(caplog), "en ulaeselig tekstfil efterlod intet spor"
