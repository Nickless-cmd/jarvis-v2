"""Meta-læring Phase 1 — tests.

AGI track #3. See spec at
docs/superpowers/specs/2026-05-12-meta-learning-phase1-design.md.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest


@pytest.fixture()
def clean_state(tmp_path, monkeypatch):
    """Isolated workspace + DB so meta-learning data doesn't pollute tests."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("JARVIS_WORKSPACES_DIR", str(tmp_path / "workspaces"))
    import core.runtime.config as cfg
    monkeypatch.setattr(cfg, "STATE_DIR", str(tmp_path / "state"))
    import importlib
    import core.runtime.db as db
    importlib.reload(db)
    import core.runtime.state_store as ss
    importlib.reload(ss)
    return None


def test_schema_bootstrap_creates_table(clean_state):
    from core.services.meta_learning_retrospective import ensure_schema
    from core.runtime.db import connect

    ensure_schema()
    with connect() as conn:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='learning_memos'"
        ).fetchone()
        assert row is not None

        idx = {r["name"] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='learning_memos'"
        ).fetchall()}
        assert "idx_learning_memos_ts" in idx


def test_schema_bootstrap_idempotent(clean_state):
    from core.services.meta_learning_retrospective import ensure_schema
    ensure_schema()
    ensure_schema()  # should not raise
