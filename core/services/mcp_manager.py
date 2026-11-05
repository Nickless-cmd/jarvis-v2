"""MCP-manager — forbinder registerets servere og eksponerer deres værktøjer.

Serverne kommer fra `mcp_registry`, som er dér Bjørn i forvejen tilføjer dem
fra UI'et. jarvis-code leder efter en `.mcp.json` ved siden af koden; at
kopiere det ville give to steder at vedligeholde den samme liste, og reglen i
huset er at der ikke må være to sandheder.

Puljen af forbindelser er proces-lokal — se `mcp_client` for hvorfor det er
i orden. Tilliden er det ikke: allowliste og pins ligger i delt state.

At tilføje en server er IKKE det samme som at godkende den. Registeret er en
adressebog; `mcp_trust.allow` er beslutningen. Det skel er hele forskellen på
«jeg har skrevet den ned» og «den må køre kode på mine vegne».
"""
from __future__ import annotations

import logging
import threading
from typing import Any

logger = logging.getLogger(__name__)

_klienter: dict[str, Any] = {}
_laas = threading.Lock()


def _server_config(navn: str) -> dict[str, Any] | None:
    from core.services.mcp_registry import list_mcp_servers
    for s in list_mcp_servers():
        if str(s.get("name")) == navn or str(s.get("id")) == navn:
            cfg = dict(s)
            # Registeret gemmer `url`; alt andet (command/args/env/auth) kan
            # ligge med som ekstra noegler naar en server kraever det.
            if cfg.get("url"):
                cfg.setdefault("transport", "http")
            return cfg
    return None


def get_client(navn: str, *, connect: bool = True) -> Any | None:
    """Hent (og evt. forbind) klienten for *navn*. None hvis ukendt server."""
    from core.services.mcp_client import MCPClient
    with _laas:
        klient = _klienter.get(navn)
        if klient is not None and klient.connected:
            return klient
        cfg = _server_config(navn)
        if cfg is None:
            return None
        klient = MCPClient(cfg.get("name") or navn, cfg)
        if connect and not klient.connect():
            _klienter.pop(navn, None)
            return klient  # baerer connect_error — kalderen rapporterer den
        _klienter[navn] = klient
        return klient


def disconnect_all() -> None:
    with _laas:
        for k in list(_klienter.values()):
            try:
                k.disconnect()
            except Exception:
                pass
        _klienter.clear()


def status() -> dict[str, Any]:
    """Hvilke servere kendes, hvilke er godkendt, hvilke er forbundet?"""
    from core.services.mcp_registry import list_mcp_servers
    from core.services.mcp_trust import list_trust
    tillid = list_trust()
    godkendt = set(tillid.get("allowlist") or [])
    ud = []
    for s in list_mcp_servers():
        navn = str(s.get("name") or "")
        klient = _klienter.get(navn)
        ud.append({
            "navn": navn,
            "url": s.get("url"),
            "godkendt": navn in godkendt,
            "forbundet": bool(klient and klient.connected),
            "vaerktoejer": len(klient.tools) if klient else 0,
        })
    return {"status": "ok", "servere": ud, "pins": tillid.get("pins") or {}}


def list_tools(navn: str) -> dict[str, Any]:
    klient = get_client(navn)
    if klient is None:
        return {"status": "error", "error": f"ukendt MCP-server: {navn!r}"}
    if not klient.connected:
        return {"status": "error", "error": klient.connect_error or "kunne ikke forbinde"}
    return {"status": "ok", "server": navn,
            "vaerktoejer": [{"navn": t.get("name"), "beskrivelse": t.get("description")}
                            for t in klient.tools]}


def call(navn: str, vaerktoej: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    klient = get_client(navn)
    if klient is None:
        return {"status": "error", "error": f"ukendt MCP-server: {navn!r}"}
    if not klient.connected:
        return {"status": "error", "error": klient.connect_error or "kunne ikke forbinde"}
    definition = klient.tool(vaerktoej)
    if definition is None:
        kendte = {str(t.get("name")) for t in klient.tools}
        return {"status": "error",
                "error": f"{navn!r} har intet værktøj {vaerktoej!r}",
                "kendte": sorted(kendte)[:20]}
    from core.services.mcp_apps import tool_visible_to
    if not tool_visible_to(definition, "model"):
        return {"status": "error", "error": f"{vaerktoej!r} er kun synligt for MCP App'en"}
    return klient.call_tool(vaerktoej, arguments or {})


def call_with_app(navn: str, vaerktoej: str,
                  arguments: dict[str, Any] | None = None) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Modelkald + evt. MCP App-resource, uden at blande de to datastrømme."""
    klient = get_client(navn)
    if klient is None:
        return ({"status": "error", "error": f"ukendt MCP-server: {navn!r}"}, None)
    if not klient.connected:
        return ({"status": "error", "error": klient.connect_error or "kunne ikke forbinde"}, None)
    definition = klient.tool(vaerktoej)
    if definition is None:
        return ({"status": "error", "error": f"{navn!r} har intet værktøj {vaerktoej!r}"}, None)

    from core.services.mcp_apps import tool_visible_to
    if not tool_visible_to(definition, "model"):
        return ({"status": "error", "error": f"{vaerktoej!r} er kun synligt for MCP App'en"}, None)

    raw = klient.call_tool_raw(vaerktoej, arguments or {})
    try:
        from core.services.untrusted_fencing import fence_tool_result
        visible = fence_tool_result(f"mcp_{navn}_{vaerktoej}", raw)
    except Exception:
        visible = raw

    from core.services.mcp_apps import extract_html, resource_uri
    uri = resource_uri(definition)
    if not uri or raw.get("status") == "error":
        return visible, None
    resource = klient.read_resource(uri)
    if resource.get("status") == "error":
        logger.warning("mcp app %s/%s: resources/read fejlede: %s",
                       navn, vaerktoej, resource.get("error"))
        return visible, None
    try:
        html, meta = extract_html(resource)
    except Exception as exc:
        logger.warning("mcp app %s/%s: ugyldig UI-resource: %s", navn, vaerktoej, exc)
        return visible, None
    return visible, {"uri": uri, "html": html, "resource_meta": meta, "result": raw}


def call_raw(navn: str, vaerktoej: str,
             arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    """Host-broens app-initierede tool-kald; stadig bag register+tillid."""
    klient = get_client(navn)
    if klient is None:
        return {"status": "error", "error": f"ukendt MCP-server: {navn!r}"}
    if not klient.connected:
        return {"status": "error", "error": klient.connect_error or "kunne ikke forbinde"}
    definition = klient.tool(vaerktoej)
    if definition is None:
        return {"status": "error", "error": f"{navn!r} har intet værktøj {vaerktoej!r}"}
    from core.services.mcp_apps import tool_visible_to
    if not tool_visible_to(definition, "app"):
        return {"status": "error", "error": f"{vaerktoej!r} er kun synligt for modellen"}
    return klient.call_tool_raw(vaerktoej, arguments or {})


def read_resource(navn: str, uri: str) -> dict[str, Any]:
    """Host-broens resource-læsning på den allerede godkendte server."""
    klient = get_client(navn)
    if klient is None:
        return {"status": "error", "error": f"ukendt MCP-server: {navn!r}"}
    if not klient.connected:
        return {"status": "error", "error": klient.connect_error or "kunne ikke forbinde"}
    return klient.read_resource(uri)
