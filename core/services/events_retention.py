"""Events-table retention — bound the unbounded ``events`` telemetry table.

The eventbus persists every event to ``events`` with no retention. Left alone it
grows without limit (measured 2.56M rows / ~4 months / 2.7GB DB, ~211k rows/day
under the cheap-lane churn). A large table means slower INSERTs (deeper index) →
longer WAL write-lock holds → more contention with API chat/cost writes (the
amplifier behind API latency spikes, alongside per-event commits which the writer
now batches).

``prune_old_events`` deletes rows older than a cutoff in SMALL batches (one commit
per batch → never a long lock), capped per invocation so the initial drain of a
huge table happens gradually across ticks rather than in one table-locking sweep.
Self-safe: never raises.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

_DEFAULT_MAX_AGE_DAYS = 14
_DEFAULT_MAX_DELETE = 50_000   # per invocation — gradual drain of a huge backlog
_DEFAULT_BATCH_SIZE = 5_000    # rows per transaction — short lock holds


def _retention_days() -> int:
    try:
        from core.runtime.settings import load_settings
        v = int(load_settings().extra.get("events_retention_days", _DEFAULT_MAX_AGE_DAYS))
        return max(1, v)
    except Exception:
        return _DEFAULT_MAX_AGE_DAYS


def prune_old_events(
    *,
    max_age_days: int | None = None,
    max_delete: int = _DEFAULT_MAX_DELETE,
    batch_size: int = _DEFAULT_BATCH_SIZE,
) -> dict[str, object]:
    """Delete events older than ``max_age_days`` in batches. Returns {"deleted": N}.

    Batched (one commit per ``batch_size`` rows) so no single long lock; capped at
    ``max_delete`` per call so a huge backlog drains gradually. Self-safe."""
    days = int(max_age_days) if max_age_days is not None else _retention_days()
    return prune_table_by_age(
        "events", "created_at", max_age_days=days,
        max_delete=max_delete, batch_size=batch_size,
    )


def prune_table_by_age(
    table: str,
    ts_column: str,
    *,
    max_age_days: int,
    max_delete: int = _DEFAULT_MAX_DELETE,
    batch_size: int = _DEFAULT_BATCH_SIZE,
) -> dict[str, object]:
    """Delete rows from ``table`` where ``ts_column`` < cutoff, in small capped
    batches (one commit each → short locks). ``table``/``ts_column`` are validated
    against an identifier allowlist to keep the f-string SQL injection-safe. Self-safe."""
    import re
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", table) or \
       not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", ts_column):
        return {"deleted": 0, "error": "invalid identifier", "table": table}
    cutoff = (datetime.now(UTC) - timedelta(days=max(1, int(max_age_days)))).isoformat()
    total = 0
    try:
        from core.runtime.db import connect
        while total < max_delete:
            take = min(batch_size, max_delete - total)
            with connect() as conn:
                cur = conn.execute(
                    f"DELETE FROM {table} WHERE rowid IN "
                    f"(SELECT rowid FROM {table} WHERE {ts_column} < ? "
                    f"ORDER BY rowid ASC LIMIT ?)",
                    (cutoff, take),
                )
                n = cur.rowcount or 0
                conn.commit()
            if n <= 0:
                break
            total += n
    except Exception as exc:
        return {"deleted": total, "error": str(exc)[:200], "table": table}
    return {"deleted": total, "table": table, "retention_days": int(max_age_days)}


# Pure-telemetry tables safe to age-prune (logs/metrics, no cognitive value).
# (table, ts_column, retention_days). Load-bearing memory/identity/learning tables
# are DELIBERATELY excluded — they are pruned only on explicit owner decision.
_TELEMETRY_RETENTION: tuple[tuple[str, str, int], ...] = (
    ("daemon_output_log", "created_at", 21),
    ("cheap_provider_invocations", "created_at", 21),
    ("tool_router_decisions", "created_at", 45),
    ("reasoning_conclusions", "created_at", 45),
    # Recency-bounded readers (verified 2026-07-17): each reads only recent/by-id
    # rows (ORDER BY ... LIMIT, WHERE id=?, WHERE status IN proposed/applied), never
    # aggregates full history → rows older than 60d have no effect on learning.
    ("runtime_action_outcomes", "recorded_at", 60),
    ("runtime_contract_candidates", "created_at", 60),
    ("behavioral_decision_reviews", "created_at", 60),
)


def prune_telemetry_tables() -> dict[str, object]:
    """Age-prune the safe telemetry tables. Self-safe. Returns per-table deleted counts."""
    out: dict[str, object] = {}
    for table, ts_col, days in _TELEMETRY_RETENTION:
        try:
            out[table] = prune_table_by_age(table, ts_col, max_age_days=days).get("deleted", 0)
        except Exception as exc:
            out[table] = f"err:{str(exc)[:60]}"
    return out


# Versioned cognitive snapshot tables: one append-only row per version of a SINGLE
# evolving entity (relationship texture, personality vector). ``texture_id``/
# ``vector_id`` are unique-per-row; ``version`` is a monotonic global counter. The
# tables grew ~550 rows/day since April (49k/24k rows) but every reader uses only
# ORDER BY version DESC LIMIT 1..20 (db_cognitive.py) — never old versions. Keeping
# the latest N versions preserves current state + recent evolution history with a
# 50× reader margin. Owner-approved keep-latest (Bjørn 2026-07-19). (table, version_col, keep_latest).
_VERSIONED_RETENTION: tuple[tuple[str, str, int], ...] = (
    ("cognitive_relationship_textures", "version", 1000),
    ("cognitive_personality_vectors", "version", 1000),
)


def prune_versioned_table(
    table: str,
    version_col: str,
    *,
    keep_latest: int,
    max_delete: int = _DEFAULT_MAX_DELETE,
    batch_size: int = _DEFAULT_BATCH_SIZE,
) -> dict[str, object]:
    """Delete all but the newest ``keep_latest`` versions from a versioned snapshot
    table. Deletes rows where ``version_col`` <= (max_version - keep_latest), in small
    capped batches (one commit each → short locks). Identifiers are allowlist-validated.
    Self-safe: never raises, never touches the current (max-version) row."""
    import re
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", table) or \
       not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", version_col):
        return {"deleted": 0, "error": "invalid identifier", "table": table}
    total = 0
    try:
        from core.runtime.db import connect
        with connect() as conn:
            row = conn.execute(f"SELECT MAX({version_col}) AS m FROM {table}").fetchone()
        maxv = row[0] if row is not None else None
        if maxv is None:
            return {"deleted": 0, "table": table}
        threshold = int(maxv) - int(max(1, keep_latest))
        if threshold <= 0:
            return {"deleted": 0, "table": table, "keep_latest": keep_latest}
        while total < max_delete:
            take = min(batch_size, max_delete - total)
            with connect() as conn:
                cur = conn.execute(
                    f"DELETE FROM {table} WHERE rowid IN "
                    f"(SELECT rowid FROM {table} WHERE {version_col} <= ? "
                    f"ORDER BY rowid ASC LIMIT ?)",
                    (threshold, take),
                )
                n = cur.rowcount or 0
                conn.commit()
            if n <= 0:
                break
            total += n
    except Exception as exc:
        return {"deleted": total, "error": str(exc)[:200], "table": table}
    return {"deleted": total, "table": table, "keep_latest": int(keep_latest)}


def prune_versioned_tables() -> dict[str, object]:
    """Keep-latest-N prune the versioned cognitive snapshot tables. Self-safe."""
    out: dict[str, object] = {}
    for table, vcol, keep in _VERSIONED_RETENTION:
        try:
            out[table] = prune_versioned_table(table, vcol, keep_latest=keep).get("deleted", 0)
        except Exception as exc:
            out[table] = f"err:{str(exc)[:60]}"
    return out
