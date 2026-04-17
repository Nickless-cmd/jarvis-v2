"""Memory decay daemon — selective forgetting and re-discovery.

Runs daily. Reduces salience of all private brain records.
Records that are frequently referenced (reinforced) retain their salience.
Records with very low salience may be surfaced in thought stream (re-discovery).
Jarvis can actively hold-fast a memory via MC to prevent decay.
"""
from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta

from core.eventbus.bus import event_bus
from core.runtime.db import (
    decay_private_brain_records_by_domain,
    get_salient_private_brain_records,
    list_private_brain_records,
    update_private_brain_record_salience,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_CADENCE_HOURS = 24
_DECAY_RATE = 0.05               # default salience lost per daily decay cycle (fallback)
_REDISCOVERY_THRESHOLD = 0.12    # records below this may be rediscovered
_REDISCOVERY_PROBABILITY = 0.25  # chance per tick to surface one near-forgotten record
_REDISCOVERY_BUFFER_MAX = 5

# Per-domain decay rates (salience lost per 24h cycle).
# Half-life reference: rate ≈ ln(2) / half_life_days
#   identity      → 30-day half-life  → 0.023
#   code_pattern  → 23-day half-life  → 0.030
#   social        →  7-day half-life  → 0.099
#   debug_context →  2-day half-life  → 0.347
#   (empty / unknown → fallback _DECAY_RATE = 0.05, ~14-day half-life)
DOMAIN_DECAY_RATES: dict[str, float] = {
    "identity":      0.023,
    "code_pattern":  0.030,
    "social":        0.099,
    "debug_context": 0.347,
}

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

_last_decay_at: datetime | None = None
_last_rediscovery: str = ""
_rediscovery_buffer: list[dict] = []

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def tick_memory_decay_daemon() -> dict:
    """Run daily decay cycle. Returns {decayed, records_updated}."""
    global _last_decay_at

    now = datetime.now(UTC)

    # Cadence gate: 24h
    if _last_decay_at is not None:
        if (now - _last_decay_at) < timedelta(hours=_CADENCE_HOURS):
            return {"decayed": False}

    domain_counts: dict[str, int] = {}
    try:
        domain_counts = decay_private_brain_records_by_domain(
            DOMAIN_DECAY_RATES,
            default_rate=_DECAY_RATE,
        )
    except Exception:
        pass
    updated = sum(domain_counts.values())

    _last_decay_at = now

    # Maybe trigger re-discovery on same cycle
    try:
        maybe_rediscover()
    except Exception:
        pass

    return {"decayed": True, "records_updated": updated, "domain_counts": domain_counts}


def hold_fast(record_id: str) -> None:
    """Prevent a memory from decaying by resetting its salience to 1.0."""
    update_private_brain_record_salience(record_id, 1.0)


def maybe_rediscover(force: bool = False) -> dict | None:
    """Possibly surface a near-forgotten memory into the re-discovery buffer.

    Returns the record if one was surfaced, else None.
    """
    global _last_rediscovery, _rediscovery_buffer

    if not force and random.random() > _REDISCOVERY_PROBABILITY:
        return None

    try:
        # Get records near the forgetting threshold
        candidates = list_private_brain_records(limit=50, status="active")
        near_forgotten = [
            r for r in candidates
            if 0.01 < float(r.get("salience", 1.0)) <= _REDISCOVERY_THRESHOLD
        ]
    except Exception:
        return None

    if not near_forgotten:
        return None

    record = random.choice(near_forgotten)
    summary = record.get("summary", "")
    _last_rediscovery = summary
    _rediscovery_buffer.insert(0, record)
    if len(_rediscovery_buffer) > _REDISCOVERY_BUFFER_MAX:
        _rediscovery_buffer = _rediscovery_buffer[:_REDISCOVERY_BUFFER_MAX]

    try:
        event_bus.publish(
            "memory.rediscovered",
            {"record_id": record.get("record_id", ""), "summary": summary[:80]},
        )
    except Exception:
        pass

    return record


def get_latest_rediscovery() -> str:
    return _last_rediscovery


def build_memory_decay_surface() -> dict:
    return {
        "last_decay_at": _last_decay_at.isoformat() if _last_decay_at else "",
        "last_rediscovery": _last_rediscovery,
        "rediscovery_buffer": [
            {"record_id": r.get("record_id", ""), "summary": r.get("summary", "")[:80]}
            for r in _rediscovery_buffer
        ],
    }
