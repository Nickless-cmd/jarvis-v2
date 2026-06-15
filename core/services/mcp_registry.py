"""MCP-server-registry (§4.6) — brugerens konfigurerede MCP-endpoints.

Dette er et KONFIGURATIONS-lager: list/tilføj/fjern MCP-server-entries, persisteret
i state_store. Selve runtime-konsumptionen (at agent-loopet rent faktisk loader og
kalder serverne) er et separat capability-spor — her ejer vi konfigurationen og
dens livscyklus. Ærligt afgrænset så UI'et ikke giver indtryk af mere end der er.
"""
from __future__ import annotations

from uuid import uuid4

from core.runtime.state_store import load_json, save_json

_STATE_KEY = "mcp_servers"


def _load() -> list[dict[str, str]]:
    raw = load_json(_STATE_KEY, [])
    if not isinstance(raw, list):
        return []
    return [r for r in raw if isinstance(r, dict)]


def list_mcp_servers() -> list[dict[str, str]]:
    return _load()


def add_mcp_server(name: str, url: str) -> dict[str, object]:
    name = str(name or "").strip()
    url = str(url or "").strip()
    if not name or not url:
        return {"status": "error", "error": "name og url er påkrævet"}
    servers = _load()
    entry = {"id": f"mcp-{uuid4().hex[:10]}", "name": name[:120], "url": url[:400]}
    servers.append(entry)
    save_json(_STATE_KEY, servers)
    return {"status": "ok", "server": entry}


def remove_mcp_server(server_id: str) -> dict[str, object]:
    sid = str(server_id or "").strip()
    servers = _load()
    kept = [s for s in servers if str(s.get("id")) != sid]
    if len(kept) == len(servers):
        return {"status": "error", "error": f"ukendt server {sid}"}
    save_json(_STATE_KEY, kept)
    return {"status": "ok", "removed": sid, "remaining": len(kept)}
