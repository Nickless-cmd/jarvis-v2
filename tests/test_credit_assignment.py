"""Tests for Lag 1 credit assignment (db_credit_assignment + meta_reflection hook)."""
from __future__ import annotations

import json
import sqlite3

import pytest

from core.runtime.db import connect, init_db
from core.runtime.db_credit_assignment import (
    ensure_credit_assignment_tables,
    record_choice,
    list_unreviewed_decisions,
    link_outcome_to_decision,
    get_credit_trend,
)
from core.services.meta_reflection_daemon import _check_credit, tick_meta_reflection_daemon


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
        # If we get here, idempotency holds


# ── Choice recording tests ───────────────────────────────────────────────

class TestRecordChoice:
    def test_record_prompt_variant_choice(self):
        decision_id = record_choice(
            kind="prompt_variant",
            title="Velg prompt variant",
            options=["variant_a", "variant_b"],
            decision="variant_a",
            why="variant_a er mere konkret",
        )
        assert decision_id.startswith("dec-")

        # Verify in DB
        with connect() as conn:
            row = conn.execute(
                "SELECT * FROM cognitive_decisions WHERE decision_id = ?",
                (decision_id,),
            ).fetchone()
        assert row is not None
        assert row["kind"] == "prompt_variant"
        assert json.loads(row["options"]) == ["variant_a", "variant_b"]
        assert row["outcome_aggregate"] is None  # not yet reviewed

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
        # conversational should not appear when filtering by prompt_variant
        assert all(d["kind"] != "conversational" for d in unreviewed)


# ── Outcome linking tests ────────────────────────────────────────────────

class TestLinkOutcome:
    def test_link_outcome_to_decision(self):
        decision_id = record_choice(
            kind="prompt_variant", title="Test choice",
            options=["x", "y"], decision="x",
        )

        result = link_outcome_to_decision(
            decision_id=decision_id,
            credit_score=75.0,
            rationale="Good decision — positive signals",
            evidence_summary="energy=moderate; no conflict",
        )

        assert result is not None
        assert result["decision_id"] == decision_id
        assert result["credit_score"] == 75.0
        assert result["aggregate"] == 75.0

        # Verify outcome_aggregate is set on decision
        with connect() as conn:
            row = conn.execute(
                "SELECT outcome_aggregate FROM cognitive_decisions WHERE decision_id = ?",
                (decision_id,),
            ).fetchone()
        assert row["outcome_aggregate"] == 75.0

        # Verify decision_id is set on outcome
        with connect() as conn:
            row = conn.execute(
                "SELECT decision_id, credit_score FROM runtime_self_review_outcomes WHERE decision_id = ?",
                (decision_id,),
            ).fetchone()
        assert row["decision_id"] == decision_id
        assert row["credit_score"] == 75.0

    def test_multiple_outcomes_average(self):
        decision_id = record_choice(
            kind="prompt_variant", title="Multi-test",
            options=["a", "b"], decision="a",
        )

        link_outcome_to_decision(
            decision_id=decision_id, credit_score=80.0,
            rationale="first review", evidence_summary="strong signals",
        )
        link_outcome_to_decision(
            decision_id=decision_id, credit_score=60.0,
            rationale="second review", evidence_summary="weaker later signals",
        )

        with connect() as conn:
            row = conn.execute(
                "SELECT outcome_aggregate FROM cognitive_decisions WHERE decision_id = ?",
                (decision_id,),
            ).fetchone()
        assert row["outcome_aggregate"] == pytest.approx(70.0)  # (80 + 60) / 2


# ── Query surface tests ──────────────────────────────────────────────────

class TestCreditTrend:
    def test_get_credit_trend(self):
        d1 = record_choice(kind="prompt_variant", title="A", options=["a", "b"], decision="a")
        d2 = record_choice(kind="prompt_variant", title="B", options=["c", "d"], decision="c")
        link_outcome_to_decision(
            decision_id=d1, credit_score=85.0,
            rationale="good", evidence_summary="signals positive",
        )
        link_outcome_to_decision(
            decision_id=d2, credit_score=45.0,
            rationale="poor", evidence_summary="conflict detected",
        )

        trend = get_credit_trend(kind="prompt_variant", limit=10)
        assert len(trend) >= 2
        scores = [t["credit_score"] for t in trend if t["credit_score"] is not None]
        assert 85.0 in scores
        assert 45.0 in scores

    def test_conversational_excluded(self):
        record_choice(kind="conversational", title="Chat", options=[], decision="")
        trend = get_credit_trend(limit=10)
        assert all(t["kind"] != "conversational" for t in trend)


# ── Meta-reflection hook tests ───────────────────────────────────────────

@pytest.fixture()
def _clean_decisions():
    """Remove outcomes and decisions so _check_credit starts fresh."""
    with connect() as conn:
        conn.execute("DELETE FROM runtime_self_review_outcomes")
        conn.execute("DELETE FROM cognitive_decisions")
        conn.commit()


class TestMetaReflectionHook:
    @pytest.mark.usefixtures("_clean_decisions")
    def test_check_credit_noop_when_no_unreviewed(self):
        """_check_credit should return scored=0 when no unreviewed decisions."""
        result = _check_credit({})
        assert result["checked"] is True
        assert result["scored"] == 0

    @pytest.mark.usefixtures("_clean_decisions")
    def test_check_credit_scores_unreviewed_decision(self):
        """_check_credit should auto-score an unreviewed prompt_variant."""
        record_choice(
            kind="prompt_variant", title="A/B test",
            options=["warm_prompt", "cold_prompt"],
            decision="warm_prompt",
        )

        result = _check_credit({"energy_level": "moderate", "curiosity_signal": "exploring"})
        assert result["checked"] is True
        assert result["scored"] == 1

        # Verify outcome was linked
        trend = get_credit_trend(kind="prompt_variant", limit=5)
        linked = [t for t in trend if t["credit_score"] is not None]
        assert len(linked) >= 1

    @pytest.mark.usefixtures("_clean_decisions")
    def test_tick_meta_reflection_includes_credit(self):
        """tick_meta_reflection_daemon should include credit in its return."""
        record_choice(
            kind="prompt_variant", title="Tick test",
            options=["a", "b"], decision="a",
        )

        # Provide active signals so meta-insight can generate
        result = tick_meta_reflection_daemon({
            "energy_level": "moderate",
            "latest_fragment": "test fragment for credit",
        })
        assert "credit" in result
        # if meta-insight also generated, we'll see it — but credit should always be reported
