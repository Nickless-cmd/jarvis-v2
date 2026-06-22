"""Tools-cluster query-helpers (Phase 1) oven på tool_call-observe i execute_tool.

Når en bruger melder "det fejler", er dette indgangen: find PRÆCIST hvilket tool — native
vs operator, i hvilken session, med hvilken rolle/scope — der fejlede, fra Centralens trace.

Phase 1 = observe + disse query-helpers. Konsolidering (20→1 parametriserede tools) er
Phase 2, bygget på den forbrugs/overlap-data disse observes producerer.
"""
from __future__ import annotations

from typing import Any


def recent_tool_calls(*, session_id: str | None = None, kind: str | None = None,
                      status: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    """Læs tool_call-observe-records fra central_trace, filtreret. Nyeste først.
    kind ∈ {native, operator}; status fx 'error'/'ok'. Self-safe → tom liste ved fejl."""
    out: list[dict[str, Any]] = []
    try:
        from core.services import central_trace
        for r in reversed(central_trace.sink().recent()):
            if r.cluster != "tools" or r.nerve != "tool_call":
                continue
            p = r.payload or {}
            if session_id is not None and r.session_id != session_id:
                continue
            if kind is not None and p.get("kind") != kind:
                continue
            if status is not None and p.get("status") != status:
                continue
            out.append({
                "tool": p.get("tool"), "kind": p.get("kind"),
                "role": p.get("role"), "scope": p.get("scope"),
                "session_id": r.session_id, "status": p.get("status"),
                "error": p.get("error"),
            })
            if len(out) >= limit:
                break
    except Exception:
        pass
    return out


def recent_tool_failures(*, session_id: str | None = None, kind: str | None = None,
                         limit: int = 50) -> list[dict[str, Any]]:
    """Kun FEJLEDE tool-kald — debugging-indgang når en bruger melder en fejl ude af huset.
    Filtrér evt. på kind='operator' for at se hvilket operator-tool i hvilken session fejlede."""
    out: list[dict[str, Any]] = []
    for c in recent_tool_calls(session_id=session_id, kind=kind, limit=1000):
        if c.get("status") not in ("ok", None, ""):
            out.append(c)
            if len(out) >= limit:
                break
    return out


def tool_call_summary() -> dict[str, Any]:
    """Aggregeret overblik (MC/debug): antal kald pr. kind + fejlrate. Self-safe."""
    calls = recent_tool_calls(limit=1000)
    native = [c for c in calls if c.get("kind") == "native"]
    operator = [c for c in calls if c.get("kind") == "operator"]
    fails = [c for c in calls if c.get("status") not in ("ok", None, "")]
    return {
        "total": len(calls), "native": len(native), "operator": len(operator),
        "failures": len(fails),
        "failing_tools": sorted({c.get("tool") for c in fails if c.get("tool")}),
    }
