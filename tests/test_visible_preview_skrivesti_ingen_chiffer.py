"""Skrive-stien for visible_runs.text_preview maa ikke gemme chiffertekst.

Maalt 27/11-2026: 2 medlems-previews bar `enc:v1:` trods at laese-stien var
beskyttet. Bruger den ægte `chat_crypto.er_krypteret`, ikke en regex.
"""
from __future__ import annotations

import logging
from types import SimpleNamespace

from core.services import chat_crypto, visible_runs as vr
from core.services.visible_preview_crypto import (
    PLADSHOLDER_KRYPTERET,
    preview_til_skrivning,
)

CHIFFER = "enc:v1:" + "QUJDREVGR0hJSktMTU5PUFFSU1RVVldYWVo=" * 8


def test_krypteret_kilde_giver_pladsholder_ikke_chiffer():
    assert chat_crypto.er_krypteret(CHIFFER)
    for snit in (lambda t: t[:140], vr._preview_text):
        ud = preview_til_skrivning(CHIFFER, snit)
        assert ud == PLADSHOLDER_KRYPTERET
        assert not chat_crypto.er_krypteret(ud)


def test_klartekst_snittes_uaendret():
    assert preview_til_skrivning("hej " * 100, lambda t: t[:140]) == ("hej " * 100)[:140]


def test_substitution_logges_uden_kildeindhold(caplog):
    """Grenen aendrer hvad der gemmes — den skal efterlade sig et spor.

    Maalt 27/11-2026: grenen fyrede 26 gange uden ét journal-traef, fordi den
    tav. Testen maaler ved KALD (ikke ved at grepe filen).
    """
    with caplog.at_level(logging.INFO, logger="core.services.visible_preview_crypto"):
        ud = preview_til_skrivning(CHIFFER, lambda t: t[:140])
    assert ud == PLADSHOLDER_KRYPTERET
    linjer = [
        r.getMessage()
        for r in caplog.records
        if r.name == "core.services.visible_preview_crypto"
    ]
    assert len(linjer) == 1, linjer
    assert "pladsholder" in linjer[0]
    assert str(len(CHIFFER)) in linjer[0]
    # kilde-indhold eller chiffer maa ALDRIG i loggen
    assert "enc:v1:" not in linjer[0]
    assert "QUJDREVGR0hJ" not in linjer[0]


def test_klartekst_logger_intet(caplog):
    """Vagten maa ikke stoje paa hver skrivning — kun naar den griber ind."""
    with caplog.at_level(logging.DEBUG, logger="core.services.visible_preview_crypto"):
        preview_til_skrivning("hej " * 100, lambda t: t[:140])
    assert not [
        r for r in caplog.records if r.name == "core.services.visible_preview_crypto"
    ]


def test_set_last_visible_run_outcome_gemmer_ikke_chiffer(monkeypatch):
    from core.services import visible_runs_outcomes as vro
    monkeypatch.setattr(vro, "_stemple_afslutning_synkront", lambda *a, **k: None)
    monkeypatch.setattr(vro, "_persist_visible_run_outcome", lambda *a, **k: None)
    run = SimpleNamespace(run_id="visible-test-chiffer", lane="l", provider="p",
                          model="m", user_id="", session_id="")
    vr.set_last_visible_run_outcome(run, status="completed", text_preview=CHIFFER[:140])
    gemt = vr.get_last_visible_run_outcome()
    assert not chat_crypto.er_krypteret(gemt.get("text_preview"))
