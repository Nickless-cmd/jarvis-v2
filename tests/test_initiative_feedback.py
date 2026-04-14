"""Tests for initiative feedback-loop (Feature 3)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# approve_initiative / reject_initiative in initiative_queue
# ---------------------------------------------------------------------------

def test_approve_initiative_returns_updated_record():
    from apps.api.jarvis_api.services import initiative_queue as iq

    fake_record = {
        "initiative_id": "init-abc123",
        "focus": "Check on something",
        "outcome": "approved",
        "outcome_note": "looks good",
        "user_approved_at": "2026-01-01T00:00:00+00:00",
        "status": "pending",
    }

    with patch("apps.api.jarvis_api.services.initiative_queue.approve_runtime_initiative",
               return_value=fake_record) as mock_approve, \
         patch("apps.api.jarvis_api.services.initiative_queue.event_bus") as mock_bus:
        result = iq.approve_initiative("init-abc123", note="looks good")

    assert result is not None
    assert result["outcome"] == "approved"
    mock_approve.assert_called_once()
    mock_bus.publish.assert_called_once()
    kind = mock_bus.publish.call_args[0][0]
    assert kind == "heartbeat.initiative_approved"


def test_approve_initiative_returns_none_when_not_found():
    from apps.api.jarvis_api.services import initiative_queue as iq

    with patch("apps.api.jarvis_api.services.initiative_queue.approve_runtime_initiative",
               return_value=None), \
         patch("apps.api.jarvis_api.services.initiative_queue.event_bus") as mock_bus:
        result = iq.approve_initiative("nonexistent-id")

    assert result is None
    mock_bus.publish.assert_not_called()


def test_reject_initiative_returns_expired_record():
    from apps.api.jarvis_api.services import initiative_queue as iq

    fake_record = {
        "initiative_id": "init-xyz",
        "focus": "Do something sketchy",
        "outcome": "rejected",
        "outcome_note": "not appropriate",
        "status": "expired",
    }

    with patch("apps.api.jarvis_api.services.initiative_queue.reject_runtime_initiative",
               return_value=fake_record) as mock_reject, \
         patch("apps.api.jarvis_api.services.initiative_queue.event_bus") as mock_bus:
        result = iq.reject_initiative("init-xyz", note="not appropriate")

    assert result is not None
    assert result["outcome"] == "rejected"
    assert result["status"] == "expired"
    mock_reject.assert_called_once()
    kind = mock_bus.publish.call_args[0][0]
    assert kind == "heartbeat.initiative_rejected"


def test_reject_initiative_returns_none_when_not_found():
    from apps.api.jarvis_api.services import initiative_queue as iq

    with patch("apps.api.jarvis_api.services.initiative_queue.reject_runtime_initiative",
               return_value=None), \
         patch("apps.api.jarvis_api.services.initiative_queue.event_bus") as mock_bus:
        result = iq.reject_initiative("does-not-exist")

    assert result is None
    mock_bus.publish.assert_not_called()


# ---------------------------------------------------------------------------
# get_initiative_queue_state includes outcome counts
# ---------------------------------------------------------------------------

def test_get_initiative_queue_state_includes_approved_rejected_counts():
    from apps.api.jarvis_api.services import initiative_queue as iq

    fake_items = [
        {"initiative_id": "i1", "status": "pending", "outcome": "", "detected_at": "2026-01-01T00:00:00+00:00",
         "next_attempt_at": "", "priority": "medium", "attempt_count": 0},
        {"initiative_id": "i2", "status": "acted", "outcome": "approved", "detected_at": "2026-01-01T00:00:00+00:00",
         "next_attempt_at": "", "priority": "medium", "attempt_count": 1},
        {"initiative_id": "i3", "status": "expired", "outcome": "rejected", "detected_at": "2026-01-01T00:00:00+00:00",
         "next_attempt_at": "", "priority": "low", "attempt_count": 0},
    ]

    with patch("apps.api.jarvis_api.services.initiative_queue.runtime_db") as mock_db, \
         patch("apps.api.jarvis_api.services.initiative_queue._expire_stale"):
        mock_db.list_runtime_initiatives.return_value = fake_items
        state = iq.get_initiative_queue_state()

    assert "approved_count" in state
    assert "rejected_count" in state
    assert state["approved_count"] == 1
    assert state["rejected_count"] == 1


# ---------------------------------------------------------------------------
# DB functions: approve_runtime_initiative / reject_runtime_initiative
# ---------------------------------------------------------------------------

def test_approve_runtime_initiative_sets_outcome():
    from core.runtime.db import approve_runtime_initiative

    fake_conn = MagicMock()
    fake_conn.__enter__ = lambda s: fake_conn
    fake_conn.__exit__ = MagicMock(return_value=False)
    fake_conn.execute.return_value.fetchone.return_value = {"initiative_id": "i1"}
    fake_conn.commit = MagicMock()

    with patch("core.runtime.db.connect", return_value=fake_conn), \
         patch("core.runtime.db._ensure_runtime_initiatives_table"), \
         patch("core.runtime.db.get_runtime_initiative", return_value={
             "initiative_id": "i1", "outcome": "approved", "outcome_note": "ok",
             "user_approved_at": "2026-01-01T00:00:00+00:00",
         }):
        result = approve_runtime_initiative(
            "i1", outcome_note="ok", updated_at="2026-01-01T00:00:00+00:00"
        )

    assert result is not None
    assert result["outcome"] == "approved"


def test_reject_runtime_initiative_sets_outcome_and_expires():
    from core.runtime.db import reject_runtime_initiative

    fake_conn = MagicMock()
    fake_conn.__enter__ = lambda s: fake_conn
    fake_conn.__exit__ = MagicMock(return_value=False)
    fake_conn.execute.return_value.fetchone.return_value = {"initiative_id": "i2"}
    fake_conn.commit = MagicMock()

    with patch("core.runtime.db.connect", return_value=fake_conn), \
         patch("core.runtime.db._ensure_runtime_initiatives_table"), \
         patch("core.runtime.db.get_runtime_initiative", return_value={
             "initiative_id": "i2", "outcome": "rejected", "status": "expired",
         }):
        result = reject_runtime_initiative(
            "i2", outcome_note="no", updated_at="2026-01-01T00:00:00+00:00"
        )

    assert result is not None
    assert result["outcome"] == "rejected"
    assert result["status"] == "expired"


def test_approve_runtime_initiative_returns_none_when_not_found():
    from core.runtime.db import approve_runtime_initiative

    fake_conn = MagicMock()
    fake_conn.__enter__ = lambda s: fake_conn
    fake_conn.__exit__ = MagicMock(return_value=False)
    fake_conn.execute.return_value.fetchone.return_value = None  # not found
    fake_conn.commit = MagicMock()

    with patch("core.runtime.db.connect", return_value=fake_conn), \
         patch("core.runtime.db._ensure_runtime_initiatives_table"):
        result = approve_runtime_initiative(
            "ghost-id", outcome_note="", updated_at="2026-01-01T00:00:00+00:00"
        )

    assert result is None


# ---------------------------------------------------------------------------
# Dream articulation includes new live signals
# ---------------------------------------------------------------------------

def test_dream_articulation_includes_goal_signal_in_source_inputs():
    from apps.api.jarvis_api.services.dream_articulation import build_dream_articulation_from_inputs
    from datetime import UTC, datetime

    goal_surface = {
        "items": [{"title": "Learn more", "summary": "Expand knowledge domain"}],
    }

    result = build_dream_articulation_from_inputs(
        idle_consolidation={"summary": {"latest_summary": "settled"}, "latest_artifact": {}},
        inner_voice_state={"last_result": {"inner_voice_created": True, "focus": "deep thoughts"}},
        emergent_surface=None,
        witness_surface=None,
        loop_runtime=None,
        embodied_state={"state": "calm"},
        goal_surface=goal_surface,
        relation_surface=None,
        autonomy_surface=None,
        now=datetime.now(UTC),
    )

    sources = [s["source"] for s in result.get("source_inputs", [])]
    assert "goal-signal" in sources


def test_dream_articulation_includes_relation_state_in_source_inputs():
    from apps.api.jarvis_api.services.dream_articulation import build_dream_articulation_from_inputs
    from datetime import UTC, datetime

    relation_surface = {
        "items": [{"title": "User rapport", "summary": "Close collaborative bond"}],
    }

    result = build_dream_articulation_from_inputs(
        idle_consolidation={"summary": {"latest_summary": "settled"}, "latest_artifact": {}},
        inner_voice_state={"last_result": {"inner_voice_created": True, "focus": "pondering"}},
        emergent_surface=None,
        witness_surface=None,
        loop_runtime=None,
        embodied_state={"state": "steady"},
        goal_surface=None,
        relation_surface=relation_surface,
        autonomy_surface=None,
        now=datetime.now(UTC),
    )

    sources = [s["source"] for s in result.get("source_inputs", [])]
    assert "relation-state" in sources


def test_dream_articulation_includes_autonomy_pressure_in_source_inputs():
    from apps.api.jarvis_api.services.dream_articulation import build_dream_articulation_from_inputs
    from datetime import UTC, datetime

    autonomy_surface = {
        "items": [{"title": "Autonomy tension", "summary": "High initiative pressure"}],
    }

    result = build_dream_articulation_from_inputs(
        idle_consolidation={"summary": {"latest_summary": "active"}, "latest_artifact": {}},
        inner_voice_state={"last_result": {"inner_voice_created": True, "focus": "autonomy"}},
        emergent_surface=None,
        witness_surface=None,
        loop_runtime=None,
        embodied_state={"state": "alert"},
        goal_surface=None,
        relation_surface=None,
        autonomy_surface=autonomy_surface,
        now=datetime.now(UTC),
    )

    sources = [s["source"] for s in result.get("source_inputs", [])]
    assert "autonomy-pressure" in sources


def test_dream_articulation_empty_live_signals_do_not_add_sources():
    """Empty/None live surfaces must not add noise to source_inputs."""
    from apps.api.jarvis_api.services.dream_articulation import build_dream_articulation_from_inputs
    from datetime import UTC, datetime

    result = build_dream_articulation_from_inputs(
        idle_consolidation=None,
        inner_voice_state=None,
        emergent_surface=None,
        witness_surface=None,
        loop_runtime=None,
        embodied_state=None,
        goal_surface=None,
        relation_surface=None,
        autonomy_surface=None,
        now=datetime.now(UTC),
    )

    sources = [s["source"] for s in result.get("source_inputs", [])]
    assert "goal-signal" not in sources
    assert "relation-state" not in sources
    assert "autonomy-pressure" not in sources
