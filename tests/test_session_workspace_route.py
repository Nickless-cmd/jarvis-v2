"""At binde en samtale til et workspace fra telefonen."""
import pytest
from fastapi import HTTPException

from apps.api.jarvis_api.routes import chat as r


class _Krop:
    def __init__(self, kind, root):
        self.kind, self.root = kind, root


def test_en_server_root_der_findes_gemmes(isolated_runtime, monkeypatch):
    monkeypatch.setattr(r, "_allowed_roots", lambda role, uid: {"repo": "/x"})
    gemt = {}
    import core.services.chat_sessions as cs
    monkeypatch.setattr(cs, "set_session_workspace",
                        lambda sid, *, kind, root: gemt.update(sid=sid, kind=kind, root=root))
    svar = r.chat_set_session_workspace("s1", _Krop("container", "repo"))
    assert svar == {"ok": True, "kind": "container", "root": "repo"}
    assert gemt == {"sid": "s1", "kind": "container", "root": "repo"}


def test_en_root_rollen_IKKE_maa_browse_afvises(isolated_runtime, monkeypatch):
    # Uden den kontrol ville valget se ud til at lykkes og foerst fejle naar
    # fil-traeet proevede at laese - altsaa en indstilling der lyver.
    monkeypatch.setattr(r, "_allowed_roots", lambda role, uid: {"workspace": "/w"})
    with pytest.raises(HTTPException) as e:
        r.chat_set_session_workspace("s1", _Krop("container", "repo"))
    assert e.value.status_code == 403


def test_en_mappe_paa_EGEN_computer_rollekontrolleres_ikke(isolated_runtime, monkeypatch):
    # Server-roots er rolle-scopede fordi de ligger paa DENNE maskine. En sti
    # paa brugerens egen computer er hans egen; broen er graensen, ikke rollen.
    import core.services.chat_sessions as cs
    gemt = {}
    monkeypatch.setattr(cs, "set_session_workspace",
                        lambda sid, *, kind, root: gemt.update(kind=kind, root=root))
    r.chat_set_session_workspace("s1", _Krop("workstation", "/home/bs/projekt"))
    assert gemt == {"kind": "workstation", "root": "/home/bs/projekt"}


def test_ukendt_kind_afvises(isolated_runtime):
    with pytest.raises(HTTPException) as e:
        r.chat_set_session_workspace("s1", _Krop("maane", "/x"))
    assert e.value.status_code == 400


def test_tom_root_afvises(isolated_runtime):
    # En tom sti ville binde samtalen til ingenting og se ud som om den var sat.
    with pytest.raises(HTTPException) as e:
        r.chat_set_session_workspace("s1", _Krop("workstation", "  "))
    assert e.value.status_code == 400


def test_roots_ruten_siger_baade_navn_og_sti(isolated_runtime, monkeypatch):
    # Uden stien kan klienten ikke vise hvad «repo» faktisk ER, og et valg man
    # ikke kan se konsekvensen af er et gaet.
    monkeypatch.setattr(r, "_allowed_roots", lambda role, uid: {"repo": "/media/p/jarvis-v2"})
    assert r.chat_roots() == {"roots": [{"name": "repo", "path": "/media/p/jarvis-v2"}]}
