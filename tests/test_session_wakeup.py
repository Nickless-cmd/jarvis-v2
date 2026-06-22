"""Tests for wakeup-digest event de-duplication (2026-06-22 round 3)."""
from unittest.mock import MagicMock, patch

from core.services import session_wakeup as sw


def test_digest_collapses_repeated_events_into_one_line():
    events = [
        {"id": i, "kind": "runtime.cheap_lane_provider_failed"} for i in range(5)
    ]
    fake_bus = MagicMock()
    fake_bus.recent.return_value = events
    fake_bus.recent_since_id.return_value = events

    with patch("core.eventbus.bus.event_bus", fake_bus), \
         patch.object(sw, "last_seen_event_id", return_value=0), \
         patch.object(sw, "mark_seen", return_value=None), \
         patch.object(sw, "_is_notable", return_value=True), \
         patch.object(sw, "_format_event", side_effect=lambda e: f"event {e['kind']}"):
        out = sw.wakeup_digest("test-session")

    assert out is not None
    assert "×5" in out
    # exactly ONE bullet for the repeated kind, not five
    assert out.count("runtime.cheap_lane_provider_failed") == 1


def test_digest_none_when_nothing_notable():
    fake_bus = MagicMock()
    fake_bus.recent.return_value = [{"id": 1, "kind": "boring.event"}]
    fake_bus.recent_since_id.return_value = [{"id": 1, "kind": "boring.event"}]

    with patch("core.eventbus.bus.event_bus", fake_bus), \
         patch.object(sw, "last_seen_event_id", return_value=0), \
         patch.object(sw, "mark_seen", return_value=None), \
         patch.object(sw, "_is_notable", return_value=False):
        assert sw.wakeup_digest("test-session") is None
