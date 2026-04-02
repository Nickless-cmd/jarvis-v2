from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Callable, Iterator, TypeVar


_T = TypeVar("_T")
_CACHE: ContextVar[dict[object, object] | None] = ContextVar(
    "runtime_surface_cache",
    default=None,
)


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