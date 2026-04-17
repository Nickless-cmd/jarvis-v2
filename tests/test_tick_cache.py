"""Tests for tick-scoped in-memory cache."""
from __future__ import annotations


class TestTickCacheInactive:
    def test_get_returns_none_when_inactive(self) -> None:
        from core.services import tick_cache

        tick_cache._cache = None
        assert tick_cache.get("anything") is None

    def test_set_is_noop_when_inactive(self) -> None:
        from core.services import tick_cache

        tick_cache._cache = None
        tick_cache.set("key", "value")
        assert tick_cache.get("key") is None


class TestTickCacheLifecycle:
    def test_start_activates_cache(self) -> None:
        from core.services import tick_cache

        tick_cache._cache = None
        tick_cache.start_tick()
        assert tick_cache._cache is not None
        tick_cache.end_tick()

    def test_end_clears_cache(self) -> None:
        from core.services import tick_cache

        tick_cache.start_tick()
        tick_cache.set("key", "value")
        tick_cache.end_tick()
        assert tick_cache._cache is None

    def test_get_set_within_tick(self) -> None:
        from core.services import tick_cache

        tick_cache.start_tick()
        tick_cache.set("energy", "high")
        assert tick_cache.get("energy") == "high"
        tick_cache.end_tick()

    def test_get_returns_none_for_missing_key(self) -> None:
        from core.services import tick_cache

        tick_cache.start_tick()
        assert tick_cache.get("nonexistent") is None
        tick_cache.end_tick()

    def test_start_tick_resets_previous_data(self) -> None:
        from core.services import tick_cache

        tick_cache.start_tick()
        tick_cache.set("old_key", "old_value")
        tick_cache.start_tick()
        assert tick_cache.get("old_key") is None
        tick_cache.end_tick()


class TestTickCacheStats:
    def test_stats_counts_hits_and_misses(self) -> None:
        from core.services import tick_cache

        tick_cache.start_tick()
        tick_cache.set("a", 1)
        tick_cache.get("a")  # hit
        tick_cache.get("b")  # miss
        stats = tick_cache.get_tick_cache_stats()
        assert stats["hits"] >= 1
        assert stats["misses"] >= 1
        tick_cache.end_tick()

    def test_stats_when_inactive(self) -> None:
        from core.services import tick_cache

        tick_cache._cache = None
        stats = tick_cache.get_tick_cache_stats()
        assert stats["active"] is False
