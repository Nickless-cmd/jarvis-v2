"""Forgetting engine — Lag 11 deletion logic.

Pure functions: candidate-scan, soft-delete, grace-sweep, release-memory.
No threading, no daemons. The runtime module wraps this with a Lock + loop.

Two tracks:
  - auto: scan low-decay candidates, soft_deleted_at = now(), counter++
  - self: validate, hard-delete, insert marker

Skopebeskyttelse via _FREDET_PATHS and _FREDET_TABLES allowlists.
"""
from __future__ import annotations

import logging
import re
from datetime import UTC, datetime, timedelta
from typing import Any

from core.eventbus.bus import event_bus
from core.runtime.db import connect
from core.runtime.db_absence_traces import (
    increment_auto_counter,
    insert_self_marker,
    mark_self_released,
)
from core.runtime.settings import load_settings

logger = logging.getLogger(__name__)


# ── Skopebeskyttelse ───────────────────────────────────────────────────

_FREDET_PATHS: frozenset[str] = frozenset({
    "workspace/SOUL.md",
    "workspace/USER.md",
    "workspace/MEMORY.md",
    "workspace/IDENTITY.md",
})

# Exact table names for fredet kerne. Mirrors the audit doc.
_FREDET_TABLES_EXACT: frozenset[str] = frozenset({
    "cognitive_decisions",
    "cognitive_narrative_identities",
    "cognitive_personality_vectors",
    "cognitive_formed_values",
    "cognitive_taste_profiles",
    "cognitive_relationship_textures",
    "cognitive_compass_states",
    "concept_baseline_stats",
    "private_self_models",
    "private_brain_records",
    "cognitive_emotion_concept_signals",
    "causal_edges",
    "absence_traces",  # never auto-fade the trace ledger itself
})

# Pattern matches for groups of fredet tables.
_FREDET_TABLES_REGEX: tuple[re.Pattern, ...] = (
    re.compile(r"^cognitive_self_model_.*"),
    re.compile(r"^runtime_state_.*"),  # operational, not episodic
)


def is_fredet_path(path: str) -> bool:
    return path in _FREDET_PATHS


def is_fredet_table(table: str) -> bool:
    if table in _FREDET_TABLES_EXACT:
        return True
    return any(p.match(table) for p in _FREDET_TABLES_REGEX)


# ── Period-label computation ────────────────────────────────────────────

def compute_period_label(released_at: datetime, now: datetime) -> str:
    """Render an aged period as a human label.

    Computed on read, never stored — labels age correctly without DB updates.
    """
    delta = now - released_at
    days = delta.days
    if days < 7:
        return f"~{days} dage siden"
    if days < 31:
        return f"~{days // 7} uger siden"
    if days < 365:
        return f"~{days // 30} måneder siden"
    years = days / 365.25
    if years < 2:
        return f"~{years:.1f} år siden"
    return f"~{int(years)} år siden"


# ── Auto-track: candidate scan + soft-delete + grace-sweep ────────────

# Tables eligible for auto-fade. Mirrors _ensure_soft_deleted_at_columns
# in db.py — keep in sync. Phase 1 minimal set.
_AUTO_FADE_TABLES: tuple[str, ...] = (
    "cognitive_chronicle_entries",
    "cognitive_personal_project_journal",
)


def _id_column_for(table: str) -> str:
    """Return the primary-key column name for a fade-eligible table."""
    if table == "cognitive_chronicle_entries":
        return "entry_id"
    return "id"


def _scan_table_for_candidates(
    *,
    table: str,
    workspace_id: str,
    decay_threshold: float,
    min_age_days: int,
    limit: int,
) -> list[Any]:
    """Find IDs of rows that should fade.

    Phase 1: rely on age + workspace match. Most episodic tables don't
    track decay_score — refining with decay scoring is Phase 2 work.
    Returns IDs in insertion order (oldest first via created_at ASC).
    """
    cutoff = (
        datetime.now(UTC) - timedelta(days=min_age_days)
    ).isoformat().replace("+00:00", "Z")
    id_col = _id_column_for(table)
    # cognitive_personal_project_journal does not have workspace_id;
    # filter only when the column exists.
    with connect() as conn:
        cols = {r[1] for r in conn.execute(
            f"PRAGMA table_info({table})"
        ).fetchall()}
        if "workspace_id" in cols:
            rows = conn.execute(
                f"SELECT {id_col} FROM {table} "
                f"WHERE workspace_id = ? "
                f"AND created_at < ? "
                f"AND soft_deleted_at IS NULL "
                f"ORDER BY created_at ASC "
                f"LIMIT ?",
                (workspace_id, cutoff, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                f"SELECT {id_col} FROM {table} "
                f"WHERE created_at < ? "
                f"AND soft_deleted_at IS NULL "
                f"ORDER BY created_at ASC "
                f"LIMIT ?",
                (cutoff, limit),
            ).fetchall()
    return [r[0] for r in rows]


def _soft_delete_row(table: str, row_id: Any) -> bool:
    """Mark row as soft-deleted. Returns True if updated."""
    id_col = _id_column_for(table)
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    with connect() as conn:
        cur = conn.execute(
            f"UPDATE {table} SET soft_deleted_at = ? "
            f"WHERE {id_col} = ? AND soft_deleted_at IS NULL",
            (now, row_id),
        )
        return cur.rowcount > 0


def _hard_delete_expired_rows(table: str, grace_days: int) -> int:
    """Hard-delete rows whose grace window has expired."""
    cutoff = (
        datetime.now(UTC) - timedelta(days=grace_days)
    ).isoformat().replace("+00:00", "Z")
    with connect() as conn:
        cur = conn.execute(
            f"DELETE FROM {table} "
            f"WHERE soft_deleted_at IS NOT NULL AND soft_deleted_at < ?",
            (cutoff,),
        )
        return cur.rowcount


def run_auto_cycle(*, workspace_id: str) -> dict[str, Any]:
    """One auto-track cycle: scan, soft-delete, grace-sweep.

    Returns a summary dict for telemetry. Honors forgetting_enabled flag.
    """
    settings = load_settings()
    if not settings.forgetting_enabled:
        return {"workspace_id": workspace_id, "skipped": "disabled"}

    threshold = settings.forgetting_auto_decay_threshold
    min_age = settings.forgetting_auto_min_age_days
    max_per_cycle = settings.forgetting_auto_max_per_cycle
    grace = settings.forgetting_grace_days

    soft_deleted = 0
    hard_deleted = 0

    for table in _AUTO_FADE_TABLES:
        if is_fredet_table(table):  # belt & suspenders
            continue
        ids = _scan_table_for_candidates(
            table=table,
            workspace_id=workspace_id,
            decay_threshold=threshold,
            min_age_days=min_age,
            limit=max(0, max_per_cycle - soft_deleted),
        )
        for row_id in ids:
            if _soft_delete_row(table, row_id):
                soft_deleted += 1
                increment_auto_counter(workspace_id=workspace_id)
            if soft_deleted >= max_per_cycle:
                break

        hard_deleted += _hard_delete_expired_rows(table, grace_days=grace)

        if soft_deleted >= max_per_cycle:
            break

    try:
        event_bus.publish(
            "cognitive_forgetting.cycle_complete",
            {
                "workspace_id": workspace_id,
                "soft_deleted": soft_deleted,
                "hard_deleted": hard_deleted,
            },
        )
    except Exception as exc:
        logger.debug("forgetting: publish cycle_complete failed: %s", exc)

    return {
        "workspace_id": workspace_id,
        "soft_deleted": soft_deleted,
        "hard_deleted": hard_deleted,
    }


# ── Self-track: release_memory ─────────────────────────────────────────

# Maps memory_kind values to their underlying tables.
_MEMORY_KIND_TO_TABLE: dict[str, str] = {
    "chronicle_entry": "cognitive_chronicle_entries",
    "journal_entry": "cognitive_personal_project_journal",
    # 'absence_marker' is handled separately (recursive release path)
}


def release_memory(
    *,
    memory_kind: str,
    memory_id: str,
    workspace_id: str = "default",
    why: str | None = None,  # accepted, never persisted
) -> dict[str, Any]:
    """Self-track release: hard-delete + marker. Irrevocable.

    Returns:
      {status: 'released'|'rejected'|'not_found'|'disabled', ...}
    """
    settings = load_settings()
    if not settings.forgetting_enabled:
        return {
            "status": "disabled",
            "reason": "forgetting is disabled in runtime settings",
        }

    # Recursive release path
    if memory_kind == "absence_marker":
        ok = mark_self_released(trace_id=memory_id)
        if not ok:
            return {"status": "not_found", "reason": "marker not found"}
        try:
            event_bus.publish(
                "cognitive_forgetting.released",
                {"track": "self", "recursive": True},
            )
        except Exception:
            pass
        return {
            "status": "released",
            "kind": "absence_marker",
            "period_label": None,
        }

    # Standard release path
    table = _MEMORY_KIND_TO_TABLE.get(memory_kind)
    if table is None:
        return {
            "status": "rejected",
            "reason": f"unknown memory_kind: {memory_kind}",
        }
    if is_fredet_table(table):
        return {
            "status": "rejected",
            "reason": f"table '{table}' is fredet — cannot release",
        }

    id_col = _id_column_for(table)
    with connect() as conn:
        row = conn.execute(
            f"SELECT created_at FROM {table} WHERE {id_col} = ?",
            (memory_id,),
        ).fetchone()
        if row is None:
            return {
                "status": "not_found",
                "reason": f"memory_id {memory_id} not in {table}",
            }
        try:
            created_at = datetime.fromisoformat(
                str(row[0]).replace("Z", "+00:00")
            )
        except ValueError:
            created_at = datetime.now(UTC)

        period_label = compute_period_label(created_at, datetime.now(UTC))

        # Transaction: hard-delete the row
        conn.execute(
            f"DELETE FROM {table} WHERE {id_col} = ?",
            (memory_id,),
        )

    # Marker insert (separate connection — risk window is microseconds;
    # consistency is acceptable for this design).
    marker = insert_self_marker(
        workspace_id=workspace_id, period_label=period_label
    )

    try:
        event_bus.publish(
            "cognitive_forgetting.released",
            {"track": "self", "trace_id": marker["trace_id"]},
        )
    except Exception:
        pass

    return {
        "status": "released",
        "kind": memory_kind,
        "period_label": period_label,
        "trace_id": marker["trace_id"],
    }


# ── Heartbeat injection ────────────────────────────────────────────────

def _is_anniversary(released_at: datetime, now: datetime) -> bool:
    """True if the age of released_at is within 1 day of a round-number bucket."""
    days = (now - released_at).days
    targets = (7, 30, 90, 180, 365, 730)
    return any(abs(days - t) <= 1 for t in targets)


def _is_proximity(released_at: datetime, now: datetime) -> bool:
    """True if released_at is in the active 14–90 day window.

    Phase 1 simplification: anything aged 14–90 days that didn't catch
    an anniversary still gets surfaced once. Cooldown prevents spam.
    """
    days = (now - released_at).days
    return 14 <= days <= 90


def format_forgetting_section_for_heartbeat(
    *, workspace_id: str = "default"
) -> str:
    """Compact prompt-injection lines for the heartbeat awareness section.

    Auto-line: monthly counter weight (only if > 0).
    Self-line(s): up to 2 markers triggered by anniversary or proximity.
    Skips markers where is_self_released = 1.

    Returns an empty string when nothing is active — caller should not
    inject the section at all.
    """
    from core.runtime.db_absence_traces import (
        get_auto_counter,
        list_self_markers,
    )

    parts: list[str] = []

    counter = get_auto_counter(workspace_id=workspace_id)
    if counter and int(counter.get("auto_count") or 0) > 0:
        parts.append(
            f"Forglemmelsens vægt: {counter['auto_count']} ting er fadet i "
            f"denne måned ({counter['month_key']})."
        )

    now = datetime.now(UTC)
    markers = list_self_markers(workspace_id=workspace_id)
    rendered = 0
    for m in markers:
        if rendered >= 2:
            break
        try:
            released = datetime.fromisoformat(
                str(m["released_at"]).replace("Z", "+00:00")
            )
        except ValueError:
            continue
        if _is_anniversary(released, now):
            label = compute_period_label(released, now)
            parts.append(
                f"For {label.replace('~', '')} valgte du at slippe noget. "
                "Du ved ikke længere hvad."
            )
            rendered += 1
        elif _is_proximity(released, now):
            label = compute_period_label(released, now)
            parts.append(
                f"Du slap noget {label}. Det stadie i dit liv er væk fra dig."
            )
            rendered += 1

    return "\n".join(parts)
