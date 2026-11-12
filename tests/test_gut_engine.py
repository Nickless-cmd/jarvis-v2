"""Hermetiske tests for gut_engine — særligt gut_gate (den nye, ægte forbruger af
adjusted_confidence). Ingen DB / eventbus: kv og record_private monkeypatches.
"""
import sqlite3

import pytest

import core.services.gut_engine as ge


@pytest.fixture(autouse=True)
def _stub_ledger(monkeypatch):
    """Hermetisk: gut_gate tæller i gate_verdict_ledger (modul-global, in-memory akkumulator).
    Uden denne stub lækker tællinger fra denne suite ind i andre suiter."""
    monkeypatch.setattr("core.services.gate_verdict_ledger.record", lambda *a, **k: None,
                        raising=False)
    # Blokerings-budgettet er også modul-globalt — ryddet pr. test, så testrækkefølgen
    # ikke afgør om en pre-flight-test ser et brugt budget.
    monkeypatch.setattr(ge, "_blok_tider", [], raising=False)
    # A2 (3/11-2026): preflight-forudsigelserne ligger også i en modul-global FIFO.
    # Uden denne reset lækker en tests forudsigelse ind i den næste `_on_started`.
    monkeypatch.setattr(ge, "_preflight_pending", [], raising=False)
    # A1 (3/11-2026): signal-cachen er også modul-global — ryddet, så en test der stubber
    # DB-laget ikke læser den forrige tests tal.
    monkeypatch.setattr(ge, "_signal_cache", {}, raising=False)
    # Den additive påvirknings-ledger er persistent i drift, men hver test får en tom,
    # privat SQLite-DB, så suiten hverken læser eller skriver runtime-state.
    influence_conn = sqlite3.connect(":memory:")
    monkeypatch.setattr("core.runtime.db_core.connect", lambda: influence_conn, raising=False)
    yield
    influence_conn.close()


# ── kv + record_private stubs ────────────────────────────────────────────
def _install_kv(monkeypatch, store):
    def _get(key, default=None):
        return store.get(key, default)
    monkeypatch.setattr("core.runtime.db_core.get_runtime_state_value", _get, raising=False)


def _capture_private(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "core.services.central_private_observe.record_private",
        lambda cluster, nerve, *, value=1.0, meta=None, reason="": calls.append(
            {"cluster": cluster, "nerve": nerve, "value": value, "meta": meta or {}, "reason": reason}
        ),
        raising=False,
    )
    return calls


# ── gut_gate: off (default) ─────────────────────────────────────────────
def test_gate_off_is_default_and_ignores_confidence(monkeypatch):
    _install_kv(monkeypatch, {})  # ingen flag sat → default "off"
    calls = _capture_private(monkeypatch)
    # Selv en confidence LANGT under enhver tærskel må passere når off.
    assert ge.gut_gate(0.0, context="x") is True
    assert ge.gut_gate(0.01) is True
    # off observerer INTET (nul adfærdsændring, ingen egress-fri støj).
    assert calls == []


def test_gate_off_explicit(monkeypatch):
    _install_kv(monkeypatch, {"central_gut_consumer_mode": "off"})
    calls = _capture_private(monkeypatch)
    assert ge.gut_gate(0.0) is True
    assert calls == []


# ── gut_gate: shadow ────────────────────────────────────────────────────
def test_gate_shadow_observes_but_never_withholds(monkeypatch):
    _install_kv(monkeypatch, {"central_gut_consumer_mode": "shadow",
                              "central_gut_gate_threshold": 0.30})
    calls = _capture_private(monkeypatch)
    # Under tærskel → ville IKKE passere, men shadow returnerer alligevel True.
    assert ge.gut_gate(0.10, context="autonomous_run") is True
    assert len(calls) == 1
    m = calls[0]["meta"]
    assert m["mode"] == "shadow"
    assert m["would_pass"] is False
    assert m["threshold"] == 0.30
    assert calls[0]["nerve"] == "gut_gate"


def test_gate_shadow_would_pass_when_above(monkeypatch):
    _install_kv(monkeypatch, {"central_gut_consumer_mode": "shadow",
                              "central_gut_gate_threshold": 0.30})
    calls = _capture_private(monkeypatch)
    assert ge.gut_gate(0.80) is True
    assert calls[0]["meta"]["would_pass"] is True


# ── gut_gate: on ────────────────────────────────────────────────────────
def test_gate_on_blocks_below_threshold(monkeypatch):
    _install_kv(monkeypatch, {"central_gut_consumer_mode": "on",
                              "central_gut_gate_threshold": 0.30})
    _capture_private(monkeypatch)
    assert ge.gut_gate(0.10) is False   # under tærskel → afvent
    assert ge.gut_gate(0.30) is True    # præcis på tærskel → proceed
    assert ge.gut_gate(0.90) is True


def test_gate_on_observes(monkeypatch):
    _install_kv(monkeypatch, {"central_gut_consumer_mode": "on"})
    calls = _capture_private(monkeypatch)
    ge.gut_gate(0.10)
    assert calls[0]["meta"]["mode"] == "on"
    assert calls[0]["meta"]["would_pass"] is False


def test_gate_default_threshold_is_030(monkeypatch):
    _install_kv(monkeypatch, {"central_gut_consumer_mode": "on"})  # ingen threshold-flag
    _capture_private(monkeypatch)
    assert ge.gut_gate(0.29) is False
    assert ge.gut_gate(0.30) is True


# ── gut_gate: self-safe ─────────────────────────────────────────────────
def test_gate_unparseable_confidence_fails_open(monkeypatch):
    _install_kv(monkeypatch, {"central_gut_consumer_mode": "on"})
    _capture_private(monkeypatch)
    assert ge.gut_gate("not-a-number") is True  # type: ignore[arg-type]


def test_gate_invalid_mode_treated_as_off(monkeypatch):
    _install_kv(monkeypatch, {"central_gut_consumer_mode": "banana"})
    calls = _capture_private(monkeypatch)
    assert ge.gut_gate(0.0) is True
    assert calls == []


def test_gate_kv_failure_fails_safe(monkeypatch):
    def _boom(key, default=None):
        raise RuntimeError("db down")
    monkeypatch.setattr("core.runtime.db_core.get_runtime_state_value", _boom, raising=False)
    # kv-fejl → mode falder til off → True, ingen kast.
    assert ge.gut_gate(0.0) is True


# ── derive_gut_signal: bias-stien (kilden til confidence gaten forbruger) ─
def test_derive_bias_lifts_proceed_confidence(monkeypatch):
    monkeypatch.setattr(ge, "get_cognitive_gut_state",
                        lambda: {"calibration_score": 1.0}, raising=False)
    monkeypatch.setattr("core.services.central_adaptation.get_gut_bias",
                        lambda: 0.20, raising=False)
    # recent_success_count>5 & confidence>0.7 → hunch proceed, hunch_confidence 0.8
    sig = ge.derive_gut_signal(task_description="t", confidence=0.9,
                               recent_success_count=6)
    assert sig["hunch"] == "proceed"
    # 0.8 * 1.0 + 0.20 = 1.0 (clampet)
    assert sig["confidence"] == 1.0


def test_derive_hunch_unchanged_by_gate(monkeypatch):
    # Gaten rører ALDRIG hunch-stien: derive returnerer samme hunch uanset consumer-mode.
    monkeypatch.setattr(ge, "get_cognitive_gut_state",
                        lambda: {"calibration_score": 0.5}, raising=False)
    monkeypatch.setattr("core.services.central_adaptation.get_gut_bias",
                        lambda: 0.0, raising=False)
    sig = ge.derive_gut_signal(task_description="t", confidence=0.1)  # <0.3 → caution
    assert sig["hunch"] == "caution"


# ── counterfactual-tælling (12/10-2026) ─────────────────────────────────
def _capture_ledger(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "core.services.gate_verdict_ledger.record",
        lambda nerve, cluster, decision, reason="": calls.append(
            {"nerve": nerve, "cluster": cluster, "decision": decision, "reason": reason}
        ),
        raising=False,
    )
    return calls


def test_counterfactual_surface_sees_influence_without_crossing(monkeypatch):
    """Fanger regressionen hvor kun grænsekryds blev læst som bias-påvirkning."""
    _install_kv(monkeypatch, {"central_gut_consumer_mode": "on",
                              "central_gut_gate_threshold": 0.30})
    _capture_private(monkeypatch)
    monkeypatch.setattr(ge, "_gut_bias", lambda: 0.1125, raising=False)
    monkeypatch.setattr(
        "core.services.gate_verdict_ledger.summary",
        lambda: {
            "gut_gate": {"total": 1, "green": 1},
            "gut_gate_uden_bias": {"total": 1, "green": 1},
        },
        raising=False,
    )

    assert ge.gut_gate(0.39, no_bias_confidence=0.34, hunch="proceed") is True
    surf = ge.build_gut_counterfactual_surface()

    assert surf["crossings"] == 0
    assert surf["influence_events"] >= 1
    assert surf["mean_abs_delta"] == pytest.approx(0.05)
    assert surf["state"] == "subthreshold"


def test_counterfactual_surface_is_inactive_when_bias_is_zero(monkeypatch):
    _install_kv(monkeypatch, {"central_gut_consumer_mode": "on",
                              "central_gut_gate_threshold": 0.30})
    _capture_private(monkeypatch)
    monkeypatch.setattr(ge, "_gut_bias", lambda: 0.0, raising=False)
    monkeypatch.setattr(
        "core.services.gate_verdict_ledger.summary",
        lambda: {
            "gut_gate": {"total": 1, "green": 1},
            "gut_gate_uden_bias": {"total": 1, "green": 1},
        },
        raising=False,
    )

    assert ge.gut_gate(0.34, no_bias_confidence=0.34, hunch="proceed") is True
    surf = ge.build_gut_counterfactual_surface()

    assert surf["influence_events"] == 0
    assert surf["state"] == "inactive"


def test_counterfactual_surface_preserves_crossing_count(monkeypatch):
    _install_kv(monkeypatch, {"central_gut_consumer_mode": "on",
                              "central_gut_gate_threshold": 0.30})
    _capture_private(monkeypatch)
    monkeypatch.setattr(ge, "_gut_bias", lambda: 0.1125, raising=False)
    monkeypatch.setattr(
        "core.services.gate_verdict_ledger.summary",
        lambda: {
            "gut_gate": {"total": 1, "green": 1},
            "gut_gate_uden_bias": {"total": 1, "red": 1},
        },
        raising=False,
    )

    assert ge.gut_gate(0.32, no_bias_confidence=0.27, hunch="proceed") is True
    surf = ge.build_gut_counterfactual_surface()

    assert surf["crossings"] == 1
    assert surf["counterfactual_delta"] == 1
    assert surf["state"] == "tipping"


def test_counterfactual_taeller_begge_afgoerelser(monkeypatch):
    _install_kv(monkeypatch, {"central_gut_consumer_mode": "on",
                              "central_gut_gate_threshold": 0.30})
    _capture_private(monkeypatch)
    calls = _capture_ledger(monkeypatch)
    # 0.3524 passerer (>= 0.30); uden bias 0.25 gør ikke → erfaringen flyttede afgørelsen.
    ge.gut_gate(0.3524, context="autonomous_run", no_bias_confidence=0.25)
    assert [(c["nerve"], c["decision"]) for c in calls] == [
        ("gut_gate", "green"),
        ("gut_gate_uden_bias", "red"),
    ]
    assert all(c["cluster"] == "cognition" for c in calls)


def test_counterfactual_uden_baseline_taeller_kun_med_bias(monkeypatch):
    _install_kv(monkeypatch, {"central_gut_consumer_mode": "on"})
    _capture_private(monkeypatch)
    calls = _capture_ledger(monkeypatch)
    ge.gut_gate(0.90)
    assert [c["nerve"] for c in calls] == ["gut_gate"]


def test_counterfactual_off_taeller_intet(monkeypatch):
    _install_kv(monkeypatch, {})  # default off → observerer intet, tæller intet
    calls = _capture_ledger(monkeypatch)
    ge.gut_gate(0.0)
    assert calls == []


def test_counterfactual_ledger_fejl_vaelter_ikke_gaten(monkeypatch):
    _install_kv(monkeypatch, {"central_gut_consumer_mode": "on"})
    _capture_private(monkeypatch)

    def _boom(*a, **k):
        raise RuntimeError("ledger nede")

    monkeypatch.setattr("core.services.gate_verdict_ledger.record", _boom, raising=False)
    assert ge.gut_gate(0.90) is True  # en tæller må ALDRIG blokere gaten


def test_influence_ledger_fejl_vaelter_ikke_gaten(monkeypatch):
    _install_kv(monkeypatch, {"central_gut_consumer_mode": "on"})
    _capture_private(monkeypatch)

    def _boom():
        raise RuntimeError("influence-DB nede")

    monkeypatch.setattr("core.runtime.db_core.connect", _boom, raising=False)
    assert ge.gut_gate(0.90, no_bias_confidence=0.80) is True


def test_counterfactual_delta_laeses_fra_ledger(monkeypatch):
    monkeypatch.setattr(
        "core.services.gate_verdict_ledger.summary",
        lambda: {
            "gut_gate": {"total": 10, "green": 10},
            "gut_gate_uden_bias": {"total": 10, "green": 7},
        },
        raising=False,
    )
    surf = ge.build_gut_counterfactual_surface()
    assert surf["counterfactual_delta"] == 3
    assert surf["events"] == 10
    assert surf["delta_pct"] == 30.0


def test_counterfactual_delta_tom_ledger(monkeypatch):
    monkeypatch.setattr("core.services.gate_verdict_ledger.summary", lambda: {}, raising=False)
    surf = ge.build_gut_counterfactual_surface()
    assert surf["active"] is False
    assert surf["events"] == 0


def test_derive_eksponerer_bias_fri_baseline(monkeypatch):
    monkeypatch.setattr(ge, "get_cognitive_gut_state",
                        lambda: {"calibration_score": 1.0}, raising=False)
    monkeypatch.setattr("core.services.central_adaptation.get_gut_bias",
                        lambda: 0.20, raising=False)
    sig = ge.derive_gut_signal(task_description="t", confidence=0.9,
                               recent_success_count=6)
    # hunch_confidence 0.8 * calibration 1.0 = 0.8 UDEN bias; 1.0 MED (clampet).
    assert sig["confidence_no_bias"] == 0.8
    assert sig["confidence"] == 1.0


# ── bias'en kan TRÆKKE FRA (12/10-2026, Bjørn) ───────────────────────────
#
# Før var begge grene klippet til `max(0.0, ±bias)`, så justeringen ALTID var ≥ 0: musklen
# kunne kun hæve confidence og var strukturelt ude af stand til at afvise noget. Det er
# grunden til at gaten aldrig efterlod et withhold-spor — ikke manglende data, men en lukket
# vej i koden. Disse tests holder den vej åben.


def _fast_mave(monkeypatch, *, kalibrering: float, bias: float):
    monkeypatch.setattr(ge, "get_cognitive_gut_state",
                        lambda: {"calibration_score": kalibrering}, raising=False)
    monkeypatch.setattr("core.services.central_adaptation.get_gut_bias",
                        lambda: bias, raising=False)


def test_negativ_bias_saenker_proceed_confidence(monkeypatch):
    _fast_mave(monkeypatch, kalibrering=1.0, bias=-0.25)
    # confidence=0.5 → default-grenen: hunch proceed, hunch_confidence 0.5.
    sig = ge.derive_gut_signal(task_description="t", confidence=0.5)
    assert sig["hunch"] == "proceed"
    assert sig["confidence_no_bias"] == 0.5
    assert sig["confidence"] == 0.25          # 0.5 − 0.25, ikke 0.5


def test_positiv_bias_saenker_caution_confidence(monkeypatch):
    """Symmetrien: fortjent tillid gør et 'caution' mindre tillidsvækkende, ikke uændret."""
    _fast_mave(monkeypatch, kalibrering=1.0, bias=0.20)
    sig = ge.derive_gut_signal(task_description="t", confidence=0.1)   # <0.3 → caution
    assert sig["hunch"] == "caution"
    assert sig["confidence_no_bias"] == 0.6    # hunch_confidence 0.6 * 1.0
    assert sig["confidence"] == 0.4            # 0.6 − 0.20


def test_negativ_bias_vender_en_tilladelse_til_en_afvisning(monkeypatch):
    """Kernen i Bjørns rettelse: uden bias passerer runnet, med en negativ bias stoppes det.

    Det er præcis det tal ChatGPT kaldte counterfactual decision delta — her med fortegnet
    vendt om, så erfaringen nu KAN trække en afgørelse fra tilladelse til afvisning.
    """
    _install_kv(monkeypatch, {"central_gut_consumer_mode": "on",
                              "central_gut_gate_threshold": 0.30})
    _capture_private(monkeypatch)
    _fast_mave(monkeypatch, kalibrering=1.0, bias=-0.25)
    sig = ge.derive_gut_signal(task_description="t", confidence=0.5)
    assert sig["confidence_no_bias"] == 0.5    # over tærsklen
    assert sig["confidence"] == 0.25           # under
    assert ge.gut_gate(0.5, no_bias_confidence=0.5) is True
    assert ge.gut_gate(sig["confidence"],
                       no_bias_confidence=sig["confidence_no_bias"]) is False


# ── pre-flight gate (12/10-2026) ─────────────────────────────────────────
def test_preflight_slipper_igennem_over_taersklen(monkeypatch):
    _install_kv(monkeypatch, {"central_gut_consumer_mode": "on",
                              "central_gut_gate_threshold": 0.30})
    _capture_private(monkeypatch)
    _fast_mave(monkeypatch, kalibrering=1.0, bias=0.0)
    ud = ge.preflight_gut_gate(task_description="t")
    assert ud["allowed"] is True
    assert ud["hunch"] == "proceed"


def test_preflight_stopper_under_taersklen(monkeypatch):
    _install_kv(monkeypatch, {"central_gut_consumer_mode": "on",
                              "central_gut_gate_threshold": 0.30})
    calls = _capture_private(monkeypatch)
    _fast_mave(monkeypatch, kalibrering=0.4, bias=0.0)   # 0.5 * 0.4 = 0.2
    ud = ge.preflight_gut_gate(task_description="t")
    assert ud["allowed"] is False
    assert ud["confidence"] == 0.2
    assert any(c["nerve"] == "gut_gate_withhold" for c in calls)
    assert len(ge._blok_tider) == 1


def test_preflight_bagkant_slipper_igennem_efter_budgettet(monkeypatch):
    """En fejlkalibreret muskel må gøre arbejdet forsigtigere — ALDRIG standse det."""
    _install_kv(monkeypatch, {"central_gut_consumer_mode": "on",
                              "central_gut_gate_threshold": 0.30})
    _capture_private(monkeypatch)
    ledger_kald = _capture_ledger(monkeypatch)
    _fast_mave(monkeypatch, kalibrering=0.4, bias=0.0)
    udfald = [ge.preflight_gut_gate(task_description="t")["allowed"]
              for _ in range(ge._MAX_BLOK_PER_TIME + 2)]
    assert udfald[:ge._MAX_BLOK_PER_TIME] == [False] * ge._MAX_BLOK_PER_TIME
    assert udfald[ge._MAX_BLOK_PER_TIME:] == [True, True]
    assert any(c["nerve"] == "gut_gate_backstop" for c in ledger_kald), \
        "overkørslen skal tælles særskilt — ellers ser den ud som et almindeligt gennemløb"


def test_preflight_fail_open_naar_derive_kaster(monkeypatch):
    def _boom(*, task_description):
        raise RuntimeError("nede")

    monkeypatch.setattr(ge, "derive_gut_signal", _boom, raising=False)
    assert ge.preflight_gut_gate(task_description="t")["allowed"] is True
    assert ge.preflight_allows("t") is True


def test_preflight_fail_open_naar_gaten_kaster(monkeypatch):
    monkeypatch.setattr(ge, "derive_gut_signal",
                        lambda **kwargs: {"hunch": "proceed", "confidence": 0.1},
                        raising=False)

    def _boom(*a, **k):
        raise RuntimeError("nede")

    monkeypatch.setattr(ge, "gut_gate", _boom, raising=False)
    ud = ge.preflight_gut_gate(task_description="t")
    assert ud["allowed"] is True
    assert ud["reason"] == "gate-fejl"


def test_preflight_mode_off_stopper_intet(monkeypatch):
    """Default-mode er off — så gaten må ikke kunne stoppe noget som helst."""
    _install_kv(monkeypatch, {})
    _capture_private(monkeypatch)
    _fast_mave(monkeypatch, kalibrering=0.1, bias=-0.25)
    assert ge.preflight_gut_gate(task_description="t")["allowed"] is True


# ── flytningen: gaten hører i pre-flight, ikke i kalibreringen ───────────
def test_started_kalder_ikke_gaten_laengere():
    """Bliver gut_gate kaldt fra _on_started igen, dobbelt-tælles counterfactual'en — den
    fyrer på et event der kommer EFTER runnet er begyndt. Kilden læses, ikke opførslen."""
    import inspect

    import core.services.gut_calibration as gc
    kilde = inspect.getsource(gc._on_started)
    assert "gut_gate(" not in kilde


def test_begge_run_start_stier_kalder_preflight():
    """Gaten skal ligge FØR runnet fødes — i begge stier, ellers falder en vej udenom."""
    from pathlib import Path
    for sti in ("core/services/visible_autonomous_run.py",
                "core/services/autonomous_stream_run.py"):
        kilde = Path(sti).read_text(encoding="utf-8")
        assert "preflight_allows" in kilde, f"{sti} kalder ikke pre-flight-gaten"


def test_surface_rapporterer_blokeringer_og_overkoersler(monkeypatch):
    """A6b (3/11-2026): `blokeret` er FAKTISK stoppede runs — ikke gatens nej.

    Før talte fladen `total - pass_med`, så en backstop-overkørsel stod som «stoppet» i
    samme flade der ved siden af viste den som «sluppet igennem». Med 3 nej hvoraf 2 blev
    overkørt er der 1 reelt stoppet run, ikke 3.
    """
    monkeypatch.setattr(
        "core.services.gate_verdict_ledger.summary",
        lambda: {
            "gut_gate": {"total": 10, "green": 7},
            "gut_gate_uden_bias": {"total": 10, "green": 10},
            "gut_gate_backstop": {"total": 2},
        },
        raising=False,
    )
    surf = ge.build_gut_counterfactual_surface()
    assert surf["counterfactual_delta"] == -3      # negativ: bias'en trak FRA
    assert surf["blokeret"] == 1                   # 3 nej − 2 overkørt af bagkanten
    assert surf["backstop_overkoersler"] == 2


def test_surface_holder_shadow_ude_af_blokeret(monkeypatch):
    """A6b: en shadow-simuleret afvisning er ikke en blokering — runnet startede.

    Shadow-afgørelser tælles på deres EGEN nerve, så de kan ikke snige sig ind i
    `blokeret` via den fælles tælling.
    """
    monkeypatch.setattr(
        "core.services.gate_verdict_ledger.summary",
        lambda: {
            "gut_gate": {"total": 4, "green": 4},
            "gut_gate_uden_bias": {"total": 4, "green": 4},
            "gut_gate_shadow": {"total": 9, "green": 1},
        },
        raising=False,
    )
    surf = ge.build_gut_counterfactual_surface()
    assert surf["blokeret"] == 0                   # ingen håndhævet afvisning
    assert surf["shadow_afgoerelser"] == 9         # de simulerede tælles særskilt


def test_shadow_taelles_paa_egen_nerve(monkeypatch):
    """A6b i registreringen: mode skal kunne skelnes i den aggregering fladen læser."""
    _install_kv(monkeypatch, {"central_gut_consumer_mode": "shadow",
                              "central_gut_gate_threshold": 0.30})
    _capture_private(monkeypatch)
    calls = _capture_ledger(monkeypatch)
    ge.gut_gate(0.10, no_bias_confidence=0.10)      # ville afvise — men shadow slipper
    nerver = [c["nerve"] for c in calls]
    assert "gut_gate" not in nerver, "en shadow-afgørelse må ikke tælles som håndhævet"
    assert "gut_gate_shadow" in nerver


def test_preflight_forudsigelse_overlever_til_kalibrering(monkeypatch):
    """A2 (3/11-2026): kalibreringen skal evaluere DEN forudsigelse gaten brugte.

    Før kastede preflight sin hunch, og `_on_started` dannede en ny fra et andet input —
    så udfaldet kalibrerede en anden forudsigelse end den der lå bag startbeslutningen.
    """
    import core.services.gut_calibration as gc

    _install_kv(monkeypatch, {"central_gut_consumer_mode": "on",
                              "central_gut_gate_threshold": 0.30})
    _capture_private(monkeypatch)
    _fast_mave(monkeypatch, kalibrering=1.0, bias=0.0)

    udfald = ge.preflight_gut_gate(task_description="kritisk migration af prod-database")
    pred = ge.take_preflight_prediction()
    assert pred is not None
    assert pred["hunch"] == udfald["hunch"]
    assert str(pred["task"]).startswith("kritisk migration")
    assert ge.take_preflight_prediction() is None   # forbrugt præcis én gang

    # _on_started tager slotten frem for at regne en ny fra et andet input.
    #
    # 3/11-2026: denne del var brudt — den kørte EFTER at del 1 havde forbrugt slotten,
    # så der var intet at tage, og `_on_started` regnede en ny fra `focus`. Testen var
    # kun grøn fordi begge sider tilfældigt gav «proceed». Nu lægges en FRISK slot, og
    # fokus-teksten er bevidst i `proceed`-klassen, så testen beviser forskellen:
    # tages slotten, er svaret `caution`; regnes der en ny, er det `proceed`.
    ge.preflight_gut_gate(task_description="kritisk migration af prod-database")
    monkeypatch.setattr(gc, "_pending", {}, raising=False)
    gc._on_started({"run_id": "run-xyz", "focus": "en helt anden tekst"})
    assert gc._pending["run-xyz"] == "caution", \
        "kalibreringen regnede en ny forudsigelse i stedet for at tage gaten's"


# ── Definition B (3/11-2026, Bjørn): confidence = styrken af RETNINGEN ────
#
# Før 3/11 læste gaten `confidence` som «hvor sandsynligt er det at opgaven lykkes»,
# men `derive_gut_signal` producerede «hvor stærkt er signalet». Da caution fik 0,6–0,7
# og proceed 0,5, slap en ADVARSEL lettere igennem end en TILLADELSE. Disse tests holder
# retningen som en del af afgørelsen, så den inversion ikke kan snige sig ind igen.


def test_caution_med_hoej_styrke_blokeres(monkeypatch):
    """Kernen i rettelsen: en stærk advarsel må ALDRIG passere på sin styrke alene."""
    _install_kv(monkeypatch, {"central_gut_consumer_mode": "on",
                              "central_gut_gate_threshold": 0.30})
    _capture_private(monkeypatch)
    # 0.70 er over tærsklen — før 3/11 gav det PASS. Nu er retningen afgørende.
    assert ge.gut_gate(0.70, hunch="caution") is False
    assert ge.gut_gate(0.70, hunch="proceed") is True


def test_caution_blokeres_uanset_styrke(monkeypatch):
    """BEVIDST POLITIK (Definition B, 3/11-2026): enhver `caution` har vetoret.

    Selv confidence=0.00 — altså «jeg har ingen tillid til min egen advarsel» — blokerer.
    Det er en forsigtigheds-politik, ikke en konsekvens af styrkeberegningen: retningen
    alene afgør om noget må fortsætte. Politikken står her, så den ikke glider tilbage
    til «høj styrke slipper igennem» uden at nogen opdager det.
    """
    _install_kv(monkeypatch, {"central_gut_consumer_mode": "on"})
    _capture_private(monkeypatch)
    for conf in (0.0, 0.30, 0.60, 0.99, 1.0):
        assert ge.gut_gate(conf, hunch="caution") is False, f"caution slap igennem ved {conf}"


def test_proceed_under_taerskel_blokeres_stadig(monkeypatch):
    """Retningen må ikke gøre tærsklen virkningsløs i den anden retning."""
    _install_kv(monkeypatch, {"central_gut_consumer_mode": "on",
                              "central_gut_gate_threshold": 0.30})
    _capture_private(monkeypatch)
    assert ge.gut_gate(0.29, hunch="proceed") is False
    assert ge.gut_gate(0.30, hunch="proceed") is True


def test_uden_hunch_er_bagudkompatibel(monkeypatch):
    """Gamle kaldesteder sender ingen hunch — de skal opføre sig som før (antaget proceed)."""
    _install_kv(monkeypatch, {"central_gut_consumer_mode": "on",
                              "central_gut_gate_threshold": 0.30})
    _capture_private(monkeypatch)
    assert ge.gut_gate(0.61) is True
    assert ge.gut_gate(0.25) is False


def test_observationen_baerer_retningen(monkeypatch):
    """Uden hunch i meta kan man ikke bagefter se HVORFOR gaten afviste."""
    _install_kv(monkeypatch, {"central_gut_consumer_mode": "on"})
    calls = _capture_private(monkeypatch)
    ge.gut_gate(0.70, hunch="caution")
    assert calls[0]["meta"]["hunch"] == "caution"
    assert calls[0]["meta"]["would_pass"] is False


def test_preflight_sender_hunch_til_gaten(monkeypatch):
    """Preflight skal videregive retningen — ellers er rettelsen død kode i produktion."""
    _install_kv(monkeypatch, {"central_gut_consumer_mode": "on",
                              "central_gut_gate_threshold": 0.30})
    _capture_private(monkeypatch)
    _fast_mave(monkeypatch, kalibrering=1.0, bias=0.0)
    # confidence=0.1 → caution med hunch_confidence 0.6 (over tærsklen 0.30).
    monkeypatch.setattr(ge, "derive_gut_signal",
                        lambda **kwargs: {
                            "hunch": "caution", "confidence": 0.60,
                            "confidence_no_bias": 0.60},
                        raising=False)
    # Evidens-porten (12/11-2026) kræver at advarslen kan vises at være præcis, før den
    # må blokere. Her gives et sample hvor caution faktisk rammer, så testen måler
    # retnings-videregivelsen og ikke porten.
    _stub_evidens(monkeypatch, caution_n=40, caution_fejl=30,
                  alle_n=300, alle_fejl=32)
    ud = ge.preflight_gut_gate(task_description="t")
    assert ud["allowed"] is False, "en advarsel over tærsklen må ikke slippe igennem"
    assert ud["hunch"] == "caution"


def test_derive_dokumenterer_definition_b(monkeypatch):
    """Kilden skal selv sige hvad feltet betyder — ellers glider det tilbage."""
    import inspect
    kilde = inspect.getsource(ge.derive_gut_signal)
    assert "Definition B" in kilde
    assert "RETNING" in kilde


# ── Definition B i counterfactual-målingen (3/11-2026) ───────────────────
#
# Rettelsen af gaten var halv: `_record_counterfactual` beregnede no-bias-siden som
# `nb >= threshold` uden at se retningen. En `caution` med nb over tærsklen blev derfor
# talt som GREEN, mens den faktiske afgørelse var RED — og ledgeren rapporterede et
# delta der ikke kom fra bias, men fra retningsreglen.

def test_counterfactual_caution_giver_nul_delta(monkeypatch):
    """Bias flytter kun styrken. En caution er afvist med OG uden bias → delta = 0."""
    _install_kv(monkeypatch, {"central_gut_consumer_mode": "on",
                              "central_gut_gate_threshold": 0.30})
    _capture_private(monkeypatch)
    calls = _capture_ledger(monkeypatch)
    ge.gut_gate(0.70, hunch="caution", no_bias_confidence=0.70)
    assert [(c["nerve"], c["decision"]) for c in calls] == [
        ("gut_gate", "red"),
        ("gut_gate_uden_bias", "red"),
    ], "caution skal være RED på BEGGE sider — ellers opfinder ledgeren et falsk delta"


def test_counterfactual_caution_kan_ikke_blive_green_uden_bias(monkeypatch):
    """Selv når no-bias-styrken er maksimal, må en caution ikke tælles som grøn."""
    _install_kv(monkeypatch, {"central_gut_consumer_mode": "on",
                              "central_gut_gate_threshold": 0.30})
    _capture_private(monkeypatch)
    calls = _capture_ledger(monkeypatch)
    ge.gut_gate(0.99, hunch="caution", no_bias_confidence=1.0)
    decisions = {c["nerve"]: c["decision"] for c in calls}
    assert decisions["gut_gate_uden_bias"] == "red"


def test_counterfactual_bias_flytter_stadig_en_proceed(monkeypatch):
    """Rettelsen må ikke gøre maalingen blind: ægte bias-forskydning skal stadig ses."""
    _install_kv(monkeypatch, {"central_gut_consumer_mode": "on",
                              "central_gut_gate_threshold": 0.30})
    _capture_private(monkeypatch)
    calls = _capture_ledger(monkeypatch)
    # proceed: 0.3524 passerer, uden bias 0.25 gør ikke → erfaringen flyttede afgørelsen.
    ge.gut_gate(0.3524, hunch="proceed", no_bias_confidence=0.25)
    assert [(c["nerve"], c["decision"]) for c in calls] == [
        ("gut_gate", "green"),
        ("gut_gate_uden_bias", "red"),
    ]


# ── A1 (3/11-2026): ægte observationer i stedet for hårdkodede nuller ────────
#
# Før kaldte preflight `derive_gut_signal(task_description=…)` — intet andet. Så var
# confidence/error/success ALTID defaults, og tre vidt forskellige opgaver gav identisk
# 0,61. Disse tests holder koblingen åben: gaten skal se noget der faktisk er målt.


def test_preflight_sender_observationer_til_signalet(monkeypatch):
    """Preflight skal videregive de målte tick-signaler — ellers er A1 død kode."""
    _install_kv(monkeypatch, {"central_gut_consumer_mode": "shadow",
                              "central_gut_gate_threshold": 0.30})
    _capture_private(monkeypatch)
    _fast_mave(monkeypatch, kalibrering=1.0, bias=0.0)
    monkeypatch.setattr(ge, "_recent_tick_signals", lambda: (7, 42), raising=False)

    set_input = {}
    ægte_derive = ge.derive_gut_signal

    def _fang(*, task_description, confidence=0.5,
              recent_error_count=0, recent_success_count=0):
        set_input["err"] = recent_error_count
        set_input["ok"] = recent_success_count
        return ægte_derive(task_description=task_description, confidence=confidence,
                           recent_error_count=recent_error_count,
                           recent_success_count=recent_success_count)

    monkeypatch.setattr(ge, "derive_gut_signal", _fang, raising=False)
    ge.preflight_gut_gate(task_description="t")
    assert set_input == {"err": 7, "ok": 42}, "gaten fik ikke de målte observationer"


def test_aegte_observationer_kan_vende_hunch_til_caution(monkeypatch):
    """Kernen i A1: fejl-signalet skal kunne ændre RETNINGEN — ikke bare tallet.

    Rettet 3/11-2026: testen brugte 23 fejl mod 270 succeser som bevis for «mange
    blokerede ticks». Det er 7,8 % — en sund drift. Den håndhævede derfor præcis den fejl
    den skulle vogte: at et ABSOLUT antal blev læst som et signal. Betingelsen `> 3` var
    altid sand i et aktivt system, så `caution` var en konstant — målt gav seks vidt
    forskellige opgaver samme svar, og `mode=on` ville have afvist 100 % af runs.
    Nu kræves en RATE over 20 % ved mindst 20 ticks — og så skal retningen stadig vendes.
    """
    _fast_mave(monkeypatch, kalibrering=1.0, bias=0.0)
    foer = ge.derive_gut_signal(task_description="t", recent_error_count=0,
                                recent_success_count=0)
    nu = ge.derive_gut_signal(task_description="t", recent_error_count=40,
                              recent_success_count=60)
    assert foer["hunch"] == "proceed"
    assert nu["hunch"] == "caution", "40 fejl af 100 skal kunne ændre retningen"
    assert nu["recent_error_rate"] == 0.4


def test_lav_fejlrate_vender_ikke_retningen_uanset_absolut_antal(monkeypatch):
    """Et højt ABSOLUT antal fejl i sund drift må ikke gøre alt til `caution`.

    Målt 3/11 kl. 18:44: 23 blocked mod 280 ok = 7,6 %. Med den gamle regel blev
    migration, deploy, logfil-læsning, testfil, analyse og volapyk ALLE `caution` med
    conf 0,59 — tærsklen (0,30) var aldrig bindende, retningen var.
    """
    _fast_mave(monkeypatch, kalibrering=1.0, bias=0.0)
    sig = ge.derive_gut_signal(task_description="laes logfilen og find fejlen",
                               recent_error_count=23, recent_success_count=280)
    assert sig["recent_error_rate"] < ge._ERROR_RATE_CAUTION
    assert sig["hunch"] == "proceed", "7,6 % fejlrate er ikke grund til caution"


def test_for_lille_grundlag_udloeser_ikke_caution(monkeypatch):
    """To fejl af tre forsøg er 67 %, men ikke et grundlag.

    Uden et minimum kan to tilfældige fejl tidligt i døgnet låse gaten i caution, og
    en rate på 2/3 er statistisk meningsløs som prognose.
    """
    _fast_mave(monkeypatch, kalibrering=1.0, bias=0.0)
    sig = ge.derive_gut_signal(task_description="laes logfilen",
                               recent_error_count=2, recent_success_count=1)
    assert sig["recent_error_rate"] > ge._ERROR_RATE_CAUTION
    assert sig["recent_sample_size"] < ge._MIN_SAMPLE_FOR_RATE
    assert sig["hunch"] == "proceed"


def test_fejlraten_er_synlig_i_signalet(monkeypatch):
    """Uden raten i signalet kan ingen efterprøve hvorfor retningen blev valgt."""
    _fast_mave(monkeypatch, kalibrering=1.0, bias=0.0)
    sig = ge.derive_gut_signal(task_description="t", recent_error_count=10,
                               recent_success_count=90)
    assert sig["recent_error_rate"] == 0.1
    assert sig["recent_sample_size"] == 100


def test_tick_signaler_taeller_blocked_som_fejl(monkeypatch):
    """`blocked` er den eneste status der betyder «kom ikke igennem»."""
    class _Row(dict):
        pass

    rows = [_Row(tick_status="blocked", n=4), _Row(tick_status="ok", n=9),
            _Row(tick_status="completed", n=3)]

    class _Conn:
        def execute(self, *_a, **_k):
            return self
        def fetchall(self):
            return rows
        def __enter__(self):
            return self
        def __exit__(self, *_a):
            return False

    monkeypatch.setattr("core.runtime.db_core.connect", lambda: _Conn(), raising=False)
    err, ok = ge._recent_tick_signals()
    assert (err, ok) == (4, 12)


def test_tick_signaler_fejler_til_nuller(monkeypatch):
    """Uden DB-adgang falder vi tilbage til dagens adfærd — ikke til en gættet værdi."""
    def _boom():
        raise RuntimeError("db nede")

    monkeypatch.setattr("core.runtime.db_core.connect", _boom, raising=False)
    assert ge._recent_tick_signals() == (0, 0)


def test_afvisning_registreres_som_beslutning(monkeypatch):
    """A3: en afvisning skal stå i ledgeren som BESLUTNING — på sin egen nerve.

    Den må ikke blande sig med de evaluerede udfald: et afvist run har intet udfald,
    så det kan aldrig kalibrere maven.
    """
    _install_kv(monkeypatch, {"central_gut_consumer_mode": "on",
                              "central_gut_gate_threshold": 0.95})
    _capture_private(monkeypatch)
    calls = _capture_ledger(monkeypatch)
    _fast_mave(monkeypatch, kalibrering=1.0, bias=0.0)
    # «kritisk migration» bliver caution via irreversible-grenen. Evidens-porten kræver
    # at advarslen er præcis før den må blokere — her gives et sample hvor den rammer.
    _stub_evidens(monkeypatch, caution_n=40, caution_fejl=30,
                  alle_n=300, alle_fejl=32)
    ud = ge.preflight_gut_gate(task_description="kritisk migration")
    assert ud["allowed"] is False
    withheld = [c for c in calls if c["nerve"] == "gut_gate_withheld"]
    assert withheld, "afvisningen blev ikke registreret som beslutning"
    assert withheld[0]["decision"] == "withheld"


# ── Evidens-port (12/11-2026): caution må kun BLOKKERE med positiv forventet værdi ──
#
# Målt 12/11 kl. 21:45Z på 344 events: maven 92,73 % korrekt mod konstantens 99,71 %
# (−6,98 pp), og af 26 caution-advarsler var 1 korrekt (3,8 %). Gaten advarede altså om
# noget der gik fint 96 % af gangene. Porten kræver at advarslen kan vises at være bedre
# end «sig altid proceed» før den må stoppe et run.

def _stub_evidens(monkeypatch, *, caution_n: int, caution_fejl: int,
                  alle_n: int = 344, alle_fejl: int | None = None):
    """Stub evidens-målingen med et bestemt sample i stedet for at læse DB'en.

    Modellerer BREAK-EVEN-reglen (12/11-2026, Bjørns anden indvending): caution skal
    løfte fejlraten over den pris, blokeringen skal tjene ind — ikke over en fast lift
    og ikke over et flertal. `alle_fejl` defaulter til caution_fejl, så et kald uden
    proceed-fejl giver samme tal som produktionen ville.
    """
    if alle_fejl is None:
        alle_fejl = caution_fejl

    def _fake():
        if caution_n < ge._EVIDENS_MIN_CAUTION:
            return {"may_block": False, "reason": "for-faa-caution-events",
                    "caution_n": caution_n, "kraevet": ge._EVIDENS_MIN_CAUTION}
        if alle_fejl == 0:
            return {"may_block": False, "reason": "ingen-fejl-at-skelne",
                    "caution_n": caution_n, "alle_n": alle_n}
        basis = alle_fejl / alle_n
        cr = caution_fejl / caution_n
        lift = cr / basis
        blok_pris, fejl_pris = ge._omkostnings_ratio()
        break_even = blok_pris / (blok_pris + fejl_pris)
        skal = cr > break_even
        return {"may_block": skal,
                "reason": "over-break-even" if skal else "under-break-even",
                "caution_n": caution_n, "caution_fejl": caution_fejl,
                "cautionrate": round(cr, 4), "basisrate": round(basis, 4),
                "lift": round(lift, 2), "break_even": round(break_even, 4),
                "alle_n": alle_n}
    monkeypatch.setattr(ge, "_caution_har_evidens", _fake, raising=False)


def _tving_caution_afvist(monkeypatch):
    """Få gaten til at ville afvise: hunch=caution og confidence under tærsklen."""
    monkeypatch.setattr(ge, "_recent_tick_signals", lambda: (0, 0), raising=False)
    monkeypatch.setattr(ge, "derive_gut_signal",
                        lambda **kw: {"hunch": "caution", "confidence": 0.1,
                                      "confidence_no_bias": 0.1}, raising=False)
    monkeypatch.setattr(ge, "gut_gate", lambda *a, **k: False, raising=False)
    monkeypatch.setattr(ge, "_blok_budget_brugt", lambda: False, raising=False)
    monkeypatch.setattr(ge, "_record_withheld_decision",
                        lambda *a, **k: None, raising=False)


def test_caution_uden_evidens_blokerer_ikke(monkeypatch):
    """Kernen i fixet: en advarsel der ikke skelner må ikke stoppe et run.

    Målt 12/11: 26 caution-advarsler, 0 fejl i caution-gruppen og 0 i proceed-gruppen
    (den ene ikke-succes var `interrupted`). Der er intet at skelne imod, så advarslen
    kan ikke have fanget noget — og må ikke blokere.
    """
    _tving_caution_afvist(monkeypatch)
    _stub_evidens(monkeypatch, caution_n=26, caution_fejl=0, alle_n=343, alle_fejl=0)
    ud = ge.preflight_gut_gate(task_description="t")
    assert ud["allowed"] is True, "en advarsel der ikke skelner må ikke blokere"
    assert ud.get("evidence_blocked") is True
    assert ud["evidence"]["reason"] == "ingen-fejl-at-skelne"
    # Signalet selv er UÆNDRET — de fire andre forbrugere skal stadig se caution.
    assert ud["hunch"] == "caution"


def test_caution_med_evidens_blokerer_stadig(monkeypatch):
    """Den anden retning: skelner advarslen faktisk, skal gaten stadig kunne stoppe.

    Uden denne test ville fixet være «advar aldrig» — og så havde jeg fjernet en
    sikkerhedsmekanisme i stedet for at afgrænse den.
    """
    _tving_caution_afvist(monkeypatch)
    # 10 af 25 caution-events fejler (40 %) mod 2 af 300 i resten (0,67 %) → lift ~60x
    _stub_evidens(monkeypatch, caution_n=25, caution_fejl=10,
                  alle_n=325, alle_fejl=12)
    ud = ge.preflight_gut_gate(task_description="t")
    assert ud["allowed"] is False, "en advarsel der skelner skal stadig kunne stoppe et run"
    assert ud["hunch"] == "caution"


def test_prisen_styrer_ikke_lift_alene(monkeypatch):
    """BJØRNS ANDEN INDVENding (12/11-2026): lift er ikke en beslutningsregel.

    Lift 13x ser imponerende ud, men den absolutte risiko er 3,85 %. Om det kan betale
    sig at blokere afhænger af hvad en falsk blokering koster mod en ufanget fejl — og
    det følger ikke af lift. Med husets default (4:1) er break-even 20 %, så 3,85 %
    blokerer IKKE. Hæves fejl-prisen til 40:1 (break-even 2,44 %), gør den.

    Den anden halvdel er pointen: reglen reagerer på konsekvenserne i stedet for at
    være en skjult 50 %-regel med en anden etiket.
    """
    _tving_caution_afvist(monkeypatch)
    # 1 fejl af 26 caution (3,85 %) mod 1 fejl af 344 i alt (0,29 %) → lift ~13x
    _stub_evidens(monkeypatch, caution_n=26, caution_fejl=1,
                  alle_n=344, alle_fejl=1)
    ud = ge.preflight_gut_gate(task_description="t")
    assert ud["allowed"] is True, (
        "3,85 % fejlrisiko er under break-even 20 % ved husets default-priser")

    # Samme data, men nu koster en ufanget fejl 40x en blokering → break-even 2,44 %
    monkeypatch.setattr(ge, "_omkostnings_ratio", lambda: (1.0, 40.0), raising=False)
    _stub_evidens(monkeypatch, caution_n=26, caution_fejl=1,
                  alle_n=344, alle_fejl=1)
    ud = ge.preflight_gut_gate(task_description="t")
    assert ud["allowed"] is False, (
        "ved 40:1 ligger 3,85 % over break-even — prisen skal kunne ændre svaret")


def test_for_lille_sample_blokerer_ikke(monkeypatch):
    """3 advarsler hvor alle 3 var korrekte er 100 % — men ikke et grundlag."""
    _tving_caution_afvist(monkeypatch)
    _stub_evidens(monkeypatch, caution_n=3, caution_fejl=3, alle_n=300, alle_fejl=3)
    ud = ge.preflight_gut_gate(task_description="t")
    assert ud["allowed"] is True
    assert ud["evidence"]["reason"] == "for-faa-caution-events"


def test_proceed_rammes_ikke_af_evidens_porten(monkeypatch):
    """Porten gælder KUN caution. Et proceed der afvises af styrke skal afvises som før."""
    monkeypatch.setattr(ge, "_recent_tick_signals", lambda: (0, 0), raising=False)
    monkeypatch.setattr(ge, "derive_gut_signal",
                        lambda **kw: {"hunch": "proceed", "confidence": 0.1,
                                      "confidence_no_bias": 0.1}, raising=False)
    monkeypatch.setattr(ge, "gut_gate", lambda *a, **k: False, raising=False)
    monkeypatch.setattr(ge, "_blok_budget_brugt", lambda: False, raising=False)
    monkeypatch.setattr(ge, "_record_withheld_decision",
                        lambda *a, **k: None, raising=False)
    _stub_evidens(monkeypatch, caution_n=26, caution_fejl=0, alle_n=343, alle_fejl=0)
    ud = ge.preflight_gut_gate(task_description="t")
    assert ud["allowed"] is False, "proceed-stien må ikke ændres af evidens-porten"
    assert "evidence_blocked" not in ud


def test_evidens_kan_ikke_maales_blokerer_ikke(monkeypatch):
    """Kan evidensen ikke måles, må gaten ikke handle — samme fail-open som resten."""
    _tving_caution_afvist(monkeypatch)
    monkeypatch.setattr(ge, "_caution_har_evidens",
                        lambda: {"may_block": False, "reason": "db-fejl"}, raising=False)
    ud = ge.preflight_gut_gate(task_description="t")
    assert ud["allowed"] is True
    assert ud["evidence"]["reason"] == "db-fejl"


def test_interrupted_taelles_ikke_som_fanget_fejl(monkeypatch, tmp_path):
    """Et afbrudt run er ikke et fejlet run.

    Målt 12/11: den ene «fejl» i datasættet var `actual: "interrupted"`. At tælle den
    som en sand advarsel giver maven æren for noget den ikke forudsagde — og ville
    opfinde et signal hvor der er nul fejl at skelne imod.
    """
    import json as _json
    import sqlite3 as _sq

    p = tmp_path / "ev.db"
    conn = _sq.connect(p)
    conn.execute("CREATE TABLE events (kind TEXT, payload_json TEXT)")
    rows = [("caution", "interrupted")] * 30 + [("proceed", "completed")] * 300
    for h, a in rows:
        conn.execute("INSERT INTO events VALUES (?,?)",
                     ("cognitive_gut.outcome_recorded",
                      _json.dumps({"hunch": h, "actual": a})))
    conn.commit()
    conn.close()

    import core.runtime.db as dbmod
    monkeypatch.setattr(dbmod, "connect", lambda *a, **k: _sq.connect(p), raising=False)
    monkeypatch.setattr(ge, "_EVIDENS_CACHE", {"at": 0.0, "value": None}, raising=False)

    ud = ge._caution_har_evidens()
    assert ud["may_block"] is False
    # Beviset: de 30 interrupted-events tælles slet ikke med. Havde de været talt som
    # fejl, ville caution_n være 30 og præcisionen 100 % — og gaten ville blokere på et
    # signal der ikke findes.
    assert ud["caution_n"] == 0, (
        "interrupted må ikke gøre caution-gruppen til en fanget fejl")
    assert ud["reason"] == "for-faa-caution-events"

def test_udfaldsmodellen_er_faelles(monkeypatch, tmp_path):
    """BJØRNS HOVEDPOINTE (12/11-2026): de tre funktioner skal mene det samme.

    Før rettelsen skelnede `_caution_har_evidens` `interrupted` fra, mens
    `record_gut_outcome` og `_observed_baseline` regnede det som fiasko. Samme
    hændelse var neutral for beslutningsporten og en dom for den statistik der
    træner maven — og det er derfor `calibration_score` kunne stå på 0,9925 mens
    maven var dårligere end en konstant.

    Testen rammer alle tre gennem den faktiske `classify_outcome`.
    """
    import json as _json
    import sqlite3 as _sq

    # 1. Klassifikationen selv — ukendt er neutralt, ikke fejl.
    assert ge.classify_outcome("completed") == "success"
    assert ge.classify_outcome("success") == "success"
    assert ge.classify_outcome("failed") == "failure"
    assert ge.classify_outcome("error") == "failure"
    assert ge.classify_outcome("interrupted") == "neutral"
    assert ge.classify_outcome("cancelled") == "neutral"
    assert ge.classify_outcome("blocked") == "neutral"
    assert ge.classify_outcome("noget-ukendt") == "neutral"
    assert ge.classify_outcome(None) == "neutral"

    # 2. record_gut_outcome: neutralt udfald kalibrerer IKKE — men eventet udsendes,
    #    så fladen kan se at hændelsen skete, uden at den læses som en dom.
    kald: list[dict] = []
    udsendt: list[tuple] = []
    monkeypatch.setattr(ge, "update_cognitive_gut_state",
                        lambda **kw: kald.append(kw) or {"ok": True}, raising=False)
    monkeypatch.setattr(ge.event_bus, "publish",
                        lambda *a, **k: udsendt.append(a), raising=False)

    ge.record_gut_outcome(hunch="caution", actual_outcome="interrupted")
    assert kald == [], "et afbrudt run må ikke kalibrere maven"
    assert udsendt[0][1]["correct"] is None
    assert udsendt[0][1]["outcome_class"] == "neutral"

    # ... og en rigtig fejl kalibrerer stadig, som før.
    ge.record_gut_outcome(hunch="caution", actual_outcome="failed")
    assert len(kald) == 1 and kald[0]["prediction_correct"] is True

    # 3. _observed_baseline: samme filtrering — ellers kan fladen og porten svare
    #    forskelligt om det samme event.
    p = tmp_path / "baseline.db"
    conn = _sq.connect(p)
    conn.execute("CREATE TABLE events (kind TEXT, payload_json TEXT)")
    for h, a in [("caution", "interrupted"), ("proceed", "interrupted"),
                 ("proceed", "completed")]:
        conn.execute("INSERT INTO events VALUES (?,?)",
                     ("cognitive_gut.outcome_recorded",
                      _json.dumps({"hunch": h, "actual": a})))
    conn.commit()
    conn.close()
    import core.runtime.db as dbmod
    monkeypatch.setattr(dbmod, "connect", lambda *a, **k: _sq.connect(p), raising=False)
    monkeypatch.setattr(ge, "_BASELINE_CACHE", {"at": 0.0, "value": None},
                        raising=False)
    b = ge._observed_baseline()
    assert b is not None
    assert b["n_observed"] == 1, "kun det afgjorte udfald tæller for fladen"
    assert b["maven_pct"] == 100.0


def test_break_even_reglen_selv_ikke_kun_porten(monkeypatch, tmp_path):
    """Rammer `_caution_har_evidens` DIREKTE — ikke gennem en stub.

    Målt 12/11: de øvrige evidens-tests stubbede målingen væk, så de beviste at PORTEN
    spørger rigtigt, men ikke at REGLEN er rigtig. Satte jeg den gamle 50 %-regel tilbage,
    var alle 63 tests stadig grønne. Denne test læser den faktiske funktion mod en
    faktisk DB, så reglen selv er dækket.

    Den beviser også Bjørns anden indvending: lift alene afgør intet. Samme data kan
    blokere eller ikke alt efter hvad blokeringen koster — det er break-even der styrer.
    """
    import json as _json
    import sqlite3 as _sq

    _kald = [0]

    def _maal(rows):
        _kald[0] += 1
        p = tmp_path / f"ev{_kald[0]}.db"
        conn = _sq.connect(p)
        conn.execute("CREATE TABLE events (kind TEXT, payload_json TEXT)")
        for h, a in rows:
            conn.execute("INSERT INTO events VALUES (?,?)",
                         ("cognitive_gut.outcome_recorded",
                          _json.dumps({"hunch": h, "actual": a})))
        conn.commit()
        conn.close()
        import core.runtime.db as dbmod
        monkeypatch.setattr(dbmod, "connect",
                            lambda *a, **k: _sq.connect(p), raising=False)
        monkeypatch.setattr(ge, "_EVIDENS_CACHE", {"at": 0.0, "value": None},
                            raising=False)
        return ge._caution_har_evidens()

    # 1 fejl af 26 caution (3,85 %) mod 1 fejl af 344 (0,29 %) → lift ~13x.
    rows = ([("caution", "error")] + [("caution", "completed")] * 25
            + [("proceed", "completed")] * 318)

    # Husets default (4:1) → break-even 20 %. 3,85 % er UNDER den grænse.
    ud = _maal(rows)
    assert ud["may_block"] is False, (
        "3,85 % er under break-even 20 % — lift alene maa ikke blokere")
    assert ud["reason"] == "under-break-even"
    assert ud["break_even"] == 0.2
    assert ud["lift"] > 10, "lift rapporteres stadig — den er informativ, ikke beslutningen"

    # Samme data, men nu koster en ufanget fejl 40x → break-even 2,44 % → bloker.
    monkeypatch.setattr(ge, "_omkostnings_ratio", lambda: (1.0, 40.0), raising=False)
    ud = _maal(rows)
    assert ud["may_block"] is True
    assert ud["reason"] == "over-break-even"

    # Ren støj: caution rammer ALDRIG, proceed rammer. Lift = 0 → må ikke blokere.
    ud = _maal([("caution", "completed")] * 25
               + [("proceed", "error")] * 3 + [("proceed", "completed")] * 297)
    assert ud["may_block"] is False
    assert ud["lift"] == 0.0


def test_break_even_findes_kun_naar_der_er_fejl(monkeypatch, tmp_path):
    """VERIFIKATIONS-FAELDEN (12/11-2026, Bjørns indvending).

    Da fixet skulle i drift, planlagde jeg at verificere det ved at lede efter
    `break_even`-feltet i portens svar. Men på et datasæt med NUL fejl returnerer
    `_caution_har_evidens` tidligt med `ingen-fejl-at-skelne` — og `break_even` findes
    slet ikke i svaret. Verifikationen ville altså have dømt en helt korrekt genstart
    som fejlet.

    Det er samme fejlform som resten af aftenen: en test der ikke kan nå den gren den
    skal bevise. Testen her fastlåser HVILKE nøgler der findes i hver gren, så en
    fremtidig verifikation kan vælge den rigtige i stedet for at gætte.
    """
    import json as _json
    import sqlite3 as _sq

    _kald = [0]

    def _maal(rows):
        _kald[0] += 1
        p = tmp_path / f"n{_kald[0]}.db"
        conn = _sq.connect(p)
        conn.execute("CREATE TABLE events (kind TEXT, payload_json TEXT)")
        for h, a in rows:
            conn.execute("INSERT INTO events VALUES (?,?)",
                         ("cognitive_gut.outcome_recorded",
                          _json.dumps({"hunch": h, "actual": a})))
        conn.commit()
        conn.close()
        import core.runtime.db as dbmod
        monkeypatch.setattr(dbmod, "connect",
                            lambda *a, **k: _sq.connect(p), raising=False)
        monkeypatch.setattr(ge, "_EVIDENS_CACHE", {"at": 0.0, "value": None},
                            raising=False)
        return ge._caution_har_evidens()

    # Nul fejl — den gren produktionen faktisk står i.
    ud = _maal([("caution", "completed")] * 25 + [("proceed", "completed")] * 318)
    assert ud["reason"] == "ingen-fejl-at-skelne"
    assert "break_even" not in ud, (
        "break_even findes IKKE uden fejl — en verifikation der leder efter det "
        "doemmer en korrekt koersel som fejlet")
    assert set(ud.keys()) == {"may_block", "reason", "caution_n", "alle_n"}, (
        "nøglesættet i denne gren skal være fastlåst, så verifikationen kan vælge rigtigt")

    # Med fejl findes break_even — det er den anden gren, og den kræver fejl > 0.
    ud = _maal([("caution", "error")] + [("caution", "completed")] * 25
               + [("proceed", "completed")] * 318)
    assert ud["reason"] == "under-break-even"
    assert "break_even" in ud
