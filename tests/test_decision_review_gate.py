"""FIX 1 tests — decision_review 24h anti-repeat gate.

Root cause covered: `_last_review_time` used to read the wrong key ('reviews'
instead of the 'recent_reviews' that get_decision_with_reviews populates) and
picked the wrong index for DESC-ordered rows, so the 24h skip gate never
tripped and every active decision was re-reviewed on every tick.

Covers:
  - _last_review_time reads 'recent_reviews' and returns the NEWEST timestamp
  - a decision reviewed <24h ago is skipped (gate holds)
  - a decision reviewed >24h ago is re-reviewed
  - flag off ('decision_review_dedup_gate'=off) → always review (old behavior)
  - per-tick max_reviews cap bounds actual LLM calls
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest import mock

import core.services.decision_review_prompter as drp


def _iso(dt: datetime) -> str:
    return dt.isoformat()


class TestLastReviewTime:
    def test_reads_recent_reviews_key(self):
        now = datetime.now(UTC)
        decision = {
            "recent_reviews": [
                {"created_at": _iso(now)},
                {"created_at": _iso(now - timedelta(hours=5))},
            ]
        }
        got = drp._last_review_time(decision)
        assert got is not None
        # newest of the two, not [-1] (which would be the older one)
        assert abs((got - now).total_seconds()) < 1

    def test_wrong_old_key_still_falls_back(self):
        now = datetime.now(UTC)
        decision = {"reviews": [{"created_at": _iso(now)}]}
        got = drp._last_review_time(decision)
        assert got is not None

    def test_empty_returns_none(self):
        assert drp._last_review_time({"recent_reviews": []}) is None
        assert drp._last_review_time({}) is None


def _run(active, full_map, *, flag=True, max_reviews=None):
    """Drive review_pending_decisions with mocked deps. Returns (result, call_count)."""
    calls = {"n": 0}

    def fake_llm(prompt, **kw):
        calls["n"] += 1
        return "VERDICT: kept\nEVIDENCE: held it"

    with mock.patch.object(
        drp, "_dedup_gate_enabled", return_value=flag
    ), mock.patch(
        "core.services.behavioral_decisions.list_active_decisions",
        return_value=active,
    ), mock.patch(
        "core.services.behavioral_decisions.get_decision_with_reviews",
        side_effect=lambda did: full_map.get(did),
    ), mock.patch(
        "core.services.behavioral_decisions.review_decision",
        return_value={"decision_id": "x"},
    ), mock.patch(
        "core.services.daemon_llm.quality_daemon_llm_call",
        side_effect=fake_llm,
    ):
        result = drp.review_pending_decisions(max_reviews=max_reviews)
    return result, calls["n"]


class TestReviewGate:
    def test_recently_reviewed_is_skipped(self):
        now = datetime.now(UTC)
        active = [{"decision_id": "d1"}]
        full = {
            "d1": {
                "decision_id": "d1",
                "directive": "be kind",
                "reason": "r",
                "recent_reviews": [{"created_at": _iso(now - timedelta(hours=1))}],
            }
        }
        result, n = _run(active, full)
        assert n == 0                       # gate held → no LLM call
        assert result["skipped_recent"] == 1
        assert result["reviewed"] == 0

    def test_overdue_is_reviewed(self):
        now = datetime.now(UTC)
        active = [{"decision_id": "d1"}]
        full = {
            "d1": {
                "decision_id": "d1",
                "directive": "be kind",
                "reason": "r",
                "recent_reviews": [{"created_at": _iso(now - timedelta(hours=30))}],
            }
        }
        result, n = _run(active, full)
        assert n == 1
        assert result["reviewed"] == 1

    def test_flag_off_reviews_even_when_recent(self):
        now = datetime.now(UTC)
        active = [{"decision_id": "d1"}]
        full = {
            "d1": {
                "decision_id": "d1",
                "directive": "be kind",
                "reason": "r",
                "recent_reviews": [{"created_at": _iso(now - timedelta(hours=1))}],
            }
        }
        result, n = _run(active, full, flag=False)
        assert n == 1                       # gate disabled → reviewed anyway
        assert result["reviewed"] == 1

    def test_per_tick_cap_bounds_calls(self):
        now = datetime.now(UTC)
        # 10 overdue decisions, cap at 3 → only 3 LLM calls
        active = [{"decision_id": f"d{i}"} for i in range(10)]
        full = {
            f"d{i}": {
                "decision_id": f"d{i}",
                "directive": "x",
                "reason": "r",
                "recent_reviews": [{"created_at": _iso(now - timedelta(hours=30))}],
            }
            for i in range(10)
        }
        result, n = _run(active, full, max_reviews=3)
        assert n == 3
        assert result["reviewed"] == 3
        assert result["skipped_recent"] == 7
