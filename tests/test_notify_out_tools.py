"""Tests for core/tools/notify_out_tools.py — kanal-filen og dens ejerskab.

Fokus: filformatet, bucketen og at ejerens kanaler aldrig blandes med et
medlems. Afsendelse er dækket i tests/test_notify_out_per_user.py med
monkeypatchede sendere; her måles kun tilstanden.
"""
from __future__ import annotations

import json

import pytest

from core.tools import notify_out_tools as n


@pytest.fixture()
def state_fil(tmp_path, monkeypatch):
    """Isolér kanal-filen til tmp_path — rør ALDRIG Bjørns rigtige fil."""
    sti = tmp_path / "notify_channels.json"
    monkeypatch.setattr(n, "_STATE_PATH", sti)
    return sti


def test_load_giver_tom_channels_naar_filen_mangler(state_fil):
    data = n._load()
    assert data == {"channels": {}}


def test_load_retter_oedelagt_json_uden_at_kaste(state_fil):
    state_fil.write_text("{ikke json", encoding="utf-8")
    assert n._load() == {"channels": {}}


def test_load_bevarer_ejerens_eksisterende_format(state_fil):
    """Bjørns fil har top-level `channels` — den skal læses uændret."""
    original = {"channels": {"min": {"name": "min", "type": "discord", "url": "https://x"}}}
    state_fil.write_text(json.dumps(original), encoding="utf-8")
    data = n._load()
    assert data["channels"]["min"]["url"] == "https://x"


def test_bucket_uden_uid_er_ejerens_channels(state_fil):
    data = {"channels": {"a": {"name": "a"}}}
    assert n._bucket(data, "") is data["channels"]


def test_bucket_for_medlem_er_adskilt_fra_ejeren(state_fil):
    data = {"channels": {"ejer": {"name": "ejer"}}}
    medlem = n._bucket(data, "42", create=True)
    medlem["egen"] = {"name": "egen"}
    assert "egen" not in data["channels"]
    assert data["users"]["42"]["channels"]["egen"]["name"] == "egen"


def test_bucket_uden_create_muterer_ikke(state_fil):
    data = {"channels": {}}
    tom = n._bucket(data, "42")
    assert tom == {}
    assert "users" not in data


def test_save_og_load_er_rundtur(state_fil):
    data = {"channels": {"a": {"name": "a", "type": "generic", "url": "https://x"}}}
    n._save(data)
    assert n._load()["channels"]["a"]["url"] == "https://x"


def test_caller_uid_er_tom_uden_brugerkontekst(monkeypatch):
    """Daemon/autonomt arbejde har ingen bruger — det er ejeren."""
    import core.identity.workspace_context as wc

    monkeypatch.setattr(wc, "current_user_id", lambda: "")
    monkeypatch.setattr(wc, "current_role", lambda: "owner")
    assert n._caller_uid() == ""


def test_caller_uid_giver_medlemmets_id(monkeypatch):
    import core.identity.workspace_context as wc

    monkeypatch.setattr(wc, "current_user_id", lambda: "999")
    monkeypatch.setattr(wc, "current_role", lambda: "member")
    assert n._caller_uid() == "999"
