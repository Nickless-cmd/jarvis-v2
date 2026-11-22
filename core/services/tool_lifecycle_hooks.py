"""Opt-in interception around model-initiated tool execution.

Hooks are process-local and disabled until ``set_enabled(True)`` is called.
An ordinary hook failure is observable but cannot break the tool call.  A
hook blocks only by returning ``HookDecision.block(...)`` from ``before_tool``.
"""
from __future__ import annotations

from dataclasses import dataclass
import logging
from threading import RLock
from typing import Any, Callable, Protocol

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class HookDecision:
    blocked: bool = False
    reason: str = ""

    @classmethod
    def block(cls, reason: str) -> "HookDecision":
        return cls(blocked=True, reason=str(reason or "blocked by lifecycle hook"))


class ToolLifecycleHook(Protocol):
    def before_tool(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> HookDecision | None: ...

    def after_tool(
        self, tool_name: str, arguments: dict[str, Any], result: dict[str, Any]
    ) -> None: ...


_lock = RLock()
_hooks: list[ToolLifecycleHook] = []
_enabled = False


def register_hook(hook: ToolLifecycleHook) -> None:
    with _lock:
        if hook not in _hooks:
            _hooks.append(hook)


def unregister_hook(hook: ToolLifecycleHook) -> None:
    with _lock:
        if hook in _hooks:
            _hooks.remove(hook)


def clear_hooks() -> None:
    with _lock:
        _hooks.clear()


def set_enabled(enabled: bool) -> None:
    global _enabled
    with _lock:
        _enabled = bool(enabled)


def is_enabled() -> bool:
    with _lock:
        return _enabled


def _snapshot() -> tuple[ToolLifecycleHook, ...]:
    with _lock:
        return tuple(_hooks) if _enabled else ()


def execute_with_hooks(
    tool_name: str,
    arguments: dict[str, Any],
    execute: Callable[[], dict[str, Any]],
) -> dict[str, Any]:
    """Run ``execute`` between registered before/after callbacks."""
    active = _snapshot()
    for hook in active:
        try:
            decision = hook.before_tool(tool_name, arguments)
        except Exception as exc:  # hook boundary: third-party callback is untrusted
            logger.warning("tool lifecycle before-hook failed: %s", exc, exc_info=True)
            continue
        if isinstance(decision, HookDecision) and decision.blocked:
            return {
                "status": "error",
                "error": "tool_blocked_by_lifecycle_hook",
                "detail": decision.reason,
                "tool": tool_name,
            }

    result = execute()
    for hook in active:
        try:
            hook.after_tool(tool_name, arguments, result)
        except Exception as exc:  # hook boundary: result must survive callback failure
            logger.warning("tool lifecycle after-hook failed: %s", exc, exc_info=True)
    return result


__all__ = [
    "HookDecision", "ToolLifecycleHook", "clear_hooks", "execute_with_hooks",
    "is_enabled", "register_hook", "set_enabled", "unregister_hook",
]
