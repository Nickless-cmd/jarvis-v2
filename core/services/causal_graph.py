"""Causal graph query API.

Læser causal_edges + events for at traversere parent/child relations.
Backward = "hvad caused dette?" Forward = "hvad caused dette så?"

BFS-traversal med visited-set forhindrer infinite loops på cykliske
grafer. Pagination via (offset, limit) så brede events med mange
children kan paginerers.
"""
from __future__ import annotations

import json
import logging
from collections import deque
from typing import Any

from core.runtime.db import connect

logger = logging.getLogger(__name__)


def _fetch_event(event_id: int) -> dict[str, Any] | None:
    with connect() as c:
        row = c.execute(
            "SELECT id, kind, payload_json, created_at FROM events WHERE id = ?",
            (event_id,),
        ).fetchone()
    if not row:
        return None
    try:
        payload = json.loads(row["payload_json"] or "{}")
    except Exception:
        payload = {}
    return {
        "id": int(row["id"]),
        "kind": str(row["kind"]),
        "payload": payload,
        "created_at": str(row["created_at"]),
    }


def _fetch_neighbors(
    event_id: int,
    direction: str,
    min_confidence: float,
) -> list[dict[str, Any]]:
    """Return list of (other_event_id, edge dict) for one hop."""
    if direction == "backward":
        sql = (
            "SELECT parent_event_id AS other_id, edge_kind, confidence, "
            "source, reasoning FROM causal_edges "
            "WHERE child_event_id = ? AND confidence >= ?"
        )
    else:
        sql = (
            "SELECT child_event_id AS other_id, edge_kind, confidence, "
            "source, reasoning FROM causal_edges "
            "WHERE parent_event_id = ? AND confidence >= ?"
        )
    with connect() as c:
        rows = c.execute(sql, (event_id, min_confidence)).fetchall()
    return [
        {
            "other_id": int(r["other_id"]),
            "edge": {
                "kind": str(r["edge_kind"]),
                "confidence": float(r["confidence"]),
                "source": str(r["source"]),
                "reasoning": str(r["reasoning"] or ""),
            },
        }
        for r in rows
    ]


def query_causal_chain(
    *,
    event_id: int,
    direction: str = "backward",
    max_depth: int = 5,
    min_confidence: float = 0.5,
    offset: int = 0,
    limit: int = 100,
) -> dict[str, Any]:
    """BFS through causal_edges from event_id in given direction.

    Returns a dict with the root event and the chain (list of steps).
    See spec §5 for full response shape.
    """
    if direction not in ("backward", "forward"):
        raise ValueError(f"direction must be 'backward' or 'forward', got {direction}")

    root = _fetch_event(event_id)
    if root is None:
        return {
            "root_event": {"id": event_id, "kind": "<unknown>", "payload": {}, "created_at": ""},
            "chain": [],
            "truncated_by_depth": False,
            "truncated_by_limit": False,
            "total_nodes_returned": 0,
            "total_available": 0,
            "next_offset": None,
        }

    visited: set[int] = {event_id}
    queue: deque[tuple[int, int, dict[str, Any] | None]] = deque()
    queue.append((0, event_id, None))

    all_nodes: list[dict[str, Any]] = []
    truncated_by_depth = False

    while queue:
        depth, eid, edge = queue.popleft()
        if depth > max_depth:
            truncated_by_depth = True
            continue
        if depth > 0:  # skip root, it's in root_event
            ev = _fetch_event(eid)
            if ev is not None:
                all_nodes.append({"depth": depth, "event": ev, "edge": edge})
        if depth == max_depth:
            neighbors = _fetch_neighbors(eid, direction, min_confidence)
            if neighbors:
                truncated_by_depth = True
            continue
        for n in _fetch_neighbors(eid, direction, min_confidence):
            other = n["other_id"]
            if other in visited:
                continue
            visited.add(other)
            queue.append((depth + 1, other, n["edge"]))

    total_available = len(all_nodes)
    sliced = all_nodes[offset : offset + limit]
    truncated_by_limit = (offset + limit) < total_available
    next_offset = offset + limit if truncated_by_limit else None

    return {
        "root_event": root,
        "chain": sliced,
        "truncated_by_depth": truncated_by_depth,
        "truncated_by_limit": truncated_by_limit,
        "total_nodes_returned": len(sliced),
        "total_available": total_available,
        "next_offset": next_offset,
    }


def query_causal_neighbors(
    *,
    event_id: int,
    direction: str = "both",
    min_confidence: float = 0.5,
) -> dict[str, Any]:
    """Direct neighbors only (depth=1) — convenience wrapper."""
    out: dict[str, Any] = {"event_id": event_id, "parents": [], "children": []}
    if direction in ("backward", "both"):
        for n in _fetch_neighbors(event_id, "backward", min_confidence):
            ev = _fetch_event(n["other_id"])
            if ev:
                out["parents"].append({"event": ev, "edge": n["edge"]})
    if direction in ("forward", "both"):
        for n in _fetch_neighbors(event_id, "forward", min_confidence):
            ev = _fetch_event(n["other_id"])
            if ev:
                out["children"].append({"event": ev, "edge": n["edge"]})
    return out


def get_immediate_cause(event_id: int) -> dict[str, Any] | None:
    """Return single highest-confidence direct parent, or None."""
    neighbors = query_causal_neighbors(event_id=event_id, direction="backward")
    if not neighbors["parents"]:
        return None
    best = max(neighbors["parents"], key=lambda p: p["edge"]["confidence"])
    return best


def build_causal_graph_surface() -> dict[str, object]:
    """Mission Control surface — read-only meta-projection.

    Added during 2026-05-13 coverage push (system_cartographer dark-edge
    closure). Reports module presence so the cartographer registers it as
    observed. Specific state-readers added as the module evolves.
    """
    return {
        "active": True,
        "mode": "causal_graph",
        "summary": "Module loaded; entry points available.",
        "authority": "derived-read-only",
    }


