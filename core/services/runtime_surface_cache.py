from __future__ import annotations

import copy
import threading
import time
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Callable, Iterator, TypeVar


_T = TypeVar("_T")
_CACHE: ContextVar[dict[object, object] | None] = ContextVar(
    "runtime_surface_cache",
    default=None,
)
_TIMED_CACHE_LOCK = threading.Lock()
_TIMED_CACHE: dict[object, tuple[float, object]] = {}


@contextmanager
def runtime_surface_cache() -> Iterator[dict[object, object]]:
    cache = _CACHE.get()
    if cache is not None:
        yield cache
        return

    created: dict[object, object] = {}
    token = _CACHE.set(created)
    try:
        yield created
    finally:
        _CACHE.reset(token)


def get_cached_runtime_surface(key: object, builder: Callable[[], _T]) -> _T:
    cache = _CACHE.get()
    if cache is None:
        return builder()
    if key not in cache:
        cache[key] = builder()
    return cache[key]  # type: ignore[return-value]


def peek_cached_runtime_surface(key: object) -> object | None:
    cache = _CACHE.get()
    if cache is None:
        return None
    return cache.get(key)


def get_timed_runtime_surface(
    key: object,
    ttl_seconds: float,
    builder: Callable[[], _T],
) -> _T:
    cache = _CACHE.get()
    if cache is not None and key in cache:
        return cache[key]  # type: ignore[return-value]

    now = time.monotonic()
    with _TIMED_CACHE_LOCK:
        cached = _TIMED_CACHE.get(key)
        if cached and cached[0] > now:
            # 2026-05-17 perf fix: ingen deepcopy på read.
            # Surface'en er 140KB+; deepcopy ved hver hit kostede ~1.6ms/call
            # = ~20% af runtime-worker CPU under load (py-spy sample).
            # Kontrakt: callers MÅ IKKE mutere returværdien. Audit:
            # alle produktions-call-sites (mission_control routes,
            # runtime_awareness_signal_tracking) læser kun.
            value = cached[1]
            if cache is not None:
                cache[key] = value
            return value  # type: ignore[return-value]

    # Deepcopy på STORE beskytter cachen mod at builder returnerer en
    # reference til ekstern muterbar state.
    value = builder()
    stored = copy.deepcopy(value)
    with _TIMED_CACHE_LOCK:
        _TIMED_CACHE[key] = (time.monotonic() + ttl_seconds, stored)
    if cache is not None:
        cache[key] = stored
    return stored  # type: ignore[return-value]


def invalidate_timed_runtime_surface(*keys_or_prefixes: object) -> int:
    """Drop matchende entries fra den KRYDS-TUR TIMED-cache (2026-06-30).

    Den 60s-TTL-cache er rigtig for surfaces der KUN ændrer sig langsomt — men
    forkert for per-tur-surfaces (tool-godkendelser, proactive-loop-signaler) der
    ændrer sig within-turn. Uden invalidering serverede den stale data i op til
    60s (verbal/MC tool-approval reflekteredes ikke). Kald denne på ENHVER mutation
    af den underliggende state. Matcher eksakt key ELLER en tuple-key hvis dens
    FØRSTE element == et givet prefix (proactive-loop-keyen er (navn, limit)).
    Returnerer antal droppede entries. Self-safe-mønster: kald-stedet wrapper i try."""
    dropped = 0
    with _TIMED_CACHE_LOCK:
        for target in keys_or_prefixes:
            for k in list(_TIMED_CACHE.keys()):
                if k == target or (isinstance(k, tuple) and k and k[0] == target):
                    _TIMED_CACHE.pop(k, None)
                    dropped += 1
    return dropped