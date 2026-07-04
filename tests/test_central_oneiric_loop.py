"""Tests for core/services/central_oneiric_loop.py — DEN ONEIRISKE SLØJFE, første skridt (record-only)."""
from __future__ import annotations

from core.services import central_oneiric_loop as ol


# ── kontrol-arm-determinisme ─────────────────────────────────────────────────────────

def test_control_day_is_deterministic():
    day = "2026-07-04"
    assert ol.is_control_day(day) == ol.is_control_day(day)
    assert ol.is_control_day(day) == ol.is_control_day(day)


def test_control_fraction_roughly_20_percent_over_many_days():
    import datetime as _dt
    base = _dt.date(2026, 1, 1)
    days = [(base + _dt.timedelta(days=i)).isoformat() for i in range(400)]
    control = sum(1 for d in days if ol.is_control_day(d))
    frac = control / len(days)
    assert 0.08 <= frac <= 0.33, f"kontrol-andel {frac:.2f} uden for rimeligt interval"


def test_not_all_days_same_arm():
    import datetime as _dt
    base = _dt.date(2026, 1, 1)
    arms = {ol.is_control_day((base + _dt.timedelta(days=i)).isoformat()) for i in range(60)}
    assert arms == {True, False}, "splittet er degenereret (alle dage samme arm)"


# ── hypotese-komposition: falsificerbare felter + §8-godkendt ───────────────────────

def test_compose_has_required_falsifiable_fields():
    hyp = ol.compose_oneiric_hypothesis(loop_persistence=0.4, day="2026-07-04", control_arm=False)
    for f in ("statement", "prediction", "null_hypothesis", "success_criterion",
              "sample_size", "ttl_seconds", "provenance"):
        assert hyp.get(f), f"mangler felt: {f}"
    prov = hyp["provenance"]
    for k in ("mechanism", "family", "cursor_id"):
        assert k in prov, f"provenance mangler {k}"
    assert isinstance(hyp["sample_size"], int) and hyp["sample_size"] > 0
    assert hyp["ttl_seconds"] > 0
    assert prov["target_metric"] == "loop/no_progress_finalize"


def test_compose_passes_governance_preregistration():
    """Den komponerede hypotese SKAL bestå §8's validate_preregistration (routes gennem governance)."""
    from core.services import central_hypothesis_governance as gov
    hyp = ol.compose_oneiric_hypothesis(loop_persistence=0.4, day="2026-07-04", control_arm=True)
    ok, missing = gov.validate_preregistration(hyp)
    assert ok, f"hypotese ikke pre-registrerbar: mangler {missing}"


def test_direction_follows_bias_sign():
    up = ol.compose_oneiric_hypothesis(loop_persistence=-0.5, day="2026-07-04", control_arm=False)
    down = ol.compose_oneiric_hypothesis(loop_persistence=0.5, day="2026-07-04", control_arm=False)
    assert up["provenance"]["predicted_direction"] == "up"
    assert down["provenance"]["predicted_direction"] == "down"


# ── tick: registrerer + emitterer nerven; governance kaldes ──────────────────────────

def test_tick_registers_and_emits_nerve(monkeypatch):
    monkeypatch.setattr(ol, "_read_loop_persistence_bias", lambda *, workspace_id: 0.4)
    monkeypatch.setattr(ol, "_kv_get", lambda k, d: d)   # ingen tidligere dag
    monkeypatch.setattr(ol, "_kv_set", lambda k, v: None)

    calls = {}
    def _fake_register(candidate):
        calls["candidate"] = candidate
        return {"status": "registered", "hyp_id": "clh-test123"}
    import core.services.central_hypothesis_generator as gen
    monkeypatch.setattr(gen, "register_governed_hypothesis", _fake_register)

    emitted = {}
    import core.services.central_private_observe as cpo
    def _fake_record(cluster, nerve, *, value=1.0, meta=None, reason=""):
        emitted.update({"cluster": cluster, "nerve": nerve, "meta": meta or {}})
        return True
    monkeypatch.setattr(cpo, "record_private", _fake_record)

    res = ol.run_oneiric_loop_tick()
    assert res["status"] == "ok" and res["registered"] == "registered"
    assert calls["candidate"]["provenance"]["mechanism"] == "dream_bias.loop_persistence"
    assert emitted["cluster"] == "dreams" and emitted["nerve"] == "oneiric_prediction"
    assert "control_arm" in emitted["meta"]
    assert emitted["meta"]["target_metric"] == "loop/no_progress_finalize"
    assert emitted["meta"]["predicted_direction"] == "down"  # bias 0.4 > 0


def test_tick_is_idempotent_per_day(monkeypatch):
    monkeypatch.setattr(ol, "_read_loop_persistence_bias", lambda *, workspace_id: 0.4)
    store = {}
    monkeypatch.setattr(ol, "_kv_get", lambda k, d: store.get(k, d))
    monkeypatch.setattr(ol, "_kv_set", lambda k, v: store.update({k: v}))
    import core.services.central_hypothesis_generator as gen
    n = {"count": 0}
    def _fake_register(candidate):
        n["count"] += 1
        return {"status": "registered", "hyp_id": f"clh-{n['count']}"}
    monkeypatch.setattr(gen, "register_governed_hypothesis", _fake_register)
    import core.services.central_private_observe as cpo
    monkeypatch.setattr(cpo, "record_private", lambda *a, **k: True)

    first = ol.run_oneiric_loop_tick()
    second = ol.run_oneiric_loop_tick()
    assert first["status"] == "ok"
    assert second["status"] == "skip"           # samme dag → ingen dobbelt-registrering
    assert n["count"] == 1


def test_tick_skips_without_bias(monkeypatch):
    monkeypatch.setattr(ol, "_read_loop_persistence_bias", lambda *, workspace_id: None)
    monkeypatch.setattr(ol, "_kv_get", lambda k, d: d)
    res = ol.run_oneiric_loop_tick()
    assert res["status"] == "skip"
    assert "loop_persistence" in res["reason"]


# ── self-safe: kaster ALDRIG ─────────────────────────────────────────────────────────

def test_tick_self_safe_on_read_failure(monkeypatch):
    def _boom(*, workspace_id):
        raise RuntimeError("bias-læsning fejlede")
    monkeypatch.setattr(ol, "_kv_get", lambda k, d: d)
    monkeypatch.setattr(ol, "_read_loop_persistence_bias", _boom)
    res = ol.run_oneiric_loop_tick()
    assert res["status"] == "error"


def test_build_surface_read_only(monkeypatch):
    monkeypatch.setattr(ol, "_read_loop_persistence_bias", lambda *, workspace_id: 0.3)
    s = ol.build_oneiric_loop_surface()
    assert s["active"] is True and s["has_bias"] is True
    assert s["predicted_direction"] == "down"
    assert s["target_metric"] == "loop/no_progress_finalize"
