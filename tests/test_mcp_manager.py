"""MCP-manager: registeret er en adressebog, allowlisten er beslutningen."""
import pytest

from core.services import mcp_manager, mcp_trust


@pytest.fixture(autouse=True)
def _ren(monkeypatch):
    st = {"allowlist": [], "pins": {}}
    monkeypatch.setattr(mcp_trust, "_load", lambda: {"allowlist": list(st["allowlist"]),
                                                     "pins": dict(st["pins"])})
    monkeypatch.setattr(mcp_trust, "_save", lambda d: st.update(d))
    monkeypatch.setattr("core.services.mcp_registry.list_mcp_servers",
                        lambda: [{"id": "m1", "name": "vejr", "url": "https://v.example/mcp"}])
    mcp_manager._klienter.clear()
    yield st
    mcp_manager._klienter.clear()


def test_status_viser_kendt_men_ikke_godkendt():
    s = mcp_manager.status()
    assert s["servere"][0]["navn"] == "vejr"
    assert s["servere"][0]["godkendt"] is False, \
        "at staa i registeret er ikke det samme som at vaere godkendt"


def test_ukendt_server_giver_fejl_ikke_forbindelse():
    r = mcp_manager.call("findes-ikke", "t", {})
    assert r["status"] == "error"
    assert "ukendt" in r["error"]


def test_ikke_godkendt_server_kan_ikke_kaldes():
    r = mcp_manager.call("vejr", "forecast", {})
    assert r["status"] == "error"
    assert "ikke godkendt" in r["error"]


def test_ukendt_vaerktoej_naar_aldrig_serveren(monkeypatch):
    mcp_trust.allow("vejr")

    class _Klient:
        connected = True
        connect_error = None
        tools = [{"name": "forecast"}]

        def call_tool(self, n, a):
            raise AssertionError("maa ikke kaldes for et ukendt vaerktoej")

    monkeypatch.setattr(mcp_manager, "get_client", lambda n, connect=True: _Klient())
    r = mcp_manager.call("vejr", "findes-ikke", {})
    assert r["status"] == "error"
    assert r["kendte"] == ["forecast"]
