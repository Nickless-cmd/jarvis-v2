"""Meta-læring retrospective generator — Phase 1 (AGI track #3).

Genererer ugentligt retrospektiv-memo via cheap-lane LLM. Syntetiserer
aktivitet fra 5 AGI-spor til prosa-fortælling med citationsnøgler +
struktureret hypothesis-blok (0-3 kandidater).

Schema-bootstrap lives here (not in db.py) per Boy Scout Rule.

See spec: docs/superpowers/specs/2026-05-12-meta-learning-phase1-design.md
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from core.runtime.db import connect

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Schema bootstrap
# ---------------------------------------------------------------------------

_SCHEMA_INITIALIZED = False


def ensure_schema() -> None:
    """Idempotently create learning_memos table + index."""
    global _SCHEMA_INITIALIZED
    if _SCHEMA_INITIALIZED:
        return
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS learning_memos (
              memo_id TEXT PRIMARY KEY,
              ts TEXT NOT NULL,
              period_start TEXT NOT NULL,
              period_end TEXT NOT NULL,
              narrative TEXT NOT NULL,
              hypothesis_candidates_json TEXT NOT NULL,
              aggregator_snapshot_json TEXT NOT NULL,
              model_used TEXT,
              acknowledged_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_learning_memos_ts
              ON learning_memos(ts);
            """
        )
        conn.commit()
    _SCHEMA_INITIALIZED = True
