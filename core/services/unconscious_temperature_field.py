"""Unconscious temperature field — backwards-compat wrapper for Lag 10.

The keyword-based implementation that lived here is replaced by the
two-stream user_temperature_engine. This module preserves the public
function signatures so existing callers (prompt_contract, mission-control)
continue to work without changes.
"""
from __future__ import annotations

from typing import Any


def build_unconscious_temperature_hint() -> str | None:
    """Backwards-compat: returns heartbeat-formatted hint string or None.

    Internally delegates to user_temperature_engine.format_temperature_field_for_heartbeat.
    """
    try:
        from core.services.user_temperature_engine import (
            format_temperature_field_for_heartbeat,
        )
        out = format_temperature_field_for_heartbeat(workspace_id="default")
        return out or None
    except Exception:
        return None


def build_unconscious_temperature_field_surface(
    *, force_refresh: bool = False
) -> dict[str, Any]:
    """Backwards-compat: surface dict for Mission Control consumers.

    force_refresh is accepted but Phase 1 ignores it (the engine always
    returns whatever's most recent in DB).
    """
    try:
        from core.services.user_temperature_engine import get_active_field_surface
        return get_active_field_surface(
            workspace_id="default", force_refresh=force_refresh,
        )
    except Exception:
        return {
            "active": False,
            "enabled": False,
            "summary": "Temperature field error",
        }
