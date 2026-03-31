"""Tests for the internal cadence layer.

Verifies:
- Producer registration and evaluation
- Cadence correctly marks producers as due / cooling_down / visible_grace / blocked
- Dispatch runs due producers in priority order
- Dependencies are respected
- Observability state is correct
- Existing daemon behavior is not broken through the cadence layer
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import apps.api.jarvis_api.services.internal_cadence as cadence_mod
from apps.api.jarvis_api.services.internal_cadence import (
    ProducerSpec,
    get_cadence_state,
    register_producer,
    run_cadence_tick,
    run_cadence_tick_with_bootstrap,
    _evaluate_producer,
)

import pytest


@pytest.fixture(autouse=True)
def _reset_cadence_state():
    """Reset cadence module state between tests."""
    cadence_mod._producers.clear()
    cadence_mod._last_run_at.clear()
    cadence_mod._last_tick_at = ""
    cadence_mod._last_tick_results.clear()
    yield
    cadence_mod._producers.clear()
    cadence_mod._last_run_at.clear()
    cadence_mod._last_tick_at = ""
    cadence_mod._last_tick_results.clear()


# ---------------------------------------------------------------------------
# Helper: simple producer that records calls
# ---------------------------------------------------------------------------

def _make_recorder(name: str = "test") -> tuple[ProducerSpec, list]:
    calls = []

    def run_fn(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        calls.append({"trigger": trigger, "last_visible_at": last_visible_at})
        return {"ran": True, "name": name}

    spec = ProducerSpec(
        name=name,
        cooldown_minutes=10,
        visible_grace_minutes=3,
        run_fn=run_fn,
        priority=5,
    )
    return spec, calls


# ---------------------------------------------------------------------------
# 1. Registration
# ---------------------------------------------------------------------------

def test_register_and_get_state(isolated_runtime) -> None:
    cadence = isolated_runtime.internal_cadence
    spec, _ = _make_recorder("alpha")
    cadence.register_producer(spec)

    state = cadence.get_cadence_state()
    assert state["producer_count"] == 1
    assert state["producers"][0]["name"] == "alpha"


# ---------------------------------------------------------------------------
# 2. Evaluation: due when cadence clear
# ---------------------------------------------------------------------------

def test_producer_due_when_fresh(isolated_runtime) -> None:
    spec, _ = _make_recorder()
    now = datetime.now(UTC)
    status, reason = _evaluate_producer(
        spec, now=now, last_visible_at=None, ran_this_tick=set(),
    )
    assert status == "due"
    assert reason == "cadence-clear"


# ---------------------------------------------------------------------------
# 3. Evaluation: cooling_down
# ---------------------------------------------------------------------------

def test_producer_cooling_down_after_recent_run(isolated_runtime) -> None:
    spec, _ = _make_recorder("cooler")
    now = datetime.now(UTC)
    cadence_mod._last_run_at["cooler"] = (now - timedelta(minutes=3)).isoformat()

    status, reason = _evaluate_producer(
        spec, now=now, last_visible_at=None, ran_this_tick=set(),
    )
    assert status == "cooling_down"
    assert "cooldown" in reason


def test_producer_due_after_cooldown_expires(isolated_runtime) -> None:
    spec, _ = _make_recorder("cooler")
    now = datetime.now(UTC)
    cadence_mod._last_run_at["cooler"] = (now - timedelta(minutes=15)).isoformat()

    status, reason = _evaluate_producer(
        spec, now=now, last_visible_at=None, ran_this_tick=set(),
    )
    assert status == "due"


# ---------------------------------------------------------------------------
# 4. Evaluation: visible_grace
# ---------------------------------------------------------------------------

def test_producer_visible_grace_when_too_recent(isolated_runtime) -> None:
    spec, _ = _make_recorder()
    now = datetime.now(UTC)
    last_visible = now - timedelta(minutes=1)

    status, reason = _evaluate_producer(
        spec, now=now, last_visible_at=last_visible, ran_this_tick=set(),
    )
    assert status == "visible_grace"
    assert "visible-too-recent" in reason


def test_producer_due_after_visible_grace_expires(isolated_runtime) -> None:
    spec, _ = _make_recorder()
    now = datetime.now(UTC)
    last_visible = now - timedelta(minutes=10)

    status, reason = _evaluate_producer(
        spec, now=now, last_visible_at=last_visible, ran_this_tick=set(),
    )
    assert status == "due"


# ---------------------------------------------------------------------------
# 5. Evaluation: dependency blocked
# ---------------------------------------------------------------------------

def test_producer_blocked_by_unmet_dependency(isolated_runtime) -> None:
    spec, _ = _make_recorder()
    spec.depends_on = ["brain_continuity"]
    now = datetime.now(UTC)

    status, reason = _evaluate_producer(
        spec, now=now, last_visible_at=None, ran_this_tick=set(),
    )
    assert status == "blocked"
    assert "dependency-not-met" in reason


def test_producer_due_when_dependency_met(isolated_runtime) -> None:
    spec, _ = _make_recorder()
    spec.depends_on = ["brain_continuity"]
    now = datetime.now(UTC)

    status, reason = _evaluate_producer(
        spec, now=now, last_visible_at=None, ran_this_tick={"brain_continuity"},
    )
    assert status == "due"


# ---------------------------------------------------------------------------
# 6. Tick dispatch: priority ordering
# ---------------------------------------------------------------------------

def test_tick_dispatches_in_priority_order(isolated_runtime) -> None:
    cadence = isolated_runtime.internal_cadence
    order = []

    def make_fn(name):
        def fn(*, trigger, last_visible_at=""):
            order.append(name)
            return {"ran": True}
        return fn

    cadence.register_producer(ProducerSpec(
        name="low_priority", cooldown_minutes=0, visible_grace_minutes=0,
        run_fn=make_fn("low_priority"), priority=20,
    ))
    cadence.register_producer(ProducerSpec(
        name="high_priority", cooldown_minutes=0, visible_grace_minutes=0,
        run_fn=make_fn("high_priority"), priority=1,
    ))
    cadence.register_producer(ProducerSpec(
        name="mid_priority", cooldown_minutes=0, visible_grace_minutes=0,
        run_fn=make_fn("mid_priority"), priority=10,
    ))

    result = cadence.run_cadence_tick(trigger="test")
    assert order == ["high_priority", "mid_priority", "low_priority"]
    assert set(result["ran"]) == {"high_priority", "mid_priority", "low_priority"}


# ---------------------------------------------------------------------------
# 7. Tick dispatch: due vs cooling_down observable
# ---------------------------------------------------------------------------

def test_tick_shows_cooling_and_due(isolated_runtime) -> None:
    cadence = isolated_runtime.internal_cadence
    calls = []

    def run_fn(*, trigger, last_visible_at=""):
        calls.append(trigger)
        return {"ran": True}

    cadence.register_producer(ProducerSpec(
        name="fast", cooldown_minutes=0, visible_grace_minutes=0,
        run_fn=run_fn, priority=1,
    ))
    cadence.register_producer(ProducerSpec(
        name="slow", cooldown_minutes=60, visible_grace_minutes=0,
        run_fn=run_fn, priority=2,
    ))

    # First tick: both run
    r1 = cadence.run_cadence_tick(trigger="tick-1")
    assert "fast" in r1["ran"]
    assert "slow" in r1["ran"]

    # Second tick: fast runs again (cooldown=0), slow cooling
    r2 = cadence.run_cadence_tick(trigger="tick-2")
    assert "fast" in r2["ran"]
    assert "slow" in r2["cooling_down"]


# ---------------------------------------------------------------------------
# 8. Error handling: producer failure doesn't block others
# ---------------------------------------------------------------------------

def test_producer_error_doesnt_block_others(isolated_runtime) -> None:
    cadence = isolated_runtime.internal_cadence

    def failing_fn(*, trigger, last_visible_at=""):
        raise RuntimeError("boom")

    ok_calls = []
    def ok_fn(*, trigger, last_visible_at=""):
        ok_calls.append(True)
        return {"ran": True}

    cadence.register_producer(ProducerSpec(
        name="fails", cooldown_minutes=0, visible_grace_minutes=0,
        run_fn=failing_fn, priority=1,
    ))
    cadence.register_producer(ProducerSpec(
        name="succeeds", cooldown_minutes=0, visible_grace_minutes=0,
        run_fn=ok_fn, priority=2,
    ))

    result = cadence.run_cadence_tick(trigger="test")
    assert "fails" in result["errors"]
    assert "succeeds" in result["ran"]
    assert len(ok_calls) == 1


# ---------------------------------------------------------------------------
# 9. Observability: get_cadence_state reflects last tick
# ---------------------------------------------------------------------------

def test_cadence_state_reflects_last_tick(isolated_runtime) -> None:
    cadence = isolated_runtime.internal_cadence
    spec, _ = _make_recorder("alpha")
    cadence.register_producer(spec)

    cadence.run_cadence_tick(trigger="test")

    state = cadence.get_cadence_state()
    assert state["last_tick_at"] is not None
    assert state["producer_count"] == 1
    assert state["last_tick_summary"]["ran"] == ["alpha"]
    assert state["producers"][0]["last_run_at"] is not None
    assert state["producers"][0]["last_tick_status"]["status"] == "ran"


# ---------------------------------------------------------------------------
# 10. Bootstrap: known producers get registered
# ---------------------------------------------------------------------------

def test_bootstrap_registers_known_producers(isolated_runtime) -> None:
    cadence = isolated_runtime.internal_cadence
    # Clear to force re-bootstrap
    cadence._producers.clear()

    result = cadence.run_cadence_tick_with_bootstrap(trigger="test")
    assert result["producer_count"] == 3

    state = cadence.get_cadence_state()
    names = [p["name"] for p in state["producers"]]
    assert "brain_continuity" in names
    assert "witness_daemon" in names
    assert "inner_voice_daemon" in names

    # Verify priority ordering
    priorities = {p["name"]: p["priority"] for p in state["producers"]}
    assert priorities["brain_continuity"] < priorities["witness_daemon"]
    assert priorities["witness_daemon"] < priorities["inner_voice_daemon"]


# ---------------------------------------------------------------------------
# 11. Dependencies: inner voice waits for witness
# ---------------------------------------------------------------------------

def test_inner_voice_blocked_when_witness_not_ran(isolated_runtime) -> None:
    cadence = isolated_runtime.internal_cadence
    cadence._producers.clear()

    # Register only inner voice (not witness or brain) — dependencies unmet
    calls = []
    def dummy_fn(*, trigger, last_visible_at=""):
        calls.append(True)
        return {"ran": True}

    cadence.register_producer(ProducerSpec(
        name="inner_voice_daemon",
        cooldown_minutes=0, visible_grace_minutes=0,
        run_fn=dummy_fn, priority=10,
        depends_on=["witness_daemon"],
    ))

    result = cadence.run_cadence_tick(trigger="test")
    assert "inner_voice_daemon" in result["blocked"]
    assert len(calls) == 0


# ---------------------------------------------------------------------------
# 12. MC endpoint works
# ---------------------------------------------------------------------------

def test_mc_cadence_endpoint(isolated_runtime) -> None:
    mc = isolated_runtime.mission_control
    # Just verify the endpoint function exists and returns a dict
    response = mc.mc_internal_cadence()
    assert isinstance(response, dict)
    assert "producer_count" in response
