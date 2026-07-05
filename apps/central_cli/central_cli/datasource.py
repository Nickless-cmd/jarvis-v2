"""Data layer for the Central HUD.

Pure functions that fetch + shape each HUD view's data from an injected client.
A client exposes ``.get_json(path, params=None)`` returning parsed JSON.

Self-safe: every shape function tolerates missing keys via ``.get(...)`` so a
partial or empty endpoint response never raises.
"""

from __future__ import annotations

import hashlib
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


def clusters(client: Any) -> list:
    """Per-cluster summary rows.

    ``/central/realtime`` ships a thin cluster grid (``{cluster, status,
    security}``) with no per-state nerve counts, so we DERIVE the counts by
    grouping ``nerves(client)`` by cluster. The realtime grid's ``status`` is
    merged in when present (it reflects breaker/degrading truth the raw nerve
    states don't capture); otherwise we fall back to a derived status.
    """
    # realtime status per cluster (thin grid), keyed by cluster name
    rt = _realtime(client)
    rt_status: dict = {}
    for c in rt.get("clusters") or []:
        if isinstance(c, dict) and c.get("cluster"):
            rt_status[str(c.get("cluster"))] = str(c.get("status") or "")

    # group nerves by cluster, tallying state buckets
    buckets: dict = {}
    for r in nerves(client):
        cl = str(r.get("cluster", ""))
        st = str(r.get("state", ""))
        b = buckets.setdefault(cl, {"nerves": 0, "aktiv": 0, "idle": 0,
                                    "degraded": 0, "død": 0})
        b["nerves"] += 1
        if st in b:
            b[st] += 1

    # ensure clusters that only exist in the realtime grid still show up
    for cl in rt_status:
        buckets.setdefault(cl, {"nerves": 0, "aktiv": 0, "idle": 0,
                                "degraded": 0, "død": 0})

    out = []
    for cl, b in buckets.items():
        status = rt_status.get(cl)
        if not status:
            # derived fallback from bucket contents
            if b["degraded"] or b["død"]:
                status = "yellow"
            elif b["aktiv"]:
                status = "green"
            else:
                status = "idle"
        out.append({"cluster": cl, "status": status, **b})

    _order = {"red": 0, "yellow": 1, "green": 2, "idle": 3}
    out.sort(key=lambda x: (_order.get(x["status"], 9), x["cluster"]))
    return out


def incidents(client: Any) -> list:
    """Incident list from /central/realtime (as-is)."""
    rt = _realtime(client)
    inc = rt.get("incidents") or []
    return list(inc)


def diagnostics(client: Any) -> dict:
    """Diagnostics payload from /central/diagnostics (as-is)."""
    data = client.get_json("/central/diagnostics")
    return data if isinstance(data, dict) else {}


def anomalies(client: Any) -> list:
    """Anomalies from /central/diagnostics, shaped for the Anomalies view.
    Self-safe: any error → empty list. Sorted by importance then count."""
    try:
        diag = client.get_json("/central/diagnostics")
    except Exception:
        return []
    if not isinstance(diag, dict):
        return []
    rank = {"high": 0, "critical": 0, "medium": 1, "low": 2}
    out = []
    for a in diag.get("anomalies") or []:
        if not isinstance(a, dict):
            continue
        out.append({
            "importance": str(a.get("importance", "") or ""),
            "category": str(a.get("category", "") or ""),
            "source": str(a.get("source", "") or ""),
            "count": int(a.get("count", 0) or 0),
            "signature": str(a.get("signature", "") or ""),
            "sample": str(a.get("sample", "") or ""),
            "location": str(a.get("location", "") or ""),
            "first": str(a.get("first_seen", "") or ""),
            "last": str(a.get("last_seen", "") or ""),
        })
    out.sort(key=lambda x: (rank.get(x["importance"], 3), -x["count"]))
    return out


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


def _short_sig(signature: str) -> str:
    """Stable 8-hex-char id derived from a signature string."""
    return hashlib.blake2s(str(signature).encode(), digest_size=4).hexdigest()


def incident_detail(client: Any, incident: dict) -> dict:
    """Enrich a realtime incident with joined root-cause / correlation / heal /
    related data.

    All fields are derived from real endpoints (never fabricated). Self-safe:
    on any error every field falls back to a safe default and no exception
    propagates.
    """
    try:
        inc = incident if isinstance(incident, dict) else {}
        severity = str(inc.get("severity") or "")
        cluster = str(inc.get("cluster") or "")
        nerve = str(inc.get("nerve") or "")
        kind = str(inc.get("kind") or "")
        message = str(inc.get("message") or "")

        # human title: nerve, or first sentence of message when nerve is empty
        if nerve:
            title = nerve
        else:
            title = message.split(".")[0].strip() if message else ""

        # --- join matching root_cause from /central/diagnostics ---
        root_cause = None
        correlation = None
        rc_signature = ""
        try:
            diag = client.get_json("/central/diagnostics")
            rcs = (diag or {}).get("root_causes") or []
        except Exception:
            rcs = []
        matches = []
        for rc in rcs:
            if not isinstance(rc, dict):
                continue
            if (str(rc.get("cluster") or "") == cluster
                    and str(rc.get("nerve") or "") == nerve):
                matches.append(rc)
        if matches:
            # highest count wins
            best = max(matches, key=lambda r: r.get("count") or 0)
            rc_signature = str(best.get("signature") or "")
            root_cause = rc_signature or None
            correlation = {
                "sig": _short_sig(rc_signature),
                "count": int(best.get("count") or 0),
                "first": str(best.get("first") or ""),
                "last": str(best.get("last") or ""),
            }

        # --- related: OTHER same-cluster realtime incidents (exclude own nerve) ---
        related: list = []
        seen_rel: set = set()
        try:
            rt = _realtime(client)
            rt_incidents = rt.get("incidents") or []
        except Exception:
            rt_incidents = []
        for other in rt_incidents:
            if not isinstance(other, dict):
                continue
            o_cluster = str(other.get("cluster") or "")
            o_nerve = str(other.get("nerve") or "")
            if o_cluster != cluster:
                continue
            if o_nerve == nerve:
                continue
            label = f"{o_cluster}/{o_nerve}"
            if label in seen_rel:
                continue
            seen_rel.add(label)
            related.append(label)
            if len(related) >= 6:
                break

        # --- heal_status ---
        heal_status = None
        heal_source = ""
        low_msg = message.lower()
        low_sig = rc_signature.lower()
        if "auto-healed" in low_sig or "healed" in low_sig:
            heal_source = rc_signature
        elif "auto-healed" in low_msg or "healed" in low_msg:
            heal_source = message
        if heal_source:
            heal_status = f"heal-note: {heal_source.strip()[:120]}"
        elif kind:
            # else: a live healer whose kind relates to this incident's kind
            try:
                hz = client.get_json("/central/healers")
                healer_list = (hz or {}).get("healers") or []
            except Exception:
                healer_list = []
            for h in healer_list:
                if not isinstance(h, dict):
                    continue
                h_kind = str(h.get("kind") or "")
                if not h_kind:
                    continue
                related_kind = (kind in h_kind or h_kind in kind
                                or kind == h_kind)
                live = (str(h.get("mode") or "").upper() == "LIVE"
                        or bool(h.get("live_flag_on")))
                if related_kind and live:
                    heal_status = f"healer {h_kind} ({h.get('mode') or ''})".strip()
                    break

        return {
            "severity": severity,
            "cluster": cluster,
            "nerve": nerve,
            "kind": kind,
            "message": message,
            "title": title,
            "root_cause": root_cause,
            "related": related,
            "heal_status": heal_status,
            "correlation": correlation,
        }
    except Exception:
        return {
            "severity": None,
            "cluster": None,
            "nerve": None,
            "kind": None,
            "message": None,
            "title": None,
            "root_cause": None,
            "related": [],
            "heal_status": None,
            "correlation": None,
        }


def agents(client: Any) -> list:
    """Agent roster from /central/agents, shaped for the Agents view.

    Self-safe: any error → empty list. Each row carries id/role/status/tokens
    plus the raw agent dict passed through for the side-panel detail.
    """
    try:
        data = client.get_json("/central/agents")
    except Exception:
        return []
    if not isinstance(data, dict):
        return []
    out = []
    for a in data.get("agents") or []:
        if not isinstance(a, dict):
            continue
        out.append({
            "agent_id": str(a.get("agent_id", "") or ""),
            "role": str(a.get("role", "") or ""),
            "status": str(a.get("status", "") or ""),
            "tokens_burned": int(a.get("tokens_burned", 0) or 0),
            "raw": a,
        })
    return out


def self_snapshot(client: Any) -> dict:
    """Jarvis' reduced self from /central/self, shaped for the Mind & Self view.

    Self-safe: any error → empty dict. Returns the ``self`` sub-object holding
    living_executive / self_model / world_model surfaces (already reduced by the
    backend to liveness / counters / governance consequence — never raw content).
    """
    try:
        data = client.get_json("/central/self")
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    slf = data.get("self")
    return slf if isinstance(slf, dict) else {}


def cost_today(client: Any) -> float | None:
    """Today's total cost in USD from /central/costs-daily, or None if unavailable.

    Uses the ``today_cost`` field. Self-safe: any error / missing / non-numeric
    field returns None.
    """
    try:
        data = client.get_json("/central/costs-daily")
        if not isinstance(data, dict):
            return None
        val = data.get("today_cost")
        if val is None:
            return None
        return float(val)
    except Exception:
        return None


def council(client: Any) -> list:
    """Council/swarm sessions from /central/council. Self-safe → []."""
    try:
        data = client.get_json("/central/council")
        if not isinstance(data, dict):
            return []
        return data.get("sessions") or []
    except Exception:
        return []


def scheduled(client: Any) -> list:
    """Pending scheduled tasks from /central/queues/scheduled. Self-safe → []."""
    try:
        data = client.get_json("/central/queues/scheduled")
        if not isinstance(data, dict):
            return []
        return data.get("tasks") or []
    except Exception:
        return []


def autonomy(client: Any) -> dict:
    """Autonomy proposal queue from /central/autonomy. Self-safe →
    ``{"proposals": [], "pending_count": 0}``."""
    fallback = {"proposals": [], "pending_count": 0}
    try:
        data = client.get_json("/central/autonomy")
        if not isinstance(data, dict):
            return dict(fallback)
        return {
            "proposals": data.get("proposals") or [],
            "pending_count": data.get("pending_count") or 0,
        }
    except Exception:
        return dict(fallback)


def costs_daily(client: Any) -> dict:
    """Daily cost time-series from /central/costs-daily, shaped for the CLI.

    Returns ``{"days": [...], "today_cost": float|None, "week_cost": float|None}``.
    Self-safe: any error → ``{"days": [], "today_cost": None, "week_cost": None}``.
    """
    fallback = {"days": [], "today_cost": None, "week_cost": None}
    try:
        data = client.get_json("/central/costs-daily")
        if not isinstance(data, dict):
            return dict(fallback)
        days = data.get("days")
        if not isinstance(days, list):
            days = []

        def _num(v: Any) -> float | None:
            if v is None:
                return None
            try:
                return float(v)
            except Exception:
                return None

        return {
            "days": days,
            "today_cost": _num(data.get("today_cost")),
            "week_cost": _num(data.get("week_cost")),
        }
    except Exception:
        return dict(fallback)
