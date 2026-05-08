"""EventContext — ContextVar holding the current parent event_id.

Producers (tool_router, agentic_round, channel-handlers) sætter context
før de dispatcher arbejde til services. Services kalder event_bus.publish()
som normalt; bus læser context auto via get_current_event() og bruger
den som default for caused_by hvis ikke eksplicit angivet.

Contextvars er thread-local + asyncio-safe — hver request/koroutine får
sin egen value uden interference.
"""
from __future__ import annotations

import contextlib
import contextvars

_current_event_context: contextvars.ContextVar[int | None] = contextvars.ContextVar(
    "current_event_context",
    default=None,
)


def set_current_event(event_id: int | None) -> contextvars.Token:
    """Set parent-event-id for the current dispatch scope.

    Returns Token to use with _current_event_context.reset() later.
    Prefer with_event_context() helper for cleanest pattern.
    """
    return _current_event_context.set(event_id)


def get_current_event() -> int | None:
    """Return current parent-event-id, or None if none active."""
    return _current_event_context.get()


@contextlib.contextmanager
def with_event_context(event_id: int | None):
    """Context manager that sets and reliably resets EventContext.

    Usage:
        with with_event_context(parent_event_id):
            do_work()  # any publish() inside picks up parent automatically
    """
    token = _current_event_context.set(event_id)
    try:
        yield
    finally:
        _current_event_context.reset(token)
