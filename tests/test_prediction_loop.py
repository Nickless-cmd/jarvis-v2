"""Test: Centralens lukkede forudsigelses-loop (rådets #2).

build_predictive_self_model FORUDSIGER allerede. Dette loop scorer
forudsigelserne mod virkeligheden og lærer:

  record_prediction(...) → score_predictions() → prediction_accuracy

Alt self-safe: skør/manglende data kaster aldrig.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from core.services import self_model_predictive as smp


def _fresh_store(monkeypatch):
    """Isolér prediktions-storen i en in-memory dict pr. test."""
    store: dict[str, object] = {}

    def _load(name, default):
        return store.get(name, default)

    def _save(name, data):
        store[name] = data

    monkeypatch.setattr(smp, "_load_predictions", lambda: list(_load(smp._PRED_STORE_KEY, [])))
    monkeypatch.setattr(smp, "_save_predictions", lambda preds: _save(smp._PRED_STORE_KEY, preds))
    return store


def _old_ts(hours: float = 48.0) -> str:
    return (datetime.now(UTC) - timedelta(hours=hours)).isoformat()


def test_hit_gives_accuracy_1(monkeypatch):
    _fresh_store(monkeypatch)
    # Prediktion: tick_quality.avg > 50 (predicted True), lavet for 48t siden.
    smp.record_prediction(
        metric="tick_quality.avg",
        threshold=50.0,
        predicted_above=True,
        probability=0.73,
        made_at=_old_ts(48),
    )
    # Virkeligheden matcher: faktisk avg = 72 (> 50 → predicted_above holdt).
    monkeypatch.setattr(smp, "_observe_actual", lambda metric: 72.0)
    res = smp.score_predictions(min_age_hours=24.0)
    assert res.get("scored", 0) == 1
    assert res.get("accuracy") == 1.0


def test_miss_gives_accuracy_below_1(monkeypatch):
    _fresh_store(monkeypatch)
    smp.record_prediction(
        metric="tick_quality.avg",
        threshold=50.0,
        predicted_above=True,
        probability=0.73,
        made_at=_old_ts(48),
    )
    # Virkeligheden matcher IKKE: faktisk avg = 30 (< 50 → predicted_above brød).
    monkeypatch.setattr(smp, "_observe_actual", lambda metric: 30.0)
    res = smp.score_predictions(min_age_hours=24.0)
    assert res.get("scored", 0) == 1
    assert res.get("accuracy") is not None
    assert res["accuracy"] < 1.0


def test_no_outstanding_predictions_is_neutral(monkeypatch):
    _fresh_store(monkeypatch)
    res = smp.score_predictions(min_age_hours=24.0)
    # Ingen udestående → neutral, ingen crash.
    assert res.get("scored", 0) == 0
    assert res.get("accuracy") is None


def test_young_predictions_not_scored_yet(monkeypatch):
    _fresh_store(monkeypatch)
    smp.record_prediction(
        metric="tick_quality.avg",
        threshold=50.0,
        predicted_above=True,
        probability=0.6,
        made_at=_old_ts(1),  # kun 1t gammel
    )
    monkeypatch.setattr(smp, "_observe_actual", lambda metric: 90.0)
    res = smp.score_predictions(min_age_hours=24.0)
    assert res.get("scored", 0) == 0
    assert res.get("accuracy") is None


def test_surface_contains_prediction_accuracy_and_absorbs_self(monkeypatch):
    _fresh_store(monkeypatch)
    smp.record_prediction(
        metric="tick_quality.avg",
        threshold=50.0,
        predicted_above=True,
        probability=0.7,
        made_at=_old_ts(48),
    )
    monkeypatch.setattr(smp, "_observe_actual", lambda metric: 80.0)

    calls: list[dict[str, object]] = []

    def _fake_absorb(cluster, nerve, value, **kwargs):
        calls.append({"cluster": cluster, "nerve": nerve, "value": value, "kwargs": kwargs})

    monkeypatch.setattr(smp, "_absorb", _fake_absorb)

    surface = smp.build_self_model_predictive_surface()
    assert "prediction_accuracy" in surface
    pa = surface["prediction_accuracy"]
    assert isinstance(pa, dict)
    assert pa.get("accuracy") == 1.0
    # absorb kaldt med cluster="self".
    assert any(c["cluster"] == "self" and c["nerve"] == "prediction_accuracy" for c in calls)


def test_self_safe_on_garbage_data(monkeypatch):
    store: dict[str, object] = {}
    # Sæt korrupt prediktions-payload ind.
    monkeypatch.setattr(smp, "_load_predictions", lambda: "not-a-list")  # type: ignore
    monkeypatch.setattr(smp, "_save_predictions", lambda preds: store.__setitem__("x", preds))

    def _boom(metric):
        raise RuntimeError("kilde nede")

    monkeypatch.setattr(smp, "_observe_actual", _boom)
    # Må ALDRIG kaste.
    res = smp.score_predictions(min_age_hours=24.0)
    assert isinstance(res, dict)
    assert res.get("accuracy") is None
    # Surface må heller aldrig kaste selv med skør absorb.
    monkeypatch.setattr(smp, "_absorb", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x")))
    surface = smp.build_self_model_predictive_surface()
    assert "prediction_accuracy" in surface


def test_record_prediction_never_raises(monkeypatch):
    # save-sti brækket → record må stadig ikke kaste.
    monkeypatch.setattr(smp, "_load_predictions", lambda: (_ for _ in ()).throw(RuntimeError("x")))
    monkeypatch.setattr(smp, "_save_predictions", lambda preds: (_ for _ in ()).throw(RuntimeError("x")))
    smp.record_prediction(metric="m", threshold=1.0, predicted_above=True, probability=0.5)
