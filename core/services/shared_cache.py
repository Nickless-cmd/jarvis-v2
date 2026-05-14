"""SQLite-backed shared cache for cross-process state.

Why this exists:

  jarvis-api runs with --workers 4. Each uvicorn worker is its own
  Python process with its own module-level dicts. Caches built with
  in-memory dicts (TTL-based or otherwise) get partitioned across
  workers — a request that lands on worker A can't see what worker B
  cached 30s ago. Hit rate ≈ 1/N_workers.

  Hit was: _COHERENT_CACHE in cognitive_state_assembly.py (5-8s cost
  per cache miss × ~75% miss rate = most of the perceived slowness).
  Same applies to the 4 TTL caches I added this morning in
  cheap_provider_runtime.py.

What this gives:

  A single SQLite table that all workers read/write. Get/set/delete
  with TTL. Sub-millisecond lookups (SQLite single-row PK access).
  WAL mode handles concurrent reads + serialized writes safely.

  Values are stored as JSON text — caller is responsible for passing
  JSON-serializable data. For non-trivial Python objects (sets,
  bytes, datetime) the caller can do its own serialization above
  this layer.

API:

  ``get(key)`` -> Any | None
  ``set(key, value, *, ttl_seconds)`` -> None
  ``delete(key)`` -> None
  ``invalidate_prefix(prefix)`` -> int (count of rows deleted)
  ``cleanup_expired()`` -> int (count of rows removed; call from cadence)
  ``stats()`` -> dict (row count + size hints for MC)

All operations are best-effort: on any DB failure they degrade
gracefully (get returns None, set silently fails). Callers should
NOT depend on the cache for correctness — only for speed.

Added 2026-05-14.
"""
from __future__ import annotations

import json
import logging
import threading
import time
from typing import Any

logger = logging.getLogger(__name__)


_TABLE_LOCK = threading.Lock()


def _ensure_table() -> None:
    """Create the shared_cache table on first use. Idempotent.

    Runs ``CREATE TABLE IF NOT EXISTS`` on every call. SQLite handles
    this in O(1) once the table exists (single sqlite_master lookup);
    paying ~microseconds per call avoids cross-test cache leakage
    where a module-level "already ensured" flag would mask a fresh
    in-memory test DB without the table.
    """
    with _TABLE_LOCK:
        try:
            from core.runtime.db import connect
            with connect() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS shared_cache (
                        cache_key   TEXT PRIMARY KEY,
                        value_json  TEXT NOT NULL,
                        expires_at  REAL NOT NULL,
                        created_at  REAL NOT NULL
                    )
                    """
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_shared_cache_expires "
                    "ON shared_cache(expires_at)"
                )
                conn.commit()
        except Exception as exc:
            logger.debug("shared_cache: ensure_table failed: %s", exc)


def get(key: str) -> Any | None:
    """Return cached value, or None if missing/expired/invalid.

    Lazy-expires: if a row exists past its expires_at, treat as missing
    (and remove on a best-effort basis). Never raises.
    """
    key = str(key or "")
    if not key:
        return None
    _ensure_table()
    try:
        from core.runtime.db import connect
        now = time.time()
        with connect() as conn:
            row = conn.execute(
                "SELECT value_json, expires_at FROM shared_cache WHERE cache_key = ?",
                (key,),
            ).fetchone()
        if not row:
            return None
        expires_at = float(row[1])
        if expires_at <= now:
            # Lazy delete — best effort, don't block on it
            try:
                with connect() as conn:
                    conn.execute("DELETE FROM shared_cache WHERE cache_key = ?", (key,))
                    conn.commit()
            except Exception:
                pass
            return None
        return json.loads(row[0])
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        logger.debug("shared_cache: get parse failed for %s: %s", key, exc)
        return None
    except Exception as exc:
        logger.debug("shared_cache: get failed for %s: %s", key, exc)
        return None


def set(key: str, value: Any, *, ttl_seconds: float) -> None:
    """Store ``value`` under ``key`` with TTL. Best-effort, never raises.

    Value must be JSON-serializable. TTL must be > 0; a non-positive
    TTL is a no-op (use ``delete`` to clear).
    """
    key = str(key or "")
    if not key:
        return
    try:
        ttl = float(ttl_seconds)
    except (TypeError, ValueError):
        return
    if ttl <= 0:
        return
    _ensure_table()
    now = time.time()
    expires_at = now + ttl
    try:
        value_json = json.dumps(value, ensure_ascii=False, default=str)
    except (TypeError, ValueError) as exc:
        logger.debug("shared_cache: set serialize failed for %s: %s", key, exc)
        return
    try:
        from core.runtime.db import connect
        with connect() as conn:
            conn.execute(
                """
                INSERT INTO shared_cache(cache_key, value_json, expires_at, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(cache_key) DO UPDATE SET
                    value_json = excluded.value_json,
                    expires_at = excluded.expires_at,
                    created_at = excluded.created_at
                """,
                (key, value_json, expires_at, now),
            )
            conn.commit()
    except Exception as exc:
        logger.debug("shared_cache: set failed for %s: %s", key, exc)


def delete(key: str) -> None:
    """Remove a key from the cache. Best-effort, never raises."""
    key = str(key or "")
    if not key:
        return
    _ensure_table()
    try:
        from core.runtime.db import connect
        with connect() as conn:
            conn.execute("DELETE FROM shared_cache WHERE cache_key = ?", (key,))
            conn.commit()
    except Exception as exc:
        logger.debug("shared_cache: delete failed for %s: %s", key, exc)


def invalidate_prefix(prefix: str) -> int:
    """Remove all keys starting with ``prefix``. Returns delete count.

    Useful for invalidating a logical group of caches in one call
    (e.g. ``invalidate_prefix("cognitive_state:")`` clears every mode).
    """
    prefix = str(prefix or "")
    if not prefix:
        return 0
    _ensure_table()
    try:
        from core.runtime.db import connect
        with connect() as conn:
            cur = conn.execute(
                "DELETE FROM shared_cache WHERE cache_key LIKE ?",
                (prefix + "%",),
            )
            conn.commit()
            return int(cur.rowcount or 0)
    except Exception as exc:
        logger.debug("shared_cache: invalidate_prefix failed: %s", exc)
        return 0


def cleanup_expired() -> int:
    """Purge rows whose expires_at has passed. Returns delete count.

    Lazy-expiry on read already handles individual stale entries;
    this is for periodic cleanup of cache rows that were written but
    never read again (so they'd linger forever).
    """
    _ensure_table()
    now = time.time()
    try:
        from core.runtime.db import connect
        with connect() as conn:
            cur = conn.execute(
                "DELETE FROM shared_cache WHERE expires_at <= ?", (now,)
            )
            conn.commit()
            return int(cur.rowcount or 0)
    except Exception as exc:
        logger.debug("shared_cache: cleanup_expired failed: %s", exc)
        return 0


def stats() -> dict[str, Any]:
    """Return basic cache stats for MC visibility."""
    _ensure_table()
    try:
        from core.runtime.db import connect
        now = time.time()
        with connect() as conn:
            total = int(conn.execute("SELECT COUNT(*) FROM shared_cache").fetchone()[0])
            live = int(
                conn.execute(
                    "SELECT COUNT(*) FROM shared_cache WHERE expires_at > ?", (now,)
                ).fetchone()[0]
            )
            bytes_total = int(
                conn.execute(
                    "SELECT COALESCE(SUM(length(value_json)), 0) FROM shared_cache"
                ).fetchone()[0]
            )
        return {
            "total_rows": total,
            "live_rows": live,
            "expired_rows": max(0, total - live),
            "approx_bytes": bytes_total,
        }
    except Exception as exc:
        logger.debug("shared_cache: stats failed: %s", exc)
        return {"total_rows": 0, "live_rows": 0, "expired_rows": 0, "approx_bytes": 0}


def build_shared_cache_surface() -> dict[str, object]:
    """MC surface — read-only meta-projection."""
    s = stats()
    return {
        "active": True,
        "mode": "shared_cache",
        "summary": (
            f"{s['live_rows']} live / {s['total_rows']} total rows, "
            f"~{s['approx_bytes']} bytes"
        ),
        "stats": s,
        "authority": "derived-read-only",
    }


def _emit_shared_cache_event(
    kind: str, payload: dict[str, object] | None = None
) -> None:
    """Defensive scoped event emitter."""
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(f"shared_cache.{kind}", payload or {})
    except Exception:
        pass
