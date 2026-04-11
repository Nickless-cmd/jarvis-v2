from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from unittest.mock import patch
import apps.api.jarvis_api.services.thought_action_proposal_daemon as tap


def _reset():
    tap._pending_proposals.clear()
    tap._resolved_proposals.clear()
    tap._last_classified_fragment = ""


def test_no_proposal_for_non_action_fragment():
    """Fragment without action language produces no proposal."""
    _reset()
    with patch("apps.api.jarvis_api.services.thought_action_proposal_daemon.classify_fragment",
               return_value={"has_action": False, "action_description": "", "destructive_score": 0.0,
                             "proposal_type": "non_destructive", "destructive_reason": ""}):
        result = tap.tick_thought_action_proposal_daemon("Bare en rolig tanke.")
    assert result["generated"] is False
    assert len(tap._pending_proposals) == 0


def test_proposal_created_for_action_fragment():
    """Fragment with action language creates a pending proposal."""
    _reset()
    with patch("apps.api.jarvis_api.services.thought_action_proposal_daemon.classify_fragment",
               return_value={"has_action": True, "action_description": "research",
                             "destructive_score": 0.0, "proposal_type": "non_destructive",
                             "destructive_reason": ""}):
        result = tap.tick_thought_action_proposal_daemon("Vil gerne undersøge det nærmere.")
    assert result["generated"] is True
    assert len(tap._pending_proposals) == 1
    assert tap._pending_proposals[0]["status"] == "pending"
    assert tap._pending_proposals[0]["proposal_type"] == "non_destructive"


def test_same_fragment_not_classified_twice():
    """Identical fragment is not re-classified if already processed."""
    _reset()
    fragment = "Vil gerne undersøge det."
    tap._last_classified_fragment = fragment
    with patch("apps.api.jarvis_api.services.thought_action_proposal_daemon.classify_fragment") as mock_cls:
        tap.tick_thought_action_proposal_daemon(fragment)
    mock_cls.assert_not_called()


def test_pending_proposals_capped_at_10():
    """Pending proposal queue is capped at 10 items."""
    _reset()
    tap._pending_proposals[:] = [
        {"id": f"p{i}", "fragment_excerpt": "x", "action_description": "research",
         "proposal_type": "non_destructive", "status": "pending", "created_at": "2026-01-01T00:00:00"}
        for i in range(10)
    ]
    with patch("apps.api.jarvis_api.services.thought_action_proposal_daemon.classify_fragment",
               return_value={"has_action": True, "action_description": "research",
                             "destructive_score": 0.0, "proposal_type": "non_destructive",
                             "destructive_reason": ""}):
        tap.tick_thought_action_proposal_daemon("En ny handling.")
    assert len(tap._pending_proposals) == 10


def test_resolve_proposal_approve():
    """Approving a proposal moves it from pending to resolved."""
    _reset()
    tap._pending_proposals.append({
        "id": "test-id-1",
        "fragment_excerpt": "Vil gerne undersøge.",
        "action_description": "research",
        "proposal_type": "non_destructive",
        "status": "pending",
        "created_at": "2026-01-01T00:00:00",
    })
    result = tap.resolve_proposal("test-id-1", "approved")
    assert result is True
    assert len(tap._pending_proposals) == 0
    assert tap._resolved_proposals[0]["status"] == "approved"


def test_resolve_proposal_dismiss():
    """Dismissing a proposal moves it from pending to resolved with dismissed status."""
    _reset()
    tap._pending_proposals.append({
        "id": "test-id-2",
        "fragment_excerpt": "Slet de gamle filer.",
        "action_description": "slet/fjern",
        "proposal_type": "needs_approval",
        "status": "pending",
        "created_at": "2026-01-01T00:00:00",
    })
    result = tap.resolve_proposal("test-id-2", "dismissed")
    assert result is True
    assert tap._resolved_proposals[0]["status"] == "dismissed"


def test_resolve_unknown_id_returns_false():
    """Resolving a non-existent proposal ID returns False."""
    _reset()
    result = tap.resolve_proposal("nonexistent", "approved")
    assert result is False


def test_build_surface_structure():
    """build_proposal_surface returns expected keys."""
    _reset()
    surface = tap.build_proposal_surface()
    assert "pending_proposals" in surface
    assert "resolved_proposals" in surface
    assert "pending_count" in surface
    assert "needs_approval_count" in surface
