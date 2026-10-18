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


def add_mcp_server(
    name: str,
    url: str = "",
    *,
    command: str = "",
    args: list[str] | None = None,
    env: dict[str, str] | None = None,
    transport: str = "",
) -> dict[str, object]:
    """Tilføj en server — HTTP (`url`) eller stdio (`command` + `args`).

    MÅLT 18/10-2026: registret kunne kun gemme `url`, så stdio-servere
    (Chrome DevTools, Serena) kunne ikke tilføjes gennem den rigtige vej —
    kun ved at skrive rå JSON ind i state. Klienten har hele tiden kunnet
    stdio (`mcp_client._connect_stdio`), så det var registeret der satte
    loftet, ikke evnen.

    At TILFØJE er stadig ikke at GODKENDE: `mcp_trust.allow` er beslutningen,
    og den ligger bevidst et andet sted.
    """
    name = str(name or "").strip()
    url = str(url or "").strip()
    command = str(command or "").strip()
    if not name:
        return {"status": "error", "error": "name er påkrævet"}
    if not url and not command:
        return {"status": "error", "error": "url eller command er påkrævet"}
    servers = _load()
    entry: dict[str, object] = {"id": f"mcp-{uuid4().hex[:10]}", "name": name[:120]}
    if url:
        entry["url"] = url[:400]
        entry["transport"] = transport or "http"
    else:
        entry["command"] = command[:400]
        entry["transport"] = transport or "stdio"
        rene_args = [str(a) for a in (args or [])]
        if rene_args:
            entry["args"] = rene_args
        if env:
            entry["env"] = {str(k): str(v) for k, v in env.items()}
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
