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


# ── stdio-servere (målt 18/10-2026) ─────────────────────────────────────────
#
# Registret kunne kun gemme `url`, så Chrome DevTools og Serena — der begge er
# stdio-processer — kunne ikke tilføjes gennem den rigtige vej. Klienten har
# hele tiden kunnet stdio; det var registeret der satte loftet.


def test_add_stdio_server(monkeypatch):
    _reset(monkeypatch)
    res = mr.add_mcp_server("serena", command="uvx",
                            args=["--from", "serena-agent", "serena"])
    assert res["status"] == "ok"
    s = mr.list_mcp_servers()[0]
    assert s["transport"] == "stdio"
    assert s["command"] == "uvx"
    assert s["args"] == ["--from", "serena-agent", "serena"]
    assert "url" not in s, "en stdio-server har ingen URL"


def test_add_kraever_url_eller_command(monkeypatch):
    _reset(monkeypatch)
    assert mr.add_mcp_server("x")["status"] == "error"
    assert mr.add_mcp_server("x", "")["status"] == "error"
    assert mr.add_mcp_server("x", "https://a.example/mcp")["status"] == "ok"
    assert mr.add_mcp_server("y", command="npx")["status"] == "ok"


def test_http_server_faar_transport_http(monkeypatch):
    _reset(monkeypatch)
    mr.add_mcp_server("context7", "https://mcp.context7.com/mcp")
    assert mr.list_mcp_servers()[0]["transport"] == "http"


def test_env_og_args_gemmes_som_strenge(monkeypatch):
    """state skal kunne serialiseres — ikke-objecter må ikke slippe ind."""
    _reset(monkeypatch)
    mr.add_mcp_server("s", command="uvx", args=[1, "to"], env={"K": 2})
    s = mr.list_mcp_servers()[0]
    assert s["args"] == ["1", "to"]
    assert s["env"] == {"K": "2"}
