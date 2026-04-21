# Web Search Result Cache

**Goal:** Give Jarvis accumulated internet memory — cached web search results reused across sessions with TTL-based expiry.

**Architecture:** Cache layer between `_exec_web_search` and Tavily API. DB table in `core/runtime/db.py`, cache logic in new `core/tools/web_cache.py`, minimal change to `simple_tools.py`.

**Tech Stack:** SQLite (existing `core/runtime/db.py`), SHA256 for cache keys, regex heuristics for TTL classification.

---

## 1. Database Table — `web_cache`

Lives in `core/runtime/db.py` following `_ensure_*_table()` pattern.

```sql
CREATE TABLE IF NOT EXISTS web_cache (
    cache_key TEXT PRIMARY KEY,
    query_raw TEXT NOT NULL,
    query_normalized TEXT NOT NULL,
    source_url TEXT,
    title TEXT,
    body TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    ttl_policy TEXT NOT NULL DEFAULT 'medium',
    hit_count INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_web_cache_expires ON web_cache(expires_at);
CREATE INDEX IF NOT EXISTS idx_web_cache_normalized ON web_cache(query_normalized);
```

### DB Functions

- `_ensure_web_cache_table(conn)` — create table + indexes if not exists
- `web_cache_lookup(cache_key: str) -> dict | None` — returns row if `expires_at > now()`, increments `hit_count`. Returns None if expired or missing.
- `web_cache_store(cache_key, query_raw, query_normalized, source_url, title, body, ttl_policy, expires_at)` — INSERT OR REPLACE
- `web_cache_cleanup() -> int` — DELETE WHERE `expires_at < now()`, returns count deleted

## 2. Cache Module — `core/tools/web_cache.py`

New file, ~80-100 lines. Three responsibilities:

### Query Normalization

`normalize_query(raw: str) -> tuple[str, str]` — returns `(normalized_text, cache_key)`

1. Lowercase, strip whitespace
2. Remove punctuation (`.,!?;:()[]"'`)
3. Sort words alphabetically
4. SHA256 hash of sorted result → `cache_key`

Example: `"Vejr i København?"` → normalized `"i københavn vejr"` → SHA256 key

### TTL Classification

`classify_ttl(query: str) -> tuple[str, timedelta]`

| Policy | TTL | Trigger patterns |
|--------|-----|-----------------|
| `short` | 6 hours | vejr, weather, kurs, valuta, pris i dag, nyheder, news, breaking |
| `medium` | 7 days | default — prices, events, articles |
| `long` | 90 days | documentation, docs, api reference, tutorial, guide, manual |
| `static` | 365 days | hvad er, what is, definition, historie, history of, matematik |

Pattern matching: simple `re.search` on lowercased query. First match wins. No match → `medium`.

### Orchestration

`cached_web_search(query: str, max_results: int, fetch_fn: Callable) -> dict`

1. Normalize query → `(normalized, cache_key)`
2. `web_cache_lookup(cache_key)` → if valid hit, return `{"text": body, "source": "cache", "cache_key": cache_key, "hit_count": N}`
3. If miss or expired: call `fetch_fn(query, max_results)` (the existing Tavily logic)
4. On success: `web_cache_store(...)` with classified TTL
5. Return result with `{"source": "tavily", "cache_key": cache_key}`

## 3. Integration — `simple_tools.py`

Minimal change to `_exec_web_search`:

- Extract existing Tavily HTTP call into `_fetch_tavily(query, max_results) -> dict`
- Replace body of `_exec_web_search` with call to `cached_web_search(query, max_results, _fetch_tavily)`
- Return dict now includes `source` and `cache_key` fields

## 4. Cleanup — Heartbeat Integration

Wire `web_cache_cleanup()` into existing heartbeat action system:

- Action type: `"cleanup_web_cache"`
- Runs once per day (check against last-run timestamp)
- Deletes expired rows, logs count

No new daemon — reuses existing heartbeat infrastructure.

## 5. Observability

Tool result includes:
- `source: "cache" | "tavily"` — where the result came from
- `cache_key` — the normalized lookup key
- `hit_count` — how many times this cached result has been served (cache hits only)
- `ttl_policy` — which expiry class was assigned

## Non-Goals

- Fuzzy/semantic matching (future enhancement)
- Prompt caching (separate task, orthogonal)
- Cache invalidation API (YAGNI — TTL handles it)
- Per-result caching (we cache the full search response, not individual URLs)
