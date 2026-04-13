"""Web search result cache — normalization, TTL classification, orchestration."""
from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime, timedelta
from typing import Any, Callable


def normalize_query(raw: str) -> tuple[str, str]:
    """Normalize query and produce SHA256 cache key.

    Returns (normalized_text, cache_key).
    """
    text = raw.lower().strip()
    text = re.sub(r"[.,!?;:()\[\]\"']", "", text)
    words = sorted(text.split())
    normalized = " ".join(words)
    cache_key = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return normalized, cache_key


_TTL_RULES: list[tuple[str, str, timedelta]] = [
    (r"vejr|weather|kurs|valuta|pris i dag|nyheder|news|breaking", "short", timedelta(hours=6)),
    (r"documentation|docs|api reference|tutorial|guide|manual", "long", timedelta(days=90)),
    (r"hvad er|what is|definition|historie|history of|matematik", "static", timedelta(days=365)),
]
_DEFAULT_TTL = ("medium", timedelta(days=7))


def classify_ttl(query: str) -> tuple[str, timedelta]:
    """Classify query into a TTL policy. First match wins, default medium."""
    lower = query.lower()
    for pattern, policy, td in _TTL_RULES:
        if re.search(pattern, lower):
            return policy, td
    return _DEFAULT_TTL


def cached_web_search(
    *,
    query: str,
    max_results: int,
    fetch_fn: Callable[[str, int], dict[str, Any]],
    conn: Any | None = None,
) -> dict[str, Any]:
    """Check cache, call fetch_fn on miss, store result."""
    from core.runtime.db import (
        _ensure_web_cache_table,
        connect,
        web_cache_lookup,
        web_cache_store,
    )

    normalized, cache_key = normalize_query(query)

    own_conn = conn is None
    if own_conn:
        conn = connect()

    try:
        _ensure_web_cache_table(conn)

        hit = web_cache_lookup(conn=conn, cache_key=cache_key)
        if hit is not None:
            return {
                "text": hit["body"],
                "source": "cache",
                "cache_key": cache_key,
                "hit_count": hit["hit_count"],
                "ttl_policy": hit["ttl_policy"],
                "status": "ok",
            }

        result = fetch_fn(query, max_results)
        if result.get("status") == "error":
            return result

        policy, ttl = classify_ttl(query)
        expires_at = (datetime.now(UTC) + ttl).isoformat()
        web_cache_store(
            conn=conn,
            cache_key=cache_key,
            query_raw=query,
            query_normalized=normalized,
            source_url="",
            title="",
            body=result.get("text", ""),
            ttl_policy=policy,
            expires_at=expires_at,
        )

        return {
            **result,
            "source": "tavily",
            "cache_key": cache_key,
            "ttl_policy": policy,
        }
    finally:
        if own_conn:
            conn.close()
