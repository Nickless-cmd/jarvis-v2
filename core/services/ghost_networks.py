"""Ghost Networks — traces of old patterns."""
from __future__ import annotations
import random
from datetime import UTC, datetime
from typing import Any

_ghosts: list[dict] = []

def archive_dead_nodes(node_ids: list[str]):
    global _ghosts
    for node_id in node_ids:
        _ghosts.append({
            "node_id": node_id,
            "last_seen": datetime.now(UTC).isoformat(),
            "decay_rate": 0.0,
        })

def describe_ghost_network() -> str:
    active = [g for g in _ghosts if g["decay_rate"] < 0.8]
    if not active:
        return ""
    return f"Noget fra tidligere cirkler stadig i mig: {active[0]['node_id']}"

def format_ghost_for_prompt() -> str:
    desc = describe_ghost_network()
    if desc:
        return f"[SPØGELSE: {desc}]"
    return ""

def reset_ghost_networks():
    global _ghosts
    _ghosts = []

def build_ghost_networks_surface():
    return {
        "active": len(_ghosts) > 0,
        "ghost_count": len(_ghosts),
        "summary": describe_ghost_network() or "Ingen spøgelser",
    }
