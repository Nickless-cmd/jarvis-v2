"""Hermetiske tests for gut_engine — særligt gut_gate (den nye, ægte forbruger af
adjusted_confidence). Ingen DB / eventbus: kv og record_private monkeypatches.
"""
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
                        lambda *, task_description: {"hunch": "proceed", "confidence": 0.1},
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
    assert surf["blokeret"] == 3
    assert surf["backstop_overkoersler"] == 2
