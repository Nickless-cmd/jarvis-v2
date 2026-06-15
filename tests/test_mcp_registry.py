import core.services.mcp_registry as mr


def _reset(monkeypatch):
    store: dict = {}
    monkeypatch.setattr(mr, "load_json", lambda key, default: list(store.get(key, default)))
    monkeypatch.setattr(mr, "save_json", lambda key, data: store.__setitem__(key, list(data)))
    return store


def test_add_and_list(monkeypatch):
    _reset(monkeypatch)
    res = mr.add_mcp_server("Cloudflare", "https://mcp.example/sse")
    assert res["status"] == "ok"
    servers = mr.list_mcp_servers()
    assert len(servers) == 1
    assert servers[0]["name"] == "Cloudflare"
    assert servers[0]["id"].startswith("mcp-")


def test_add_validates(monkeypatch):
    _reset(monkeypatch)
    assert mr.add_mcp_server("", "x")["status"] == "error"
    assert mr.add_mcp_server("x", "")["status"] == "error"


def test_remove(monkeypatch):
    _reset(monkeypatch)
    sid = mr.add_mcp_server("A", "u")["server"]["id"]
    assert mr.remove_mcp_server(sid)["status"] == "ok"
    assert mr.list_mcp_servers() == []
    assert mr.remove_mcp_server("nope")["status"] == "error"
