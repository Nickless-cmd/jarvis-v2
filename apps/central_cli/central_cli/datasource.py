"""Data layer for the Central HUD.

Pure functions that fetch + shape each HUD view's data from an injected client.
A client exposes ``.get_json(path, params=None)`` returning parsed JSON.

Self-safe: every shape function tolerates missing keys via ``.get(...)`` so a
partial or empty endpoint response never raises.
"""

from __future__ import annotations

from typing import Any

_BLOCKS = " ▁▂▃▄▅▆▇█"


def _spark(vals: Any) -> str:
    """Render a small float list as a unicode block sparkline."""
    vals = [float(v) for v in (vals or []) if v is not None]
    if not vals:
        return ""
    lo, hi = min(vals), max(vals)
    rng = (hi - lo) or 1.0
    return "".join(_BLOCKS[min(8, int((v - lo) / rng * 8))] for v in vals)


def _realtime(client: Any) -> dict:
    data = client.get_json("/central/realtime")
    return data if isinstance(data, dict) else {}


def overview(client: Any) -> dict:
    """Top-level status summary from /central/realtime."""
    rt = _realtime(client)
    coverage = rt.get("coverage") or {}
    incidents = rt.get("incidents") or []
    breakers = rt.get("open_breakers") or []
    return {
        "status": rt.get("status", "unknown"),
        "nerves": coverage.get("nerves", 0),
        "clusters": coverage.get("clusters", 0),
        "incidents": len(incidents),
        "breakers": len(breakers),
        "top_incidents": list(incidents[:8]),
    }


def _incident_set(client: Any) -> set:
    """(cluster, nerve) pairs with error/critical severity."""
    rt = _realtime(client)
    out = set()
    for inc in rt.get("incidents") or []:
        if not isinstance(inc, dict):
            continue
        if inc.get("severity") in ("error", "critical"):
            out.add((inc.get("cluster"), inc.get("nerve")))
    return out


def nerves(client: Any) -> list:
    """Per-nerve rows from /central/timeseries, with derived state + sparkline.

    Each timeseries key is ``"cluster:nerve"``; its value holds per-process
    sub-dicts (api/runtime). Merge them: max count, most-recent ts, longest
    recent list. State: incident -> degraded; count 0 / no data -> død;
    else -> aktiv (idle reserved for count>0 but no recent list).
    """
    data = client.get_json("/central/timeseries")
    series = (data or {}).get("series") or {}
    incident_set = _incident_set(client)

    rows = []
    for key, procs in series.items():
        cluster, _, nerve = str(key).partition(":")
        if not procs or not isinstance(procs, dict):
            procs = {}

        count = 0
        last = ""
        recent: list = []
        for sub in procs.values():
            if not isinstance(sub, dict):
                continue
            count = max(count, sub.get("count") or 0)
            ts = sub.get("ts") or ""
            if ts and ts > last:
                last = ts
            r = sub.get("recent") or []
            if len(r) > len(recent):
                recent = r

        if (cluster, nerve) in incident_set:
            state = "degraded"
        elif count == 0 or not recent:
            state = "død"
        elif recent:
            state = "aktiv"
        else:
            state = "idle"

        rows.append({
            "cluster": cluster,
            "nerve": nerve,
            "state": state,
            "last": last,
            "count": count,
            "spark": _spark(recent),
        })
    return rows


def incidents(client: Any) -> list:
    """Incident list from /central/realtime (as-is)."""
    rt = _realtime(client)
    inc = rt.get("incidents") or []
    return list(inc)


def diagnostics(client: Any) -> dict:
    """Diagnostics payload from /central/diagnostics (as-is)."""
    data = client.get_json("/central/diagnostics")
    return data if isinstance(data, dict) else {}


def governance(client: Any) -> list:
    """Governance flags from /central/governance."""
    data = client.get_json("/central/governance")
    return (data or {}).get("flags") or []


def healers(client: Any) -> dict:
    """Healers payload from /central/healers (as-is)."""
    data = client.get_json("/central/healers")
    return data if isinstance(data, dict) else {}


def feed(client: Any) -> list:
    """Decision feed from /central/realtime, collapsing identical rows.

    Groups identical (cluster, nerve, decision) entries into one row with a
    ``count`` of how many collapsed. Order of first appearance is preserved.
    """
    rt = _realtime(client)
    order: list = []
    seen: dict = {}
    for row in rt.get("feed") or []:
        if not isinstance(row, dict):
            continue
        key = (row.get("cluster"), row.get("nerve"), row.get("decision"))
        if key in seen:
            seen[key]["count"] += 1
            continue
        entry = {
            "cluster": row.get("cluster"),
            "nerve": row.get("nerve"),
            "decision": row.get("decision"),
            "reason": row.get("reason", ""),
            "count": 1,
        }
        seen[key] = entry
        order.append(entry)
    return order
