"""Kort TTL-cache til poll-endpoints: samme svar til samme spoerger inden for et par sekunder.

Maalt 14/11-2026 (py-spy, 30 s): ~890 req/min mod API'et, 85 % fra én klient, og
/agents/contract/feed alene stod for ~58 % af CPU'en — hvert kald bygger feedet forfra.
Cachen tager toppen af stormen uden at aendre hvad en klient ser ud over et par sekunders
alder; lokale skrivninger kalder ``invalidate`` og ses med det samme.

* ``get_or_compute`` serialiserer pr. noegle: ti samtidige polls giver EN beregning.
* Svaret gives ud som kopi — en kalder der roerer ved det kan ikke forurene cachen.
* En fejl caches aldrig.
* En ``invalidate`` midt i en beregning kasserer resultatet (det var bygget af gammel tilstand).
* ``ttl_s <= 0`` slaar cachen fra (tests, eller en nodbremse).
"""
from __future__ import annotations

import copy
import threading
import time
from collections.abc import Callable, Hashable
from typing import Any


class ShortTTLCache:
    def __init__(self, ttl_s: float, clock: Callable[[], float] = time.monotonic) -> None:
        self.ttl_s = ttl_s
        self._clock = clock
        self._lock = threading.Lock()
        self._entries: dict[Hashable, tuple[float, Any]] = {}
        self._key_locks: dict[Hashable, threading.Lock] = {}
        self._generation = 0

    def get_or_compute(self, key: Hashable, fn: Callable[[], Any]) -> Any:
        if self.ttl_s <= 0:
            return fn()
        with self._lock:
            key_lock = self._key_locks.setdefault(key, threading.Lock())
        with key_lock:
            hit = self._fresh(key)
            if hit is not None:
                return copy.deepcopy(hit[0])
            with self._lock:
                started_gen = self._generation
            value = fn()
            with self._lock:
                if started_gen == self._generation:
                    self._entries[key] = (self._clock(), value)
            return copy.deepcopy(value)

    def _fresh(self, key: Hashable) -> tuple[Any] | None:
        with self._lock:
            entry = self._entries.get(key)
        if entry is None or self._clock() - entry[0] >= self.ttl_s:
            return None
        return (entry[1],)

    def invalidate(self, key: Hashable | None = None) -> None:
        with self._lock:
            self._generation += 1
            if key is None:
                self._entries.clear()
            else:
                self._entries.pop(key, None)
