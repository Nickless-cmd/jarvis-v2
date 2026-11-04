"""Tests for counterfactual → verdensmodel-bindingen.

Fokus (4/11-2026): `_extract_event_kind` er den ene søm der afgør om en
forudsigelse kan efterprøves. Den læste kun en evidence-streng; nu læser den
feltet først, så en forudsigelse skrevet med `event_kind=` også kan afgøres.
Begge veje skal virke — den gamle, så historikken ikke mister sin betydning,
og den nye, så feltet faktisk bruges.
"""
from __future__ import annotations

from core.services.counterfactual_predictions import (
    _extract_event_kind,
    _frequency_verdict,
    _is_horizon_expired,
)
from datetime import UTC, datetime, timedelta


def test_extract_laeser_feltet_foerst():
    pred = {"event_kind": "tool.completed", "evidence": ["event_kind:anden.kind"]}
    assert _extract_event_kind(pred) == "tool.completed", (
        "feltet skal vinde over evidence-strengen — det er den ærlige datamodel"
    )


def test_extract_falder_tilbage_paa_evidence_strengen():
    """Gamle forudsigelser har kun strengen. De må ikke miste deres betydning."""
    pred = {"evidence": ["counterfactual:cf-1", "event_kind:goal.updated"]}
    assert _extract_event_kind(pred) == "goal.updated"


def test_extract_uden_begge_dele_giver_tom():
    assert _extract_event_kind({"evidence": ["counterfactual:cf-1"]}) == ""
    assert _extract_event_kind({}) == ""


def test_verdict_uden_event_kind_gaetter_ikke():
    """Den ærlige halvdel: uden kind kan frekvensen ikke sammenlignes."""
    v = _frequency_verdict(event_kind="", created_at=datetime.now(UTC))
    assert v["outcome"] == "uncertain"
    assert v["reason"] == "no-event-kind-tag-on-prediction"


def test_horisonten_skal_vaere_udloebet():
    now = datetime.now(UTC)
    gammel = {"created_at": (now - timedelta(days=9)).isoformat()}
    frisk = {"created_at": (now - timedelta(days=1)).isoformat()}
    assert _is_horizon_expired(gammel, now) is True
    assert _is_horizon_expired(frisk, now) is False


# --- Mutationstest (4/11-2026): dommeren skal kunne MODSIGE generatoren ---
#
# Målt i drift samme dag: 861 åbne counterfactual-forudsigelser, alle med
# præcis én expectation-skabelon ("declining frequency ..."), alle med tom
# anchor og tom event_kind. Dommeren `_frequency_verdict` har ingen parameter
# for forventet retning — den antager hardcodet "fald". Generatoren kan kun
# sige "fald". Derfor ser systemet konsistent ud: de to halve fejl ophæver
# hinanden, og fejlen materialiserer sig først når nogen skriver en forventning
# om STIGNING.
#
# Testen nedenfor er den ægte prøve: to forudsigelser med MODSATRETTEDE
# forventninger skal kunne få hver sin dom af den SAMME observation. Gør de
# ikke det, læser dommeren ikke forventningen — og så er ledgeren ikke en
# kalibreringsmekanisme, men en stemme der altid siger det samme.


def test_modsatrettede_forventninger_kan_ikke_faa_samme_dom():
    """Den observation der understøtter 'fald' skal MODSIGE 'stigning'.

    Fejler denne, er dommeren retningsblind: den dømmer ud fra observationen
    alene og ignorerer hvad der blev forudsagt. Det er den fejlform der gør
    kalibrering umulig — Centralen kan ikke tage fejl af noget den aldrig
    påstod.
    """
    import inspect

    params = inspect.signature(_frequency_verdict).parameters
    assert "expected_direction" in params, (
        "dommeren tager kun (event_kind, created_at) — den kan ikke se om der "
        "blev forudsagt fald eller stigning, så modsatrettede forventninger "
        "får samme dom. Målt 4/11-2026: 861 åbne poster, én skabelon, "
        "dommeren hardcodet til 'declining'."
    )


def test_modsatrettede_forventninger_faar_hver_sin_dom(monkeypatch):
    """SAMME observation (fald 7→0) skal støtte 'declining' og MODSIGE 'increasing'.

    Det er mutationstesten: hvis begge får samme dom, læser dommeren stadig
    ikke forventningen — og så er ledgeren en stemme der altid siger det samme.
    """
    import core.services.counterfactual_predictions as cp

    class _FakeConn:
        """Første kald = baseline (7), andet = post (0) — et entydigt fald.

        Dommeren spørger altid baseline først, post bagefter; vi tæller
        kaldene i stedet for at gætte ud fra SQL-teksten.
        """

        calls = 0

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def execute(self, sql, params):
            _FakeConn.calls += 1
            n = 7 if _FakeConn.calls == 1 else 0
            return type("R", (), {"fetchone": lambda self: (n,)})()

    def _ny_conn():
        _FakeConn.calls = 0
        return _FakeConn()

    monkeypatch.setattr("core.runtime.db.connect", _ny_conn)

    now = datetime.now(UTC)
    fald = cp._frequency_verdict(
        event_kind="goal.updated", created_at=now,
        expected_direction=cp.DIRECTION_DECLINING,
    )
    stigning = cp._frequency_verdict(
        event_kind="goal.updated", created_at=now,
        expected_direction=cp.DIRECTION_INCREASING,
    )
    assert fald["outcome"] == "supported", fald
    assert stigning["outcome"] == "contradicted", stigning
    assert fald["outcome"] != stigning["outcome"], (
        "samme observation gav samme dom for modsatrettede forventninger — "
        "dommeren læser ikke forventningen"
    )


def test_retningen_skrives_og_laeses_fra_forventningen():
    """Generatoren skal skrive retningen, så dommeren kan læse den tilbage."""
    import core.services.counterfactual_predictions as cp

    pred = {
        "expectation": "increasing frequency vs prior 7 days [direction:increasing]",
        "evidence": ["counterfactual:cf-1", "direction:increasing"],
    }
    assert cp._extract_direction(pred) == cp.DIRECTION_INCREASING
    # Ældre poster uden retning: bagudkompatibel antagelse, ikke en sandhed.
    assert cp._extract_direction({"expectation": "declining frequency"}) == cp.DIRECTION_DECLINING


# --- Falsificerbarheds-gaten (4/11-2026) --------------------------------
# Målt i drift: `decision`, `dream`, `correction` og `failed_run` er
# trigger_types i kalderne, men har NUL rækker i `events`. 855 af 909 åbne
# forudsigelser var den samme uafgørlige påstand. Gaten afviser bindingen
# FØR ledgeren røres — en forudsigelse der ikke kan efterprøves fortrænger
# en der kan.


def test_gaten_afviser_ikke_observerbar_kind(monkeypatch):
    """`decision` kan ikke observeres → ingen post, og ledgeren røres ikke."""
    import core.services.counterfactual_predictions as cp

    kald: list[dict] = []
    monkeypatch.setattr(
        "core.services.world_model_signal_tracking."
        "record_runtime_world_model_prediction",
        lambda **kw: kald.append(kw) or {"status": "ok"},
    )
    monkeypatch.setattr(cp, "_event_kind_is_observable", lambda k: k == "goal.updated")

    r = cp.bind_counterfactual_to_prediction(
        cf_id="cf-gate1", trigger_type="decision", event_kind="decision",
    )
    assert r["status"] == "skipped", r
    assert "not-observable" in r["reason"]
    assert kald == [], "gaten skal afvise FØR ledgeren skrives"


def test_gaten_slipper_observerbar_kind_igennem(monkeypatch):
    """Samme vej, observerbar kind → posten skrives med kind'en i evidence."""
    import core.services.counterfactual_predictions as cp

    kald: list[dict] = []
    monkeypatch.setattr(
        "core.services.world_model_signal_tracking."
        "record_runtime_world_model_prediction",
        lambda **kw: kald.append(kw) or {"status": "ok"},
    )
    monkeypatch.setattr(cp, "_event_kind_is_observable", lambda k: k == "goal.updated")

    r = cp.bind_counterfactual_to_prediction(
        cf_id="cf-gate2", trigger_type="goal.updated",
    )
    assert r["status"] == "ok", r
    assert len(kald) == 1
    assert "event_kind:goal.updated" in kald[0]["evidence"], kald[0]["evidence"]


def test_proben_svarer_paa_den_faktiske_database(monkeypatch):
    """Proben må ikke gætte: en kind der findes i `events` er observerbar,
    en der ikke findes er det ikke. Målt mod den isolerede DB."""
    import core.services.counterfactual_predictions as cp
    from core.runtime.db import connect

    with connect() as conn:
        conn.execute(
            "INSERT INTO events (kind, created_at, payload_json) VALUES (?, ?, ?)",
            ("test.observerbar.kind", datetime.now(UTC).isoformat(), "{}"),
        )
        conn.commit()

    cp._OBSERVABLE_CACHE.clear()
    assert cp._event_kind_is_observable("test.observerbar.kind") is True
    assert cp._event_kind_is_observable("findes.ikke.her") is False
    assert cp._event_kind_is_observable("") is False
