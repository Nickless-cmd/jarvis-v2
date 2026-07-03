"""Hermetiske tests for gut_engine — særligt gut_gate (den nye, ægte forbruger af
adjusted_confidence). Ingen DB / eventbus: kv og record_private monkeypatches.
"""
import core.services.gut_engine as ge


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
