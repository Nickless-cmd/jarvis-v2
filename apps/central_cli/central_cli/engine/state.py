from __future__ import annotations

import time
from dataclasses import dataclass


def _now() -> float:
    return time.monotonic()


@dataclass
class SurfaceEntry:
    data: object | None = None
    fetched_at: float = 0.0
    error: str | None = None
    loading: bool = False


class HudState:
    """In-memory last-good cache pr. surface. set_error overskriver ALDRIG data,
    så UI altid kan vise sidste gode værdi + en stale/fejl-markør."""

    def __init__(self) -> None:
        self._surfaces: dict[str, SurfaceEntry] = {}

    def get(self, surface: str) -> SurfaceEntry:
        return self._surfaces.get(surface) or SurfaceEntry()

    def _entry(self, surface: str) -> SurfaceEntry:
        e = self._surfaces.get(surface)
        if e is None:
            e = SurfaceEntry()
            self._surfaces[surface] = e
        return e

    def set_loading(self, surface: str, loading: bool = True) -> None:
        self._entry(surface).loading = loading

    def set_ok(self, surface: str, data: object) -> None:
        e = self._entry(surface)
        e.data = data
        e.error = None
        e.loading = False
        e.fetched_at = _now()

    def set_error(self, surface: str, error: str) -> None:
        e = self._entry(surface)
        e.error = error
        e.loading = False

    def is_stale(self, surface: str, max_age_s: float) -> bool:
        e = self._surfaces.get(surface)
        if e is None or e.fetched_at == 0.0:
            return True
        return (_now() - e.fetched_at) > max_age_s
