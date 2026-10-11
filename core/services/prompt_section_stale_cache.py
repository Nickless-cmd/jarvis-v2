"""Kort stale-while-revalidate-cache til dyre, brugeruafhængige promptdele.

Kun snapshot-sektioner må bruge cachen. Transcript, den aktuelle brugerbesked,
relevans og memory-selection hører ikke hjemme her. En frisk værdi genbruges;
en lidt gammel værdi returneres straks mens én baggrundstråd opdaterer den.
"""
from __future__ import annotations

import contextvars
from dataclasses import dataclass
import threading
import time
from typing import Any, Callable


FRESH_TTL_S = 30.0
STALE_TTL_S = 300.0
MAX_ENTRIES = 128


@dataclass(frozen=True, slots=True)
class _Entry:
    stored_at: float
    value: Any


_entries: dict[tuple, _Entry] = {}
_inflight: set[tuple] = set()
_lock = threading.Lock()


def _default_spawn(callback: Callable[[], None]) -> None:
    threading.Thread(
        target=callback, name="prompt-section-refresh", daemon=True,
    ).start()


def _store(key: tuple, value: Any, *, stored_at: float | None = None) -> None:
    with _lock:
        if len(_entries) >= MAX_ENTRIES and key not in _entries:
            oldest = min(_entries, key=lambda item: _entries[item].stored_at)
            _entries.pop(oldest, None)
        _entries[key] = _Entry(
            time.monotonic() if stored_at is None else stored_at, value,
        )


def get_or_refresh(
    key: tuple,
    builder: Callable[[], Any],
    *,
    now: float | None = None,
    spawn: Callable[[Callable[[], None]], None] | None = None,
) -> Any:
    """Hent snapshot; refresh stale data uden at blokere den synlige lane."""
    checked_at = time.monotonic() if now is None else now
    with _lock:
        entry = _entries.get(key)
    if entry is None or checked_at - entry.stored_at >= STALE_TTL_S:
        value = builder()
        _store(key, value, stored_at=checked_at)
        return value
    if checked_at - entry.stored_at < FRESH_TTL_S:
        return entry.value

    with _lock:
        should_refresh = key not in _inflight
        if should_refresh:
            _inflight.add(key)
    if should_refresh:
        caller_context = contextvars.copy_context()

        def _refresh() -> None:
            try:
                value = caller_context.run(builder)
                _store(key, value)
            except Exception:
                # Det sidste gode snapshot er bedre end at gøre en berigelse
                # load-bearing. Næste tur prøver igen.
                pass
            finally:
                with _lock:
                    _inflight.discard(key)

        try:
            (spawn or _default_spawn)(_refresh)
        except Exception:
            with _lock:
                _inflight.discard(key)
    return entry.value


def context_key(
    section: str, *, session_id: str | None = None, variant: str = "",
) -> tuple:
    """Isolér snapshots pr. identitet/workspace/session og promptvariant."""
    try:
        from core.identity.workspace_context import (
            current_role, current_user_id, current_workspace_name,
        )
        workspace = str(current_workspace_name() or "")
        user_id = str(current_user_id() or "")
        role = str(current_role() or "")
    except Exception:
        workspace = user_id = role = ""
    return (section, workspace, user_id, role, str(session_id or ""), variant)


def clear() -> None:
    with _lock:
        _entries.clear()
        _inflight.clear()
