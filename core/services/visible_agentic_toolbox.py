"""Canonical tool-array builder for visible agentic follow-up rounds.

The first pass already builds its array through
``turens_vaerktoejer.vaerktoejer_for_turen``.  The follow-up loop used to
duplicate router + session-pin assembly inside ``visible_runs`` and read the
tool scope implicitly from a ContextVar.  An async-generator/thread boundary
can lose that ambient value; production then alternated between the scoped
catalogue (about 84 tools after the pin) and the unscoped catalogue (98-107).

This small boundary takes the run's persisted scope explicitly and delegates
selection to the same builder as the first pass.  One turn therefore has one
toolbox construction rule instead of two subtly different ones.
"""
from __future__ import annotations

from typing import Any, Callable


def build_agentic_toolbox(
    run: Any,
    *,
    tool_scope: str,
    get_definitions: Callable[..., list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Return the pinned toolbox for follow-up rounds using explicit scope."""
    from core.services.turens_vaerktoejer import vaerktoejer_for_turen

    scope = str(tool_scope or "").strip().lower()
    alle = get_definitions(scope=scope)
    return vaerktoejer_for_turen(
        alle,
        user_message=str(getattr(run, "user_message", "") or ""),
        session_id=getattr(run, "session_id", None),
        lane="autonomous" if bool(getattr(run, "autonomous", False)) else "visible",
        run_id=str(getattr(run, "run_id", "") or ""),
    )
