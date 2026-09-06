"""Operator-kanalen: bash gaar over paa Bjoerns maskine — kun for Bjoern.

Kanalen fjerner en godkendelse pr. kald. Det er kun forsvarligt saa laenge
owner-gaten holder ved HVER indgang, saa det er dét disse tests handler om.
"""
import time

import pytest

from core.services import operator_channel as oc


@pytest.fixture(autouse=True)
def _ren_tilstand(monkeypatch):
    st: dict = {}
    monkeypatch.setattr(oc, "_load", lambda: dict(st))
    monkeypatch.setattr(oc, "_save", lambda d: (st.clear(), st.update(d)))
    yield st


def test_kun_owner_kan_aabne():
    r = oc.open_channel("s1", is_owner=False)
    assert r["status"] == "error"
    assert oc.is_open("s1") is False


def test_owner_kan_aabne_og_lukke():
    assert oc.open_channel("s1", is_owner=True)["open"] is True
    assert oc.is_open("s1") is True
    assert oc.close_channel("s1", is_owner=True)["open"] is False
    assert oc.is_open("s1") is False


def test_ikke_owner_kan_ikke_lukke_andres_kanal():
    oc.open_channel("s1", is_owner=True)
    assert oc.close_channel("s1", is_owner=False)["status"] == "error"
    assert oc.is_open("s1") is True


def test_kanalen_udloeber_af_sig_selv(_ren_tilstand):
    oc.open_channel("s1", is_owner=True)
    _ren_tilstand["s1"]["aabnet"] = time.time() - (oc._TTL_S + 1)
    assert oc.is_open("s1") is False, "en glemt kanal maa ikke staa aaben i morgen"


def test_kanalen_er_pr_session():
    oc.open_channel("s1", is_owner=True)
    assert oc.is_open("s2") is False


def test_reroute_sker_ikke_for_ikke_owner(monkeypatch):
    oc.open_channel("s1", is_owner=True)
    kaldt = []
    monkeypatch.setattr("core.tools.simple_tools.execute_tool",
                        lambda n, a: kaldt.append(n) or {"status": "ok"})
    assert oc.maybe_reroute_bash("ls /", None, is_owner=False, session_id="s1") is None
    assert kaldt == []


def test_reroute_sker_ikke_naar_kanalen_er_lukket(monkeypatch):
    kaldt = []
    monkeypatch.setattr("core.tools.simple_tools.execute_tool",
                        lambda n, a: kaldt.append(n) or {"status": "ok"})
    assert oc.maybe_reroute_bash("ls /", None, is_owner=True, session_id="s1") is None
    assert kaldt == []


def test_aaben_kanal_sender_bash_over_broen(monkeypatch):
    oc.open_channel("s1", is_owner=True)
    set_kald = {}

    def _falsk(navn, args):
        set_kald["navn"] = navn
        set_kald["args"] = args
        return {"status": "ok", "text": "fra hans maskine"}

    monkeypatch.setattr("core.tools.simple_tools.execute_tool", _falsk)
    r = oc.maybe_reroute_bash("ls /media/projects", "/tmp",
                              is_owner=True, session_id="s1")
    assert set_kald["navn"] == "operator_bash"
    assert set_kald["args"]["command"] == "ls /media/projects"
    assert set_kald["args"]["cwd"] == "/tmp"
    assert r["via"] == "operator-kanal"


def test_broen_nede_bliver_en_fejl_ikke_et_styrt(monkeypatch):
    oc.open_channel("s1", is_owner=True)

    def _sprang(navn, args):
        raise RuntimeError("broen svarer ikke")

    monkeypatch.setattr("core.tools.simple_tools.execute_tool", _sprang)
    r = oc.maybe_reroute_bash("ls", None, is_owner=True, session_id="s1")
    assert r["status"] == "error"
    assert "kunne ikke nå din maskine" in r["error"]


def test_hint_kun_naar_stien_peger_paa_hans_maskine():
    assert oc.closed_channel_hint("ls /media/projects", None,
                                  is_owner=True, session_id="s1")
    assert oc.closed_channel_hint("ls /etc", None,
                                  is_owner=True, session_id="s1") == ""


def test_hint_tier_naar_kanalen_allerede_er_aaben():
    oc.open_channel("s1", is_owner=True)
    assert oc.closed_channel_hint("ls /media/projects", None,
                                  is_owner=True, session_id="s1") == ""


def test_owner_gaten_fejler_LUKKET(monkeypatch):
    """Kan rollen ikke afgoeres, er svaret nej — ikke ja."""
    def _sprang():
        raise RuntimeError("ingen kontekst")

    monkeypatch.setattr("core.identity.workspace_context.current_role", _sprang)
    assert oc.current_is_owner() is False
