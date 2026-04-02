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
            value = copy.deepcopy(cached[1])
            if cache is not None:
                cache[key] = value
            return value  # type: ignore[return-value]

    value = builder()
    with _TIMED_CACHE_LOCK:
        _TIMED_CACHE[key] = (time.monotonic() + ttl_seconds, copy.deepcopy(value))
    if cache is not None:
        cache[key] = value
    return value