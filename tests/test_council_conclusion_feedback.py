from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from unittest.mock import patch
from apps.api.jarvis_api.services.council_runtime import get_latest_council_conclusion


def test_get_latest_council_conclusion_returns_none_when_no_closed_sessions():
    with patch(
        "apps.api.jarvis_api.services.council_runtime.list_council_sessions",
        return_value=[],
        create=True,
    ):
        # Patch inside the lazy import path
        import core.runtime.db as db
        orig = db.list_council_sessions
        db.list_council_sessions = lambda **kw: []
        try:
            result = get_latest_council_conclusion()
            assert result is None
        finally:
            db.list_council_sessions = orig


def test_get_latest_council_conclusion_returns_most_recent_closed():
    fake_sessions = [
        {
            "council_id": "c1",
            "status": "closed",
            "topic": "Should I rewrite my soul?",
            "summary": "Council recommends caution.",
            "updated_at": "2026-04-11T20:00:00",
            "mode": "council",
        },
        {
            "council_id": "c2",
            "status": "deliberating",
            "topic": "Something else",
            "summary": "",
            "updated_at": "2026-04-11T21:00:00",
            "mode": "council",
        },
    ]
    import core.runtime.db as db
    orig = db.list_council_sessions
    db.list_council_sessions = lambda **kw: fake_sessions
    try:
        result = get_latest_council_conclusion()
        assert result is not None
        assert result["council_id"] == "c1"
        assert "caution" in result["summary"]
        assert result["topic"] == "Should I rewrite my soul?"
    finally:
        db.list_council_sessions = orig


def test_get_latest_council_conclusion_skips_non_closed():
    fake_sessions = [
        {"council_id": "c1", "status": "deliberating", "topic": "X", "summary": "...", "mode": "council"},
        {"council_id": "c2", "status": "forming", "topic": "Y", "summary": "...", "mode": "swarm"},
    ]
    import core.runtime.db as db
    orig = db.list_council_sessions
    db.list_council_sessions = lambda **kw: fake_sessions
    try:
        result = get_latest_council_conclusion()
        assert result is None
    finally:
        db.list_council_sessions = orig
