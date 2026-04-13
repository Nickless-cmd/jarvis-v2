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
