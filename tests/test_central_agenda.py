"""Tests for Spec D / D1 — central_agenda (Centralen EJER Jarvis' dagsorden, autoritet bag flag)."""
from __future__ import annotations

import pytest

from core.services import central_agenda as ag


@pytest.fixture(autouse=True)
def _reset(isolated_runtime):
    ag._kv_set(ag._AUTHORITATIVE_FLAG, False)
    ag._kv_set(ag._AGENDA_KEY, {})
    yield


def test_agenda_converges_fragments(monkeypatch, isolated_runtime):
    """De spredte kilder konvergerer til ÉN ejet dagsorden."""
    monkeypatch.setattr(ag, "_read_goals", lambda: [{"text": "forstå central-drift", "source": "goal_synth"}])
    monkeypatch.setattr(ag, "_read_plans", lambda: [{"plan_id": "p1", "title": "byg D2",
                                                     "steps": [{"text": "valens", "completed": False}], "source": "plan"}])
    monkeypatch.setattr(ag, "_read_todos", lambda: [{"text": "ryd memory", "source": "todo"}])
    monkeypatch.setattr(ag, "_read_initiatives", lambda: [{"text": "skriv til Bjørn", "source": "initiative"}])
    monkeypatch.setattr(ag, "_top_want", lambda: None)
    a = ag.build_agenda()
    assert a["counts"] == {"goals": 1, "plans": 1, "todos": 1, "initiatives": 1}
    assert a["active_plan"]["plan_id"] == "p1"


def test_next_intention_prioritizes_plan_step(monkeypatch, isolated_runtime):
    agenda = {"active_plan": {"plan_id": "p1", "steps": [{"text": "trin A", "completed": True},
                                                         {"text": "trin B", "completed": False}]},
              "top_want": {"text": "w"}, "initiatives": [], "goals": [], "todos": []}
    ni = ag.choose_next_intention(agenda)
    assert ni["kind"] == "plan_step" and ni["text"] == "trin B"    # første ufuldførte trin


def test_next_intention_falls_through_to_want_then_goal():
    a1 = {"active_plan": None, "top_want": {"text": "længsel"}, "initiatives": [], "goals": [], "todos": []}
    assert ag.choose_next_intention(a1)["kind"] == "want"
    a2 = {"active_plan": None, "top_want": None, "initiatives": [], "goals": [{"text": "mål"}], "todos": []}
    assert ag.choose_next_intention(a2)["kind"] == "goal"


# ── AUTORITET bag flag ───────────────────────────────────────────────────────────────
def test_authority_shadow_default(isolated_runtime):
    """SHADOW default: authoritative_next_intention returnerer None (runtime bruger gammel sti)."""
    ag._kv_set(ag._AGENDA_KEY, {"next_intention": {"kind": "goal", "text": "noget"}})
    assert ag.is_authoritative() is False
    assert ag.authoritative_next_intention() is None


def test_authority_live_drives_intention(isolated_runtime):
    """LIVE: Centralens valgte intention returneres → runtime læser Jarvis' retning FRA Centralen."""
    ag._kv_set(ag._AGENDA_KEY, {"next_intention": {"kind": "plan_step", "text": "byg D2"}})
    ag._kv_set(ag._AUTHORITATIVE_FLAG, True)
    ni = ag.authoritative_next_intention()
    assert ni and ni["text"] == "byg D2"


def test_authority_none_without_intention(isolated_runtime):
    ag._kv_set(ag._AGENDA_KEY, {"next_intention": None})
    ag._kv_set(ag._AUTHORITATIVE_FLAG, True)
    assert ag.authoritative_next_intention() is None       # ingen intention → None (fail-safe)


def test_tick_owns_agenda_durably(monkeypatch, isolated_runtime):
    monkeypatch.setattr(ag, "_read_goals", lambda: [{"text": "m", "source": "goal_synth"}])
    monkeypatch.setattr(ag, "_read_plans", lambda: [])
    monkeypatch.setattr(ag, "_read_todos", lambda: [])
    monkeypatch.setattr(ag, "_read_initiatives", lambda: [])
    monkeypatch.setattr(ag, "_top_want", lambda: None)
    res = ag.run_agenda_tick()
    assert res["status"] == "ok" and res["mode"] == "shadow"
    # durabelt ejet → læsbart efter "genstart"
    assert ag.get_agenda()["next_intention"]["kind"] == "goal"


# ── konsument-integration: autonome runs (void-fill, aldrig override) ─────────────────
def test_autonomous_void_fill_only_when_live_and_blank(isolated_runtime):
    """start_autonomous_run: Centralens intention fylder KUN en tom retning, og kun live."""
    from core.services import central_agenda as a
    a._kv_set(a._AGENDA_KEY, {"next_intention": {"kind": "goal", "text": "Centralens retning"}})
    # shadow → None → ingen fill
    assert a.authoritative_next_intention() is None
    # live → fill-værdien er der
    a._kv_set(a._AUTHORITATIVE_FLAG, True)
    assert a.authoritative_next_intention()["text"] == "Centralens retning"
