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
