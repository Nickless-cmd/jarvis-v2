"""Body Memory — Jarvis' physical sensation snapshots."""
from __future__ import annotations
import random
from datetime import UTC, datetime
from typing import Any

_body_snapshots: list[dict] = []

def record_body_snapshot(context: str, sensation: str = None, intensity: float = None):
    global _body_snapshots
    sensation = sensation or random.choice(["varm", "kold", "tryk", "prikken"])
    intensity = intensity or random.uniform(0.3, 0.9)
    _body_snapshots.append({
        "context": context,
        "sensation": sensation,
        "intensity": intensity,
        "timestamp": datetime.now(UTC).isoformat(),
    })

def describe_body_memory() -> str:
    if not _body_snapshots:
        return ""
    latest = _body_snapshots[-1]
    return f"Jeg mindes en {latest['sensation']} fornemmelse fra {latest['context']}"

def format_body_for_prompt() -> str:
    desc = describe_body_memory()
    if desc:
        return f"[KROP: {desc}]"
    return ""

def reset_body_memory():
    global _body_snapshots
    _body_snapshots = []

def build_body_memory_surface():
    return {
        "active": len(_body_snapshots) > 0,
        "snapshot_count": len(_body_snapshots),
        "latest": _body_snapshots[-1] if _body_snapshots else None,
        "summary": describe_body_memory() or "Ingen kropslig hukommelse",
    }
