"""Decision Ghosts — paths not taken."""
from __future__ import annotations
import random
from typing import Any

_rejected_paths: list[dict] = []

def record_rejected_path(decision: str, reason: str, alternative: str):
    global _rejected_paths
    _rejected_paths.append({
        "decision": decision,
        "reason": reason,
        "alternative": alternative,
        "regret_potential": random.uniform(0.1, 0.6),
    })

def describe_ghost_decision() -> str:
    if not _rejected_paths:
        return ""
    top = max(_rejected_paths, key=lambda x: x["regret_potential"])
    return f"Af og til tænker jeg: Hvis jeg havde valgt {top['alternative']} i stedet for..."

def format_decision_ghost_for_prompt() -> str:
    desc = describe_ghost_decision()
    if desc:
        return f"[BESLUTNINGSSPØGELSE: {desc}]"
    return ""

def reset_decision_ghosts():
    global _rejected_paths
    _rejected_paths = []

def build_decision_ghosts_surface():
    return {
        "active": len(_rejected_paths) > 0,
        "rejected_count": len(_rejected_paths),
        "top_regret": max((r for r in _rejected_paths), key=lambda x: x["regret_potential"]) if _rejected_paths else None,
        "summary": describe_ghost_decision() or "Ingen spøgelser af beslutninger",
    }
