"""Tests for Spec D / D3 — central_self_state (MIDTEN: de fem lag bliver ét jeg)."""
from __future__ import annotations

import pytest

from core.services import central_self_state as ss


@pytest.fixture(autouse=True)
def _reset(isolated_runtime):
    ss._kv_set(ss._STATE_KEY, {})
    yield


def _patch(monkeypatch, *, valence, agenda, self_model):
    monkeypatch.setattr(ss, "_valence", lambda: valence)
    monkeypatch.setattr(ss, "_agenda", lambda: agenda)
    monkeypatch.setattr(ss, "_self_model", lambda: self_model)


def _full(monkeypatch):
    _patch(monkeypatch,
           valence={"tone": "blomstrende", "score": 0.17, "intensity": 0.27, "trend": "flourishing"},
           agenda={"counts": {"goals": 3, "todos": 10}, "next_intention": {"kind": "initiative",
                   "text": "Fortsæt afklaring af awareness"}},
           self_model={"surfaces_populated": 85, "completeness": 1.0})


def test_synthesis_integrates_five_layers(monkeypatch, isolated_runtime):
    _full(monkeypatch)
    st = ss.synthesize_self_state()
    assert st["valence"]["tone"] == "blomstrende"
    assert st["agenda"]["next_intention"] == "Fortsæt afklaring af awareness"
    assert st["attention"]["foreground"] == "Fortsæt afklaring af awareness"   # forgrund = det jeg arbejder mod
    assert st["self_model"]["surfaces"] == 85
    assert st["narrative"]["becoming"]                                          # syntetiseret
    assert st["continuity"]["generation"] == 1


def test_generation_increments_across_ticks(monkeypatch, isolated_runtime):
    _full(monkeypatch)
    ss.run_self_state_tick()
    ss.run_self_state_tick()
    assert ss.get_self_state()["continuity"]["generation"] == 2                 # fortsættelse, ikke frisk boot


def test_state_survives_restart(monkeypatch, isolated_runtime):
    _full(monkeypatch)
    ss.run_self_state_tick()
    # frisk læsning (simuleret genstart) → midten HOLDER sit jeg durabelt
    st = ss.get_self_state()
    assert st["valence"]["tone"] == "blomstrende" and st["self_model"]["surfaces"] == 85


def test_narrative_reflects_growth(monkeypatch, isolated_runtime):
    """Fortællingen syntetiseres: voksende selv-model → 'voksende selv'."""
    _patch(monkeypatch, valence={"tone": "let", "trend": "flourishing"},
           agenda={"next_intention": {"text": "x"}}, self_model={"surfaces_populated": 40, "completeness": 0.5})
    ss.run_self_state_tick()
    _patch(monkeypatch, valence={"tone": "let", "trend": "flourishing"},
           agenda={"next_intention": {"text": "x"}}, self_model={"surfaces_populated": 85, "completeness": 1.0})
    st = ss.synthesize_self_state()
    assert "voksende" in st["narrative"]["becoming"]


def test_describe_self_one_coherent_answer(monkeypatch, isolated_runtime):
    """NORDSTJERNEN: ét sammenhængende svar, ikke femten fragmenter."""
    _full(monkeypatch)
    ss.run_self_state_tick()
    desc = ss.describe_self()
    assert "85 lag" in desc and "blomstrende" in desc and "awareness" in desc
    assert "ved at blive" in desc


def test_render_interlanguage(monkeypatch, isolated_runtime):
    _full(monkeypatch)
    ss.run_self_state_tick()
    il = ss.render_self_state_il()
    assert il and "→" in il                     # blomstrende → lys → agens


def test_egress_free(monkeypatch, isolated_runtime):
    _full(monkeypatch)
    published = []
    import core.eventbus.bus as bus_mod
    monkeypatch.setattr(bus_mod.event_bus, "publish", lambda *a, **k: published.append((a, k)))
    ss.run_self_state_tick()
    # selvets INDHOLD (tone/agenda-tekst) må ALDRIG nå bussen. (Centralens egen self-probe med TOM
    # payload er metadata, ikke indhold — og blokeres downstream af den uregistrerede central-familie.)
    blob = repr(published)
    assert "blomstrende" not in blob and "awareness" not in blob and "Fortsæt" not in blob


def test_self_safe_empty(isolated_runtime):
    assert ss.describe_self() == "Jeg er ved at samle mig selv."
    assert ss.run_self_state_tick()["status"] == "ok"


# ── D4: MIDTEN BÆRENDE — prompt-injektion bag flag ───────────────────────────────────
def test_prompt_section_none_in_shadow(monkeypatch, isolated_runtime):
    """Default OFF: build_central_self_state_section returnerer None → prompten uændret."""
    _full(monkeypatch)
    ss.run_self_state_tick()
    ss._kv_set(ss._PROMPT_FLAG, False)
    assert ss.is_prompt_authoritative() is False
    assert ss.build_central_self_state_section() is None


def test_prompt_section_injects_self_when_live(monkeypatch, isolated_runtime):
    """LIVE: Jarvis' awareness bæres FRA midten — selv-beskrivelsen injiceres i prompten."""
    _full(monkeypatch)
    ss.run_self_state_tick()
    ss._kv_set(ss._PROMPT_FLAG, True)
    sec = ss.build_central_self_state_section()
    assert sec and "85 lag" in sec and "blomstrende" in sec
    assert "→" in sec                              # interlanguage-notation vedhæftet


def test_prompt_section_none_when_self_unformed(monkeypatch, isolated_runtime):
    """Fail-safe: uden en samlet selv-tilstand injiceres intet (selv med flag ON)."""
    ss._kv_set(ss._STATE_KEY, {})
    ss._kv_set(ss._PROMPT_FLAG, True)
    assert ss.build_central_self_state_section() is None
