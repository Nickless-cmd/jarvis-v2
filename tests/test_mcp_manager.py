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

        def tool(self, navn):
            return next((t for t in self.tools if t["name"] == navn), None)

        def call_tool(self, n, a):
            raise AssertionError("maa ikke kaldes for et ukendt vaerktoej")

    monkeypatch.setattr(mcp_manager, "get_client", lambda n, connect=True: _Klient())
    r = mcp_manager.call("vejr", "findes-ikke", {})
    assert r["status"] == "error"
    assert r["kendte"] == ["forecast"]


def test_tool_med_ui_resource_leverer_resultat_og_app(monkeypatch):
    class _Klient:
        connected = True
        connect_error = None
        tools = []

        def tool(self, navn):
            return {"name": navn, "_meta": {"ui": {"resourceUri": "ui://vejr/app"}}}

        def call_tool_raw(self, navn, args):
            return {"content": [{"type": "text", "text": "sol"}],
                    "structuredContent": {"grader": 21}}

        def read_resource(self, uri):
            return {"contents": [{"uri": uri, "mimeType": "text/html;profile=mcp-app",
                                   "text": "<html><body>vejr</body></html>"}]}

    monkeypatch.setattr(mcp_manager, "get_client", lambda n, connect=True: _Klient())
    result, app = mcp_manager.call_with_app("vejr", "forecast", {"by": "Svendborg"})
    assert "UTROET" in result["content"][0]["text"]
    assert app and app["uri"] == "ui://vejr/app"
    assert app["result"]["structuredContent"]["grader"] == 21


def test_model_og_app_visibility_haandhaeves(monkeypatch):
    kald = []

    class _Klient:
        connected = True
        connect_error = None
        tools = []

        def tool(self, navn):
            audience = "app" if navn == "app_only" else "model"
            return {"name": navn, "_meta": {"ui": {"visibility": [audience]}}}

        def call_tool_raw(self, navn, args):
            kald.append(navn)
            return {"content": []}

    monkeypatch.setattr(mcp_manager, "get_client", lambda n, connect=True: _Klient())
    model_result, app = mcp_manager.call_with_app("vejr", "app_only", {})
    assert model_result["status"] == "error"
    assert app is None
    assert mcp_manager.call_raw("vejr", "model_only", {})["status"] == "error"
    assert kald == []
