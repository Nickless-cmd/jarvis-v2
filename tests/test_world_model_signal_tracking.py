"""Verificér at world-model-pipelinen nu binder egress-frit til Centralen (§5a, 3. jul).

Før: prediction/kalibrering nåede ALDRIG Centralen (family world_model_signal urouteret).
Nu: record/resolve/milestone observer via record_private → cognition/world_model[_calibration].
Middelværdien af world_model_calibration-serien = kalibreringsraten.

Hermetisk: monkeypatcher state-persistens væk, så testen ikke rører runtime-state-store.
"""
from __future__ import annotations

import pytest

from core.services import central_timeseries
from core.services import world_model_signal_tracking as wm


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    central_timeseries._reset_for_tests()
    # Isolér fra state-store: predictions holdes in-memory pr. test.
    store: list[dict] = []
    monkeypatch.setattr(wm, "_load_predictions", lambda: list(store))
    monkeypatch.setattr(wm, "_save_predictions", lambda preds: store.__setitem__(slice(None), preds))
    yield
    central_timeseries._reset_for_tests()


def test_recording_prediction_observes_to_central():
    res = wm.record_runtime_world_model_prediction(
        subject="deploy", expectation="det lykkes", confidence="high",
    )
    assert res["status"] == "ok"
    samples = central_timeseries.recent("cognition", "world_model", limit=5)
    assert samples, "prediction_recorded skal observe til cognition/world_model"
    last = samples[-1]
    assert last.meta.get("event") == "prediction_recorded"
    assert last.meta.get("confidence") == "high"
    assert last.value == pytest.approx(1.0)  # high → 3/3


def test_resolving_prediction_feeds_calibration_series():
    rec = wm.record_runtime_world_model_prediction(subject="x", expectation="y", confidence="low")
    pid = rec["prediction"]["prediction_id"]
    wm.resolve_runtime_world_model_prediction(pid, observed="skete", outcome="supported")
    cal = central_timeseries.recent("cognition", "world_model_calibration", limit=5)
    assert cal, "resolve skal fodre world_model_calibration-serien"
    assert cal[-1].value == pytest.approx(1.0)  # supported → 1.0
    assert cal[-1].meta.get("outcome") == "supported"


def test_calibration_series_mean_is_calibration_rate():
    # 2 supported + 2 contradicted → middel 0.5 = 50% kalibrering.
    for outcome in ("supported", "supported", "contradicted", "contradicted"):
        rec = wm.record_runtime_world_model_prediction(subject="s", expectation="e")
        pid = rec["prediction"]["prediction_id"]
        wm.resolve_runtime_world_model_prediction(pid, observed="o", outcome=outcome)
    cal = central_timeseries.recent("cognition", "world_model_calibration", limit=10)
    vals = [s.value for s in cal if s.value is not None]
    assert vals, "skal have kalibrerings-samples"
    assert sum(vals) / len(vals) == pytest.approx(0.5)


def test_binding_is_self_safe(monkeypatch):
    # Selv hvis record_private kaster, må recording aldrig fejle.
    import core.services.central_private_observe as cpo
    monkeypatch.setattr(cpo, "record_private", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    res = wm.record_runtime_world_model_prediction(subject="a", expectation="b")
    assert res["status"] == "ok"


# ---------------------------------------------------------------------------
# FIFO-loftet må ikke kunne kortslutte falsifikations-sløjfen
#
# Målt 2026-09-05: sløjfen der efterprøver Jarvis' forudsigelser var bygget,
# tilkoblet og kørte dagligt — og havde resolvet NUL forudsigelser i systemets
# fem måneders levetid. Blokeringen var ren aritmetik:
#
#     produktion   ~107 forudsigelser/døgn
#     horisont     HORIZON_DAYS 7 + GRACE_DAYS 1 = 8 dage
#     nødvendigt   107 × 8 ≈ 856 pladser
#     loft         120
#
# Hver forudsigelse blev skubbet ud af FIFO'en ~7 dage FØR den blev moden.
# ---------------------------------------------------------------------------

# Målt produktionsrate 4.-5. september 2026 (120 poster på 27 timer).
_MAALT_DOEGNRATE = 107


def test_fifo_loftet_raekker_til_hele_horisonten():
    from core.services.counterfactual_predictions import GRACE_DAYS, HORIZON_DAYS
    from core.services.world_model_signal_tracking import _MAX_PREDICTIONS

    noedvendigt = _MAALT_DOEGNRATE * (HORIZON_DAYS + GRACE_DAYS)
    assert _MAX_PREDICTIONS >= noedvendigt, (
        "_MAX_PREDICTIONS=%d rækker ikke til %d dages horisont ved ~%d "
        "forudsigelser/døgn (kræver %d). Forudsigelserne skubbes ud af FIFO'en "
        "før de bliver modne, og sløjfen kan aldrig resolve noget."
        % (_MAX_PREDICTIONS, HORIZON_DAYS + GRACE_DAYS, _MAALT_DOEGNRATE, noedvendigt)
    )


def test_horisonten_maa_ikke_vokse_ud_over_loftet():
    """Vagten skal virke begge veje — en længere horisont kræver mere plads."""
    from core.services.counterfactual_predictions import GRACE_DAYS, HORIZON_DAYS
    from core.services.world_model_signal_tracking import _MAX_PREDICTIONS

    maks_dage = _MAX_PREDICTIONS / float(_MAALT_DOEGNRATE)
    assert (HORIZON_DAYS + GRACE_DAYS) <= maks_dage, (
        "horisonten er sat op til %d dage, men loftet rummer kun %.1f dages "
        "produktion" % (HORIZON_DAYS + GRACE_DAYS, maks_dage)
    )
