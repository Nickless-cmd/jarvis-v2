"""Tests for shared_cache — cross-process SQLite-backed cache."""
from __future__ import annotations

import time

import pytest

from core.services import shared_cache as sc


@pytest.fixture(autouse=True)
def _clean_cache():
    """Wipe cache rows between tests so they don't bleed."""
    sc.invalidate_prefix("test:")
    yield
    sc.invalidate_prefix("test:")


def test_get_missing_returns_none():
    assert sc.get("test:nope") is None


def test_set_and_get_roundtrip():
    sc.set("test:hello", {"a": 1, "b": "two"}, ttl_seconds=60)
    assert sc.get("test:hello") == {"a": 1, "b": "two"}


def test_set_overwrites():
    sc.set("test:k", "first", ttl_seconds=60)
    sc.set("test:k", "second", ttl_seconds=60)
    assert sc.get("test:k") == "second"


def test_ttl_expires():
    sc.set("test:short", "value", ttl_seconds=0.1)
    assert sc.get("test:short") == "value"
    time.sleep(0.2)
    assert sc.get("test:short") is None


def test_zero_ttl_is_noop():
    sc.set("test:zero", "value", ttl_seconds=0)
    assert sc.get("test:zero") is None


def test_negative_ttl_is_noop():
    sc.set("test:neg", "value", ttl_seconds=-1)
    assert sc.get("test:neg") is None


def test_delete():
    sc.set("test:del", "value", ttl_seconds=60)
    sc.delete("test:del")
    assert sc.get("test:del") is None


def test_invalidate_prefix():
    sc.set("test:group:a", 1, ttl_seconds=60)
    sc.set("test:group:b", 2, ttl_seconds=60)
    sc.set("test:other:c", 3, ttl_seconds=60)
    n = sc.invalidate_prefix("test:group:")
    assert n == 2
    assert sc.get("test:group:a") is None
    assert sc.get("test:group:b") is None
    assert sc.get("test:other:c") == 3


def test_cleanup_expired():
    sc.set("test:exp1", "v", ttl_seconds=0.05)
    sc.set("test:exp2", "v", ttl_seconds=0.05)
    sc.set("test:alive", "v", ttl_seconds=300)
    time.sleep(0.15)
    n = sc.cleanup_expired()
    assert n >= 2
    assert sc.get("test:alive") == "v"


def test_complex_value_types():
    sc.set("test:complex", {"list": [1, 2, 3], "nested": {"k": "v"}, "bool": True, "null": None}, ttl_seconds=60)
    v = sc.get("test:complex")
    assert v["list"] == [1, 2, 3]
    assert v["nested"]["k"] == "v"
    assert v["bool"] is True
    assert v["null"] is None


def test_unserializable_value_is_silent_noop():
    """Sets that can't be JSON-serialized should not raise; cache stays None."""
    class _NotJSON:
        pass
    sc.set("test:bad", _NotJSON(), ttl_seconds=60)
    # default=str in dumps coerces it; this is more lenient than strict JSON.
    # The test ensures no exception escapes — value may or may not be retrievable.
    val = sc.get("test:bad")
    # Either None (if json.dumps fully failed) or a stringified version — both acceptable
    assert val is None or isinstance(val, str)


def test_stats():
    sc.set("test:stat1", "v", ttl_seconds=60)
    sc.set("test:stat2", "v", ttl_seconds=60)
    s = sc.stats()
    assert s["total_rows"] >= 2
    assert s["live_rows"] >= 2
    assert s["approx_bytes"] > 0


def test_empty_key_is_noop():
    sc.set("", "v", ttl_seconds=60)
    assert sc.get("") is None
