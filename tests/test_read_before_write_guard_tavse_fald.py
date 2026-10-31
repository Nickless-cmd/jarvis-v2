"""Vagter for de 6 tavse fald i read_before_write_guard.py (31/10-2026).

Fejlformen: alle seks falder er fail-CLOSED — de blokerer skrivningen, hvilket
er den sikre retning. Men de var TAVSE, og det giver en værre fejl end tavshed:

  ``_was_read`` svarer ``False`` naar cachen er nede. Kalderen faar beskeden
  «filen er ikke blevet laest i denne session» — hvilket er en LOEGN naar
  aarsagen er at cachen ikke kunne slaaes op. Guarden blokerer altsaa alt,
  og forklarer det med brugerens adfaerd.

Hver vagt beviser TO ting:
  1. fejlen efterlader et spor (WARNING paa modul-loggeren), og
  2. returvaerdien er stadig den fail-closed vaerdi kalderne forventer.

Plus én stoej-vagt: et vellykket opslag maa IKKE logge.
"""
from __future__ import annotations

import logging
from pathlib import Path

import core.services.read_before_write_guard as rbw

LOGGER = "core.services.read_before_write_guard"


def _advarsler(caplog) -> list[str]:
    return [
        r.getMessage()
        for r in caplog.records
        if r.name == LOGGER and r.levelno >= logging.WARNING
    ]


def _braek(*_a, **_k):
    raise RuntimeError("cache nede")


# ── _was_read / _operator_was_read ───────────────────────────────────────


def test_was_read_logger_og_svarer_false(monkeypatch, caplog):
    """Cache-nedbrud blokerer skrivningen — men det skal kunne ses."""
    import core.services.shared_cache as sc

    monkeypatch.setattr(sc, "get", _braek)
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        assert rbw._was_read("/tmp/en-fil.md", "s1") is False
    assert any("/tmp/en-fil.md" in m for m in _advarsler(caplog)), (
        "et cache-nedbrud efterlod intet spor — beskeden lyder som brugerens fejl"
    )


def test_operator_was_read_logger_og_svarer_false(monkeypatch, caplog):
    """Samme form paa operator-siden."""
    import core.services.shared_cache as sc

    monkeypatch.setattr(sc, "get", _braek)
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        assert rbw._operator_was_read("/tmp/op-fil.md", "s1") is False
    assert any("/tmp/op-fil.md" in m for m in _advarsler(caplog)), (
        "operator-vagtens cache-nedbrud efterlod intet spor"
    )


def test_was_read_logger_ikke_ved_cache_hit(monkeypatch, caplog):
    """STOEJ-VAGT: et hit i cachen er normal drift og maa ikke logge."""
    import core.services.shared_cache as sc

    monkeypatch.setattr(sc, "get", lambda _k: {"read_at": "nu"})
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        assert rbw._was_read("/tmp/en-fil.md", "s1") is True
    assert _advarsler(caplog) == [], "normal drift sto ejede i loggen"


# ── get_session_edit_summary ─────────────────────────────────────────────


def test_edit_summary_logger_og_returnerer_tom(monkeypatch, caplog):
    """{} betyder «ingen redigeringer» — men ogsaa «cachen kunne ikke laeses»."""
    import core.services.shared_cache as sc

    monkeypatch.setattr(sc, "get", _braek)
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        assert rbw.get_session_edit_summary("s1") == {}
    assert any("s1" in m for m in _advarsler(caplog)), (
        "en brudt session saa ud som en ren session"
    )


# ── check_read_before_write: preview-fejlen ──────────────────────────────


def test_preview_fejl_logger_og_blokerer_stadig(monkeypatch, caplog, tmp_path):
    """Previewet fejler — blokeringen staar, men aarsagen skal kunne ses."""
    fil = tmp_path / "findes.md"
    fil.write_text("indhold\n", encoding="utf-8")

    monkeypatch.setattr(rbw, "_kraever_laesning", lambda _t: True)
    monkeypatch.setattr(rbw, "_was_read", lambda _p, _s: False)

    def _kast(*_a, **_k):
        raise RuntimeError("kan ikke laeses")

    monkeypatch.setattr(Path, "read_text", _kast)
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        ok, reason = rbw.check_read_before_write(str(fil), "s1")
    assert ok is False, "guarden skal stadig blokere"
    assert reason and "READ-BEFORE-WRITE" in reason, "kontrakten er uaendret"
    assert any("preview" in m.lower() for m in _advarsler(caplog)), (
        "preview-fejlen efterlod intet spor i loggen"
    )
