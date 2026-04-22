"""Agent auto-cleanup tests — stale waiting + failed agents."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest


def _backdate_agent(agent_id: str, *, status: str, minutes_ago: int) -> None:
    """Force an agent's updated_at back in time + set status. Used to
    simulate a stale/hanging agent without waiting real time."""
    from core.runtime.db import connect
    ts = (datetime.now(UTC) - timedelta(minutes=minutes_ago)).isoformat()
    with connect() as conn:
        conn.execute(
            "UPDATE agent_registry SET status = ?, updated_at = ? WHERE agent_id = ?",
            (status, ts, agent_id),
        )
        conn.commit()


def _make_agent(agent_id_suffix: str) -> str:
    """Create a minimal agent_registry row for testing."""
    from uuid import uuid4
    from core.runtime.db import (
        create_agent_registry_entry, get_agent_registry_entry,
    )
    agent_id = f"agent-test-{agent_id_suffix}-{uuid4().hex[:8]}"
    create_agent_registry_entry(
        agent_id=agent_id,
        role="test",
        goal="cleanup test",
        status="queued",
        provider="stub",
        model="stub",
    )
    return agent_id


def test_cleanup_cancels_waiting_agents_over_threshold(isolated_runtime):
    """Agent i waiting >120 min skal blive cancelled."""
    from core.services.agent_runtime import cleanup_stale_agents
    from core.runtime.db import get_agent_registry_entry

    agent_id = _make_agent("stale_wait")
    # Backdate til waiting + 3 timer siden
    _backdate_agent(agent_id, status="waiting", minutes_ago=180)

    result = cleanup_stale_agents(
        waiting_timeout_minutes=120,
        failed_timeout_minutes=30,
    )

    assert agent_id in result["cancelled_waiting_ids"]
    assert result["cancelled_waiting_count"] >= 1

    updated = get_agent_registry_entry(agent_id)
    assert updated["status"] == "cancelled"
    assert "auto_cleanup_stale_waiting" in str(updated.get("last_error") or "")


def test_cleanup_preserves_recent_waiting(isolated_runtime):
    """Agent i waiting <120 min skal IKKE cancelles."""
    from core.services.agent_runtime import cleanup_stale_agents
    from core.runtime.db import get_agent_registry_entry

    agent_id = _make_agent("fresh_wait")
    _backdate_agent(agent_id, status="waiting", minutes_ago=30)  # kun 30 min

    result = cleanup_stale_agents(
        waiting_timeout_minutes=120,
        failed_timeout_minutes=30,
    )

    assert agent_id not in result["cancelled_waiting_ids"]
    updated = get_agent_registry_entry(agent_id)
    assert updated["status"] == "waiting"


def test_cleanup_cancels_failed_agents_over_threshold(isolated_runtime):
    """Agent i failed >30 min skal blive cancelled."""
    from core.services.agent_runtime import cleanup_stale_agents
    from core.runtime.db import get_agent_registry_entry

    agent_id = _make_agent("stale_fail")
    _backdate_agent(agent_id, status="failed", minutes_ago=45)

    result = cleanup_stale_agents(
        waiting_timeout_minutes=120,
        failed_timeout_minutes=30,
    )

    assert agent_id in result["cancelled_failed_ids"]
    updated = get_agent_registry_entry(agent_id)
    assert updated["status"] == "cancelled"
    assert "auto_cleanup_stale_failed" in str(updated.get("last_error") or "")


def test_cleanup_preserves_recent_failed(isolated_runtime):
    """Agent i failed <30 min skal IKKE cancelles."""
    from core.services.agent_runtime import cleanup_stale_agents
    from core.runtime.db import get_agent_registry_entry

    agent_id = _make_agent("fresh_fail")
    _backdate_agent(agent_id, status="failed", minutes_ago=10)

    result = cleanup_stale_agents(
        waiting_timeout_minutes=120,
        failed_timeout_minutes=30,
    )

    assert agent_id not in result["cancelled_failed_ids"]
    updated = get_agent_registry_entry(agent_id)
    assert updated["status"] == "failed"


def test_cleanup_ignores_active_running_agents(isolated_runtime):
    """Agenter i active/starting/queued er urørte uanset alder."""
    from core.services.agent_runtime import cleanup_stale_agents
    from core.runtime.db import get_agent_registry_entry

    active = _make_agent("active_agent")
    _backdate_agent(active, status="active", minutes_ago=600)  # 10 timer
    starting = _make_agent("starting_agent")
    _backdate_agent(starting, status="starting", minutes_ago=600)

    result = cleanup_stale_agents()

    assert active not in result["cancelled_waiting_ids"]
    assert active not in result["cancelled_failed_ids"]
    assert get_agent_registry_entry(active)["status"] == "active"
    assert get_agent_registry_entry(starting)["status"] == "starting"


def test_cleanup_returns_summary(isolated_runtime):
    """Return dict indeholder counts + thresholds + timestamp."""
    from core.services.agent_runtime import cleanup_stale_agents

    result = cleanup_stale_agents(
        waiting_timeout_minutes=120,
        failed_timeout_minutes=30,
    )
    assert "cancelled_waiting_count" in result
    assert "cancelled_failed_count" in result
    assert "thresholds" in result
    assert result["thresholds"]["waiting_timeout_minutes"] == 120
    assert result["thresholds"]["failed_timeout_minutes"] == 30
    assert "ran_at" in result


def test_cleanup_publishes_events(isolated_runtime):
    """Hver auto-cancellation publisher agent.auto_cancelled event."""
    from core.services.agent_runtime import cleanup_stale_agents
    from core.eventbus.bus import event_bus

    agent_id = _make_agent("event_test")
    _backdate_agent(agent_id, status="failed", minutes_ago=45)

    # Clear + capture
    before_events = set(e.get("id") for e in event_bus.recent(limit=200))
    cleanup_stale_agents(
        waiting_timeout_minutes=120,
        failed_timeout_minutes=30,
    )
    after_events = event_bus.recent(limit=200)
    new_events = [e for e in after_events if e.get("id") not in before_events]

    matching = [
        e for e in new_events
        if str(e.get("kind") or "") == "runtime.agent_auto_cancelled"
        and str((e.get("payload") or {}).get("agent_id") or "") == agent_id
    ]
    assert len(matching) >= 1, (
        f"Forventede agent.auto_cancelled event for {agent_id}; new events: "
        f"{[(e.get('kind'), e.get('payload')) for e in new_events[:5]]}"
    )
