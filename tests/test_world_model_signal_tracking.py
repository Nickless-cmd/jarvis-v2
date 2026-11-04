"""Verificér at world-model-pipelinen nu binder egress-frit til Centralen (§5a, 3. jul).

Før: prediction/kalibrering nåede ALDRIG Centralen (family world_model_signal urouteret).
Nu: record/resolve/milestone observer via record_private → cognition/world_model[_calibration].
Middelværdien af world_model_calibration-serien = kalibreringsraten.

Hermetisk: monkeypatcher state-persistens væk, så testen ikke rører runtime-state-store.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.services import central_timeseries
from core.services import world_model_signal_tracking as wm
from core.runtime import db_core
from core.runtime.db_runtime_executive_signals import upsert_runtime_world_model_signal


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


def test_legacy_conversation_topics_are_excluded_before_quarantine(monkeypatch, tmp_path):
    db_core.close_pooled_connection()
    monkeypatch.setattr(db_core, "DB_PATH", tmp_path / "world-signals.db")
    # RELATIV dato, ikke en fast. Her stod «2026-09-10T10:00:00+00:00», og
    # `build_runtime_world_model_signal_surface` kalder først
    # `refresh_runtime_world_model_signal_statuses`, som markerer et signal
    # «stale» efter `_STALE_AFTER_DAYS` (10). Den 20/9-2026 kl. 10:00 UTC blev
    # fixturen præcis 10 døgn gammel, og testen skiftede fra grøn til rød midt
    # på dagen — uden at en linje kode var ændret. To fulde kørsler samme
    # formiddag lå på hver sin side af grænsen.
    #
    # Halvdelen af vinduet: rigeligt inde i det, og den knækker ikke hvis
    # grænsen sættes lidt ned.
    now = (datetime.now(UTC) - timedelta(days=max(wm._STALE_AFTER_DAYS // 2, 1))).isoformat()

    def add(signal_id: str, signal_type: str) -> None:
        upsert_runtime_world_model_signal(
            signal_id=signal_id,
            signal_type=signal_type,
            canonical_key=f"key:{signal_id}",
            status="active",
            title=signal_id,
            summary=signal_id,
            rationale="fixture",
            source_kind="visible_run",
            confidence="medium",
            evidence_summary="fixture",
            support_summary="fixture",
            support_count=1,
            session_count=1,
            created_at=now,
            updated_at=now,
        )

    add("real-world-signal", "workspace-scope-assumption")
    add("legacy-topic-1", "conversational_context")
    add("legacy-topic-2", "conversational_context")

    surface = wm.build_runtime_world_model_signal_surface(limit=1)

    assert [item["signal_id"] for item in surface["items"]] == ["real-world-signal"]
    assert surface["summary"]["active_count"] == 1, (
        "signalet blev markeret stale — er fixturens dato faldet ud af "
        f"vinduet på {wm._STALE_AFTER_DAYS} dage?")
    db_core.close_pooled_connection()


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


# ---------------------------------------------------------------------------
# Kalibreringen kunne per konstruktion ikke beregnes
#
# Målt 4/11-2026: `_frequency_verdict` kræver et `event_kind` på forudsigelsen
# for at kunne tælle hændelser før/efter. Producenten skrev det ALDRIG. Så
# 132 af 132 resolved endte som `uncertain` med reason
# `no-event-kind-tag-on-prediction`, og `calibration` var strukturelt `None`.
# Sweepet kørte dagligt uden at kunne afgøre noget — samme fejlform som
# `max()`-tælleren: mekanismen findes, indgangsbetingelsen kan intet opfylde.
# ---------------------------------------------------------------------------

_EVENT_KIND = "test.prediction.event"


def _seed_events(tmp_path, monkeypatch, *, created: datetime) -> None:
    """20 hændelser i baseline-vinduet, 2 i post-vinduet → ratio 0.1."""
    from core.runtime import db_core
    from core.runtime.db_schema import init_db

    db_core.close_pooled_connection()
    monkeypatch.setattr(db_core, "DB_PATH", tmp_path / "prediction-events.db")
    init_db()
    with db_core.connect() as conn:
        for i in range(20):
            ts = (created - timedelta(days=3) + timedelta(hours=i)).isoformat()
            conn.execute(
                "INSERT INTO events (kind, payload_json, created_at) VALUES (?, ?, ?)",
                (_EVENT_KIND, "{}", ts),
            )
        for i in range(2):
            ts = (created + timedelta(days=2, hours=i)).isoformat()
            conn.execute(
                "INSERT INTO events (kind, payload_json, created_at) VALUES (?, ?, ?)",
                (_EVENT_KIND, "{}", ts),
            )
        conn.commit()


def test_forudsigelse_med_event_kind_KAN_afgoeres(tmp_path, monkeypatch):
    """Uden denne kan kalibreringen aldrig blive andet end None."""
    from core.services.counterfactual_predictions import (
        sweep_expired_counterfactual_predictions,
    )

    created = datetime.now(UTC) - timedelta(days=12)
    _seed_events(tmp_path, monkeypatch, created=created)

    rec = wm.record_runtime_world_model_prediction(
        subject="hændelses-frekvens",
        expectation="frekvensen falder efter læring",
        event_kind=_EVENT_KIND,
        source="counterfactual",
        now=created,
    )
    assert rec["prediction"]["event_kind"] == _EVENT_KIND, (
        "producenten skrev ikke event_kind — så kan sweepet ikke afgøre noget"
    )

    summary = sweep_expired_counterfactual_predictions(now=datetime.now(UTC))
    assert summary["by_outcome"]["supported"] == 1, (
        "forudsigelsen blev ikke afgjort som supported selv om frekvensen "
        f"faldt til 10% af baseline — by_outcome={summary['by_outcome']}"
    )

    preds = wm._load_predictions()
    assert preds[0]["outcome"] == "supported"
    surface = wm.build_runtime_world_model_prediction_surface()
    assert surface["summary"]["calibration"] == 1.0, (
        "kalibreringen blev ikke beregnelig — det var hele pointen"
    )
    from core.runtime import db_core
    db_core.close_pooled_connection()


def test_uden_event_kind_forbliver_forudsigelsen_uafgjort(tmp_path, monkeypatch):
    """Den ærlige halvdel: uden feltet KAN den ikke afgøres — og må ikke gætte."""
    from core.services.counterfactual_predictions import (
        sweep_expired_counterfactual_predictions,
    )

    created = datetime.now(UTC) - timedelta(days=12)
    _seed_events(tmp_path, monkeypatch, created=created)

    wm.record_runtime_world_model_prediction(
        subject="uden kind",
        expectation="kan ikke efterprøves",
        source="counterfactual",
        now=created,
    )

    summary = sweep_expired_counterfactual_predictions(now=datetime.now(UTC))
    assert summary["by_outcome"]["supported"] == 0
    assert summary["by_outcome"]["contradicted"] == 0
    preds = wm._load_predictions()
    assert preds[0]["outcome"] == "uncertain"
    from core.runtime import db_core
    db_core.close_pooled_connection()


# ---------------------------------------------------------------------------
# 0/0 er UNDEFINED, ikke 0 %
#
# Målt 4/11-2026: `_calibration_of` returnerede 0.0 når nævneren var tom. Alle
# 48 `count_10`-milestones i drift sagde derfor «Kalibrering sidste 30: 0.0%»
# — Centralen fik 48 gange besked om en måling der aldrig havde fundet sted.
# Samme fejlform som `tool_rate`: en default der ligner en måling.
# ---------------------------------------------------------------------------


@pytest.fixture
def _iso_milestones(monkeypatch):
    """Isolér milestone-persistensen. Uden den skriver testen i den LEVENDE fil."""
    hist: list[dict] = []
    monkeypatch.setattr(wm, "_load_milestones", lambda: {"history": list(hist)})
    monkeypatch.setattr(
        wm, "_save_milestones", lambda d: hist.__setitem__(slice(None), d.get("history") or [])
    )
    return hist


def test_kalibrering_uden_domme_er_None_ikke_nul():
    """0 supported + 0 contradicted → None. En usikker post er ikke en dom."""
    preds = [{"outcome": "uncertain"}, {"outcome": "uncertain"}]
    assert wm._calibration_of(preds) is None, (
        "tom nævner blev rapporteret som 0.0 — det påstår nul korrekthed hvor "
        "sandheden er 'aldrig målt'"
    )


def test_kalibrering_med_domme_giver_tal():
    """Halvdelen rigtige → 50.0. Grænsen må ikke gøre funktionen blind."""
    preds = [
        {"outcome": "supported"},
        {"outcome": "contradicted"},
        {"outcome": "uncertain"},  # ekskluderes fra nævneren
    ]
    assert wm._calibration_of(preds) == 50.0


def test_milestone_uden_domme_siger_ikke_maalt(_iso_milestones):
    """Den formidlede tekst må ikke påstå en procentsats der ikke findes."""
    resolved = [
        {
            "prediction_id": f"p{i}",
            "status": "resolved",
            "outcome": "uncertain",
            "resolved_at": (datetime.now(UTC) - timedelta(hours=10 - i)).isoformat(),
            "created_at": (datetime.now(UTC) - timedelta(days=9)).isoformat(),
        }
        for i in range(10)
    ]
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(wm, "_load_predictions", lambda: list(resolved))
        m = wm._compute_calibration_milestone()

    assert m is not None, "regel 1 skal fyre ved 10 resolved"
    assert "ikke maalt" in m["message"], (
        f"milestone påstod en kalibrering der ikke er målt: {m['message']!r}"
    )
    assert "0.0%" not in m["message"]
