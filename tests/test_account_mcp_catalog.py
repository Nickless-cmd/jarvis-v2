"""MCP-katalogets API bygger oven paa registry uden at omgaa trust."""

import asyncio

from fastapi.testclient import TestClient

import core.services.mcp_registry as mcp_registry
import core.services.mcp_trust as mcp_trust
from apps.api.jarvis_api.routes import account


def _som_owner(monkeypatch) -> None:
    monkeypatch.setattr(account, "_current_role", lambda _uid: "owner")
    monkeypatch.setattr(account, "current_context_snapshot", lambda: {"user_id": ""})


def test_catalog_markerer_installeret_server(monkeypatch):
    monkeypatch.setattr(
        mcp_registry,
        "list_mcp_servers",
        lambda: [
            {
                "id": "mcp-existing",
                "name": "Git",
                "transport": "stdio",
                "command": "uvx",
                "args": ["mcp-server-git"],
            }
        ],
    )

    from apps.api.jarvis_api.app import app

    response = TestClient(app).get("/account/mcp/catalog")

    assert response.status_code == 200
    by_id = {entry["id"]: entry for entry in response.json()["servers"]}
    assert by_id["git"]["installed"] is True
    assert by_id["fetch"]["installed"] is False
    assert by_id["filesystem"]["tools"]


def test_catalog_install_bruger_registry(monkeypatch):
    _som_owner(monkeypatch)
    captured = {}

    def fake_add(name, url="", **kwargs):
        captured.update(name=name, url=url, **kwargs)
        return {"status": "ok", "server": {"id": "mcp-new", "name": name}}

    monkeypatch.setattr(mcp_registry, "add_mcp_server", fake_add)

    response = asyncio.run(account.account_mcp_catalog_install("fetch"))

    assert response["status"] == "ok"
    assert captured == {
        "name": "Fetch",
        "url": "",
        "command": "uvx",
        "args": ["mcp-server-fetch"],
        "transport": "stdio",
    }


def test_catalog_install_godkender_ikke_serveren(monkeypatch):
    _som_owner(monkeypatch)
    state = {}

    def load_json(key, default):
        value = state.get(key, default)
        if isinstance(value, list):
            return [dict(item) for item in value]
        if isinstance(value, dict):
            return {k: list(v) if isinstance(v, list) else dict(v) for k, v in value.items()}
        return value

    monkeypatch.setattr(mcp_registry, "load_json", load_json)
    monkeypatch.setattr(mcp_registry, "save_json", lambda key, value: state.__setitem__(key, value))
    monkeypatch.setattr(mcp_trust, "load_json", load_json)
    monkeypatch.setattr(mcp_trust, "save_json", lambda key, value: state.__setitem__(key, value))

    response = asyncio.run(account.account_mcp_catalog_install("fetch"))

    assert response["status"] == "ok"
    assert mcp_registry.list_mcp_servers()[0]["name"] == "Fetch"
    assert mcp_trust.is_allowlisted("Fetch") is False
