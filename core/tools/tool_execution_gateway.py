"""Outer gateway for schema checks, lifecycle interception and observation."""
from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)


def execute_tool_call(
    name: str,
    arguments: dict[str, Any],
    *,
    execute: Callable[[], dict[str, Any]],
    internal: bool,
) -> dict[str, Any]:
    """Run the pre-dispatch contract and the post-dispatch observation once."""
    try:
        from core.services import tool_contract_shadow as contract_shadow

        hard = [breach for breach in contract_shadow.observe(name, arguments) if breach.haard]
        if hard and contract_shadow.haandhaever():
            from core.tools.tool_schema_contract import afvisning

            rejected = afvisning(name, hard)
            if not internal:
                from core.tools.tool_call_observation import observe_tool_call

                observe_tool_call(name, arguments, rejected)
            return rejected
    except Exception:
        # The schema shadow is measurement infrastructure and must not take
        # down execution. Enforcement rejections above still return normally.
        pass

    if internal:
        return execute()

    # Brugerdefinerede shell-hooks (config/tool_hooks.json). Indlæses her og
    # ikke ved opstart, så de virker i enhver proces der udfører tool-kald —
    # en CLI, en test, en genstartet worker — uden et registreringssted nogen
    # skal huske. Et kald uden config er et flag-tjek og koster intet.
    try:
        from core.services import tool_shell_hooks

        tool_shell_hooks.ensure_loaded()
    except Exception:  # en defekt config må ikke gøre tools ubrugelige
        logger.warning("kunne ikke indlæse tool-hooks", exc_info=True)

    from core.services.tool_lifecycle_hooks import execute_with_hooks

    result = execute_with_hooks(name, arguments, execute)
    from core.tools.tool_call_observation import observe_tool_call

    observe_tool_call(name, arguments, result)
    return result


def execute_force_tool_call(
    name: str,
    arguments: dict[str, Any],
    *,
    execute: Callable[[], dict[str, Any]],
    internal: bool,
) -> dict[str, Any]:
    """Lifecycle and observation gateway for the autonomous/approved path."""
    if internal:
        return execute()

    try:
        from core.services import tool_shell_hooks

        tool_shell_hooks.ensure_loaded()
    except Exception:  # en defekt config må ikke gøre tools ubrugelige
        logger.warning("kunne ikke indlæse tool-hooks", exc_info=True)

    from core.services.tool_lifecycle_hooks import execute_with_hooks

    result = execute_with_hooks(name, arguments, execute)
    from core.tools.tool_call_observation import observe_tool_call

    try:
        observe_tool_call(name, arguments, result)
    except Exception:
        # Preserve force-path self-safety: usage telemetry is not execution.
        logger.warning("force tool observation failed for %s", name, exc_info=True)
    return result


__all__ = ["execute_force_tool_call", "execute_tool_call"]
