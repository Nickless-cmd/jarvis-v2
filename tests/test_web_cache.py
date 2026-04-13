"""Tests for web_cache database layer and cache module."""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta

import pytest


@pytest.fixture()
def mem_conn():
    """In-memory SQLite connection matching production row_factory."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    return conn


# ── DB layer tests ──────────────────────────────────────────────


class TestEnsureWebCacheTable:
    def test_creates_table(self, mem_conn):
        from core.runtime.db import _ensure_web_cache_table

        _ensure_web_cache_table(mem_conn)
        row = mem_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='web_cache'"
        ).fetchone()
        assert row is not None

    def test_idempotent(self, mem_conn):
        from core.runtime.db import _ensure_web_cache_table

        _ensure_web_cache_table(mem_conn)
        _ensure_web_cache_table(mem_conn)  # no error


class TestWebCacheStore:
    def test_store_and_retrieve_raw(self, mem_conn):
        from core.runtime.db import _ensure_web_cache_table, web_cache_store

        _ensure_web_cache_table(mem_conn)
        expires = (datetime.now(UTC) + timedelta(days=7)).isoformat()
        web_cache_store(
            conn=mem_conn,
            cache_key="abc123",
            query_raw="Vejr i København?",
            query_normalized="i københavn vejr",
            source_url="https://example.com",
            title="Weather",
            body="Sunny 18°C",
            ttl_policy="short",
            expires_at=expires,
        )
        row = mem_conn.execute(
            "SELECT * FROM web_cache WHERE cache_key = ?", ("abc123",)
        ).fetchone()
        assert row is not None
        assert row["body"] == "Sunny 18°C"
        assert row["ttl_policy"] == "short"
        assert row["hit_count"] == 0

    def test_store_replaces_existing(self, mem_conn):
        from core.runtime.db import _ensure_web_cache_table, web_cache_store

        _ensure_web_cache_table(mem_conn)
        expires = (datetime.now(UTC) + timedelta(days=7)).isoformat()
        for body in ("old", "new"):
            web_cache_store(
                conn=mem_conn,
                cache_key="key1",
                query_raw="test",
                query_normalized="test",
                source_url="",
                title="",
                body=body,
                ttl_policy="medium",
                expires_at=expires,
            )
        row = mem_conn.execute(
            "SELECT body FROM web_cache WHERE cache_key = ?", ("key1",)
        ).fetchone()
        assert row["body"] == "new"


class TestWebCacheLookup:
    def test_returns_valid_hit(self, mem_conn):
        from core.runtime.db import (
            _ensure_web_cache_table,
            web_cache_lookup,
            web_cache_store,
        )

        _ensure_web_cache_table(mem_conn)
        expires = (datetime.now(UTC) + timedelta(hours=6)).isoformat()
        web_cache_store(
            conn=mem_conn,
            cache_key="hit1",
            query_raw="weather",
            query_normalized="weather",
            source_url="",
            title="Weather",
            body="Sunny",
            ttl_policy="short",
            expires_at=expires,
        )
        result = web_cache_lookup(conn=mem_conn, cache_key="hit1")
        assert result is not None
        assert result["body"] == "Sunny"
        assert result["hit_count"] == 1

    def test_returns_none_for_expired(self, mem_conn):
        from core.runtime.db import (
            _ensure_web_cache_table,
            web_cache_lookup,
            web_cache_store,
        )

        _ensure_web_cache_table(mem_conn)
        expired = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
        web_cache_store(
            conn=mem_conn,
            cache_key="old1",
            query_raw="news",
            query_normalized="news",
            source_url="",
            title="",
            body="stale",
            ttl_policy="short",
            expires_at=expired,
        )
        assert web_cache_lookup(conn=mem_conn, cache_key="old1") is None

    def test_returns_none_for_missing(self, mem_conn):
        from core.runtime.db import _ensure_web_cache_table, web_cache_lookup

        _ensure_web_cache_table(mem_conn)
        assert web_cache_lookup(conn=mem_conn, cache_key="nope") is None

    def test_increments_hit_count(self, mem_conn):
        from core.runtime.db import (
            _ensure_web_cache_table,
            web_cache_lookup,
            web_cache_store,
        )

        _ensure_web_cache_table(mem_conn)
        expires = (datetime.now(UTC) + timedelta(days=7)).isoformat()
        web_cache_store(
            conn=mem_conn,
            cache_key="multi",
            query_raw="q",
            query_normalized="q",
            source_url="",
            title="",
            body="data",
            ttl_policy="medium",
            expires_at=expires,
        )
        web_cache_lookup(conn=mem_conn, cache_key="multi")
        web_cache_lookup(conn=mem_conn, cache_key="multi")
        result = web_cache_lookup(conn=mem_conn, cache_key="multi")
        assert result["hit_count"] == 3


class TestWebCacheCleanup:
    def test_deletes_expired_rows(self, mem_conn):
        from core.runtime.db import (
            _ensure_web_cache_table,
            web_cache_cleanup,
            web_cache_store,
        )

        _ensure_web_cache_table(mem_conn)
        expired = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
        valid = (datetime.now(UTC) + timedelta(days=7)).isoformat()
        web_cache_store(
            conn=mem_conn,
            cache_key="gone",
            query_raw="old",
            query_normalized="old",
            source_url="",
            title="",
            body="expired",
            ttl_policy="short",
            expires_at=expired,
        )
        web_cache_store(
            conn=mem_conn,
            cache_key="keep",
            query_raw="new",
            query_normalized="new",
            source_url="",
            title="",
            body="valid",
            ttl_policy="medium",
            expires_at=valid,
        )
        deleted = web_cache_cleanup(conn=mem_conn)
        assert deleted == 1
        assert (
            mem_conn.execute("SELECT COUNT(*) FROM web_cache").fetchone()[0] == 1
        )


# ── Cache module tests ──────────────────────────────────────────


class TestNormalizeQuery:
    def test_basic_normalization(self):
        from core.tools.web_cache import normalize_query

        normalized, key = normalize_query("Vejr i København?")
        assert normalized == "i københavn vejr"
        assert len(key) == 64  # SHA256 hex

    def test_strips_punctuation(self):
        from core.tools.web_cache import normalize_query

        normalized, _ = normalize_query('Hello, World! "test"')
        assert normalized == "hello test world"

    def test_same_words_different_order_same_key(self):
        from core.tools.web_cache import normalize_query

        _, key1 = normalize_query("weather copenhagen")
        _, key2 = normalize_query("copenhagen weather")
        assert key1 == key2

    def test_empty_string(self):
        from core.tools.web_cache import normalize_query

        normalized, key = normalize_query("")
        assert normalized == ""
        assert len(key) == 64


class TestClassifyTtl:
    def test_short_weather(self):
        from core.tools.web_cache import classify_ttl

        policy, td = classify_ttl("Vejr i København")
        assert policy == "short"
        assert td == timedelta(hours=6)

    def test_short_news(self):
        from core.tools.web_cache import classify_ttl

        policy, _ = classify_ttl("breaking news today")
        assert policy == "short"

    def test_long_documentation(self):
        from core.tools.web_cache import classify_ttl

        policy, td = classify_ttl("python docs argparse tutorial")
        assert policy == "long"
        assert td == timedelta(days=90)

    def test_static_definition(self):
        from core.tools.web_cache import classify_ttl

        policy, td = classify_ttl("hvad er fotosyntese")
        assert policy == "static"
        assert td == timedelta(days=365)

    def test_default_medium(self):
        from core.tools.web_cache import classify_ttl

        policy, td = classify_ttl("best restaurants in Aarhus")
        assert policy == "medium"
        assert td == timedelta(days=7)


class TestCachedWebSearch:
    def test_cache_miss_calls_fetch(self, mem_conn):
        from core.tools.web_cache import cached_web_search

        calls = []

        def fake_fetch(query: str, max_results: int) -> dict:
            calls.append(query)
            return {"text": "result from tavily", "result_count": 1, "query": query, "status": "ok"}

        result = cached_web_search(
            query="test query",
            max_results=5,
            fetch_fn=fake_fetch,
            conn=mem_conn,
        )
        assert len(calls) == 1
        assert result["source"] == "tavily"
        assert result["text"] == "result from tavily"
        assert "cache_key" in result

    def test_cache_hit_skips_fetch(self, mem_conn):
        from core.tools.web_cache import cached_web_search

        call_count = 0

        def fake_fetch(query: str, max_results: int) -> dict:
            nonlocal call_count
            call_count += 1
            return {"text": "fresh data", "result_count": 1, "query": query, "status": "ok"}

        cached_web_search(query="same query", max_results=5, fetch_fn=fake_fetch, conn=mem_conn)
        assert call_count == 1

        result = cached_web_search(query="same query", max_results=5, fetch_fn=fake_fetch, conn=mem_conn)
        assert call_count == 1
        assert result["source"] == "cache"
        assert result["hit_count"] == 1

    def test_reordered_query_hits_cache(self, mem_conn):
        from core.tools.web_cache import cached_web_search

        call_count = 0

        def fake_fetch(query: str, max_results: int) -> dict:
            nonlocal call_count
            call_count += 1
            return {"text": "data", "result_count": 1, "query": query, "status": "ok"}

        cached_web_search(query="copenhagen weather", max_results=5, fetch_fn=fake_fetch, conn=mem_conn)
        result = cached_web_search(query="weather copenhagen", max_results=5, fetch_fn=fake_fetch, conn=mem_conn)
        assert call_count == 1
        assert result["source"] == "cache"

    def test_fetch_error_passes_through(self, mem_conn):
        from core.tools.web_cache import cached_web_search

        def failing_fetch(query: str, max_results: int) -> dict:
            return {"error": "API down", "status": "error"}

        result = cached_web_search(query="broken", max_results=5, fetch_fn=failing_fetch, conn=mem_conn)
        assert result["status"] == "error"

    def test_returns_ttl_policy(self, mem_conn):
        from core.tools.web_cache import cached_web_search

        def fake_fetch(query: str, max_results: int) -> dict:
            return {"text": "sunny", "result_count": 1, "query": query, "status": "ok"}

        result = cached_web_search(query="vejr i dag", max_results=5, fetch_fn=fake_fetch, conn=mem_conn)
        assert result["ttl_policy"] == "short"
