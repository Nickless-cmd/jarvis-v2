"""Test: Centralens forudsigelses-loop — nu FALSIFICERBART.

Historik (12/11-2026): den første version meldte accuracy 1.0 på 196
forudsigelser med kun to unikke faktiske værdier. Forudsigelsen blev udledt af
et 14-dages glidende gennemsnit, og scoringen hentede det SAMME vindue 24 timer
senere. Fejlen var aritmetisk næsten udelukket, og de daværende tests mockede
den faktiske måling — de beviste at mekanikken KUNNE score et miss, ikke at
virkeligheden kunne give den et.

Disse tests gør det modsatte: de fodrer rigtige tick-evalueringer gennem
state-laget og verificerer at
  - fremtidsvinduet er ADSKILT fra forudsigelsens grundlag,
  - en forudsigelse kan tabe,
  - for lidt data er «ingen dom», ikke et hit,
  - v1-records erklæres void og påvirker ikke accuracy.

Alt self-safe: skør/manglende data kaster aldrig.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from core.services import self_model_predictive as smp


def _fake_state(monkeypatch, initial: dict | None = None) -> dict:
    """Isolér HELE state-laget — både prediktions-storen og tick-evals.

    Vi patcher ``core.runtime.state_store`` og ikke modullets egne indgange,
    fordi det er den faktiske søm: forudsigelsen og scoringen skal læse samme
    kilde, og en mock længere inde ville skjule netop den kobling.
    """
    store: dict = dict(initial or {})

    def _load(name, default=None):
        return store.get(name, default)

    def _save(name, data):
        store[name] = data

    monkeypatch.setattr("core.runtime.state_store.load_json", _load)
    monkeypatch.setattr("core.runtime.state_store.save_json", _save)
    return store


def _evals(start: datetime, count: int, score: int, step_hours: float = 6.0) -> list[dict]:
    return [
        {
            "evaluated_at": (start + timedelta(hours=i * step_hours)).isoformat(),
            "score": score,
        }
        for i in range(count)
    ]


# ── Kernen: forudsigelsen skal kunne tabe ───────────────────────────────────


def test_forudsigelsen_kan_fejle(monkeypatch):
    """Baseline 60, vi vædder «holder», fremtiden giver 40 → MISS."""
    now = datetime.now(UTC)
    made = now - timedelta(hours=200)  # 168t-horisonten er passeret

    evals = []
    # Grundlaget: højt niveau i de 14 dage FØR forudsigelsen.
    evals += _evals(made - timedelta(days=14), 20, 70, step_hours=12)
    # Fremtiden: lavt niveau i det adskilte vindue.
    evals += _evals(made, 20, 40, step_hours=6)

    store = _fake_state(monkeypatch, {"tick_quality_evaluations": evals})
    smp.record_prediction(
        metric="tick_quality.avg",
        threshold=60.0,
        predicted_above=True,
        probability=0.6,
        made_at=made.isoformat(),
    )

    res = smp.score_predictions()
    assert res["scored"] == 1
    assert res["accuracy"] == 0.0

    rec = store["self_model_predictions"][-1]
    assert rec["hit"] is False
    assert rec["actual"] == 40.0
    # Vinduet indeholder KUN de 20 fremtidige målinger. Havde scoringen læst
    # forudsigelsens eget grundlag med, ville tallet være blandet og fejlen
    # skjult — det var præcis den gamle fejl.
    assert rec["n_window"] == 20


def test_forudsigelsen_rammer_naar_fremtiden_ligner(monkeypatch):
    now = datetime.now(UTC)
    made = now - timedelta(hours=200)
    evals = _evals(made, 20, 65, step_hours=6)

    store = _fake_state(monkeypatch, {"tick_quality_evaluations": evals})
    smp.record_prediction(
        metric="tick_quality.avg",
        threshold=60.0,
        predicted_above=True,
        probability=0.6,
        made_at=made.isoformat(),
    )

    res = smp.score_predictions()
    assert res["scored"] == 1
    assert res["accuracy"] == 1.0
    assert store["self_model_predictions"][-1]["hit"] is True


def test_gammel_maaling_uden_for_fremtidsvinduet_taelles_ikke(monkeypatch):
    """En måling før made_at må aldrig indgå — det er hele adskillelsen."""
    now = datetime.now(UTC)
    made = now - timedelta(hours=200)
    evals = []
    evals += _evals(made - timedelta(hours=48), 30, 95, step_hours=1)  # før
    evals += _evals(made, 12, 30, step_hours=6)                        # i vinduet

    store = _fake_state(monkeypatch, {"tick_quality_evaluations": evals})
    smp.record_prediction(
        metric="tick_quality.avg",
        threshold=60.0,
        predicted_above=True,
        probability=0.6,
        made_at=made.isoformat(),
    )

    smp.score_predictions()
    rec = store["self_model_predictions"][-1]
    assert rec["n_window"] == 12
    assert rec["actual"] == 30.0  # ikke blandet med de 95


# ── Modenhed og datagrundlag ────────────────────────────────────────────────


def test_for_lidt_data_er_ingen_dom_ikke_et_hit(monkeypatch):
    now = datetime.now(UTC)
    made = now - timedelta(hours=200)
    # Kun 3 målinger i vinduet — under _PRED_MIN_SAMPLES.
    store = _fake_state(
        monkeypatch, {"tick_quality_evaluations": _evals(made, 3, 90, step_hours=6)}
    )
    smp.record_prediction(
        metric="tick_quality.avg",
        threshold=60.0,
        predicted_above=True,
        probability=0.6,
        made_at=made.isoformat(),
    )

    res = smp.score_predictions()
    assert res["scored"] == 0
    assert res["insufficient"] == 1
    assert res["accuracy"] is None
    assert store["self_model_predictions"][-1].get("scored") is False


def test_ung_forudsigelse_er_pending_ikke_scoret(monkeypatch):
    now = datetime.now(UTC)
    store = _fake_state(monkeypatch, {"tick_quality_evaluations": []})
    smp.record_prediction(
        metric="tick_quality.avg",
        threshold=60.0,
        predicted_above=True,
        probability=0.6,
        made_at=(now - timedelta(hours=1)).isoformat(),
    )

    res = smp.score_predictions()
    assert res["scored"] == 0
    assert res["pending"] == 1
    assert res["accuracy"] is None


# ── Kalibrering: betyder sandsynligheden noget? ─────────────────────────────


def test_brier_straffer_overmod(monkeypatch):
    now = datetime.now(UTC)
    made = now - timedelta(hours=200)
    evals = _evals(made, 20, 40, step_hours=6)  # outcome = 0 (under tærsklen)
    store = _fake_state(monkeypatch, {"tick_quality_evaluations": evals})

    smp.record_prediction(
        metric="tick_quality.avg",
        threshold=60.0,
        predicted_above=True,
        probability=0.6,
        made_at=made.isoformat(),
    )
    res = smp.score_predictions()
    # outcome 0 med p=0.6 → (0.6 - 0)^2 = 0.36
    assert res["brier"] == 0.36
    assert store["self_model_predictions"][-1]["brier"] == 0.36


def test_kalibrering_viser_predicted_mod_observed(monkeypatch):
    now = datetime.now(UTC)
    made = now - timedelta(hours=200)
    # To forudsigelser i samme bøtte: én rammer, én rammer ikke.
    evals = []
    evals += _evals(made - timedelta(hours=1), 20, 70, step_hours=1)  # outcome 1
    store = _fake_state(monkeypatch, {"tick_quality_evaluations": evals})
    smp.record_prediction(
        metric="tick_quality.avg", threshold=60.0, predicted_above=True,
        probability=0.6, made_at=made.isoformat(),
    )
    smp.score_predictions()

    # Anden forudsigelse, samme bøtte, andet vindue: outcome 0.
    made2 = now - timedelta(hours=400)
    store["tick_quality_evaluations"] = _evals(made2, 20, 40, step_hours=1)
    smp.record_prediction(
        metric="tick_quality.avg", threshold=60.0, predicted_above=True,
        probability=0.6, made_at=made2.isoformat(),
    )
    res = smp.score_predictions()

    bins = {b["bin"]: b for b in res["calibration"]}
    b = bins["0.60-1.00"]
    assert b["n"] == 2
    assert b["predicted"] == 0.6
    assert b["observed"] == 0.5  # vi sagde 60 %, det skete 50 % af gangene


# ── Legacy: den tautologiske version må ikke pynte på tallet ────────────────


def test_v1_records_er_void_og_taeller_ikke(monkeypatch):
    now = datetime.now(UTC)
    store = _fake_state(monkeypatch, {"tick_quality_evaluations": []})
    # En gammel record uden v/horisont — præcis den slags der gav accuracy 1.0.
    store["self_model_predictions"] = [{
        "metric": "tick_quality.avg",
        "threshold": 50.0,
        "predicted_above": True,
        "probability": 0.82,
        "made_at": (now - timedelta(hours=400)).isoformat(),
        "scored": False,
    }]

    res = smp.score_predictions()
    assert res["void"] == 1
    assert res["legacy_excluded"] == 1
    assert res["scored"] == 0
    assert res["accuracy"] is None  # ingen v2-data = intet tal at prale med
    rec = store["self_model_predictions"][0]
    assert rec["void"] is True
    assert "tautologisk" in rec["void_reason"]


def test_allerede_scoret_v1_voides_ogsaa(monkeypatch):
    """Fundet i produktion 12/11-2026: 196 v1-records stod som scored=True.

    Uden dette ville de beholde deres falske hit/actual og kunne læses som
    præcision — accuracy var korrekt None, men historikken løj.
    """
    now = datetime.now(UTC)
    store = _fake_state(monkeypatch, {"tick_quality_evaluations": []})
    store["self_model_predictions"] = [{
        "metric": "tick_quality.avg",
        "threshold": 50.0,
        "predicted_above": True,
        "probability": 0.82,
        "made_at": (now - timedelta(hours=900)).isoformat(),
        "scored": True,
        "hit": True,
        "actual": 59.4,
    }]

    res = smp.score_predictions()
    assert res["void"] == 1
    assert res["legacy_excluded"] == 1
    assert res["accuracy"] is None
    assert store["self_model_predictions"][0]["void"] is True


# ── Forudsigelsen selv: skrives den som et ægte væddemål? ───────────────────


def test_record_fra_model_er_adskilt_og_brugbar(monkeypatch):
    store = _fake_state(monkeypatch, {"tick_quality_evaluations": []})
    smp._maybe_record_from_model(
        {"tick_quality": {"avg": 59.4, "trend": "degrading", "samples": 1085}}
    )
    rec = store["self_model_predictions"][-1]
    assert rec["v"] == 2
    assert rec["threshold"] == 59.4          # tærsklen ER det målte niveau
    assert rec["baseline"] == 59.4
    assert rec["predicted_above"] is False   # faldende trend → vædder imod
    assert rec["horizon_hours"] == smp._PRED_HORIZON_HOURS
    assert rec["window_start"] == rec["made_at"]
    assert rec["window_end"] > rec["made_at"]
    assert 0.35 <= rec["probability"] <= 0.65  # aldrig overmodig


# ── Self-safe ───────────────────────────────────────────────────────────────


def test_self_safe_on_garbage_data(monkeypatch):
    store: dict = {}
    monkeypatch.setattr(smp, "_load_predictions", lambda: "not-a-list")  # type: ignore
    monkeypatch.setattr(smp, "_save_predictions", lambda preds: store.__setitem__("x", preds))

    def _boom(*_a, **_k):
        raise RuntimeError("kilde nede")

    monkeypatch.setattr(smp, "_tick_scores_in_window", _boom)
    res = smp.score_predictions()
    assert isinstance(res, dict)
    assert res.get("accuracy") is None

    monkeypatch.setattr(smp, "_absorb", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x")))
    surface = smp.build_self_model_predictive_surface()
    assert "prediction_accuracy" in surface


def test_record_prediction_never_raises(monkeypatch):
    monkeypatch.setattr(smp, "_load_predictions", lambda: (_ for _ in ()).throw(RuntimeError("x")))
    monkeypatch.setattr(smp, "_save_predictions", lambda preds: (_ for _ in ()).throw(RuntimeError("x")))
    smp.record_prediction(metric="m", threshold=1.0, predicted_above=True, probability=0.5)


def test_surface_eksponerer_brier_og_kalibrering(monkeypatch):
    _fake_state(monkeypatch, {"tick_quality_evaluations": []})
    calls: list[dict] = []
    monkeypatch.setattr(
        smp, "_absorb",
        lambda cluster, nerve, value, **kw: calls.append({"cluster": cluster, "nerve": nerve}),
    )
    surface = smp.build_self_model_predictive_surface()
    assert "prediction_accuracy" in surface
    assert "prediction_brier" in surface
    assert isinstance(surface["prediction_calibration"], list)
    assert any(c["cluster"] == "self" and c["nerve"] == "prediction_accuracy" for c in calls)
