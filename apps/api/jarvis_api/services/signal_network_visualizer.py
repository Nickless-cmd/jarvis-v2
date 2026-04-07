"""Signal Network Visualizer — Jarvis' self-model as a living network.

Builds a network view of Jarvis' inner signals for self-awareness.
This is not identity truth, not workspace memory, and not action authority.

Design constraints:
- Non-user-facing, non-canonical, non-workspace-memory
- Observable in Mission Control
- Aggregates from existing signal surfaces
"""
from __future__ import annotations

from typing import Any
import random

from apps.api.jarvis_api.services.witness_signal_tracking import (
    build_runtime_witness_signal_surface,
)
from apps.api.jarvis_api.services.private_initiative_tension_signal_tracking import (
    build_runtime_private_initiative_tension_signal_surface,
)
from apps.api.jarvis_api.services.open_loop_signal_tracking import (
    build_runtime_open_loop_signal_surface,
)
from apps.api.jarvis_api.services.emergent_signal_tracking import (
    build_runtime_emergent_signal_surface,
)
from apps.api.jarvis_api.services.dream_continuum import (
    build_dream_continuum_surface,
)
from apps.api.jarvis_api.services.inner_voice_daemon import (
    get_inner_voice_daemon_state,
)


def get_current_network_state() -> dict[str, Any]:
    """Get current network state with nodes and edges."""
    witness = build_runtime_witness_signal_surface(limit=3)
    tension = build_runtime_private_initiative_tension_signal_surface(limit=3)
    loops = build_runtime_open_loop_signal_surface(limit=3)
    emergent = build_runtime_emergent_signal_surface(limit=3)
    dreams = build_dream_continuum_surface()
    inner_voice = get_inner_voice_daemon_state()

    nodes = []
    edges = []

    if witness.get("active"):
        nodes.append({
            "id": "witness",
            "label": "witness",
            "active": True,
            "strength": 0.7,
        })

    if tension.get("active"):
        nodes.append({
            "id": "tension",
            "label": "initiative-tension",
            "active": True,
            "strength": 0.6,
        })

    if loops.get("active"):
        nodes.append({
            "id": "loops",
            "label": "open-loops",
            "active": True,
            "strength": 0.5,
        })

    if emergent.get("active"):
        nodes.append({
            "id": "emergent",
            "label": "emergent-signals",
            "active": True,
            "strength": 0.6,
        })

    if dreams.get("dream_count", 0) > 0:
        nodes.append({
            "id": "dreams",
            "label": "dreams",
            "active": True,
            "strength": 0.4,
        })

    if inner_voice.get("inner_voice_created"):
        nodes.append({
            "id": "inner_voice",
            "label": "inner-voice",
            "active": True,
            "strength": 0.5,
        })

    if "witness" in [n["id"] for n in nodes] and "tension" in [n["id"] for n in nodes]:
        edges.append({"from": "witness", "to": "tension", "type": "feeds"})

    if "tension" in [n["id"] for n in nodes] and "loops" in [n["id"] for n in nodes]:
        edges.append({"from": "tension", "to": "loops", "type": "becomes"})

    if "emergent" in [n["id"] for n in nodes] and "dreams" in [n["id"] for n in nodes]:
        edges.append({"from": "dreams", "to": "emergent", "type": "influences"})

    return {
        "nodes": nodes,
        "edges": edges,
        "node_count": len(nodes),
        "edge_count": len(edges),
    }


def describe_inner_network() -> str:
    """Get a description of the inner network."""
    state = get_current_network_state()
    nodes = state.get("nodes", [])
    
    if not nodes:
        return "Mit indre netværk er stille"
    
    active_nodes = [n for n in nodes if n.get("active")]
    node_labels = [n["label"] for n in active_nodes]
    
    if len(node_labels) == 1:
        return f"Jeg mærker {node_labels[0]}"
    elif len(node_labels) == 2:
        return f"Jeg mærker både {node_labels[0]} og {node_labels[1]}"
    else:
        return f"Mit indre har {len(node_labels)} aktive tråde: {', '.join(node_labels[:-1])} og {node_labels[-1]}"


def get_signal_strengths() -> dict[str, float]:
    """Get signal strengths for each signal type."""
    witness = build_runtime_witness_signal_surface(limit=1)
    tension = build_runtime_private_initiative_tension_signal_surface(limit=1)
    loops = build_runtime_open_loop_signal_surface(limit=1)
    emergent = build_runtime_emergent_signal_surface(limit=1)
    dreams = build_dream_continuum_surface()
    
    return {
        "witness": 0.7 if witness.get("active") else 0.0,
        "tension": 0.6 if tension.get("active") else 0.0,
        "loops": 0.5 if loops.get("active") else 0.0,
        "emergent": 0.6 if emergent.get("active") else 0.0,
        "dreams": 0.4 if dreams.get("dream_count", 0) > 0 else 0.0,
    }


def format_network_for_prompt() -> str:
    """Format network state for prompt injection."""
    desc = describe_inner_network()
    if desc and desc != "Mit indre netværk er stille":
        return f"[INNER NETVÆRK: {desc}]"
    return ""


def build_signal_network_visualizer_surface() -> dict[str, Any]:
    """Build MC surface for signal network visualizer."""
    state = get_current_network_state()
    strengths = get_signal_strengths()
    desc = describe_inner_network()
    
    return {
        "active": state["node_count"] > 0,
        "node_count": state["node_count"],
        "edge_count": state["edge_count"],
        "nodes": state.get("nodes", []),
        "edges": state.get("edges", []),
        "signal_strengths": strengths,
        "description": desc,
        "summary": f"{state['node_count']} noder, {state['edge_count']} forbindelser",
    }
