"""Durable queue deadline for accepted contract assignments (§12.3)."""
from __future__ import annotations

import logging
import sqlite3
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

QUEUE_TTL = timedelta(hours=2)


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def ensure_deadline_columns(conn: sqlite3.Connection) -> None:
    columns = {row[1] for row in conn.execute("PRAGMA table_info(agent_assignments)")}
    if "queue_deadline_at" not in columns:
        try:
            conn.execute("ALTER TABLE agent_assignments ADD COLUMN queue_deadline_at TEXT NOT NULL DEFAULT ''")
        except sqlite3.OperationalError as exc:
            if "duplicate column" not in str(exc).lower():
                raise
    conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_queue_deadline "
                 "ON agent_assignments(status, queue_deadline_at)")
    # Rolling upgrades can leave already accepted queued rows. Their original
    # acceptance time, never migration time, starts the two-hour clock.
    for row in conn.execute("SELECT assignment_id, created_at FROM agent_assignments "
                            "WHERE status='queued' AND queue_deadline_at='' ").fetchall():
        try:
            accepted_at = datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
        except ValueError:
            # En raekke uden parselig `created_at` kan ikke faa en deadline — og
            # bliver dermed liggende i `queued` for evigt. Det er praecis den
            # slags der ikke maa ske i tavshed, saa den navngives.
            logger.warning(
                "agent-deadlines: springer %s over — ulaeselig created_at=%r",
                row["assignment_id"], row["created_at"],
            )
            continue
        if accepted_at.tzinfo is None:
            # Naiv tid kan ikke sammenlignes med UTC. Samme konsekvens som
            # ovenfor, samme grund til at sige det hoejt.
            logger.warning(
                "agent-deadlines: springer %s over — created_at=%r mangler tidszone",
                row["assignment_id"], row["created_at"],
            )
            continue
        conn.execute("UPDATE agent_assignments SET queue_deadline_at=? WHERE assignment_id=? "
                     "AND queue_deadline_at=''", (_iso(accepted_at + QUEUE_TTL), row["assignment_id"]))


def initial_queue_deadline(now: datetime | None = None) -> str:
    return _iso((now or datetime.now(UTC)) + QUEUE_TTL)


def extend_queue_deadline(*, assignment_id: str, owner_user_id: str,
                          until: datetime) -> bool:
    """An authenticated adapter may extend only its owner's still queued job."""
    from core.runtime.db_agent_contract import ContractError, _conn

    if not owner_user_id or until.tzinfo is None or until <= datetime.now(UTC):
        raise ContractError("INVALID_SCOPE", "owner og fremtidig UTC-frist kraeves")
    conn = _conn()
    conn.execute("BEGIN IMMEDIATE")
    try:
        row = conn.execute("SELECT queue_deadline_at FROM agent_assignments WHERE assignment_id=? "
                           "AND owner_user_id=? AND status='queued'",
                           (assignment_id, owner_user_id)).fetchone()
        if row is None:
            conn.rollback()
            return False
        current = datetime.fromisoformat(row["queue_deadline_at"].replace("Z", "+00:00"))
        if until <= current:
            conn.rollback()
            return False
        conn.execute("UPDATE agent_assignments SET queue_deadline_at=?, updated_at=? "
                     "WHERE assignment_id=?", (_iso(until), _iso(datetime.now(UTC)), assignment_id))
        conn.commit()
        return True
    except BaseException:
        conn.rollback()
        raise


def expire_due_queues(*, now: datetime | None = None) -> list[dict[str, Any]]:
    """Settle only still-queued jobs; a concurrent worker claim wins safely."""
    from core.runtime import db_agent_contract as c

    cutoff = _iso(now or datetime.now(UTC))
    rows = c._conn().execute(
        "SELECT assignment_id FROM agent_assignments WHERE status='queued' "
        "AND queue_deadline_at!='' AND queue_deadline_at<=? "
        "ORDER BY queue_deadline_at, assignment_id LIMIT 24", (cutoff,)).fetchall()
    done = []
    for row in rows:
        outcome = c.commit_terminal_outcome(
            assignment_id=row["assignment_id"], status="timed_out", error_code="QUEUE_DEADLINE",
            error_phase="admission", summary="Accepteret koe overskred sin frist",
            only_from=("queued",))
        if outcome["committed"]:
            done.append({"assignment_id": row["assignment_id"], "action": "queue_timed_out"})
    return done
