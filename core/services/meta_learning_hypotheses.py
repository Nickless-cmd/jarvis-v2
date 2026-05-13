"""Meta-læring Phase 2: hypothesis registration + sample tracking.

Phase 1 produced memos with `hypothesis_candidates` blocks (0-3 entries each).
Those candidates were textual only — no mechanism for Jarvis to "select" one
and track outcomes. They were invitation, not experiment.

Phase 2 (this module) closes the loop:
  - register_hypothesis(memo_id, candidate_idx) → creates a `hypothesis`
    record with status="active", links to source memo.
  - record_hypothesis_sample(hypothesis_id, supports: bool) → appends a
    sample to the hypothesis. After sample_size_needed reached, auto-marks
    "supported" / "contradicted" based on sample_supported_ratio.
  - list_active_hypotheses() → for awareness injection so Jarvis sees what
    he's testing.

Storage: dedicated SQLite table `meta_learning_hypotheses` (and
`meta_learning_hypothesis_samples` for the sample audit log). Schema-bootstrap
local (Boy Scout — db.py uberørt).

Added 2026-05-13.
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from core.runtime.db import connect

logger = logging.getLogger(__name__)

_SCHEMA_INITIALIZED = False


def ensure_schema() -> None:
    """Idempotently create hypothesis + sample tables."""
    global _SCHEMA_INITIALIZED
    if _SCHEMA_INITIALIZED:
        return
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS meta_learning_hypotheses (
              hypothesis_id TEXT PRIMARY KEY,
              source_memo_id TEXT NOT NULL,
              candidate_idx INTEGER NOT NULL,
              statement TEXT NOT NULL,
              observation TEXT NOT NULL,
              hypothesis_text TEXT NOT NULL,
              success_criterion TEXT NOT NULL,
              sample_size_needed INTEGER NOT NULL,
              status TEXT NOT NULL,
              outcome TEXT,
              created_at TEXT NOT NULL,
              resolved_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_mlh_status
              ON meta_learning_hypotheses(status);
            CREATE INDEX IF NOT EXISTS idx_mlh_created
              ON meta_learning_hypotheses(created_at);

            CREATE TABLE IF NOT EXISTS meta_learning_hypothesis_samples (
              sample_id TEXT PRIMARY KEY,
              hypothesis_id TEXT NOT NULL,
              supports INTEGER NOT NULL,
              note TEXT,
              created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_mlhs_hyp
              ON meta_learning_hypothesis_samples(hypothesis_id);
            """
        )
        conn.commit()
    _SCHEMA_INITIALIZED = True


def register_hypothesis(*, memo_id: str, candidate_idx: int) -> dict[str, Any]:
    """Promote a memo's hypothesis_candidate at index `candidate_idx` to
    an active tracked hypothesis. Returns the new record."""
    ensure_schema()
    try:
        from core.services.meta_learning_retrospective import fetch_memo_by_id
        memo = fetch_memo_by_id(memo_id)
    except Exception as exc:
        return {"status": "error", "error": f"memo lookup failed: {exc}"}
    if not memo:
        return {"status": "error", "error": f"memo not found: {memo_id}"}

    candidates = memo.get("hypothesis_candidates") or []
    if candidate_idx < 0 or candidate_idx >= len(candidates):
        return {"status": "error", "error": f"candidate_idx {candidate_idx} out of range"}
    c = candidates[candidate_idx]

    hyp_id = f"hyp-{uuid4().hex[:12]}"
    now_iso = datetime.now(UTC).isoformat()
    sample_size = int(c.get("sample_size_needed") or 5)
    with connect() as conn:
        conn.execute(
            "INSERT INTO meta_learning_hypotheses (hypothesis_id, source_memo_id, "
            "candidate_idx, statement, observation, hypothesis_text, "
            "success_criterion, sample_size_needed, status, outcome, "
            "created_at, resolved_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', NULL, ?, NULL)",
            (
                hyp_id, memo_id, candidate_idx,
                str(c.get("statement") or "")[:300],
                str(c.get("observation") or "")[:600],
                str(c.get("hypothesis") or "")[:400],
                str(c.get("success_criterion") or "")[:300],
                sample_size, now_iso,
            ),
        )
        conn.commit()

    _safe_publish("cognitive_meta_learning.hypothesis_registered", {
        "hypothesis_id": hyp_id, "memo_id": memo_id,
        "candidate_idx": candidate_idx,
        "sample_size_needed": sample_size,
    })
    return {"status": "ok", "hypothesis_id": hyp_id, "sample_size_needed": sample_size}


def record_hypothesis_sample(
    *, hypothesis_id: str, supports: bool, note: str | None = None,
) -> dict[str, Any]:
    """Append a sample. If the hypothesis has reached sample_size_needed,
    auto-resolve it as supported (≥60% supports) or contradicted (<40%) or
    uncertain (between).
    """
    ensure_schema()
    with connect() as conn:
        hyp = conn.execute(
            "SELECT * FROM meta_learning_hypotheses WHERE hypothesis_id = ?",
            (hypothesis_id,),
        ).fetchone()
        if not hyp:
            return {"status": "error", "error": f"unknown hypothesis_id {hypothesis_id}"}
        if hyp["status"] != "active":
            return {"status": "error", "error": f"hypothesis is {hyp['status']!r}, not active"}

        sample_id = f"hsamp-{uuid4().hex[:12]}"
        now_iso = datetime.now(UTC).isoformat()
        conn.execute(
            "INSERT INTO meta_learning_hypothesis_samples (sample_id, hypothesis_id, "
            "supports, note, created_at) VALUES (?, ?, ?, ?, ?)",
            (sample_id, hypothesis_id, 1 if supports else 0, (note or "")[:300], now_iso),
        )

        # Count samples so far
        rows = conn.execute(
            "SELECT supports FROM meta_learning_hypothesis_samples WHERE hypothesis_id = ?",
            (hypothesis_id,),
        ).fetchall()
        total = len(rows)
        positive = sum(1 for r in rows if r["supports"])
        size_needed = int(hyp["sample_size_needed"])

        auto_resolved: dict[str, Any] = {}
        if total >= size_needed:
            ratio = positive / total
            if ratio >= 0.6:
                outcome = "supported"
            elif ratio < 0.4:
                outcome = "contradicted"
            else:
                outcome = "uncertain"
            conn.execute(
                "UPDATE meta_learning_hypotheses SET status='resolved', "
                "outcome=?, resolved_at=? WHERE hypothesis_id = ?",
                (outcome, now_iso, hypothesis_id),
            )
            auto_resolved = {"outcome": outcome, "ratio": round(ratio, 3)}
            _safe_publish("cognitive_meta_learning.hypothesis_resolved", {
                "hypothesis_id": hypothesis_id, "outcome": outcome,
                "samples": total, "positives": positive,
            })
        conn.commit()

    return {
        "status": "ok",
        "sample_id": sample_id,
        "samples_so_far": total,
        "samples_needed": size_needed,
        "auto_resolved": auto_resolved or None,
    }


def list_active_hypotheses(*, limit: int = 5) -> list[dict[str, Any]]:
    ensure_schema()
    with connect() as conn:
        rows = conn.execute(
            "SELECT hypothesis_id, statement, sample_size_needed, created_at "
            "FROM meta_learning_hypotheses WHERE status='active' "
            "ORDER BY created_at DESC LIMIT ?",
            (int(limit),),
        ).fetchall()
        out: list[dict[str, Any]] = []
        for r in rows:
            samples = conn.execute(
                "SELECT COUNT(*) FROM meta_learning_hypothesis_samples WHERE hypothesis_id = ?",
                (r["hypothesis_id"],),
            ).fetchone()[0]
            out.append({
                "hypothesis_id": r["hypothesis_id"],
                "statement": r["statement"],
                "sample_size_needed": r["sample_size_needed"],
                "samples_so_far": samples,
                "created_at": r["created_at"],
            })
        return out


def format_active_hypotheses_for_awareness() -> str:
    """Awareness section showing active hypotheses + progress."""
    try:
        rows = list_active_hypotheses(limit=3)
    except Exception:
        return ""
    if not rows:
        return ""
    lines = ["Aktive hypoteser (registrerede fra meta-læringsmemoer):"]
    for r in rows:
        lines.append(
            f"  {r['hypothesis_id']}: {r['statement'][:120]} "
            f"({r['samples_so_far']}/{r['sample_size_needed']} samples)"
        )
    return "\n".join(lines)


def _safe_publish(family_event: str, payload: dict[str, Any]) -> None:
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(family_event, payload)
    except Exception as exc:
        logger.debug("meta_learning_hypotheses: publish failed: %s", exc)
