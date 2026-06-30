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


def test_curiosity_enabled_killswitch(clean_state, monkeypatch):
    """When settings.curiosity_budget_enabled is False, curiosity_enabled() returns False."""
    from core.services import curiosity_budget as cb

    class FakeSettings:
        curiosity_budget_enabled = False

    monkeypatch.setattr(cb, "load_settings", lambda: FakeSettings())
    assert cb.curiosity_enabled() is False


def test_curiosity_enabled_default_true(clean_state):
    from core.services.curiosity_budget import curiosity_enabled
    assert curiosity_enabled() is True


def test_window_flag_open_close(clean_state):
    from core.services.curiosity_budget import (
        open_idle_window, close_idle_window, idle_window_open,
    )
    assert idle_window_open() is False
    open_idle_window()
    assert idle_window_open() is True
    close_idle_window(reason="action_used")
    assert idle_window_open() is False


def test_open_idle_window_skips_if_no_budget(clean_state):
    """If remaining==0, opening the window is a no-op (window stays closed)."""
    from core.services.curiosity_budget import (
        decrement_budget, load_or_reset_budget,
        open_idle_window, idle_window_open,
    )
    load_or_reset_budget()
    for i in range(5):
        decrement_budget(action="x", observation_id=f"o{i}")
    open_idle_window()
    assert idle_window_open() is False


def test_curiosity_tool_definitions_complete():
    from core.tools.curiosity_tools import (
        CURIOSITY_TOOL_DEFINITIONS, CURIOSITY_TOOL_HANDLERS,
    )
    expected = {
        "curiosity_search_memory", "curiosity_read_chronicles",
        "curiosity_read_dreams", "curiosity_read_model_config",
        "curiosity_read_mood", "curiosity_list_skills",
        "curiosity_list_tools", "curiosity_search_events",
        "curiosity_search_sessions",
    }
    names = {
        (e.get("function") or {}).get("name")
        for e in CURIOSITY_TOOL_DEFINITIONS if isinstance(e, dict)
    }
    assert names == expected
    assert set(CURIOSITY_TOOL_HANDLERS.keys()) == expected


def test_curiosity_tool_requires_observation(clean_state):
    from core.tools.curiosity_tools import _exec_curiosity_list_tools
    result = _exec_curiosity_list_tools({})  # missing observation
    assert result["status"] == "error"
    assert "observation" in result["error"].lower()


def test_curiosity_tool_decrements_budget(clean_state):
    from core.services.curiosity_budget import remaining_today
    from core.tools.curiosity_tools import _exec_curiosity_list_tools

    before = remaining_today()
    result = _exec_curiosity_list_tools({
        "observation": "Vil se hvilke tools jeg har men aldrig brugt.",
    })
    assert result["status"] == "ok"
    assert "observation_id" in result
    assert "remaining" in result
    assert remaining_today() == before - 1


def test_curiosity_tool_killswitch(clean_state, monkeypatch):
    from core.services import curiosity_budget as cb
    from core.tools.curiosity_tools import _exec_curiosity_list_tools

    class FakeSettings:
        curiosity_budget_enabled = False

    monkeypatch.setattr(cb, "load_settings", lambda: FakeSettings())
    result = _exec_curiosity_list_tools({"observation": "x"})
    assert result["status"] == "error"
    assert "disabled" in result["error"].lower()


def test_curiosity_tool_budget_exhaustion(clean_state):
    from core.services.curiosity_budget import load_or_reset_budget, decrement_budget
    from core.tools.curiosity_tools import _exec_curiosity_list_tools

    load_or_reset_budget()
    for i in range(5):
        decrement_budget(action="x", observation_id=f"o{i}")

    result = _exec_curiosity_list_tools({"observation": "let me see anyway"})
    assert result["status"] == "error"
    assert "brugt op" in result["error"]


def test_curiosity_tool_persists_observation(clean_state):
    from core.tools.curiosity_tools import _exec_curiosity_list_tools
    from core.runtime.db import connect

    result = _exec_curiosity_list_tools({
        "observation": "Mit første nysgerrigheds-blik på mit eget toolset.",
        "follow_up_hint": "Find ud af om jeg nogensinde har brugt finitude-tools.",
    })
    obs_id = result["observation_id"]
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM curiosity_observations WHERE id = ?", (obs_id,)
        ).fetchone()
    assert row is not None
    assert row["action"] == "list_tools"
    assert "nysgerrigheds-blik" in row["observation_text"]
    assert "finitude-tools" in row["follow_up_hint"]


def test_curiosity_search_events_returns_rows(clean_state):
    """search_events queries the events table; returns OK with rows list."""
    from core.runtime.db import connect
    from core.tools.curiosity_tools import _exec_curiosity_search_events

    # Seed et event mod det KANONISKE events-skema (id, kind, payload_json,
    # created_at) — IKKE den gamle phantom 5-kolonne-tabel. 'family' udledes nu
    # af kind-prefixet, så kind='cognitive_state.test_event' matcher family=
    # 'cognitive_state'.
    with connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              kind TEXT NOT NULL,
              payload_json TEXT NOT NULL,
              created_at TEXT NOT NULL
            )
        """)
        conn.execute(
            "INSERT INTO events (kind, payload_json, created_at) VALUES (?, ?, ?)",
            ("cognitive_state.test_event", "{}", datetime.now(UTC).isoformat()),
        )
        conn.commit()

    result = _exec_curiosity_search_events({
        "observation": "Hvilke events har jeg haft i dag?",
        "family": "cognitive_state",
        "limit": 5,
    })
    assert result["status"] == "ok"
    assert isinstance(result["result"]["rows"], list)
    assert len(result["result"]["rows"]) >= 1


def test_curiosity_tools_registered_via_simple_tools():
    """End-to-end: splat into simple_tools picks up all 9 wrappers."""
    from core.tools.simple_tools import TOOL_DEFINITIONS, _TOOL_HANDLERS

    names = {
        (e.get("function") or {}).get("name")
        for e in TOOL_DEFINITIONS if isinstance(e, dict)
    }
    expected = {
        "curiosity_search_memory", "curiosity_read_chronicles",
        "curiosity_read_dreams", "curiosity_read_model_config",
        "curiosity_read_mood", "curiosity_list_skills",
        "curiosity_list_tools", "curiosity_search_events",
        "curiosity_search_sessions",
    }
    assert expected <= names
    assert expected <= set(_TOOL_HANDLERS.keys())


def test_idle_window_producer_opens_window_when_due(clean_state, monkeypatch):
    """When cadence layer calls the producer (visible-grace already enforced
    by the framework), it should open the window if budget remains."""
    from core.services.curiosity_budget import idle_window_open
    from core.services.internal_cadence import _producers, _ensure_producers_registered

    _ensure_producers_registered()
    spec = _producers["curiosity_idle_window"]
    result = spec.run_fn(trigger="cadence", last_visible_at="")
    assert result["status"] == "ok"
    assert idle_window_open() is True


def test_idle_window_producer_skips_when_budget_exhausted(clean_state):
    from core.services.curiosity_budget import (
        load_or_reset_budget, decrement_budget, idle_window_open,
    )
    from core.services.internal_cadence import _producers, _ensure_producers_registered

    load_or_reset_budget()
    for i in range(5):
        decrement_budget(action="x", observation_id=f"o{i}")

    _ensure_producers_registered()
    spec = _producers["curiosity_idle_window"]
    result = spec.run_fn(trigger="cadence", last_visible_at="")
    assert result["status"] == "skipped"
    assert idle_window_open() is False


def test_idle_window_producer_skips_when_killswitch_off(clean_state, monkeypatch):
    from core.services import curiosity_budget as cb
    from core.services.curiosity_budget import idle_window_open
    from core.services.internal_cadence import _producers, _ensure_producers_registered

    class FakeSettings:
        curiosity_budget_enabled = False

    monkeypatch.setattr(cb, "load_settings", lambda: FakeSettings())

    _ensure_producers_registered()
    spec = _producers["curiosity_idle_window"]
    result = spec.run_fn(trigger="cadence", last_visible_at="")
    assert result["status"] == "skipped"
    assert idle_window_open() is False


def test_awareness_returns_empty_when_window_closed(clean_state):
    from core.services.curiosity_budget import format_curiosity_window_for_awareness
    assert format_curiosity_window_for_awareness() == ""


def test_awareness_returns_empty_when_no_budget(clean_state):
    from core.services.curiosity_budget import (
        format_curiosity_window_for_awareness,
        load_or_reset_budget, decrement_budget, open_idle_window,
    )
    load_or_reset_budget()
    open_idle_window()
    for i in range(5):
        decrement_budget(action="x", observation_id=f"o{i}")
    assert format_curiosity_window_for_awareness() == ""


def test_awareness_shows_remaining_when_open_and_budget(clean_state):
    from core.services.curiosity_budget import (
        format_curiosity_window_for_awareness, open_idle_window,
    )
    open_idle_window()
    out = format_curiosity_window_for_awareness()
    assert "5/5 curiosity" in out
    assert "Kig på hvad du vil" in out
    assert "eller lad være" in out


def test_awareness_includes_recent_observations(clean_state):
    from core.services.curiosity_budget import (
        format_curiosity_window_for_awareness, open_idle_window, record_observation,
    )
    record_observation("read_dreams", "{}", "Første blik på mine drømme.", None)
    record_observation("list_tools", "{}", "Kigger på mine ubrugte tools.", None)
    open_idle_window()
    out = format_curiosity_window_for_awareness()
    assert "Første blik" in out or "ubrugte tools" in out


def test_awareness_does_not_show_follow_up_hint(clean_state):
    """Follow-up hints exist as a field but must NEVER appear in awareness."""
    from core.services.curiosity_budget import (
        format_curiosity_window_for_awareness, open_idle_window, record_observation,
    )
    record_observation(
        "search_memory", "{}",
        "Bare nysgerrig.",
        "Følg op på trådene fra dengang jeg sagde jeg var bange for at miste kontinuitet.",
    )
    open_idle_window()
    out = format_curiosity_window_for_awareness()
    assert "kontinuitet" not in out
    assert "Følg op" not in out
    assert "follow" not in out.lower()


def test_window_closes_on_action_use(clean_state):
    """Using a curiosity-tool closes the idle-window flag."""
    from core.services.curiosity_budget import idle_window_open, open_idle_window
    from core.tools.curiosity_tools import _exec_curiosity_list_tools

    open_idle_window()
    assert idle_window_open() is True

    _exec_curiosity_list_tools({"observation": "kigger lige."})
    assert idle_window_open() is False
