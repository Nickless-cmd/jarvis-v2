"""Vagter for de 7 tavse fald i workspace_crypto.py (31/10-2026).

Filen havde INGEN logger — alle syv fald var tavse per konstruktion.

Den farligste er `member_user_id_for_path`: den fejler FAIL-OPEN. Fejler
bade users.json-opslaget og SQLite-fallbacken, returnerer den None, og
None betyder "plaintext". En medlemsfil bliver altsaa skrevet ukrypteret
fordi to opslag fejlede — uden et spor er der intet at finde bagefter.

Hver vagt beviser TO ting: fejlen logger, OG returvaerdien er uaendret.
"""
from __future__ import annotations

import logging
import os


import core.services.workspace_crypto as wc

LOGGER = "core.services.workspace_crypto"


def _advarsler(caplog) -> list[str]:
    return [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]


# ── 1. should_encrypt: owner-opslag fejler ───────────────────────────────


def test_should_encrypt_logger_naar_opslag_fejler(monkeypatch, caplog):
    """Fail-safe retning bevaret (krypterer), men faldet skal kunne ses."""
    import core.identity.users as users

    def _braek(*_a, **_k):
        raise RuntimeError("users.json er korrupt")

    monkeypatch.setattr(users, "find_user_by_discord_id", _braek)

    with caplog.at_level(logging.WARNING, logger=LOGGER):
        svar = wc.should_encrypt("1246415163603816499")

    assert svar is True, "fail-safe retning aendret — owner ville blive ukrypteret"
    assert any("non-owner" in m for m in _advarsler(caplog)), "opslagsfejl efterlod intet spor"


def test_should_encrypt_ubundet_logger_ikke(caplog):
    """Ubundet bruger er owner-kontekst — det er et svar, ikke en fejl."""
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        assert wc.should_encrypt("") is False
    assert _advarsler(caplog) == []


# ── 2. member_user_id_for_path: begge opslag fejler (FAIL-OPEN) ──────────


def test_member_opslag_fejl_logger_men_returnerer_none(monkeypatch, caplog):
    """Begge opslag fejler → None = plaintext. Retningen er bevaret, sporet nyt."""
    import core.identity.users as users
    import core.runtime.db_users as dbu

    def _braek(*_a, **_k):
        raise RuntimeError("opslag nede")

    monkeypatch.setattr(users, "find_user_by_workspace", _braek)
    monkeypatch.setattr(dbu, "get_user_row_by_workspace", _braek)

    with caplog.at_level(logging.WARNING, logger=LOGGER):
        svar = wc.member_user_id_for_path("/home/bs/.jarvis-v2/workspaces/michelle/USER.md")

    assert svar is None, "returvaerdien er aendret — det maa fixet ikke goere"
    beskeder = _advarsler(caplog)
    assert any("users.json" in m for m in beskeder), "users.json-fejl efterlod intet spor"
    assert any("plaintext" in m for m in beskeder), "fail-open-faldet efterlod intet spor"


def test_member_uden_workspaces_komponent_logger_ikke(caplog):
    """En sti uden 'workspaces' er et gyldigt svar — ikke en fejl."""
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        assert wc.member_user_id_for_path("/tmp/et-eller-andet.md") is None
    assert _advarsler(caplog) == []


# ── 3. plaintext-rest kunne ikke fjernes efter krypteret skrivning ───────


def test_plaintext_rest_logger_naar_fjernelse_fejler(monkeypatch, caplog, tmp_path):
    """Den krypterede fil skrives — men klartekst-udgaven bliver liggende."""
    monkeypatch.setenv("JARVISX_ENCRYPT_WORKSPACES", "1")
    monkeypatch.setattr(wc, "member_user_id_for_path", lambda _p: "member-1")

    import core.services.encryption as enc
    import core.services.keyring_store as ks

    monkeypatch.setattr(enc, "encrypt", lambda data, key: b"KRYPTERET")
    monkeypatch.setattr(ks, "get_user_key", lambda _u: b"k" * 32)

    sti = tmp_path / "USER.md"
    sti.write_text("gammel klartekst", encoding="utf-8")

    aegte_remove = os.remove

    def _remove(p):
        if str(p) == str(sti):
            raise OSError("kan ikke slette")
        return aegte_remove(p)

    monkeypatch.setattr(os, "remove", _remove)

    with caplog.at_level(logging.WARNING, logger=LOGGER):
        target = wc.write_text_for_path(sti, "nyt indhold")

    assert target.endswith(".enc"), "den krypterede fil blev ikke skrevet"
    assert any("klartekst" in m for m in _advarsler(caplog)), "lækagen efterlod intet spor"


# ── 4. stoej-vagt: normal member-skrivning logger ikke ───────────────────


def test_normal_skrivning_logger_ikke(monkeypatch, caplog, tmp_path):
    """En velfungerende plaintext-skrivning maa ikke producere advarsler."""
    monkeypatch.delenv("JARVISX_ENCRYPT_WORKSPACES", raising=False)
    monkeypatch.setattr(wc, "member_user_id_for_path", lambda _p: None)

    sti = tmp_path / "almindelig.md"
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        wc.write_text_for_path(sti, "indhold")

    assert sti.read_text(encoding="utf-8") == "indhold"
    assert _advarsler(caplog) == [], f"normal skrivning stoejede: {_advarsler(caplog)}"
