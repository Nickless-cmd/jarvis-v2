"""Governed kill-switch for session-persistence boot-reconciler. Default OFF (shadow).

Mirror of ``structured_content_flag.py`` but **default OFF**: until an owner
explicitly flips ``session_persistence`` ON in runtime-state, the boot-reconciler
runs in observe-only mode (counts what WOULD be reconciled, writes nothing).

Flip ON (owner) → the reconciler flips forladte ``running`` crash-zombies to
``interrupted`` so the existing interruption_prompt_section resumes them next turn.
Read-fejl → False (shadow er den sikre default; kill-switch kræver et EKSPLICIT on).
"""
from __future__ import annotations

_STATE_KEY = "session_persistence"

_ON_VALUES = {"on", "1", "true", "yes"}


def _read_flag() -> object | None:
    """Læs rå flag-værdi fra runtime-state. None = usat."""
    from core.runtime.db import get_runtime_state_value
    return get_runtime_state_value(_STATE_KEY)


def session_persistence_enabled() -> bool:
    """True KUN når eksplicit slået til ('on'/'1'/'true'/'yes'). Usat eller
    læse-fejl → False (default OFF = shadow, ejerens valg indtil verificeret)."""
    try:
        raw = _read_flag()
    except Exception:
        return False
    if raw is None:
        return False
    return str(raw).strip().lower() in _ON_VALUES
