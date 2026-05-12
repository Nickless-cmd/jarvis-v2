"""Curiosity-budget service — Phase 1 (AGI track #6 Åben udforskning).

Private space for Jarvis to use 5 read-only actions/day on his own mental
landscape. State (budget + idle-window) in state_store; observations
persisted in dedicated SQLite table `curiosity_observations`.

Schema-bootstrap lives here (not in db.py) per the Boy Scout Rule — db.py
is 33k lines, so new modules manage their own schema idempotently.

See spec: docs/superpowers/specs/2026-05-12-curiosity-budget-phase1-design.md
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from core.runtime.db import connect
from core.runtime.state_store import load_json, save_json

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Schema bootstrap
# ---------------------------------------------------------------------------

_SCHEMA_INITIALIZED = False


def ensure_schema() -> None:
    """Idempotently create curiosity_observations table + indexes.

    Called automatically by all public functions in this module before they
    touch the DB. Safe to call repeatedly.
    """
    global _SCHEMA_INITIALIZED
    if _SCHEMA_INITIALIZED:
        return
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS curiosity_observations (
              id TEXT PRIMARY KEY,
              ts TEXT NOT NULL,
              action TEXT NOT NULL,
              args_json TEXT NOT NULL,
              observation_text TEXT NOT NULL,
              follow_up_hint TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_curiosity_ts
              ON curiosity_observations(ts);
            CREATE INDEX IF NOT EXISTS idx_curiosity_action
              ON curiosity_observations(action);
            """
        )
        conn.commit()
    _SCHEMA_INITIALIZED = True
