"""Curiosity-budget Phase 1 — tests.

AGI track #6 Åben udforskning. See spec at
docs/superpowers/specs/2026-05-12-curiosity-budget-phase1-design.md.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest


@pytest.fixture()
def clean_state(tmp_path, monkeypatch):
    """Isolated state_store + DB so curiosity-data doesn't pollute across tests."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("JARVIS_WORKSPACES_DIR", str(tmp_path / "workspaces"))
    # Force DB path to tmp
    import core.runtime.config as cfg
    monkeypatch.setattr(cfg, "STATE_DIR", str(tmp_path / "state"))
    import importlib
    import core.runtime.db as db
    importlib.reload(db)
    import core.runtime.state_store as ss
    importlib.reload(ss)
    import core.services.curiosity_budget as cb
    importlib.reload(cb)
    return None


def test_schema_bootstrap_creates_table(clean_state):
    """First call to ensure_schema() creates curiosity_observations + indexes."""
    from core.services.curiosity_budget import ensure_schema
    from core.runtime.db import connect

    ensure_schema()
    with connect() as conn:
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='curiosity_observations'"
        )
        row = cur.fetchone()
        assert row is not None, "curiosity_observations table missing"

        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='curiosity_observations'"
        )
        index_names = {r["name"] for r in cur.fetchall()}
        assert "idx_curiosity_ts" in index_names
        assert "idx_curiosity_action" in index_names


def test_schema_bootstrap_idempotent(clean_state):
    """Calling ensure_schema() twice doesn't error."""
    from core.services.curiosity_budget import ensure_schema
    ensure_schema()
    ensure_schema()  # should not raise
