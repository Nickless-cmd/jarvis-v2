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


def test_load_budget_fresh_returns_full(clean_state):
    """First call on a fresh day returns 5/5 remaining."""
    from core.services.curiosity_budget import load_or_reset_budget
    state = load_or_reset_budget()
    assert state["remaining"] == 5
    assert state["used_today"] == []
    assert state["date"] == datetime.now(UTC).strftime("%Y-%m-%d")


def test_load_budget_resets_on_new_day(clean_state, monkeypatch):
    """If stored date != today, budget resets."""
    from core.services import curiosity_budget as cb
    # Seed yesterday's spent state directly
    yesterday = (datetime.now(UTC) - timedelta(days=1)).strftime("%Y-%m-%d")
    from core.runtime.state_store import save_json
    save_json("runtime_curiosity_budget", {
        "date": yesterday,
        "remaining": 0,
        "used_today": [{"ts": "x", "action": "y", "observation_id": "z"}],
    })

    state = cb.load_or_reset_budget()
    assert state["remaining"] == 5
    assert state["used_today"] == []
    assert state["date"] == datetime.now(UTC).strftime("%Y-%m-%d")


def test_decrement_budget_returns_new_remaining(clean_state):
    from core.services.curiosity_budget import decrement_budget, load_or_reset_budget

    load_or_reset_budget()  # seed 5/5
    result = decrement_budget(action="search_memory", observation_id="obs-1")
    assert result["status"] == "ok"
    assert result["remaining"] == 4

    state2 = load_or_reset_budget()
    assert state2["remaining"] == 4
    assert len(state2["used_today"]) == 1
    assert state2["used_today"][0]["action"] == "search_memory"
    assert state2["used_today"][0]["observation_id"] == "obs-1"


def test_decrement_budget_blocks_at_zero(clean_state):
    """When remaining==0, decrement returns error and does not mutate."""
    from core.services.curiosity_budget import decrement_budget, load_or_reset_budget
    load_or_reset_budget()
    for i in range(5):
        decrement_budget(action="x", observation_id=f"o{i}")
    result = decrement_budget(action="x", observation_id="should-fail")
    assert result["status"] == "error"
    assert "brugt op" in result["error"]

    state = load_or_reset_budget()
    assert state["remaining"] == 0
    assert len(state["used_today"]) == 5  # not 6


def test_record_observation_persists_row(clean_state):
    from core.services.curiosity_budget import record_observation
    from core.runtime.db import connect

    obs_id = record_observation(
        action="search_memory",
        args_json='{"query": "first kontinuitet"}',
        observation_text="Jeg vil se mit eget mønster i kontinuitets-snak.",
        follow_up_hint="Følg op på trådene fra dengang jeg sagde jeg var bange.",
    )
    assert obs_id.startswith("obs-")

    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM curiosity_observations WHERE id = ?", (obs_id,)
        ).fetchone()
        assert row is not None
        assert row["action"] == "search_memory"
        assert row["observation_text"].startswith("Jeg vil")
        assert row["follow_up_hint"].startswith("Følg op")


def test_record_observation_handles_no_follow_up(clean_state):
    from core.services.curiosity_budget import record_observation
    from core.runtime.db import connect
    obs_id = record_observation(
        action="read_dreams",
        args_json="{}",
        observation_text="Bare nysgerrig på hvad jeg har drømt.",
        follow_up_hint=None,
    )
    with connect() as conn:
        row = conn.execute(
            "SELECT follow_up_hint FROM curiosity_observations WHERE id = ?",
            (obs_id,),
        ).fetchone()
        assert row["follow_up_hint"] is None


def test_fetch_recent_observations_returns_newest_first(clean_state):
    """Used by awareness-injection to show 2-3 most recent observations."""
    from core.services.curiosity_budget import fetch_recent_observations, record_observation

    obs_a = record_observation("read_dreams", "{}", "first obs", None)
    obs_b = record_observation("read_dreams", "{}", "second obs", None)
    obs_c = record_observation("read_dreams", "{}", "third obs", None)

    rows = fetch_recent_observations(limit=2)
    assert len(rows) == 2
    assert rows[0]["id"] == obs_c
    assert rows[1]["id"] == obs_b
