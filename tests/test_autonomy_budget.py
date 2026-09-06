"""Dagligt budget for selvvalgte handlinger + tælling af stilheden (blok E, 4/9)."""
from __future__ import annotations

import datetime as dt

import pytest

from core.services import autonomy_budget as AB


@pytest.fixture
def state(monkeypatch):
    store: dict = {}
    monkeypatch.setattr("core.runtime.db.get_runtime_state_value",
                        lambda k, d=None: store.get(k, d))
    monkeypatch.setattr("core.runtime.db.set_runtime_state_value",
                        lambda k, v: store.__setitem__(k, v))
    return store


def test_budget_allows_five_then_stops(state):
    now = dt.datetime(2026, 9, 4, 10, tzinfo=dt.UTC)
    for i in range(AB.DEFAULT_DAILY_BUDGET):
        assert AB.may_act("write_chronicle_entry", now=now)["allowed"] is True
        AB.note_action("write_chronicle_entry", now=now)
        assert AB.remaining(now) == AB.DEFAULT_DAILY_BUDGET - (i + 1)
    blocked = AB.may_act("explore_own_codebase", now=now)
    assert blocked["allowed"] is False and blocked["reason"] == "daily-budget-spent"


def test_budget_resets_the_next_day(state):
    day1 = dt.datetime(2026, 9, 4, 23, tzinfo=dt.UTC)
    for _ in range(AB.DEFAULT_DAILY_BUDGET):
        AB.note_action("a", now=day1)
    assert AB.may_act(now=day1)["allowed"] is False
    day2 = day1 + dt.timedelta(hours=2)
    assert AB.may_act(now=day2)["allowed"] is True
    assert AB.remaining(day2) == AB.DEFAULT_DAILY_BUDGET


def test_the_log_says_what_he_did(state):
    now = dt.datetime(2026, 9, 4, 10, tzinfo=dt.UTC)
    AB.note_action("write_growth_journal", now=now)
    surface = AB.build_autonomy_budget_surface()
    assert surface["spent_today"] == 1 and surface["remaining"] == AB.DEFAULT_DAILY_BUDGET - 1
    assert "1/5" in surface["summary"]


def test_budget_is_adjustable(state):
    AB.set_daily_budget(2)
    now = dt.datetime(2026, 9, 4, 10, tzinfo=dt.UTC)
    AB.note_action("a", now=now)
    AB.note_action("b", now=now)
    assert AB.may_act(now=now)["allowed"] is False


def test_silence_is_counted_by_reason(state):
    for _ in range(4):
        AB.note_silence(outcome="stay_quiet", reason_code="user-active")
    AB.note_silence(outcome="defer", reason_code="open-loops")
    counts = AB.silence_counts()
    assert counts["stay_quiet|user-active"] == 4 and counts["defer|open-loops"] == 1


def test_weekly_summary_needs_something_to_report(state):
    AB.note_silence(outcome="stay_quiet", reason_code="user-active")
    assert AB.build_weekly_summary() == ""
    for _ in range(5):
        AB.note_silence(outcome="stay_quiet", reason_code="user-active")
    text = AB.build_weekly_summary()
    assert "6 gange" in text and "user-active" in text


def test_weekly_review_surfaces_once_and_resets(state, monkeypatch):
    added: list[dict] = []
    monkeypatch.setattr("core.services.proactive_candidates.add_candidate",
                        lambda **kw: (added.append(kw), {"status": "added"})[1])
    for _ in range(6):
        AB.note_silence(outcome="quiet_hold", reason_code="cadence")
    now = dt.datetime(2026, 9, 4, tzinfo=dt.UTC)
    assert AB.run_weekly_review(now=now)["surfaced"] is True
    assert len(added) == 1 and AB.silence_counts() == {}
    assert AB.run_weekly_review(now=now + dt.timedelta(days=2))["ran"] is False
    assert AB.run_weekly_review(now=now + dt.timedelta(days=8))["ran"] is True


def test_a_broken_state_store_never_blocks_him(monkeypatch):
    def _boom(*_a, **_k):
        raise RuntimeError("state nede")
    monkeypatch.setattr("core.runtime.db.get_runtime_state_value", _boom)
    monkeypatch.setattr("core.runtime.db.set_runtime_state_value", _boom)
    assert AB.may_act("noget")["allowed"] is True
    AB.note_silence(outcome="stay_quiet", reason_code="x")  # må ikke kaste
