"""Connections-cluster — gør forbindelses-LIVSCYKLUSSEN synlig i Den Intelligente Central:
hvem/hvad er forbundet til API'en (jarvis-desk, mobile companion, MC-websocket, members)
hvornår, fra hvilken enhed/platform. Komplementerer endpoint-usage (request-laget) + stream
(SSE-laget) med selve FORBINDELSEN.

PRIVACY: metadata-only (user_id, device, platform, event) — ALDRIG indhold. Workspace-
krypteringen er urørt (Bjørn: alt krypteret undtaget owner-kontoen). Centralen er det interne
kontrol-plan; at se HVEM der er forbundet er Bjørns visibilitet, ikke en læk til andre brugere.

Grundlag for kommende adaptiv læring: "hvem var aktiv da X skete", forbindelses-mønstre pr.
device/bruger. Self-safe; kaster aldrig.
"""
from __future__ import annotations

from typing import Any


def _observe(nerve: str, data: dict[str, Any]) -> None:
    try:
        from core.services.central_core import central
        central().observe({"cluster": "connections", "nerve": nerve, **data})
    except Exception:
        pass


def note_presence(user_id: str, device_key: str, platform: str = "", **meta: Any) -> None:
    """En device-presence-ping (jarvis-desk/mobile companion). Metadata-only."""
    _observe("device_presence", {
        "user_id": str(user_id or ""), "device": str(device_key or ""),
        "platform": str(platform or ""),
        "foreground": meta.get("foreground"), "network": meta.get("network"),
    })


def note_ws(event: str, client: str = "", **meta: Any) -> None:
    """MC-websocket-livscyklus: event ∈ {connected, disconnected, error}. client = host:port."""
    _observe("ws_connection", {"event": str(event or ""), "client": str(client or ""), **{
        k: v for k, v in meta.items() if k in ("user_id", "reason")}})


def note_connection_error(client: str, reason: str, **meta: Any) -> None:
    """Forbindelses-FEJL (WS-error, broken pipe, abort). → observe (synlig, ikke severe)."""
    _observe("connection_error", {"client": str(client or ""), "reason": str(reason or "")[:160]})


def note_unauthorized(user_id: str, session_id: str, resource: str, reason: str,
                      *, role: str = "", run_id: str = "") -> None:
    """UAUTORISERET adgang (tool-deny / identity-spoof / rate-limit) på en forbindelse →
    observe + incident. Self-safe.

    SEVERITY (6. jul): en FORVENTET rolle-deny (``tool_not_permitted``) er gaten der VIRKER —
    fx en member-scoped run hvor modellen over-rækker efter et owner-tool og korrekt blokeres.
    Det er observerbart (gult=error), IKKE et system-brud (severe-rødt). Ægte anomalier (identity-
    spoof, rate-abuse, ukendt reason) forbliver SEVERE. Signalet bærer nu ægte user_id + role
    + run_id, så "hvem/hvor" er besvarbart (før stod kun rollen "member" → uhandlingsbart)."""
    _observe("unauthorized", {
        "user_id": str(user_id or ""), "session_id": str(session_id or ""),
        "resource": str(resource or ""), "reason": str(reason or "")[:120],
        "role": str(role or ""), "run_id": str(run_id or ""),
    })
    try:
        from core.runtime.db_central_incidents import record_central_incident
        _sev = "error" if reason == "tool_not_permitted" else "severe"
        _who = user_id or (f"role:{role}" if role else "?")
        record_central_incident(
            cluster="connections", nerve="unauthorized", kind="access", severity=_sev,
            message=(f"tool-deny: {resource} ({reason}) user={_who} role={role or '-'} "
                     f"run={run_id or '-'}"),
            run_id=str(run_id or ""), session_id=str(session_id or ""),
        )
    except Exception:
        pass


def session_activity(session_id: str, *, limit: int = 300) -> dict[str, Any]:
    """Forbindelses-debugging pr. session: hvilke tools blev brugt, hvilke FEJLEDE (+ årsag),
    og uautoriserede forsøg. Kombinerer tool_observer (tool-laget) + connections-trace. Når en
    bruger melder en forbindelses-/adgangs-fejl ser vi PRÆCIST hvad der skete i sessionen."""
    out: dict[str, Any] = {"session_id": str(session_id or ""), "tools": [],
                           "failed_tools": [], "unauthorized": [], "connection_errors": []}
    try:
        from core.services.tool_observer import recent_tool_calls
        seen: set[str] = set()
        for c in recent_tool_calls(session_id=session_id, limit=limit):
            t = c.get("tool")
            if t and t not in seen:
                seen.add(t)
                out["tools"].append({"tool": t, "kind": c.get("kind")})
            if c.get("status") not in ("ok", None, ""):
                out["failed_tools"].append({"tool": t, "kind": c.get("kind"),
                                            "error": c.get("error")})
    except Exception:
        pass
    try:
        from core.services import central_trace
        for r in central_trace.sink().recent():
            if r.cluster != "connections":
                continue
            # central.observe flytter session_id til record-feltet (reserveret), ikke payload.
            if str(getattr(r, "session_id", "") or "") != str(session_id or ""):
                continue
            p = r.payload or {}
            if r.nerve == "unauthorized":
                out["unauthorized"].append({"resource": p.get("resource"), "reason": p.get("reason")})
            elif r.nerve == "connection_error":
                out["connection_errors"].append({"reason": p.get("reason")})
    except Exception:
        pass
    return out


def active_summary(*, window: int = 500) -> dict[str, Any]:
    """Read-only: hvem/hvad har været forbundet i den seneste trace (til MC/adaptiv-læring).
    Aggregerer connections-observes fra ring-bufferen. Self-safe."""
    devices: dict[str, dict[str, Any]] = {}
    ws_open = 0
    ws_closed = 0
    try:
        from core.services import central_trace
        for r in central_trace.sink().recent()[-window:]:
            if r.cluster != "connections":
                continue
            p = r.payload or {}
            if r.nerve == "device_presence":
                key = f"{p.get('user_id')}::{p.get('device')}"
                devices[key] = {"user_id": p.get("user_id"), "device": p.get("device"),
                                "platform": p.get("platform")}
            elif r.nerve == "ws_connection":
                if p.get("event") == "connected":
                    ws_open += 1
                elif p.get("event") == "disconnected":
                    ws_closed += 1
    except Exception:
        pass
    return {
        "active_devices": list(devices.values()),
        "device_count": len(devices),
        "ws_connected": ws_open, "ws_disconnected": ws_closed,
    }
