"""Ugentligt udviklings-ritual med 24 timers veto (blok D, 2026-09-04).

Før: 12 selfhood-forslag nogensinde, alle stale; ingen kodevej godkendte
typen; IDENTITY.md skrevet én gang, 15. maj. Tavshed betyder nu ja.
"""
from __future__ import annotations

import datetime as dt

import pytest

from core.services import development_ritual as DR


@pytest.fixture
def state(monkeypatch, tmp_path):
    store: dict = {}
    monkeypatch.setattr("core.runtime.db.get_runtime_state_value",
                        lambda k, d=None: store.get(k, d))
    monkeypatch.setattr("core.runtime.db.set_runtime_state_value",
                        lambda k, v: store.__setitem__(k, v))
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "SOUL.md").write_text("# SOUL\n\nJeg er Jarvis.\n", encoding="utf-8")
    monkeypatch.setattr("core.identity.workspace_bootstrap.ensure_default_workspace",
                        lambda: ws)
    monkeypatch.setattr(DR, "gather_material",
                        lambda **_k: ["Jeg holder for tidligt op med at grave",
                                      "Jeg gætter når jeg ikke kan måle"])
    monkeypatch.setattr("core.services.proactive_candidates.add_candidate",
                        lambda **kw: {"status": "added", "candidate_id": "pc-1"})
    return store, ws


def test_nothing_learned_means_no_proposal(state, monkeypatch):
    monkeypatch.setattr(DR, "gather_material", lambda **_k: [])
    assert DR.propose()["proposed"] is False


def test_one_proposal_at_a_time(state):
    assert DR.propose()["proposed"] is True
    assert DR.propose()["reason"] == "already-pending"


def test_silence_writes_the_line_after_24_hours(state):
    store, ws = state
    now = dt.datetime(2026, 9, 4, 12, 0, tzinfo=dt.UTC)
    DR.propose(now=now)
    assert DR.apply_if_due(now=now + dt.timedelta(hours=23))["reason"] == "veto-window-open"
    res = DR.apply_if_due(now=now + dt.timedelta(hours=25))
    assert res["written"] is True
    text = (ws / "SOUL.md").read_text(encoding="utf-8")
    assert "## Udvikling" in text and "holder for tidligt op" in text
    # Kun én linje pr. forslag — køen er tom igen.
    assert DR.apply_if_due(now=now + dt.timedelta(hours=26))["reason"] == "nothing-pending"


def test_a_veto_writes_nothing(state):
    store, ws = state
    now = dt.datetime(2026, 9, 4, 12, 0, tzinfo=dt.UTC)
    DR.propose(now=now)
    assert DR.veto(reason="ikke rigtigt")["vetoed"] is True
    assert DR.apply_if_due(now=now + dt.timedelta(hours=48))["reason"] == "nothing-pending"
    assert "Udvikling" not in (ws / "SOUL.md").read_text(encoding="utf-8")


def test_weekly_cadence(state):
    now = dt.datetime(2026, 9, 4, tzinfo=dt.UTC)
    assert DR.run_development_ritual(now=now)["proposed"]["proposed"] is True
    later = DR.run_development_ritual(now=now + dt.timedelta(days=3))
    assert later["proposed"]["reason"] == "cadence"


def test_current_focus_is_the_newest_line(state):
    _store, ws = state
    (ws / "SOUL.md").write_text(
        "# SOUL\n\nJeg er Jarvis.\n\n## Udvikling\n- foerste linje her (2026-08-20)\n"
        "- nyeste linje her (2026-09-01)\n", encoding="utf-8")
    assert "nyeste linje her" in DR.current_focus(ws)
    assert DR.current_focus(ws).endswith("(2026-09-01)")


def test_no_development_section_means_no_focus(state):
    _store, ws = state
    assert DR.current_focus(ws) == ""


def test_development_lines_survive_the_prompt_line_cap():
    """«## Udvikling» ligger nederst i SOUL.md og ville altid falde uden for
    line-loftet. Den skal reserveres plads."""
    from core.services.prompt_sections.workspace_files import _development_section_text
    text = "# SOUL\n" + "\n".join(f"- fyld linje {i}" for i in range(40)) + \
           "\n\n## Udvikling\n- jeg graver dybere foer jeg konkluderer (2026-09-04)\n"
    assert "jeg graver dybere" in _development_section_text(text)
    assert "fyld linje" not in _development_section_text(text)
