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


# ── REGRESSION: _read_goals er en READ, aldrig en synthesis-write (aug 2026) ──────────
def test_read_goals_reads_never_synthesizes(monkeypatch, isolated_runtime):
    """Feed-læsning må ALDRIG kalde den skrivende synthesize_candidate_goals.

    Regression: central_agenda._read_goals() kaldte synthesize_candidate_goals() på
    hver agenda-build → 1763 dublet-mål ophobet, throttle omgået. En read der skriver
    = dobbelt-sandhed. Nu skal den læse eksisterende mål via list_goals.
    """
    import core.services.autonomous_goals as goals_mod

    def _boom(*_a, **_k):  # pragma: no cover - må aldrig rammes
        raise AssertionError("_read_goals kaldte synthesize_candidate_goals (skriver!)")

    monkeypatch.setattr("core.services.goal_signal_synthesizer.synthesize_candidate_goals", _boom)
    monkeypatch.setattr(goals_mod, "list_goals", lambda **_k: [
        {"goal_id": "g1", "title": "aktivt mål", "status": "active", "priority": "high"},
    ])
    read = ag._read_goals()
    assert read and read[0]["text"] == "aktivt mål"
    assert read[0]["source"] == "goal"


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


# ── C1/D2: Centralens forgrund må bære en VÆRDI, ikke en Python-repr (3/11-2026) ─────
def test_want_rendres_fra_sine_egne_felter():
    """`Want` har hverken `text` eller `summary` — så den gamle fallback skrev `str(w)`.

    Målt 3/11-2026: Centralens forgrund var «Want(want_id='want-11871', want_type='growth',
    …, life_phase='deep_» — en repr afskåret midt i et ord, som derefter gik videre ind i
    prompten som «jeg arbejder mod: …». En repr kan ikke læses, citeres eller handles på.
    """
    from core.services.initiative_accumulator import Want

    w = Want(want_id="w1", want_type="growth", topic="self_improvement",
             strength=0.4612692276, created_at="2026-11-03T10:51:35+00:00",
             life_phase="deep_work")
    tekst = ag.render_want_text(w)

    assert "Want(" not in tekst, "en repr er ikke en retning"
    assert "want_id" not in tekst
    assert "self_improvement" in tekst and "vokse" in tekst
    assert "0.46" in tekst and "deep_work" in tekst


def test_want_uden_laesbart_indhold_giver_tom_streng():
    """Kan intet udledes, tømmes feltet — så kalderen kan tie frem for at vise skrald."""
    from core.services.initiative_accumulator import Want

    tomt = Want(want_id="w2", want_type="", topic="", strength=0.0,
                created_at="", life_phase="")
    assert ag.render_want_text(tomt) == ""


def test_want_som_dict_laeses_som_tekst():
    """Den positive tvilling: en dict med reel tekst går uændret igennem.

    Uden den kunne `render_want_text` bestå ved at returnere tomt for ALT.
    """
    assert ag.render_want_text({"text": "skriv til Bjørn"}) == "skriv til Bjørn"
    assert ag.render_want_text({"topic": "rydde op"}) == "rydde op"


def test_top_want_skriver_aldrig_en_repr(monkeypatch, isolated_runtime):
    """_top_want er kilden til Centralens forgrund — den må ikke lække en repr videre."""
    import core.services.initiative_accumulator as ia

    monkeypatch.setattr(ia, "get_top_want", lambda: ia.Want(
        want_id="want-11871", want_type="growth", topic="self_improvement",
        strength=0.46, created_at="2026-11-03T10:51:35+00:00", life_phase="deep_work",
    ))
    w = ag._top_want()
    assert w is not None
    assert "Want(" not in w["text"]
    assert w["text"] == "Jeg vil gerne vokse om self_improvement (styrke 0.46, fase deep_work)"
    assert w["want_type"] == "growth"
