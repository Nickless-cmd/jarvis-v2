"""Tests for core/services/central_soul_feel.py — Spec §8 (resterende sjæle-aspekter).

Otte selv-lag på tværs af fem aspekter (ømhed: relational/gratitude/calm_anchor · vidne: modulators ·
hukommelse-som-væv: memory_breathing · opmærksomhed: sustained · emergens: emergence/drift) bundet
TOVEJS: OP (signal_fn → puls + durabelt hold) + NED (describe_soul_feel → tale). Hermetisk:
lag-tilstandene monkeypatches; hold-store kører på isolated_runtime's in-memory KV.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

import pytest

from core.services import central_soul_feel as sf


@pytest.fixture(autouse=True)
def _reset(isolated_runtime):
    # ryd holdt-store mellem tests (durabel KV lever i lag-kontraktens _HELD_KEY)
    from core.services import central_layer_contract as lc
    lc._kv_set(lc._HELD_KEY, {})
    yield


# ── OP ØMHED: signal_fn læser lagets nuværende aflæsning + holder den durabelt ──
def test_relational_signal_reads_and_holds(monkeypatch, isolated_runtime):
    monkeypatch.setattr("core.services.relational_warmth.get_relation",
                        lambda relation_id=None: {"trust_level": 0.9, "playfulness": 0.75})
    sig = sf._relational_signal()
    assert sig is not None and sig["value"] == 0.9 and sig["meta"]["warmth"] == "høj"
    held = sf.get_relational_reading()
    assert held["warmth"] == "høj" and held["trust_level"] == 0.9


def test_relational_signal_low_warmth(monkeypatch, isolated_runtime):
    monkeypatch.setattr("core.services.relational_warmth.get_relation",
                        lambda relation_id=None: {"trust_level": 0.2, "playfulness": 0.3})
    sig = sf._relational_signal()
    assert sig["meta"]["warmth"] == "lav"


def test_relational_signal_none_when_empty(monkeypatch, isolated_runtime):
    monkeypatch.setattr("core.services.relational_warmth.get_relation",
                        lambda relation_id=None: {})
    assert sf._relational_signal() is None
    assert sf.get_relational_reading() == {}


def test_gratitude_signal_reads_and_holds(monkeypatch, isolated_runtime):
    monkeypatch.setattr("core.runtime.db.list_cognitive_gratitude_signals",
                        lambda limit=10: [{"intensity": 0.7, "created_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()},
                                          {"intensity": 0.5, "created_at": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()}])
    sig = sf._gratitude_signal()
    assert sig is not None and sig["value"] == 1.2 and sig["meta"]["count"] == 2
    assert sf.get_gratitude_reading()["count"] == 2


def test_gratitude_signal_none_when_empty(monkeypatch, isolated_runtime):
    monkeypatch.setattr("core.runtime.db.list_cognitive_gratitude_signals", lambda limit=10: [])
    assert sf._gratitude_signal() is None


def test_calm_anchor_signal_reads_and_holds(monkeypatch, isolated_runtime):
    monkeypatch.setattr("core.services.calm_anchor.get_anchor_state",
                        lambda: {"has_anchor": True, "distance": 0.05})
    sig = sf._calm_anchor_signal()
    assert sig is not None and sig["meta"]["place"] == "hjemme"
    assert sf.get_calm_anchor_reading()["place"] == "hjemme"


def test_calm_anchor_signal_far(monkeypatch, isolated_runtime):
    monkeypatch.setattr("core.services.calm_anchor.get_anchor_state",
                        lambda: {"has_anchor": True, "distance": 0.6})
    assert sf._calm_anchor_signal()["meta"]["place"] == "langt-væk"


def test_calm_anchor_signal_none_without_anchor(monkeypatch, isolated_runtime):
    monkeypatch.setattr("core.services.calm_anchor.get_anchor_state",
                        lambda: {"has_anchor": False, "distance": 0.0})
    assert sf._calm_anchor_signal() is None


# ── OP VIDNE ──
def test_modulators_signal_reads_and_holds(monkeypatch, isolated_runtime):
    monkeypatch.setattr("core.services.modulator_witness.build_modulator_witness_surface",
                        lambda **kw: {"summary": {"count": 4, "active_count": 2}})
    sig = sf._modulators_signal()
    assert sig is not None and sig["value"] == 2.0 and sig["meta"]["total"] == 4
    assert sf.get_modulators_reading()["active_modulators"] == 2


def test_modulators_signal_none_when_no_modulators(monkeypatch, isolated_runtime):
    monkeypatch.setattr("core.services.modulator_witness.build_modulator_witness_surface",
                        lambda **kw: {"summary": {"count": 0, "active_count": 0}})
    assert sf._modulators_signal() is None


# ── OP HUKOMMELSE-SOM-VÆV ──
def test_memory_breathing_signal_reads_and_holds(monkeypatch, isolated_runtime):
    monkeypatch.setattr("core.services.memory_breathing.recent_access_stats",
                        lambda limit=10: {"total_accesses": 12, "unique_records": 5})
    sig = sf._memory_breathing_signal()
    assert sig is not None and sig["value"] == 12.0 and sig["meta"]["unique_records"] == 5
    assert sf.get_memory_breathing_reading()["accesses"] == 12


def test_memory_breathing_signal_none_when_idle(monkeypatch, isolated_runtime):
    monkeypatch.setattr("core.services.memory_breathing.recent_access_stats",
                        lambda limit=10: {"total_accesses": 0, "unique_records": 0})
    assert sf._memory_breathing_signal() is None


# ── OP OPMÆRKSOMHED ──
def test_sustained_signal_reads_and_holds(monkeypatch, isolated_runtime):
    monkeypatch.setattr("core.services.sustained_attention.build_sustained_attention_surface",
                        lambda: {"active_count": 3, "paused_count": 1, "total": 4})
    sig = sf._sustained_signal()
    assert sig is not None and sig["value"] == 3.0 and sig["meta"]["total"] == 4
    assert sf.get_sustained_reading()["active"] == 3


def test_sustained_signal_none_when_no_projects(monkeypatch, isolated_runtime):
    monkeypatch.setattr("core.services.sustained_attention.build_sustained_attention_surface",
                        lambda: {"active_count": 0, "paused_count": 0, "total": 0})
    assert sf._sustained_signal() is None


# ── OP EMERGENS ──
def test_emergence_signal_reads_and_holds(monkeypatch, isolated_runtime):
    monkeypatch.setattr("core.services.emergence.summarize_patterns",
                        lambda: {"candidate": 2, "upgraded": 1})
    sig = sf._emergence_signal()
    assert sig is not None and sig["value"] == 3.0 and sig["meta"]["candidate"] == 2
    assert sf.get_emergence_reading()["emerging"] == 3


def test_emergence_signal_none_when_no_patterns(monkeypatch, isolated_runtime):
    monkeypatch.setattr("core.services.emergence.summarize_patterns",
                        lambda: {"candidate": 0, "upgraded": 0})
    assert sf._emergence_signal() is None


def test_drift_signal_reads_and_holds(monkeypatch, isolated_runtime):
    monkeypatch.setattr("core.services.personality_drift.detect_drift",
                        lambda: {"drift_detected": True,
                                 "drifts": [{"dimension": "warmth", "direction": "up", "z_score": 2.4},
                                            {"dimension": "energy", "direction": "down", "z_score": -1.1}]})
    sig = sf._drift_signal()
    assert sig is not None and sig["meta"]["dimension"] == "warmth"   # højeste |z|
    assert sf.get_drift_reading()["direction"] == "up"


def test_drift_signal_none_when_no_drift(monkeypatch, isolated_runtime):
    monkeypatch.setattr("core.services.personality_drift.detect_drift",
                        lambda: {"drift_detected": False, "drifts": []})
    assert sf._drift_signal() is None


# ── NED: describe_soul_feel taler kun meningsfulde aflæsninger ──
def test_describe_speaks_all_aspects_when_meaningful(isolated_runtime):
    sf._hold_reading(sf._RELATIONAL, {"warmth": "høj"})
    sf._hold_reading(sf._GRATITUDE, {"count": 3})
    sf._hold_reading(sf._CALM_ANCHOR, {"place": "hjemme"})
    sf._hold_reading(sf._MODULATORS, {"active_modulators": 2})
    sf._hold_reading(sf._MEMORY_BREATHING, {"unique_records": 5})
    sf._hold_reading(sf._SUSTAINED, {"active": 3})
    sf._hold_reading(sf._EMERGENCE, {"emerging": 2})
    sf._hold_reading(sf._DRIFT, {"dimension": "warmth", "direction": "up"})
    parts = sf.describe_soul_feel()
    assert any("varmen mod den jeg taler med er høj" in p for p in parts)
    assert any("taknemmelighed" in p for p in parts)
    assert any("mild ved mig selv" in p and "hjemme" in p for p in parts)
    assert any("2 skjulte stemmer der former mig" in p for p in parts)
    assert any("hukommelse ånder" in p and "5 minder" in p for p in parts)
    assert any("holder fast i 3 vedvarende spor" in p for p in parts)
    assert any("noget er ved at emergere" in p and "2 mønstre" in p for p in parts)
    assert any("personlighed driver i warmth" in p and "opad" in p for p in parts)


def test_describe_singular_grammar(isolated_runtime):
    sf._hold_reading(sf._MODULATORS, {"active_modulators": 1})
    sf._hold_reading(sf._MEMORY_BREATHING, {"unique_records": 1})
    sf._hold_reading(sf._EMERGENCE, {"emerging": 1})
    parts = sf.describe_soul_feel()
    assert any("1 skjult stemme der former mig" in p for p in parts)
    assert any("rørt 1 minde " in p for p in parts)
    assert any("1 mønster" in p and "mønstre" not in p for p in parts)


def test_describe_order_is_warmth_first_emergence_last(isolated_runtime):
    sf._hold_reading(sf._RELATIONAL, {"warmth": "høj"})
    sf._hold_reading(sf._EMERGENCE, {"emerging": 1})
    parts = sf.describe_soul_feel()
    assert parts[0].startswith("varmen") and parts[-1].startswith("noget er ved at emergere")


def test_describe_relational_rolig_stays_silent(isolated_runtime):
    # "rolig" er hvile-værdien → tales IKKE
    sf._hold_reading(sf._RELATIONAL, {"warmth": "rolig"})
    assert sf.describe_soul_feel() == []


def test_describe_calm_anchor_near_stays_silent(isolated_runtime):
    # nær-baseline er tavs (kun hjemme/væk/langt-væk tales)
    sf._hold_reading(sf._CALM_ANCHOR, {"place": "nær-baseline"})
    assert sf.describe_soul_feel() == []


def test_describe_low_warmth_spoken(isolated_runtime):
    sf._hold_reading(sf._RELATIONAL, {"warmth": "lav"})
    parts = sf.describe_soul_feel()
    assert parts == ["varmen mod den jeg taler med er lav — jeg er reserveret"]


def test_describe_empty_when_nothing_held(isolated_runtime):
    assert sf.describe_soul_feel() == []


def test_describe_guarded_on_partial(isolated_runtime):
    # kun emergens holdt → kun emergens tales (guarded pr. lag)
    sf._hold_reading(sf._EMERGENCE, {"emerging": 4})
    parts = sf.describe_soul_feel()
    assert parts == ["noget er ved at emergere i mig: 4 mønstre"]


# ── self-safe: lag-fejl → intet pulses, describe kaster aldrig ──
def test_signals_self_safe_on_layer_error(monkeypatch, isolated_runtime):
    monkeypatch.setattr("core.services.relational_warmth.get_relation",
                        lambda relation_id=None: (_ for _ in ()).throw(RuntimeError("x")))
    monkeypatch.setattr("core.runtime.db.list_cognitive_gratitude_signals",
                        lambda limit=10: (_ for _ in ()).throw(RuntimeError("x")))
    monkeypatch.setattr("core.services.personality_drift.detect_drift",
                        lambda: (_ for _ in ()).throw(RuntimeError("x")))
    assert sf._relational_signal() is None
    assert sf._gratitude_signal() is None
    assert sf._drift_signal() is None


def test_describe_self_safe_on_corrupt_hold(monkeypatch, isolated_runtime):
    monkeypatch.setattr(sf, "get_emergence_reading",
                        lambda: (_ for _ in ()).throw(RuntimeError("x")))
    # ét lags fejl må ikke sprede sig — describe returnerer stadig en liste
    assert isinstance(sf.describe_soul_feel(), list)


# ── OP-registrering: otte lag registreres på cadence-motoren, egress PRIVATE, cluster cognition ──
def test_register_wires_eight_layers(monkeypatch, isolated_runtime):
    from core.services import central_layer_contract as lc
    specs = []
    import core.services.internal_cadence as ic
    monkeypatch.setattr(ic, "register_producer", lambda spec: specs.append(spec))
    lc._CONTRACTS.clear()
    sf.register_soul_feel_layers()
    names = {s.name for s in specs}
    assert names == {sf._RELATIONAL, sf._GRATITUDE, sf._CALM_ANCHOR, sf._MODULATORS,
                     sf._MEMORY_BREATHING, sf._SUSTAINED, sf._EMERGENCE, sf._DRIFT}
    for name in names:
        assert lc._CONTRACTS[name].egress is lc.Egress.PRIVATE
        assert lc._CONTRACTS[name].cluster == "cognition"


def test_run_contract_tick_pulses_private(monkeypatch, isolated_runtime):
    # OP end-to-end: lag-kontraktens tick kalder signal_fn → record_private (egress-frit), aldrig bussen
    from core.services import central_layer_contract as lc
    monkeypatch.setattr("core.services.emergence.summarize_patterns",
                        lambda: {"candidate": 1, "upgraded": 0})
    published = []
    import core.eventbus.bus as bus_mod
    monkeypatch.setattr(bus_mod.event_bus, "publish", lambda *a, **k: published.append((a, k)))
    recorded = []
    monkeypatch.setattr("core.services.central_private_observe.record_private",
                        lambda *a, **k: recorded.append((a, k)))
    c = lc.LayerContract(name=sf._EMERGENCE, cluster="cognition", nerve="emergence",
                         signal_fn=sf._emergence_signal, egress=lc.Egress.PRIVATE)
    r = lc._run_contract_tick(c)
    assert r["observed"] is True
    assert recorded and not published            # egress-frit
    assert sf.get_emergence_reading()["emerging"] == 1   # durabelt hold sat via side-effekt


def test_build_surface_shows_all_aspects(isolated_runtime):
    sf._hold_reading(sf._RELATIONAL, {"warmth": "høj"})
    sf._hold_reading(sf._SUSTAINED, {"active": 2})
    surface = sf.build_soul_feel_surface()
    assert surface["active"] is True
    assert surface["warmth"]["relational"]["warmth"] == "høj"
    assert surface["attention"]["sustained"]["active"] == 2
    assert any("holder fast i 2" in p for p in surface["spoken"])


# ── GRATITUDE RECENCY WINDOW (2026-07-08) ──
def _sig(days_ago, intensity=1.0):
    dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return {"intensity": intensity, "created_at": dt.isoformat()}


def test_gratitude_all_recent_fires(monkeypatch):
    monkeypatch.setattr("core.runtime.db.list_cognitive_gratitude_signals",
                        lambda limit=10: [_sig(1), _sig(2)])
    r = sf._gratitude_signal()
    assert r is not None and r["meta"]["count"] == 2


def test_gratitude_all_old_returns_none(monkeypatch):
    monkeypatch.setattr("core.runtime.db.list_cognitive_gratitude_signals",
                        lambda limit=10: [_sig(30), _sig(45)])
    assert sf._gratitude_signal() is None


def test_gratitude_mixed_counts_only_recent(monkeypatch):
    monkeypatch.setattr("core.runtime.db.list_cognitive_gratitude_signals",
                        lambda limit=10: [_sig(1), _sig(30), _sig(2)])
    r = sf._gratitude_signal()
    assert r is not None and r["meta"]["count"] == 2


def test_gratitude_unparseable_created_at_excluded(monkeypatch):
    monkeypatch.setattr("core.runtime.db.list_cognitive_gratitude_signals",
                        lambda limit=10: [{"intensity": 1.0, "created_at": "not-a-date"}])
    assert sf._gratitude_signal() is None


def test_gratitude_empty_returns_none(monkeypatch):
    monkeypatch.setattr("core.runtime.db.list_cognitive_gratitude_signals",
                        lambda limit=10: [])
    assert sf._gratitude_signal() is None
