"""VAGT — to shadow-mekanismer der målte en KONSTANT i stedet for en måling.

Bjørn 30/10-2026: «Tag den». De to eksperimenter var reviewet som
ikke-kalibrerbare; her rettes defekterne, og vagterne fælder tilbagefaldet.

## Målt FØR (bevis, ikke formodning)

`convene_judge` — 40 af 40 samples i `central_timeseries` (cognition/
convene_judge) havde `convene=True`, `movement` 4.0 (39x) / 3.667 (1x) og
`reason='real_movement'`. Niveau-summen var konstant 4.0 fordi fire signaler
måler TILSTEDEVÆRELSE: `conflict` er 1.0 så længe `last_conflict` er en
ikke-tom streng (en konflikt fra kl. 05:56 talte stadig kl. 08:40),
`existential_wonder` er 1.0 så længe der ligger en wonder fra i går, og
`creative_drift`/`desire` tæller PERSISTENTE appetites og dagens drift-buffer.

`event_trigger` — 500 durable samples, kun 3 unikke signal-snapshots, og 201
havde `crossed` ikke-tom samtidig med `movement = max(abs(v))` = præcis 0.0.
Årsagen var `theta_abs`-grenen: den sammenlignede NIVEAUET (`val`) med gulvet
og så aldrig på `absdelta`, så et signal der står stille over θ_abs krydser
igen og igen med `movements[name] = val - b = 0`.

## Hvad vagterne værner

1. Dommeren indkalder IKKE på et konstant signal (fælder niveau-summen).
2. Dommeren indkalder på en ÆGTE ændring (den må ikke bare altid sige nej).
3. En læsefejl er UKENDT, ikke «signalet faldt til nul» (ellers fyrer den når
   kilden er nede — målt: den fejl fældede `test_self_safe_...`).
4. `theta_abs` kræver en delta: statisk krydser ikke.
5. Ægte delta krydser — også små (slow-boil skal stadig fanges).
6. `roles == []` er MED VILJE (Bjørn 15. jul) og må ikke «rettes».
"""
from __future__ import annotations

import sys
import types
from unittest.mock import patch

import pytest


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #
@pytest.fixture()
def runtime_state(monkeypatch, isolated_runtime):
    """Durable dict-backed runtime-state (dommerens reference + triggerens nøgler)."""
    from core.runtime import db_core

    store: dict = {}

    def _get(key, default=None):
        return store.get(str(key), default)

    def _set(key, value, **_kw):
        store[str(key)] = value

    monkeypatch.setattr(db_core, "get_runtime_state_value", _get)
    monkeypatch.setattr(db_core, "set_runtime_state_value", _set)
    return store


@pytest.fixture()
def fake_baseline(monkeypatch):
    """Kontrollerbar `signal_baseline` (triggerens reference)."""
    ns = types.ModuleType("core.services.signal_baseline")
    ns._store = {}
    ns._cold = False

    def get_baseline(signal):
        return ns._store.get(str(signal))

    def set_baseline(signal, value):
        ns._store[str(signal)] = float(value)

    def is_cold_start(min_signals: int = 3):
        return bool(ns._cold)

    ns.get_baseline = get_baseline
    ns.set_baseline = set_baseline
    ns.is_cold_start = is_cold_start

    monkeypatch.setitem(sys.modules, "core.services.signal_baseline", ns)
    import core.services as _svc

    monkeypatch.setattr(_svc, "signal_baseline", ns, raising=False)
    return ns


def _surfaces():
    """Alle fire tilstedeværelses-signaler står på 1.0 → niveau-sum 4.0.

    Det er præcis den tilstand der gjorde dommeren konstant.
    """
    return {
        "autonomy_pressure": {"summary": {"active_count": 0}},
        "open_loop": {"summary": {"open_count": 0}},
        "internal_opposition": {"active": False},
        "existential_wonder": {"latest_wonder": "en wonder fra i går"},
        "creative_drift": {"drift_count_today": 3},
        "desire": {"active_count": 3},
        "conflict": {"last_conflict": "spænding"},
        "affective_meta_state": {"mood": "steady"},
    }


@pytest.fixture()
def judge(monkeypatch, runtime_state):
    """Dommeren i shadow-mode med tomme surface-fallback (alt kommer fra `surfaces`)."""
    import core.services.central_convene_judge as cj

    monkeypatch.setattr(cj, "current_mode", lambda: "shadow")
    monkeypatch.setattr(
        "core.services.signal_surface_router.read_surface", lambda name: {}
    )
    cj.reset_reference()
    return cj


# --------------------------------------------------------------------------- #
# 1-3: dommeren
# --------------------------------------------------------------------------- #
def test_dommeren_indkalder_IKKE_paa_et_konstant_signal(judge):
    """FÆLDER niveau-summen: 4.0 konstant må ikke blive til «real_movement»."""
    s = _surfaces()
    kald = []
    for _ in range(3):
        v = judge.judge_convene(surfaces=s, top_signals=[], score=0.0)
        kald.append((v["convene"], v["movement_total"]))

    assert all(c is False for c, _ in kald), (
        "dommeren indkaldte rådet på et KONSTANT signal — den måler tilstedeværelse, "
        "ikke bevægelse: %r" % (kald,)
    )
    assert all(m == 0.0 for _, m in kald), (
        "movement_total skal være 0 når intet flyttede sig, fik %r" % (kald,)
    )


def test_dommeren_indkalder_paa_en_AEGTE_aendring(judge):
    """Den må ikke bare altid sige nej — en faktisk ændring skal bære."""
    s = _surfaces()
    judge.judge_convene(surfaces=s, top_signals=[], score=0.0)  # etablér reference

    s2 = dict(s)
    s2["conflict"] = {"last_conflict": ""}  # 1.0 → 0.0 = ægte fald
    v = judge.judge_convene(surfaces=s2, top_signals=[], score=0.0)

    assert v["convene"] is True, "en ægte ændring blev ikke set: %r" % (v,)
    assert v["movement_total"] >= judge._MOVEMENT_THRESHOLD
    assert v["reason"] == "real_movement"


def test_dommeren_laesefejl_er_UKENDT_ikke_nul(judge):
    """En læsefejl må ikke ligne «signalet faldt til nul» = falsk bevægelse."""
    judge.judge_convene(surfaces=_surfaces(), top_signals=[], score=0.0)

    with patch(
        "core.services.signal_surface_router.read_surface",
        side_effect=RuntimeError("boom"),
    ):
        v = judge.judge_convene(surfaces=None, top_signals=[], score=0.0)

    assert v["convene"] is False, (
        "en læsefejl blev læst som en kæmpe bevægelse — dommeren fyrer når kilden er nede"
    )
    assert v["movement_total"] == 0.0


# --------------------------------------------------------------------------- #
# 4-5: delta-triggerens theta_abs-gren
# --------------------------------------------------------------------------- #
def test_theta_abs_krydser_IKKE_paa_et_statisk_signal(fake_baseline, runtime_state):
    """FÆLDER `val >= theta_abs` uden delta — den gav 201/500 kryds ved movement 0."""
    import importlib

    sdt = importlib.import_module("core.services.signal_delta_trigger")
    fake_baseline.set_baseline("statisk", 0.90)

    d = sdt.evaluate({"statisk": 0.90})  # delta 0, men over θ_abs 0.85

    assert d is None, (
        "triggeren krydsede på et signal der stod HELT stille over θ_abs — "
        "det er den konstante «crossed uden bevægelse»: %r" % (d,)
    )


def test_theta_abs_krydser_STADIG_paa_en_lille_aegte_delta(fake_baseline, runtime_state):
    """Slow-boil skal bevares: en lille MEN ægte delta over θ_abs fanges."""
    import importlib

    sdt = importlib.import_module("core.services.signal_delta_trigger")
    fake_baseline.set_baseline("slowboil", 0.90)

    d = sdt.evaluate({"slowboil": 0.86})  # delta 0.04, under θ_high, over θ_abs

    assert d is not None, "slow-boil-drift blev kvalt af fixet"
    assert d["crossed"] == ["slowboil"]
    assert d["movements"]["slowboil"] == pytest.approx(-0.04)


def test_aegte_stort_delta_krydser(fake_baseline, runtime_state):
    """Kontrolarm: den normale vej (delta >= θ_high) må ikke være brudt."""
    import importlib

    sdt = importlib.import_module("core.services.signal_delta_trigger")
    fake_baseline.set_baseline("bevaegelse", 0.20)

    d = sdt.evaluate({"bevaegelse": 0.55})

    assert d is not None
    assert d["crossed"] == ["bevaegelse"]
    assert d["movements"]["bevaegelse"] == pytest.approx(0.35)


# --------------------------------------------------------------------------- #
# 6: rollerne er tomme MED VILJE
# --------------------------------------------------------------------------- #
def test_roller_er_tomme_med_vilje_ikke_en_defekt(judge):
    """Bjørn 15. jul: dommeren FORESKRIVER ikke roller. `roles == []` er kontrakten.

    Defekt-rapporten kaldte de tomme roller en fejl. Det er den ikke — den
    hører til beslutningen om at dommeren er en NUDGE (bevægelse + emne), og
    Jarvis konstruerer selv rollerne per-emne. Vagten står her så en senere
    «ret» ikke genindfører et statisk signal→rolle-map.
    """
    import inspect

    import core.services.central_convene_judge as cj

    kilde = inspect.getsource(cj.judge_convene)
    assert "roles: list[str] = []" in kilde, (
        "rollerne blev udledt igen — dommeren må ikke foreskrive roller"
    )
    assert not hasattr(cj, "_derive_roles")
    assert not hasattr(cj, "_SIGNAL_PERSPECTIVES")
