"""Tests for goal_reporter — de tre målinger føres tilbage til målet.

Kernen i testen er den beslutning der er let at tage fejl af: at det svageste
led bestemmer progress, ikke gennemsnittet.
"""
from __future__ import annotations

from core.services import goal_reporter as gr


def test_criterion_fulfilment_caps_at_one_and_handles_none():
    assert gr._criterion_fulfilment(75, 75) == 1.0
    assert gr._criterion_fulfilment(150, 75) == 1.0  # i mål er i mål
    assert gr._criterion_fulfilment(37.5, 75) == 0.5
    assert gr._criterion_fulfilment(None, 75) is None
    assert gr._criterion_fulfilment("skrald", 75) is None


def test_progress_is_governed_by_the_weakest_criterion():
    # tick i mål (93 ≥ 75), heed langt fra (36% < 80%) → 36/80 = 45%
    p = gr.compute_progress(tick_score=93.2, heed_rate=0.36)
    assert p["progress_pct"] == 45
    assert p["weakest"] == "heed-rate"


def test_progress_is_100_only_when_both_criteria_are_met():
    p = gr.compute_progress(tick_score=93.2, heed_rate=0.85)
    assert p["progress_pct"] == 100


def test_progress_is_none_without_measurements():
    p = gr.compute_progress(tick_score=None, heed_rate=None)
    assert p["progress_pct"] is None
    assert p["weakest"] is None


def test_progress_survives_one_missing_measurement():
    p = gr.compute_progress(tick_score=90.0, heed_rate=None)
    assert p["progress_pct"] == 100  # kun det målte kriterium tæller


def test_report_writes_update_to_the_goal(monkeypatch):
    written: dict = {}
    monkeypatch.setattr(
        gr,
        "collect_metrics",
        lambda *, days=7: {
            "tick_score": 90.0,
            "heed_rate": 0.5,
            "adherence": 3.8,
            "window_days": days,
        },
    )
    monkeypatch.setattr(
        gr, "_find_goal", lambda *, title_fragment: {"goal_id": "goal_x", "progress_pct": 0}
    )

    import core.runtime.db_goals as dbg

    def fake_append(**kw):
        written.update(kw)
        return {"progress_pct": 62}

    monkeypatch.setattr(dbg, "append_goal_update", fake_append)

    res = gr.report_goal_metrics()

    assert res["status"] == "ok"
    assert written["goal_id"] == "goal_x"
    assert written["source"] == "goal_reporter"
    assert written["progress_delta"] == 62
    assert res["to_progress"] == 62
    assert "decision-adherence: 3.8%" in res["note"]


def test_dry_run_does_not_write(monkeypatch):
    monkeypatch.setattr(
        gr,
        "collect_metrics",
        lambda *, days=7: {"tick_score": 90.0, "heed_rate": 0.5, "adherence": None,
                           "window_days": days},
    )
    monkeypatch.setattr(
        gr, "_find_goal", lambda *, title_fragment: {"goal_id": "goal_x", "progress_pct": 10}
    )

    import core.runtime.db_goals as dbg

    def explode(**kw):  # pragma: no cover — må ikke kaldes
        raise AssertionError("dry_run skrev til målet")

    monkeypatch.setattr(dbg, "append_goal_update", explode)

    res = gr.report_goal_metrics(dry_run=True)
    assert res["dry_run"] is True
    assert res["to_progress"] == 62


def test_missing_goal_is_reported_not_silent(monkeypatch):
    monkeypatch.setattr(
        gr,
        "collect_metrics",
        lambda *, days=7: {"tick_score": 90.0, "heed_rate": 0.5, "adherence": None,
                           "window_days": days},
    )
    monkeypatch.setattr(gr, "_find_goal", lambda *, title_fragment: None)

    res = gr.report_goal_metrics()
    assert res["status"] == "error"
    assert "matcher" in res["error"]
