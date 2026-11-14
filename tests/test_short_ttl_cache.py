"""ShortTTLCache: kort levetid, per-noegle serialisering, kopi ud, fejl caches aldrig."""
from __future__ import annotations

import threading

import pytest

from core.services.short_ttl_cache import ShortTTLCache


class Clock:
    def __init__(self) -> None:
        self.t = 100.0

    def __call__(self) -> float:
        return self.t


def _cache(ttl: float = 3.0) -> tuple[ShortTTLCache, Clock]:
    clk = Clock()
    return ShortTTLCache(ttl_s=ttl, clock=clk), clk


def test_second_call_within_ttl_reuses_value():
    c, clk = _cache()
    calls: list[int] = []

    def fn():
        calls.append(1)
        return {"n": len(calls)}

    assert c.get_or_compute("a", fn) == {"n": 1}
    clk.t += 2.9
    assert c.get_or_compute("a", fn) == {"n": 1}
    assert len(calls) == 1


def test_value_expires_at_ttl_boundary():
    c, clk = _cache()
    n = iter(range(1, 10))
    c.get_or_compute("a", lambda: next(n))
    clk.t += 3.0                       # praecis TTL: udloebet
    assert c.get_or_compute("a", lambda: next(n)) == 2


def test_keys_are_independent():
    c, _ = _cache()
    assert c.get_or_compute("a", lambda: "A") == "A"
    assert c.get_or_compute("b", lambda: "B") == "B"
    assert c.get_or_compute("a", lambda: "X") == "A"


def test_invalidate_one_key_leaves_the_other():
    c, _ = _cache()
    c.get_or_compute("a", lambda: "A1")
    c.get_or_compute("b", lambda: "B1")
    c.invalidate("a")
    assert c.get_or_compute("a", lambda: "A2") == "A2"
    assert c.get_or_compute("b", lambda: "B2") == "B1"


def test_invalidate_all():
    c, _ = _cache()
    c.get_or_compute("a", lambda: "A1")
    c.get_or_compute("b", lambda: "B1")
    c.invalidate()
    assert c.get_or_compute("a", lambda: "A2") == "A2"
    assert c.get_or_compute("b", lambda: "B2") == "B2"


def test_caller_mutation_does_not_leak_into_cache():
    c, _ = _cache()
    first = c.get_or_compute("a", lambda: {"cards": [1, 2]})
    first["cards"].append(99)
    assert c.get_or_compute("a", lambda: {"cards": []}) == {"cards": [1, 2]}


def test_exception_is_not_cached():
    c, _ = _cache()

    def boom():
        raise RuntimeError("db laast")

    with pytest.raises(RuntimeError):
        c.get_or_compute("a", boom)
    assert c.get_or_compute("a", lambda: "ok") == "ok"


def test_zero_ttl_disables_caching():
    c, _ = _cache(ttl=0)
    n = iter(range(1, 10))
    assert c.get_or_compute("a", lambda: next(n)) == 1
    assert c.get_or_compute("a", lambda: next(n)) == 2


def test_concurrent_callers_share_one_computation():
    c, _ = _cache()
    started = threading.Event()
    release = threading.Event()
    calls: list[int] = []

    def slow():
        calls.append(1)
        started.set()
        release.wait(5)
        return "v"

    out: list[str] = []
    ts = [threading.Thread(target=lambda: out.append(c.get_or_compute("a", slow))) for _ in range(6)]
    ts[0].start()
    assert started.wait(5)
    for t in ts[1:]:
        t.start()
    release.set()
    for t in ts:
        t.join(5)
    assert out == ["v"] * 6
    assert len(calls) == 1


def test_invalidate_during_compute_discards_the_stale_result():
    """En skrivning midt i en genberegning maa ikke efterlade den gamle vaerdi som frisk."""
    c, _ = _cache()
    results = iter(["gammel", "ny"])

    def fn():
        v = next(results)
        if v == "gammel":
            c.invalidate("a")          # skrivningen lander mens vi beregner
        return v

    assert c.get_or_compute("a", fn) == "gammel"      # kalderen faar sit svar
    assert c.get_or_compute("a", fn) == "ny"          # men det er ikke gemt som frisk
