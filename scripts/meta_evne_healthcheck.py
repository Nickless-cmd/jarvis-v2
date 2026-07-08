#!/usr/bin/env python
"""Meta-evne healthcheck — read-only snapshot of all new tracker stacks.

Background: between 2026-05-22 and 2026-05-24 we landed five DB-polling
trackers (metacognition_signals, partner_knowledge_facts,
room_entity_observations, session_inbox, inner_voice_shadow) plus
related infrastructure. Codex' recommendation 2026-05-24: build a
single read-only surface that confirms the stack is breathing before
adding more layers.

Usage:
  /opt/conda/envs/ai/bin/python scripts/meta_evne_healthcheck.py
  /opt/conda/envs/ai/bin/python scripts/meta_evne_healthcheck.py --json
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

JARVIS_HOME = Path(os.environ.get("HOME", "/root")) / ".jarvis-v2"
DB_PATH = JARVIS_HOME / "state" / "jarvis.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _count(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> int:
    try:
        row = conn.execute(sql, params).fetchone()
        return int(row[0] or 0) if row else 0
    except sqlite3.OperationalError:
        return 0  # table missing → tracker hasn't run yet


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,),
    ).fetchone()
    return row is not None


def _hours_ago(iso: str | None) -> float | None:
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return (datetime.now(UTC) - dt).total_seconds() / 3600.0
    except (ValueError, TypeError):
        return None


# ── Per-tracker probes ───────────────────────────────────────────────────


def probe_metacognition(conn) -> dict[str, Any]:
    """Probe the metacognition_signals tracker.

    Returns total signal count, count in the last 24h, hours since the last
    signal, and 24h average scores for the contradiction_within_response and
    claim_density dimensions. Status is MISSING (no table), STALE (no signals
    in 24h) or OK.
    """
    if not _table_exists(conn, "metacognition_signals"):
        return {"status": "MISSING", "note": "table not created — tracker never ran"}
    total = _count(conn, "SELECT COUNT(*) FROM metacognition_signals")
    last_24h = _count(
        conn,
        "SELECT COUNT(*) FROM metacognition_signals WHERE computed_at >= ?",
        ((datetime.now(UTC) - timedelta(hours=24)).isoformat(),),
    )
    avg_by_dim: dict[str, float] = {}
    for dim in ("contradiction_within_response", "claim_density"):
        row = conn.execute(
            "SELECT AVG(score) FROM metacognition_signals "
            "WHERE dimension=? AND computed_at >= ?",
            (dim, (datetime.now(UTC) - timedelta(hours=24)).isoformat()),
        ).fetchone()
        avg_by_dim[dim] = round(float(row[0] or 0), 3)
    last_row = conn.execute(
        "SELECT MAX(computed_at) FROM metacognition_signals"
    ).fetchone()
    last_at = last_row[0] if last_row else None
    return {
        "status": "OK" if last_24h > 0 else "STALE",
        "total": total,
        "last_24h": last_24h,
        "hours_since_last": round(_hours_ago(last_at) or -1, 2),
        "avg_24h": avg_by_dim,
    }


def probe_theory_of_mind(conn) -> dict[str, Any]:
    """Probe the partner_knowledge_facts ledger.

    Returns total fact count, counts split by origin (told-by-jarvis /
    stated-by-partner), hours since the last fact, and how many facts with
    reference_count >= 3 were touched in the last hour. Status is MISSING,
    EMPTY (no facts) or OK.
    """
    if not _table_exists(conn, "partner_knowledge_facts"):
        return {"status": "MISSING"}
    total = _count(conn, "SELECT COUNT(*) FROM partner_knowledge_facts")
    by_origin: dict[str, int] = {}
    for origin in ("told-by-jarvis", "stated-by-partner"):
        by_origin[origin] = _count(
            conn,
            "SELECT COUNT(*) FROM partner_knowledge_facts WHERE origin=?",
            (origin,),
        )
    last_row = conn.execute(
        "SELECT MAX(last_at) FROM partner_knowledge_facts"
    ).fetchone()
    last_at = last_row[0] if last_row else None
    repeat_count = _count(
        conn,
        "SELECT COUNT(*) FROM partner_knowledge_facts "
        "WHERE reference_count >= 3 AND last_at >= ?",
        ((datetime.now(UTC) - timedelta(hours=1)).isoformat(),),
    )
    return {
        "status": "OK" if total > 0 else "EMPTY",
        "total": total,
        "by_origin": by_origin,
        "hours_since_last": round(_hours_ago(last_at) or -1, 2),
        "repetitions_last_hour": repeat_count,
    }


def probe_spatial_entity(conn) -> dict[str, Any]:
    """Probe the room_entity_observations ledger.

    Returns the number of distinct entities, the top 5 entities by
    observation_count, and hours since the last observation. Status is
    MISSING, EMPTY (no rows) or OK.
    """
    if not _table_exists(conn, "room_entity_observations"):
        return {"status": "MISSING"}
    total = _count(conn, "SELECT COUNT(*) FROM room_entity_observations")
    top_rows = conn.execute(
        "SELECT entity_label, observation_count FROM room_entity_observations "
        "ORDER BY observation_count DESC LIMIT 5"
    ).fetchall()
    last_row = conn.execute(
        "SELECT MAX(last_seen_at) FROM room_entity_observations"
    ).fetchone()
    last_at = last_row[0] if last_row else None
    return {
        "status": "OK" if total > 0 else "EMPTY",
        "distinct_entities": total,
        "top_5": [(r["entity_label"], r["observation_count"]) for r in top_rows],
        "hours_since_last_observation": round(_hours_ago(last_at) or -1, 2),
    }


def probe_session_inbox(conn) -> dict[str, Any]:
    """Probe the session_inbox daemon gate.

    Returns the number of currently queued items, total delivered and dropped
    counts, and hours since the last delivery. Status is MISSING or OK.
    """
    if not _table_exists(conn, "session_inbox"):
        return {"status": "MISSING"}
    queued = _count(conn, "SELECT COUNT(*) FROM session_inbox WHERE status='queued'")
    delivered = _count(conn, "SELECT COUNT(*) FROM session_inbox WHERE status='delivered'")
    dropped = _count(conn, "SELECT COUNT(*) FROM session_inbox WHERE status='dropped'")
    last_delivery = conn.execute(
        "SELECT MAX(delivered_at) FROM session_inbox WHERE status='delivered'"
    ).fetchone()
    last_delivered_at = last_delivery[0] if last_delivery else None
    return {
        "status": "OK",
        "queued_now": queued,
        "delivered_total": delivered,
        "dropped_total": dropped,
        "hours_since_last_delivery": round(_hours_ago(last_delivered_at) or -1, 2),
    }


def probe_inner_voice_shadow(conn) -> dict[str, Any]:
    """Probe the inner_voice_shadow pilot.

    Returns total shadow count, successful (llm_output present, no error) and
    errored counts, the success rate, average LLM latency, average character
    length of the template vs LLM output, and hours since the last shadow.
    Status is MISSING, EMPTY (no rows) or OK.
    """
    if not _table_exists(conn, "inner_voice_shadow"):
        return {"status": "MISSING"}
    total = _count(conn, "SELECT COUNT(*) FROM inner_voice_shadow")
    success = _count(
        conn,
        "SELECT COUNT(*) FROM inner_voice_shadow "
        "WHERE llm_output IS NOT NULL AND llm_error IS NULL",
    )
    fail = _count(
        conn,
        "SELECT COUNT(*) FROM inner_voice_shadow WHERE llm_error IS NOT NULL",
    )
    row = conn.execute(
        "SELECT AVG(llm_latency_ms), AVG(length(template_output)), "
        "AVG(length(llm_output)) "
        "FROM inner_voice_shadow WHERE llm_output IS NOT NULL"
    ).fetchone()
    avg_latency = int(row[0] or 0)
    avg_template_chars = int(row[1] or 0)
    avg_llm_chars = int(row[2] or 0)
    last_row = conn.execute(
        "SELECT MAX(generated_at) FROM inner_voice_shadow"
    ).fetchone()
    last_at = last_row[0] if last_row else None
    success_rate = (success / total) if total else 0.0
    return {
        "status": "OK" if total > 0 else "EMPTY",
        "total_shadows": total,
        "successful": success,
        "errored": fail,
        "success_rate": round(success_rate, 3),
        "avg_latency_ms": avg_latency,
        "avg_template_chars": avg_template_chars,
        "avg_llm_chars": avg_llm_chars,
        "hours_since_last": round(_hours_ago(last_at) or -1, 2),
    }


def probe_visible_runs(conn) -> dict[str, Any]:
    """Sanity check: is the runtime actually producing visible runs?
    If yes → the events table is alive → the DB-polling trackers should
    be picking up activity. If no → trackers will show as STALE for
    legitimate reasons (no traffic) rather than broken listeners."""
    if not _table_exists(conn, "visible_runs"):
        return {"status": "MISSING"}
    last_24h = _count(
        conn,
        "SELECT COUNT(*) FROM visible_runs WHERE finished_at >= ?",
        ((datetime.now(UTC) - timedelta(hours=24)).isoformat(),),
    )
    last_1h = _count(
        conn,
        "SELECT COUNT(*) FROM visible_runs WHERE finished_at >= ?",
        ((datetime.now(UTC) - timedelta(hours=1)).isoformat(),),
    )
    last_row = conn.execute("SELECT MAX(finished_at) FROM visible_runs").fetchone()
    last_at = last_row[0] if last_row else None
    return {
        "status": "OK",
        "runs_last_24h": last_24h,
        "runs_last_hour": last_1h,
        "hours_since_last_run": round(_hours_ago(last_at) or -1, 2),
    }


# ── Output ───────────────────────────────────────────────────────────────


def render_text(report: dict[str, Any]) -> str:
    """Render the report dict as a human-readable text block.

    Prints one section per tracker with a status marker, followed by an
    overall verdict derived from the tracker statuses (all breathing,
    missing tables, stale trackers, or OK with empty trackers).
    """
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("META-EVNE HEALTHCHECK")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append("=" * 60)
    lines.append("")

    def section(title: str, data: dict[str, Any]) -> None:
        status = data.get("status", "?")
        marker = {"OK": "✓", "STALE": "⚠", "EMPTY": "·", "MISSING": "✗"}.get(status, "?")
        lines.append(f"{marker} {title}  ({status})")
        for k, v in data.items():
            if k == "status":
                continue
            lines.append(f"    {k}: {v}")
        lines.append("")

    section("Visible runs (traffic indicator)", report["visible_runs"])
    section("Metacognition tracker (E.v1)", report["metacognition"])
    section("Theory of Mind ledger (A.v1)", report["theory_of_mind"])
    section("Spatial entity ledger (D.v1)", report["spatial_entity"])
    section("Session inbox (daemon gate)", report["session_inbox"])
    section("Inner voice shadow (pilot)", report["inner_voice_shadow"])

    # Overall health summary
    statuses = [report[k].get("status") for k in (
        "metacognition", "theory_of_mind", "spatial_entity",
        "session_inbox", "inner_voice_shadow",
    )]
    if all(s == "OK" for s in statuses):
        verdict = "ALL TRACKERS BREATHING"
    elif any(s == "MISSING" for s in statuses):
        missing = [k for k in (
            "metacognition", "theory_of_mind", "spatial_entity",
            "session_inbox", "inner_voice_shadow",
        ) if report[k].get("status") == "MISSING"]
        verdict = f"MISSING TABLES: {', '.join(missing)}"
    elif any(s == "STALE" for s in statuses):
        stale = [k for k in (
            "metacognition", "theory_of_mind", "spatial_entity",
            "session_inbox", "inner_voice_shadow",
        ) if report[k].get("status") == "STALE"]
        verdict = f"STALE TRACKERS: {', '.join(stale)}"
    else:
        verdict = "OK with some empty trackers (awaiting first signal)"

    lines.append("-" * 60)
    lines.append(f"VERDICT: {verdict}")
    lines.append("-" * 60)
    return "\n".join(lines)


def main() -> int:
    """CLI entry point: run all tracker probes and print the report.

    Connects to the Jarvis DB, runs every probe into a report dict, and prints
    it as JSON (with --json) or formatted text. Returns 0 on success, 1 if the
    DB connection fails.
    """
    parser = argparse.ArgumentParser(description="Meta-evne healthcheck")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text")
    args = parser.parse_args()

    try:
        conn = _connect()
    except Exception as exc:
        print(f"ERROR: cannot connect to DB {DB_PATH}: {exc}", file=sys.stderr)
        return 1

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "db_path": str(DB_PATH),
        "visible_runs": probe_visible_runs(conn),
        "metacognition": probe_metacognition(conn),
        "theory_of_mind": probe_theory_of_mind(conn),
        "spatial_entity": probe_spatial_entity(conn),
        "session_inbox": probe_session_inbox(conn),
        "inner_voice_shadow": probe_inner_voice_shadow(conn),
    }
    conn.close()

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(render_text(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
