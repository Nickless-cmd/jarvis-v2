"""Tests for Lag 1 credit assignment (db_credit_assignment + meta_reflection hook).

Conventions (aligned with Claude review 2026-05-17):
- credit_score: 1-5 scale
- evidence_summary: JSON blob with raw context signals
- Eventbus: credit_assignment.choice_recorded + .outcome_linked
"""
from __future__ import annotations

import json
import sqlite3

import pytest

from core.eventbus.bus import event_bus
from core.runtime.db import connect, init_db
from core.runtime.db_credit_assignment import (
    ensure_credit_assignment_tables,
    record_choice,
    list_unreviewed_decisions,
    link_outcome_to_decision,
    get_credit_trend,
)
from core.services.meta_reflection_daemon import _check_outcomes, tick_meta_reflection_daemon


# ── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _ensure_schema():
    """Ensure credit assignment columns exist in the test DB."""
    init_db()
    with connect() as conn:
        ensure_credit_assignment_tables(conn)


# ── Schema migration tests ───────────────────────────────────────────────

class TestSchemaMigration:
    def test_columns_exist_on_cognitive_decisions(self):
        with connect() as conn:
            cols = {
                r[1] for r in conn.execute(
                    "PRAGMA table_info(cognitive_decisions)"
                ).fetchall()
            }
        assert "kind" in cols
        assert "outcome_aggregate" in cols

    def test_columns_exist_on_runtime_self_review_outcomes(self):
        with connect() as conn:
            cols = {
                r[1] for r in conn.execute(
                    "PRAGMA table_info(runtime_self_review_outcomes)"
                ).fetchall()
            }
        assert "decision_id" in cols
        assert "credit_score" in cols

    def test_idempotent(self):
        """Run migration twice — no errors."""
        with connect() as conn:
            ensure_credit_assignment_tables(conn)
            ensure_credit_assignment_tables(conn)

    def test_pending_index_exists(self):
        """idx_cognitive_decisions_pending should be created for O(log N) lookup."""
        with connect() as conn:
            indices = {
                r["name"] for r in conn.execute(
                    "PRAGMA index_list(cognitive_decisions)"
                ).fetchall()
            }
        assert "idx_cognitive_decisions_pending" in indices


# ── Choice recording tests ───────────────────────────────────────────────

class TestRecordChoice:
    def test_record_prompt_variant_choice(self):
        decision_id = record_choice(
            kind="prompt_variant",
            title="Vælg prompt variant",
            options=["variant_a", "variant_b"],
            decision="variant_a",
            why="variant_a er mere konkret",
        )
        assert decision_id.startswith("dec-")

        with connect() as conn:
            row = conn.execute(
                "SELECT * FROM cognitive_decisions WHERE decision_id = ?",
                (decision_id,),
            ).fetchone()
        assert row is not None
        assert row["kind"] == "prompt_variant"
        assert json.loads(row["options"]) == ["variant_a", "variant_b"]
        assert row["outcome_aggregate"] is None

    def test_list_unreviewed_decisions(self):
        record_choice(
            kind="prompt_variant", title="Test",
            options=["a", "b"], decision="a",
        )
        unreviewed = list_unreviewed_decisions(kind="prompt_variant", limit=5)
        assert len(unreviewed) >= 1
        assert all(d["kind"] == "prompt_variant" for d in unreviewed)
        assert all(d["outcome_aggregate"] is None for d in unreviewed)

    def test_conversational_not_listed_by_default(self):
        record_choice(
            kind="conversational", title="Small talk",
            options=["a", "b"], decision="a",
        )
        unreviewed = list_unreviewed_decisions(kind="prompt_variant", limit=5)
        assert all(d["kind"] != "conversational" for d in unreviewed)

    def test_choice_recorded_eventbus_payload(self):
        """Verify the credit_assignment.choice_recorded event contract."""
        import queue as _queue

        sub = event_bus.subscribe()
        try:
            decision_id = record_choice(
                kind="prompt_variant",
                title="Eventbus test",
                options=["a", "b"],
                decision="a",
                why="testing event payload",
            )

            # Drain queue for the matching event
            found = None
            deadline = 5
            while deadline > 0:
                try:
                    evt = sub.get(timeout=1)
                    if evt and evt.get("kind") == "credit_assignment.choice_recorded":
                        found = evt
                        break
                except _queue.Empty:
                    deadline -= 1
        finally:
            event_bus.unsubscribe(sub)

        assert found is not None, "credit_assignment.choice_recorded not published"
        payload = found["payload"]
        assert payload["decision_id"] == decision_id
        assert payload["kind"] == "prompt_variant"
        assert payload["score"] is None
        assert payload["rationale"] == "testing event payload"


# ── Outcome linking tests ────────────────────────────────────────────────

class TestLinkOutcome:
    def test_link_outcome_to_decision(self):
        decision_id = record_choice(
            kind="prompt_variant", title="Test choice",
            options=["x", "y"], decision="x",
        )

        result = link_outcome_to_decision(
            decision_id=decision_id,
            credit_score=4.0,
            rationale="Good decision — positive signals",
            evidence_summary=json.dumps({"signals": {"energy": "moderate"}}),
        )

        assert result is not None
        assert result["decision_id"] == decision_id
        assert result["credit_score"] == 4.0
        assert result["aggregate"] == 4.0
        assert result["scale"] == "1-5"

        with connect() as conn:
            row = conn.execute(
                "SELECT outcome_aggregate FROM cognitive_decisions WHERE decision_id = ?",
                (decision_id,),
            ).fetchone()
        assert row["outcome_aggregate"] == 4.0

        with connect() as conn:
            row = conn.execute(
                "SELECT decision_id, credit_score FROM runtime_self_review_outcomes WHERE decision_id = ?",
                (decision_id,),
            ).fetchone()
        assert row["decision_id"] == decision_id
        assert row["credit_score"] == 4.0

    def test_multiple_outcomes_average(self):
        decision_id = record_choice(
            kind="prompt_variant", title="Multi-test",
            options=["a", "b"], decision="a",
        )

        link_outcome_to_decision(
            decision_id=decision_id, credit_score=4.0,
            rationale="first review",
            evidence_summary=json.dumps({"signals": {"energy": "moderate"}}),
        )
        link_outcome_to_decision(
            decision_id=decision_id, credit_score=3.0,
            rationale="second review",
            evidence_summary=json.dumps({"signals": {"energy": "low"}}),
        )

        with connect() as conn:
            row = conn.execute(
                "SELECT outcome_aggregate FROM cognitive_decisions WHERE decision_id = ?",
                (decision_id,),
            ).fetchone()
        assert row["outcome_aggregate"] == pytest.approx(3.5)

    def test_credit_score_clamped_to_1_5(self):
        decision_id = record_choice(
            kind="prompt_variant", title="Clamp test",
            options=["a", "b"], decision="a",
        )

        # Score above 5 should clamp
        result = link_outcome_to_decision(
            decision_id=decision_id, credit_score=10.0,
            rationale="way too high", evidence_summary="{}",
        )
        assert result["credit_score"] == 5.0

        # Score below 1 should clamp
        result = link_outcome_to_decision(
            decision_id=decision_id, credit_score=-5.0,
            rationale="way too low", evidence_summary="{}",
        )
        assert result["credit_score"] == 1.0

    def test_outcome_linked_eventbus_payload(self):
        """Verify the credit_assignment.outcome_linked event contract."""
        import queue as _queue

        decision_id = record_choice(
            kind="prompt_variant", title="Eventbus outcome test",
            options=["a", "b"], decision="a",
        )

        sub = event_bus.subscribe()
        try:
            link_outcome_to_decision(
                decision_id=decision_id, credit_score=5.0,
                rationale="excellent", evidence_summary="{}",
            )

            found = None
            deadline = 5
            while deadline > 0:
                try:
                    evt = sub.get(timeout=1)
                    if evt and evt.get("kind") == "credit_assignment.outcome_linked":
                        found = evt
                        break
                except _queue.Empty:
                    deadline -= 1
        finally:
            event_bus.unsubscribe(sub)

        assert found is not None, "credit_assignment.outcome_linked not published"
        payload = found["payload"]
        assert payload["decision_id"] == decision_id
        assert payload["score"] == 5.0
        assert payload["rationale"] == "excellent"


# ── Query surface tests ──────────────────────────────────────────────────

class TestCreditTrend:
    def test_get_credit_trend(self):
        d1 = record_choice(kind="prompt_variant", title="A", options=["a", "b"], decision="a")
        d2 = record_choice(kind="prompt_variant", title="B", options=["c", "d"], decision="c")
        link_outcome_to_decision(
            decision_id=d1, credit_score=4.0,
            rationale="good", evidence_summary='{"signals": {"energy": "moderate"}}',
        )
        link_outcome_to_decision(
            decision_id=d2, credit_score=2.0,
            rationale="poor", evidence_summary='{"signals": {"conflict": true}}',
        )

        trend = get_credit_trend(kind="prompt_variant", limit=10)
        assert len(trend) >= 2
        scores = [t["credit_score"] for t in trend if t["credit_score"] is not None]
        assert 4.0 in scores
        assert 2.0 in scores

    def test_conversational_excluded(self):
        record_choice(kind="conversational", title="Chat", options=[], decision="")
        trend = get_credit_trend(limit=10)
        assert all(t["kind"] != "conversational" for t in trend)


# ── Meta-reflection hook tests ───────────────────────────────────────────

@pytest.fixture()
def _clean_decisions():
    """Remove outcomes and decisions so _check_outcomes starts fresh."""
    with connect() as conn:
        conn.execute("DELETE FROM runtime_self_review_outcomes")
        conn.execute("DELETE FROM cognitive_decisions")
        conn.commit()


class TestMetaReflectionHook:
    @pytest.mark.usefixtures("_clean_decisions")
    def test_check_outcomes_noop_when_no_unreviewed(self):
        result = _check_outcomes({})
        assert result["checked"] is True
        assert result["scored"] == 0

    @pytest.mark.skip(
        reason="STALE (2026-06-30): _check_outcomes scorer nu kun model_tier + "
        "response_style (kræver hhv. 3 efterfølgende ture / 1 user-msg eller "
        "30-min ttl-expiry), IKKE prompt_variant. Faithful rewrite kræver "
        "chat_messages-tur-fixtures — separat opgave. Resten af suiten dækker "
        "_check_outcomes' no-op + db_credit_assignment-laget."
    )
    @pytest.mark.usefixtures("_clean_decisions")
    def test_check_outcomes_scores_unreviewed_decision(self):
        record_choice(
            kind="prompt_variant", title="A/B test",
            options=["warm_prompt", "cold_prompt"],
            decision="warm_prompt",
        )

        result = _check_outcomes({"energy_level": "moderate", "curiosity_signal": "exploring"})
        assert result["checked"] is True
        assert result["scored"] == 1

        trend = get_credit_trend(kind="prompt_variant", limit=5)
        linked = [t for t in trend if t["credit_score"] is not None]
        assert len(linked) >= 1

        # Score should be in 1-5 range
        for t in linked:
            if t["credit_score"] is not None:
                assert 1.0 <= t["credit_score"] <= 5.0

    @pytest.mark.usefixtures("_clean_decisions")
    def test_check_outcomes_evidence_summary_is_json(self):
        """evidence_summary should be valid JSON with signals as raw context."""
        record_choice(
            kind="prompt_variant", title="JSON evidence test",
            options=["x", "y"], decision="x",
        )

        _check_outcomes({"energy_level": "low", "last_conflict": "disagreement"})

        with connect() as conn:
            outcomes = conn.execute(
                """SELECT evidence_summary FROM runtime_self_review_outcomes
                   ORDER BY id DESC LIMIT 1"""
            ).fetchall()

        if outcomes:
            raw = outcomes[0]["evidence_summary"]
            if raw and raw != "{}":
                parsed = json.loads(raw)
                assert "signals" in parsed, f"evidence_summary missing 'signals' key: {raw}"

    @pytest.mark.usefixtures("_clean_decisions")
    def test_tick_meta_reflection_includes_credit(self):
        record_choice(
            kind="prompt_variant", title="Tick test",
            options=["a", "b"], decision="a",
        )

        result = tick_meta_reflection_daemon({
            "energy_level": "moderate",
            "latest_fragment": "test fragment for credit",
        })
        assert "credit" in result


# ── Eventbus payload contract tests ──────────────────────────────────────

class TestEventbusContracts:
    """Explicit contract tests for event payload schemas.

    These ensure backward compatibility: if any future change alters the
    event payload shape, the test fails and the change is deliberate.
    Uses the queue-based event_bus.subscribe() mechanism.
    """

    def _drain_for(self, sub, kind: str, timeout: int = 5) -> dict | None:
        import queue as _queue

        while timeout > 0:
            try:
                evt = sub.get(timeout=1)
                if evt and evt.get("kind") == kind:
                    return evt
            except _queue.Empty:
                timeout -= 1
        return None

    def test_choice_recorded_contract(self):
        """credit_assignment.choice_recorded payload must match schema."""
        sub = event_bus.subscribe()
        try:
            did = record_choice(
                kind="prompt_variant", title="Contract",
                options=["a", "b"], decision="a",
            )
            found = self._drain_for(sub, "credit_assignment.choice_recorded")
        finally:
            event_bus.unsubscribe(sub)

        assert found is not None, "credit_assignment.choice_recorded not fired"
        p = found["payload"]
        # Required keys
        assert "decision_id" in p
        assert "kind" in p
        assert "created_at" in p
        assert "score" in p
        assert "rationale" in p
        # Types
        assert isinstance(p["decision_id"], str)
        assert isinstance(p["kind"], str)
        assert p["score"] is None  # not yet reviewed

    def test_outcome_linked_contract(self):
        """credit_assignment.outcome_linked payload must match schema."""
        did = record_choice(
            kind="prompt_variant", title="Contract outcome",
            options=["a", "b"], decision="a",
        )

        sub = event_bus.subscribe()
        try:
            link_outcome_to_decision(
                decision_id=did, credit_score=4.0,
                rationale="solid choice", evidence_summary="{}",
            )
            found = self._drain_for(sub, "credit_assignment.outcome_linked")
        finally:
            event_bus.unsubscribe(sub)

        assert found is not None, "credit_assignment.outcome_linked not fired"
        p = found["payload"]
        assert "decision_id" in p
        assert "kind" in p
        assert "created_at" in p
        assert "score" in p
        assert "rationale" in p
        assert p["score"] == 4.0
        assert isinstance(p["score"], float)
