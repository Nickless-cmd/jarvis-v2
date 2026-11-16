"""Tests for ét værktøjs-scope pr. session (16/11-2026).

Baggrunden er målt, ikke antaget: samme session skiftede 38 ↔ 44 ↔ 110
værktøjer mellem to ture, fordi scopet blev udledt per tur. Cache-hit var
58,7 % på runden efter et skift mod 96,6 % ellers.
"""
from __future__ import annotations

import pytest

from core.services import session_tool_scope as sts


@pytest.fixture()
def butik(monkeypatch):
    """In-memory afløser for runtime_state — uden at røre den levende DB."""
    import core.runtime.db as db

    lager: dict[str, object] = {}

    monkeypatch.setattr(db, "get_runtime_state_value",
                        lambda key, default=None: lager.get(key, default))
    monkeypatch.setattr(db, "set_runtime_state_value",
                        lambda key, value, **kw: lager.__setitem__(key, value))
    return lager


def test_eksplicit_scope_gemmes_og_vinder(butik):
    assert sts.resolve_scope("s1", "code") == "code"
    # Næste tur beder om chat → eksplicit vinder og bliver den nye faste værdi
    assert sts.resolve_scope("s1", "chat") == "chat"
    # ...og en tur uden mode arver nu chat, ikke code
    assert sts.resolve_scope("s1", "") == "chat"


def test_tomt_scope_arver_det_gemte(butik):
    sts.resolve_scope("s1", "chat")
    assert sts.resolve_scope("s1", "") == "chat"


def test_tomt_scope_uden_post_er_ubegraenset(butik):
    assert sts.resolve_scope("ukendt", "") == ""


def test_gemt_tomt_scope_er_en_gyldig_vaerdi(butik):
    """Ubegrænset SKAL kunne huskes — ellers ville en samtale der bevidst
    kører ubegrænset få sit scope opfundet på ny hver tur."""
    sts.resolve_scope("s1", "")
    assert sts.resolve_scope("s1", "") == ""


def test_sessioner_er_isolerede(butik):
    sts.resolve_scope("a", "chat")
    sts.resolve_scope("b", "code")
    assert sts.resolve_scope("a", "") == "chat"
    assert sts.resolve_scope("b", "") == "code"


def test_uden_session_roeres_intet(butik):
    assert sts.resolve_scope("", "chat") == "chat"
    assert butik == {}


def test_killswitch_giver_gammel_adfaerd(butik, monkeypatch):
    import core.runtime.settings as settings_mod

    class _S:
        session_tool_scope_sticky = False

    monkeypatch.setattr(settings_mod, "load_settings", lambda: _S())
    sts.resolve_scope("s1", "chat")          # gemmes ikke
    assert sts.resolve_scope("s1", "") == ""
    assert butik == {}


def test_lagerfejl_koster_ikke_turen_dens_scope(butik, monkeypatch):
    import core.runtime.db as db

    def _braender(*a, **kw):
        raise RuntimeError("db nede")

    monkeypatch.setattr(db, "set_runtime_state_value", _braender)
    monkeypatch.setattr(db, "get_runtime_state_value", _braender)
    assert sts.resolve_scope("s1", "code") == "code"
    assert sts.resolve_scope("s1", "") == ""


def test_clear_glemmer_sessionen(butik):
    sts.resolve_scope("s1", "chat")
    sts.clear("s1")
    assert sts.resolve_scope("s1", "") == ""
