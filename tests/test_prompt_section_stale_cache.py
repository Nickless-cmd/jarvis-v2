from __future__ import annotations

from core.services import prompt_section_stale_cache as cache


def test_miss_builds_once_and_fresh_hit_reuses_value():
    cache.clear()
    calls: list[int] = []

    def build():
        calls.append(1)
        return "v1"

    assert cache.get_or_refresh(("u", "inner"), build, now=10) == "v1"
    assert cache.get_or_refresh(("u", "inner"), build, now=20) == "v1"
    assert calls == [1]


def test_stale_hit_returns_immediately_and_refreshes_once_in_background():
    cache.clear()
    scheduled: list[object] = []
    values = iter(("v1", "v2"))
    key = ("u", "continuity")

    assert cache.get_or_refresh(key, lambda: next(values), now=10) == "v1"
    assert cache.get_or_refresh(
        key, lambda: next(values), now=50, spawn=scheduled.append,
    ) == "v1"
    assert cache.get_or_refresh(
        key, lambda: next(values), now=51, spawn=scheduled.append,
    ) == "v1"
    assert len(scheduled) == 1

    scheduled[0]()
    assert cache.get_or_refresh(key, lambda: "wrong", now=52) == "v2"


def test_failed_background_refresh_keeps_last_good_value():
    cache.clear()
    scheduled: list[object] = []
    key = ("u", "cognitive")
    assert cache.get_or_refresh(key, lambda: "good", now=1) == "good"

    def fail():
        raise RuntimeError("nope")

    assert cache.get_or_refresh(key, fail, now=40, spawn=scheduled.append) == "good"
    scheduled[0]()
    assert cache.get_or_refresh(key, lambda: "wrong", now=41) == "good"
