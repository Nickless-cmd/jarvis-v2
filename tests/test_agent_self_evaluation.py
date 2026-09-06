"""Unit tests for agent_self_evaluation."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from core.services.agent_self_evaluation import (
    evaluate_tick_quality,
    tick_quality_summary,
    detect_stale_goals,
    stale_goals_section,
    decision_adherence_summary,
    self_evaluation_section,
)


def _fake_tick(act_kind="productive_idle", priorities=None, actions=None, elapsed_ms=1000):
    return {
        "elapsed_ms": elapsed_ms,
        "phases": {
            "sense": {
                "mood_name": "x", "active_goals": [], "events_last_hour": 0,
                "context_pressure_level": "comfortable", "errors_last_hour": 0,
            },
            "reflect": {"priorities": priorities or []},
            "act": {
                "kind": act_kind,
                "result": {"actions": actions or []},
            },
        },
    }


# 2026-09-05: scoringen måler nu SPOR, ikke form. De tre tests herunder holdt
# tidligere fast i formen (havde slaget priorities? hvor mange handlinger?), og
# netop den form gav 70 til 199 af 200 slag. Et slag med priorities der ikke
# efterlader noget, skal kunne score lavt — det er hele pointen.


def _uden_spor(monkeypatch=None):
    """Patch spor-opslaget til tomt, så testen ikke afhænger af en levende DB."""
    return patch("core.services.agent_self_evaluation._trace_kinds_since",
                 return_value=[])


def _med_spor(*kinds):
    return patch("core.services.agent_self_evaluation._trace_kinds_since",
                 return_value=list(kinds))


def test_slag_uden_spor_scorer_lavt():
    """Ingen handlinger, ingen spor: kun tiden er sund."""
    with patch("core.services.agent_self_evaluation.load_json", return_value=[]), \
         patch("core.services.agent_self_evaluation.save_json"), _uden_spor():
        result = evaluate_tick_quality(tick_result=_fake_tick())
    assert "score" in result and "evaluated_at" in result
    assert result["score"] < 60


def test_priorities_alene_giver_ikke_hoej_score():
    """Den gamle scoring gav +45 for priorities + dispatch uanset udbytte."""
    with patch("core.services.agent_self_evaluation.load_json", return_value=[]), \
         patch("core.services.agent_self_evaluation.save_json"), _uden_spor():
        result = evaluate_tick_quality(tick_result=_fake_tick(
            act_kind="tick_dispatched",
            priorities=["compact_context", "verify_mutations"],
            elapsed_ms=2000,
        ))
    assert result["score"] < 60, "form uden spor må ikke give høj score"


def test_spor_loefter_scoren():
    """Samme slag, men denne gang efterlod det noget."""
    with patch("core.services.agent_self_evaluation.load_json", return_value=[]), \
         patch("core.services.agent_self_evaluation.save_json"), \
         _med_spor("memory.written", "credit_assignment.choice_recorded",
                   "thought_stream.fragment_generated", "learning_pipeline.cycle_completed",
                   "runtime.emergent_signal_created", "dream.recorded"):
        result = evaluate_tick_quality(tick_result=_fake_tick(
            act_kind="productive_idle",
            actions=["personality_snapshot", "composite_candidates:2"],
            elapsed_ms=5000,
        ))
    assert result["score"] >= 80
    assert len(result["trace_kinds"]) == 6


def test_samme_spor_som_sidst_giver_ingen_nyhed():
    """Et system der kører den samme runde igen, er ikke produktivt."""
    forrige = [{"evaluated_at": (datetime.now(UTC) - timedelta(seconds=30)).isoformat(),
                "score": 40, "trace_kinds": ["memory.written", "dream.recorded"]}]
    with patch("core.services.agent_self_evaluation.load_json", return_value=forrige), \
         patch("core.services.agent_self_evaluation.save_json"), \
         _med_spor("memory.written", "dream.recorded"):
        gentaget = evaluate_tick_quality(tick_result=_fake_tick(actions=["x"]))
    with patch("core.services.agent_self_evaluation.load_json", return_value=forrige), \
         patch("core.services.agent_self_evaluation.save_json"), \
         _med_spor("noget.helt_nyt", "og_et_til.ogsaa_nyt"):
        nyt = evaluate_tick_quality(tick_result=_fake_tick(actions=["x"]))
    assert nyt["score"] > gentaget["score"], "nye spor skal score højere end en gentagelse"


def test_haengende_slag_faar_ingen_tidspoint():
    with patch("core.services.agent_self_evaluation.load_json", return_value=[]), \
         patch("core.services.agent_self_evaluation.save_json"), _uden_spor():
        result = evaluate_tick_quality(tick_result=_fake_tick(elapsed_ms=200_000))
    assert any("HANG" in n for n in result["notes"])


def test_posten_gemmer_hvad_slaget_udrettede():
    """Uden actions/trace_kinds i posten kan nyheds-målingen ikke virke næste gang."""
    with patch("core.services.agent_self_evaluation.load_json", return_value=[]), \
         patch("core.services.agent_self_evaluation.save_json"), \
         _med_spor("memory.written"):
        result = evaluate_tick_quality(tick_result=_fake_tick(actions=["a", "b"]))
    assert result["actions"] == ["a", "b"]
    assert result["trace_kinds"] == ["memory.written"]
    assert result["window_seconds"] >= 0


def test_laast_maaling_raabes_op_i_opsummeringen():
    """Den fejl vi lige har rettet, må aldrig kunne gemme sig igen."""
    nu = datetime.now(UTC)
    evals = [{"evaluated_at": (nu - timedelta(minutes=i)).isoformat(), "score": 70}
             for i in range(20)]
    with patch("core.services.agent_self_evaluation.load_json", return_value=evals):
        s = tick_quality_summary()
    assert s["trend"] == "locked"
    assert s["distinct_scores"] == 1
    assert "låst" in s["warning"]


def test_summary_no_evals_returns_empty():
    with patch("core.services.agent_self_evaluation.load_json", return_value=[]):
        s = tick_quality_summary()
    assert s["count"] == 0
    assert s["avg_score"] is None


def test_summary_calculates_trend_improving():
    now = datetime.now(UTC)
    evals = [
        {"evaluated_at": (now - timedelta(days=6)).isoformat(), "score": 30},
        {"evaluated_at": (now - timedelta(days=5)).isoformat(), "score": 35},
        {"evaluated_at": (now - timedelta(days=4)).isoformat(), "score": 40},
        {"evaluated_at": (now - timedelta(days=1)).isoformat(), "score": 80},
        {"evaluated_at": (now - timedelta(hours=12)).isoformat(), "score": 85},
        {"evaluated_at": now.isoformat(), "score": 90},
    ]
    with patch("core.services.agent_self_evaluation.load_json", return_value=evals):
        s = tick_quality_summary(days=7)
    assert s["count"] == 6
    assert s["trend"] == "improving"


def test_detect_stale_goals_returns_old_ones():
    old_iso = (datetime.now(UTC) - timedelta(days=5)).isoformat()
    fresh_iso = datetime.now(UTC).isoformat()
    with patch("core.services.autonomous_goals.list_goals", return_value=[
        {"goal_id": "g1", "title": "stale one", "priority": "high",
         "updated_at": old_iso, "created_at": old_iso},
        {"goal_id": "g2", "title": "fresh one", "priority": "low",
         "updated_at": fresh_iso, "created_at": fresh_iso},
    ]):
        stale = detect_stale_goals(stale_days=3)
    assert len(stale) == 1
    assert stale[0]["title"] == "stale one"


def test_stale_goals_section_returns_none_when_clean():
    with patch("core.services.agent_self_evaluation.detect_stale_goals", return_value=[]):
        assert stale_goals_section() is None


def test_stale_goals_section_lists_when_present():
    with patch("core.services.agent_self_evaluation.detect_stale_goals", return_value=[
        {"goal_id": "g1", "title": "stagnerer", "priority": "high",
         "last_update": "2026-04-20T00:00:00Z", "days_stale": 3},
    ]):
        section = stale_goals_section()
    assert section is not None
    assert "stagnerer" in section


def test_adherence_returns_none_when_no_decisions():
    with patch("core.runtime.db_decisions.list_decisions", return_value=[]):
        result = decision_adherence_summary()
    assert result["score"] is None


def test_adherence_calculates_score():
    with patch("core.runtime.db_decisions.list_decisions", return_value=[
        {"decision_id": "d1", "directive": "x", "adherence_score": 1.0},
        {"decision_id": "d2", "directive": "y", "adherence_score": 0.5},
    ]):
        result = decision_adherence_summary()
    assert result["score"] == 75.0
    assert result["flag"] is None  # 75 > 60


def test_adherence_flags_low_score():
    with patch("core.runtime.db_decisions.list_decisions", return_value=[
        {"decision_id": "d1", "directive": "x", "adherence_score": 0.0},
        {"decision_id": "d2", "directive": "y", "adherence_score": 0.5},
    ]):
        result = decision_adherence_summary()
    assert result["flag"]
    assert result["recovery"]["needed"] is True
    assert result["low_decisions"][0]["decision_id"] == "d1"


def test_adherence_recovery_detects_duplicate_active_decisions():
    with patch("core.runtime.db_decisions.list_decisions", return_value=[
        {"decision_id": "d1", "directive": "Do the thing", "priority": 80, "adherence_score": 0.5, "created_at": "1"},
        {"decision_id": "d2", "directive": "  do   the thing  ", "priority": 75, "adherence_score": None, "created_at": "2"},
    ]):
        result = decision_adherence_summary()
    assert result["duplicate_groups"][0]["keeper_id"] == "d1"
    assert result["duplicate_groups"][0]["duplicate_ids"] == ["d2"]
    assert "duplicate" in result["recovery"]["actions"][0].lower()


def test_self_evaluation_section_combines_all():
    with patch("core.services.agent_self_evaluation.tick_quality_summary",
               return_value={"avg_score": 65, "trend": "stable", "count": 10}), \
         patch("core.services.agent_self_evaluation.decision_adherence_summary",
               return_value={"score": 50, "flag": True}), \
         patch("core.services.agent_self_evaluation.detect_stale_goals",
               return_value=[{"goal_id": "g1"}]):
        section = self_evaluation_section()
    assert section is not None
    assert "65" in section
    assert "50%" in section
    # Section text was lowercase "stagnerer"; now capitalized "Stagnerende"
    # (Danish gerund form, more readable as section header). Match either.
    assert "tagnerer" in section or "Stagnerende" in section or "stagnerende" in section
