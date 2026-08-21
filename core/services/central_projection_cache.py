"""Kortlivet cache for Centralens projektioner — så polling ikke koster.

Målt 21. aug 2026 på CT105, et 5-minutters vindue i TOMGANG (intet aktivt run):

    /central/costs-daily   359ms x 192 kald = 68,9s serverarbejde   (70%)
    /central/realtime       78ms x 310 kald = 24,1s                 (25%)
    de ti andre endpoints tilsammen        =  5,0s                  ( 5%)

98,1s arbejde pr. 300s = 32,7% af én kerne brugt konstant på at besvare de
samme spørgsmål igen og igen. Central CLI stod for 63% af trafikken, jarvis-desk
for 34%.

`costs-daily` var værst af to grunde. Den kørte FIRE forespørgsler pr. kald
(daily_cost_summary 110ms + this_week_cost 131ms + today_cost 57ms +
telemetry_summary 45ms), hver med fuld SCAN over 480.705 rækker i `costs` —
der var intet indeks på `created_at`. Og den **skrev** til databasen via
`absorb()` ved hvert eneste GET, hvilket lagde write-locks på den 2,1GB WAL-DB
som runtime-processen også bruger (jf. eventbus_latency_spikes).

Oveni kaldte Central CLI den dobbelt så ofte som naboerne: `cost_today()` og
daily-serien i `datasource.py` henter begge det samme endpoint pr. refresh.

## Hvorfor in-process og ikke shared_cache

`shared_cache` er SQLite-backed, fordi den blev bygget da api'en kørte
`--workers 4` og in-memory dicts blev partitioneret pr. worker. CT105 kører i
dag `--workers 1`, og pointen her er netop at UNDGÅ at røre databasen — en
SQLite-læsning pr. poll ville bevare det problem vi fjerner. Skrues workers op
igen, degraderer denne cache nådigt: hitraten falder til ~1/N, hvilket stadig
er markant bedre end ingen cache.

## Ærlighed frem for friskhed-illusion

Et cachet svar er ældre end kaldet antyder. `cached()` returnerer derfor også
alderen, så endpointet kan lægge `cache_age_ms` i svaret og HUD'en kan vise
hvor gammelt tallet er, i stedet for at lade som om det er dette sekund.

Cachen er et plaster, ikke kuren. Kuren er push i stedet for poll — Centralen
burde abonnere på ændringer frem for at spørge fire gange i sekundet.
"""
from __future__ import annotations

import threading
import time
from typing import Any, Callable, TypeVar

T = TypeVar("T")

_LOCK = threading.Lock()
_ENTRIES: dict[str, tuple[float, Any]] = {}
_STATS = {"hits": 0, "misses": 0}


def cached(key: str, ttl_s: float, producer: Callable[[], T]) -> tuple[T, float]:
    """Returnér ``(værdi, alder_i_sekunder)`` — beregn kun hvis TTL er udløbet.

    ``producer`` kaldes UDEN for låsen, så et langsomt kald (costs-daily er
    343ms) ikke blokerer andre nøgler. Prisen er at to samtidige misses på
    samme nøgle begge kan beregne; det er harmløst her (producenterne er rene
    læsninger) og at holde låsen under 343ms DB-arbejde ville være værre.

    Producent-fejl caches ALDRIG — en exception propagerer til kalderen, som
    allerede har sine egne self-safe fallbacks. Ellers ville et enkelt uheld
    fryse et tomt svar fast i hele TTL'en.
    """
    now = time.monotonic()
    with _LOCK:
        entry = _ENTRIES.get(key)
        if entry is not None and (now - entry[0]) < ttl_s:
            _STATS["hits"] += 1
            return entry[1], now - entry[0]
        _STATS["misses"] += 1

    value = producer()
    with _LOCK:
        _ENTRIES[key] = (time.monotonic(), value)
    return value, 0.0


def invalidate(prefix: str = "") -> int:
    """Smid cachede værdier væk. Tom prefix rydder alt. Returnerer antal fjernet."""
    with _LOCK:
        keys = [k for k in _ENTRIES if k.startswith(prefix)]
        for k in keys:
            _ENTRIES.pop(k, None)
        return len(keys)


def stats() -> dict[str, Any]:
    """Hits/misses/hitrate — så effekten kan aflæses i stedet for antages."""
    with _LOCK:
        hits, misses = _STATS["hits"], _STATS["misses"]
        total = hits + misses
        return {
            "hits": hits,
            "misses": misses,
            "hit_rate": round(hits / total, 3) if total else 0.0,
            "keys": len(_ENTRIES),
        }
