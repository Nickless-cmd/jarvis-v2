"""Adgang til samtaler — «luk hullet i de gamle» (Bjørn 19/9-2026)."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

import core.identity.users as users
import core.identity.workspace_context as wc
import core.services.chat_sessions as cs
from core.identity.session_access import arbejdsrum_for, maa_tilgaa_session

BRUGERE = {
    "id-bjoern": SimpleNamespace(workspace="bjorn", role="owner"),
    "id-mikkel": SimpleNamespace(workspace="mikkel", role="member"),
    "id-lotte": SimpleNamespace(workspace="lotte", role="member"),
}


@pytest.fixture
def verden(monkeypatch):
    monkeypatch.setattr(users, "find_user_by_discord_id", lambda uid: BRUGERE.get(uid))
    ejere: dict[str, str] = {}
    monkeypatch.setattr(cs, "get_session_owner", lambda sid: ejere.get(sid))

    def som(uid: str, rolle: str) -> None:
        monkeypatch.setattr(wc, "current_user_id", lambda: uid)
        monkeypatch.setattr(wc, "current_role", lambda: rolle)
    return ejere, som


def test_en_member_maa_sin_egen_men_ikke_andres(verden):
    ejere, som = verden
    ejere.update({"mikkels": "id-mikkel", "lottes": "id-lotte"})
    som("id-mikkel", "member")
    assert maa_tilgaa_session("mikkels") is True
    assert maa_tilgaa_session("lottes") is False


def test_en_member_maa_ikke_bjoerns_uanset_stempel(verden):
    """Målt: Bjørns samtaler står under tre stempler — id, «bjorn» og «system»."""
    ejere, som = verden
    ejere.update({"a": "id-bjoern", "b": "bjorn", "c": "system"})
    som("id-mikkel", "member")
    assert [maa_tilgaa_session(s) for s in "abc"] == [False, False, False]


def test_ejeren_maa_alt(verden):
    ejere, som = verden
    ejere.update({"lottes": "id-lotte", "b": "bjorn"})
    som("id-bjoern", "owner")
    assert maa_tilgaa_session("lottes") and maa_tilgaa_session("b")


def test_ustemplet_og_uden_bruger_er_aabent_som_foer(verden):
    ejere, som = verden
    som("id-mikkel", "member")
    assert maa_tilgaa_session("legacy-uden-stempel") is True
    ejere["x"] = "id-bjoern"
    som("", "")
    assert maa_tilgaa_session("x") is True


def test_arbejdsrum_sammenlignes_ikke_raa_id(verden):
    assert arbejdsrum_for("id-bjoern") == "bjorn"
    assert arbejdsrum_for("bjorn") == "bjorn"
    assert arbejdsrum_for("ukendt-42") == "ukendt-42"


def test_ruten_afviser_at_slette_en_andens_samtale(verden, monkeypatch):
    from fastapi import HTTPException
    from apps.api.jarvis_api.routes import chat as rute
    ejere, som = verden
    ejere["lottes"] = "id-lotte"
    slettet: list[str] = []
    monkeypatch.setattr(rute, "delete_chat_session", lambda sid: slettet.append(sid) or True)
    som("id-mikkel", "member")
    with pytest.raises(HTTPException) as e:
        rute.chat_delete_session("lottes")
    assert e.value.status_code == 403
    assert slettet == []
    som("id-lotte", "member")
    assert rute.chat_delete_session("lottes")["ok"] is True
