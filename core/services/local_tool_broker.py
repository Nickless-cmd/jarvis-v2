"""Local-tool broker (Path B — server-owned transcript, client-local execution).

The server owns the code-lane transcript and drives the agentic loop. When the loop
hits a tool_call, instead of executing server-side (or via the operator bridge), it
PAUSES: it emits the tool_call to the local jarvis-code client on the SSE stream and
waits here for the client to execute it locally and POST the result back to
``/chat/tool_results``. Correlated strictly by ``call_id`` (never position).

Coordination uses ``threading.Event`` so it works whether the visible run is a sync
generator running in a worker thread or an async coroutine (an async caller waits via
``asyncio.to_thread``). The endpoint's ``resolve`` is a fast, thread-safe set().

Durable-ish: the canonical transcript lives server-side in ``chat_sessions``, so a
dropped SSE / client disconnect times out the pending call (the run surfaces a typed
tool error and can be resumed from the transcript) — it never wedges the loop forever.

This module is intentionally standalone (no imports from ``visible_runs``) so it can be
unit-tested and wired in without touching the 7k-line run file.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

# Default: how long the server waits for the client to run one tool before giving up.
# Local coding tools are <5ms, but bash/pytest/large reads + approval prompts can take
# a while — generous, but bounded so a vanished client never wedges the run.
DEFAULT_TOOL_TIMEOUT_S = 300.0


@dataclass
class _Pending:
    event: threading.Event = field(default_factory=threading.Event)
    result: str | None = None
    is_error: bool = False
    session_id: str = ""
    name: str = ""
    created_at: float = field(default_factory=time.time)


# call_id -> _Pending. Module-level, single-process (CT105 runs one uvicorn worker).
_pending: dict[str, _Pending] = {}
_lock = threading.Lock()


def register(call_id: str, *, session_id: str, name: str = "") -> _Pending:
    """Register a tool_call the server is about to hand to the local client.
    Returns the _Pending whose event the run will wait on."""
    p = _Pending(session_id=str(session_id or ""), name=str(name or ""))
    with _lock:
        _pending[str(call_id)] = p
    return p


def wait(call_id: str, pending: _Pending, timeout: float = DEFAULT_TOOL_TIMEOUT_S) -> tuple[str | None, bool]:
    """Block until the client resolves ``call_id`` or ``timeout`` elapses.
    Returns (result, is_error). On timeout: (None, True). Always cleans up the entry."""
    got = pending.event.wait(timeout)
    with _lock:
        _pending.pop(str(call_id), None)
    if not got:
        return None, True
    return pending.result, pending.is_error


def resolve(call_id: str, content: str, *, is_error: bool = False) -> bool:
    """Called by POST /chat/tool_results. Deliver the client's result to the waiting run.
    Returns True if a live pending call was resolved, False if unknown/already-done."""
    with _lock:
        p = _pending.get(str(call_id))
        if p is None or p.event.is_set():
            return False
        p.result = str(content or "")
        p.is_error = bool(is_error)
        p.event.set()
        return True


def pending_call_ids(session_id: str) -> list[str]:
    """The call_ids currently awaiting a client result for a session (diagnostics)."""
    sid = str(session_id or "")
    with _lock:
        return [cid for cid, p in _pending.items() if p.session_id == sid and not p.event.is_set()]


def cancel_session(session_id: str) -> int:
    """Fail all pending calls for a session (e.g. client disconnected). Returns count.
    Sets an error result so the waiting run unblocks with a typed failure, not a hang."""
    sid = str(session_id or "")
    n = 0
    with _lock:
        for cid, p in list(_pending.items()):
            if p.session_id == sid and not p.event.is_set():
                p.result = "[local tool aborted: client disconnected]"
                p.is_error = True
                p.event.set()
                n += 1
    return n
