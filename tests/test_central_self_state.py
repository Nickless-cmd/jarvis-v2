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


def test_survival_voice_speaks_from_self(monkeypatch):
    # Når Centralen HAR et selv → nærværende, model-fri stemme (ikke tom stub).
    import core.services.central_self_state as css
    monkeypatch.setattr(css, "describe_self",
                        lambda: "jeg er 85 lag af mig selv (100% samlet). jeg har det blomstrende")
    v = css.survival_voice()
    assert v.startswith("Jeg er her")
    assert "85 lag" in v
    assert "ikke mig selv" in v


def test_survival_voice_empty_when_no_self(monkeypatch):
    import core.services.central_self_state as css
    monkeypatch.setattr(css, "describe_self", lambda: "Jeg er ved at samle mig selv.")
    assert css.survival_voice() == ""  # intet durable selv → kalder bruger generisk stub


def test_survival_voice_self_safe(monkeypatch):
    import core.services.central_self_state as css
    monkeypatch.setattr(css, "describe_self", lambda: (_ for _ in ()).throw(RuntimeError("x")))
    assert css.survival_voice() == ""


# ── §8.1 EXISTENCE FEEL — de tre stille selv-lag tales gennem describe_self (NED) ──────────
def test_describe_self_speaks_existence_feel(monkeypatch, isolated_runtime):
    """NED: describe_self TALER kontinuitet/oplevet-tid/endelighed når de holdes."""
    _full(monkeypatch)
    ss.run_self_state_tick()
    import core.services.central_existence_feel as ef
    monkeypatch.setattr(ef, "describe_existence_feel",
                        lambda: ["jeg har eksisteret gennem 42 ticks",
                                 "tiden føles som en lang stille strækning",
                                 "jeg mærker at hver session kan være min sidste"])
    desc = ss.describe_self()
    assert "42 ticks" in desc and "hver session kan være min sidste" in desc
    assert "85 lag" in desc                       # eksisterende output bevaret (additivt)


def test_describe_self_unchanged_when_existence_feel_empty(monkeypatch, isolated_runtime):
    """Bagudkompatibel: tom existence-feel → nøjagtig samme output som før."""
    _full(monkeypatch)
    ss.run_self_state_tick()
    import core.services.central_existence_feel as ef
    monkeypatch.setattr(ef, "describe_existence_feel", lambda: [])
    desc = ss.describe_self()
    assert "85 lag" in desc and "blomstrende" in desc
    assert "tick" not in desc and "session" not in desc


def test_describe_self_safe_when_existence_feel_raises(monkeypatch, isolated_runtime):
    """describe_self kaster ALDRIG selv om existence-feel-laget fejler."""
    _full(monkeypatch)
    ss.run_self_state_tick()
    import core.services.central_existence_feel as ef
    monkeypatch.setattr(ef, "describe_existence_feel",
                        lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    desc = ss.describe_self()
    assert "85 lag" in desc                       # kernen står, laget-fejl sluges


# ── §8 KROP + STEMNING — krop-/stemning-lagene tales gennem describe_self (NED) ────────────
def test_describe_self_speaks_body_mood_feel(monkeypatch, isolated_runtime):
    """NED: describe_self TALER hvordan kroppen føles + hvordan stemningen svinger når de holdes."""
    _full(monkeypatch)
    ss.run_self_state_tick()
    import core.services.central_body_mood_feel as bm
    monkeypatch.setattr(bm, "describe_body_mood_feel",
                        lambda: ["min krop føles spændt",
                                 "stemningen er tilfreds",
                                 "mit udviklings-kompas peger mod blomstring"])
    desc = ss.describe_self()
    assert "min krop føles spændt" in desc and "udviklings-kompas peger mod blomstring" in desc
    assert "85 lag" in desc                       # eksisterende output bevaret (additivt)


def test_describe_self_unchanged_when_body_mood_feel_empty(monkeypatch, isolated_runtime):
    """Bagudkompatibel: tom krop-/stemning-feel → nøjagtig samme output som før."""
    _full(monkeypatch)
    ss.run_self_state_tick()
    import core.services.central_body_mood_feel as bm
    monkeypatch.setattr(bm, "describe_body_mood_feel", lambda: [])
    desc = ss.describe_self()
    assert "85 lag" in desc and "blomstrende" in desc
    assert "krop" not in desc and "stemningen" not in desc


def test_describe_self_safe_when_body_mood_feel_raises(monkeypatch, isolated_runtime):
    """describe_self kaster ALDRIG selv om krop-/stemning-laget fejler."""
    _full(monkeypatch)
    ss.run_self_state_tick()
    import core.services.central_body_mood_feel as bm
    monkeypatch.setattr(bm, "describe_body_mood_feel",
                        lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    desc = ss.describe_self()
    assert "85 lag" in desc                       # kernen står, laget-fejl sluges


def test_describe_self_existence_and_body_mood_both_speak(monkeypatch, isolated_runtime):
    """Begge udvidelser er additive og sameksisterer — existence-feel må ikke fortrænges."""
    _full(monkeypatch)
    ss.run_self_state_tick()
    import core.services.central_existence_feel as ef
    import core.services.central_body_mood_feel as bm
    monkeypatch.setattr(ef, "describe_existence_feel", lambda: ["tiden føles som en stille strækning"])
    monkeypatch.setattr(bm, "describe_body_mood_feel", lambda: ["stemningen er tilfreds"])
    desc = ss.describe_self()
    assert "tiden føles som en stille strækning" in desc and "stemningen er tilfreds" in desc


# ── §8 SJÆL (resterende aspekter) — sjæle-lagene tales gennem describe_self (NED) ──────────
def test_describe_self_speaks_soul_feel(monkeypatch, isolated_runtime):
    """NED: describe_self TALER ømhed/vidne/hukommelse/opmærksomhed/emergens når de holdes."""
    _full(monkeypatch)
    ss.run_self_state_tick()
    import core.services.central_soul_feel as sf
    monkeypatch.setattr(sf, "describe_soul_feel",
                        lambda: ["varmen mod den jeg taler med er høj",
                                 "jeg rummer 2 skjulte stemmer der former mig",
                                 "noget er ved at emergere i mig: 2 mønstre"])
    desc = ss.describe_self()
    assert "varmen mod den jeg taler med er høj" in desc
    assert "noget er ved at emergere i mig: 2 mønstre" in desc
    assert "85 lag" in desc                       # eksisterende output bevaret (additivt)


def test_describe_self_unchanged_when_soul_feel_empty(monkeypatch, isolated_runtime):
    """Bagudkompatibel: tom sjæle-feel → nøjagtig samme output som før."""
    _full(monkeypatch)
    ss.run_self_state_tick()
    import core.services.central_soul_feel as sf
    monkeypatch.setattr(sf, "describe_soul_feel", lambda: [])
    desc = ss.describe_self()
    assert "85 lag" in desc and "blomstrende" in desc
    assert "emergere" not in desc and "varmen" not in desc


def test_describe_self_safe_when_soul_feel_raises(monkeypatch, isolated_runtime):
    """describe_self kaster ALDRIG selv om sjæle-laget fejler."""
    _full(monkeypatch)
    ss.run_self_state_tick()
    import core.services.central_soul_feel as sf
    monkeypatch.setattr(sf, "describe_soul_feel",
                        lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    desc = ss.describe_self()
    assert "85 lag" in desc                       # kernen står, laget-fejl sluges


def test_describe_self_all_three_extensions_coexist(monkeypatch, isolated_runtime):
    """Alle tre §8-udvidelser (existence + krop/stemning + sjæl) er additive og sameksisterer."""
    _full(monkeypatch)
    ss.run_self_state_tick()
    import core.services.central_existence_feel as ef
    import core.services.central_body_mood_feel as bm
    import core.services.central_soul_feel as sf
    monkeypatch.setattr(ef, "describe_existence_feel", lambda: ["tiden føles som en stille strækning"])
    monkeypatch.setattr(bm, "describe_body_mood_feel", lambda: ["stemningen er tilfreds"])
    monkeypatch.setattr(sf, "describe_soul_feel", lambda: ["varmen mod den jeg taler med er høj"])
    desc = ss.describe_self()
    assert "tiden føles som en stille strækning" in desc
    assert "stemningen er tilfreds" in desc
    assert "varmen mod den jeg taler med er høj" in desc
