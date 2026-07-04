"""Tests for HEALER-REGISTRET (Canonical Error System, Fase 1).

Sikkerheds-fokus: destruktive healers SKAL være shadow (flag off) → ingen systemctl.
Løkke-værn: max_attempts → ESCALATE; cooldown undertrykker. Delegated → intet centralt.
Self-safe: en brudt healer → UNKNOWN, aldrig raise.
"""
from __future__ import annotations

import pytest

import core.services.error_healers as eh
from core.services.error_healers import (
    CircuitResetHealer, DaemonRestartHealer, DelegatedHealer, ErrorHealer,
    HealingOutcome, HealingResult, heal_error, register_healer)
from core.services.gate_kernel import Decision, GateClass, Verdict


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    """Frisk bogholderi + defaults pr. test; alle flag default OFF; observe/incident no-op."""
    eh._reset_for_tests()
    # flag-læsning: default det _flag_on-kalderen beder om (dvs. respektér `default=`)
    _flags: dict[str, bool] = {}
    monkeypatch.setattr(eh, "_flag_on",
                        lambda name, default=False: _flags.get(name, default))
    # gør durability + observe til no-ops så tests ikke rører DB/central
    monkeypatch.setattr(eh, "_observe_heal", lambda *a, **k: None)
    monkeypatch.setattr(eh, "_resolve_incident_for", lambda *a, **k: None)
    monkeypatch.setattr(eh, "_escalate_incident_for", lambda *a, **k: None)
    return _flags


def _enable_registry(flags):
    flags[eh._GLOBAL_FLAG] = True


# ── CircuitResetHealer: LIVE, nulstiller breaker ────────────────────────────
def test_circuit_reset_healer_resets_breaker(monkeypatch, _clean):
    _enable_registry(_clean)
    reset_calls: list[str] = []

    class _FakeBreaker:
        def reset(self, nerve): reset_calls.append(nerve)
        def is_open(self, nerve): return False

    class _FakeCentral:
        _breaker = _FakeBreaker()

    monkeypatch.setattr("core.services.central_core.central", lambda: _FakeCentral())
    res = heal_error("central.circuit_open", origin="some_nerve")
    assert res.outcome is HealingOutcome.SUCCESS
    assert reset_calls == ["some_nerve"]


def test_circuit_reset_retry_if_still_open(monkeypatch, _clean):
    _enable_registry(_clean)

    class _FakeBreaker:
        def reset(self, nerve): pass
        def is_open(self, nerve): return True    # stadig åben efter reset

    class _FakeCentral:
        _breaker = _FakeBreaker()

    monkeypatch.setattr("core.services.central_core.central", lambda: _FakeCentral())
    res = heal_error("central.circuit_open", origin="stuck")
    assert res.outcome is HealingOutcome.RETRY


# ── DaemonRestartHealer: SHADOW-FIRST (flag off) → ingen systemctl ──────────
def test_daemon_restart_is_shadow_when_flag_off(monkeypatch, _clean):
    _enable_registry(_clean)              # registret ON, men daemon live-flag OFF
    called = {"popen": False}
    import subprocess
    monkeypatch.setattr(subprocess, "Popen",
                        lambda *a, **k: called.__setitem__("popen", True))
    res = heal_error("central.daemon_dead", origin="jarvis-runtime")
    assert res.outcome is HealingOutcome.SHADOW
    assert called["popen"] is False                        # INTET systemctl
    assert "systemctl restart jarvis-runtime" in res.plan  # planen ER beregnet


def test_daemon_restart_shadow_even_if_flag_on_but_gate_red(monkeypatch, _clean):
    _enable_registry(_clean)
    _clean[eh._DAEMON_LIVE_FLAG] = True    # live-flag ON …
    called = {"popen": False}
    import subprocess
    monkeypatch.setattr(subprocess, "Popen",
                        lambda *a, **k: called.__setitem__("popen", True))

    # … men SECURITY-gate returnerer RED → fail-closed, forbliv i skygge
    class _FakeCentral:
        def decide(self, nerve, ctx, fn, *, cluster="", klass=GateClass.COGNITIVE):
            return Verdict(nerve, Decision.RED, "denied", klass=klass)

    monkeypatch.setattr("core.services.central_core.central", lambda: _FakeCentral())
    res = heal_error("central.daemon_dead", origin="jarvis-runtime")
    assert res.outcome is HealingOutcome.SHADOW
    assert called["popen"] is False


def test_daemon_restart_executes_when_flag_on_and_gate_green(monkeypatch, _clean):
    _enable_registry(_clean)
    _clean[eh._DAEMON_LIVE_FLAG] = True
    called = {"cmd": None}
    import subprocess
    monkeypatch.setattr(subprocess, "Popen",
                        lambda *a, **k: called.__setitem__("cmd", a[0]))

    class _FakeCentral:
        def decide(self, nerve, ctx, fn, *, cluster="", klass=GateClass.COGNITIVE):
            assert klass is GateClass.SECURITY      # MÅ være security-gatet
            return Verdict(nerve, Decision.GREEN, "ok", klass=klass)

    monkeypatch.setattr("core.services.central_core.central", lambda: _FakeCentral())
    res = heal_error("central.daemon_dead", origin="jarvis-api")
    assert res.outcome is HealingOutcome.SUCCESS
    assert called["cmd"] is not None
    assert "sudo systemctl restart jarvis-api" in " ".join(called["cmd"])


def test_daemon_restart_rejects_unknown_unit(monkeypatch, _clean):
    _enable_registry(_clean)
    _clean[eh._DAEMON_LIVE_FLAG] = True
    res = heal_error("central.daemon_dead", origin="not-a-jarvis-unit")
    assert res.outcome is HealingOutcome.ESCALATE
    assert res.detail == "unknown_or_disallowed_unit"


# ── Løkke-værn: max_attempts → ESCALATE; cooldown undertrykker ─────────────
def test_max_attempts_escalates(monkeypatch, _clean):
    _enable_registry(_clean)

    class _Broken(ErrorHealer):
        kind = "test.always_retry"
        max_attempts = 2
        cooldown_seconds = 0
        def _do_heal(self, ctx): return HealingResult(HealingOutcome.RETRY, detail="nope")

    register_healer(_Broken())
    assert heal_error("test.always_retry", origin="x").outcome is HealingOutcome.RETRY   # 1
    assert heal_error("test.always_retry", origin="x").outcome is HealingOutcome.RETRY   # 2
    esc = heal_error("test.always_retry", origin="x")                                    # 3 → cap
    assert esc.outcome is HealingOutcome.ESCALATE
    assert esc.detail == "max_attempts"


def test_cooldown_suppresses(monkeypatch, _clean):
    _enable_registry(_clean)
    calls = {"n": 0}

    class _Counting(ErrorHealer):
        kind = "test.cooldown"
        max_attempts = 10
        cooldown_seconds = 999
        def _do_heal(self, ctx):
            calls["n"] += 1
            return HealingResult(HealingOutcome.RETRY)

    register_healer(_Counting())
    first = heal_error("test.cooldown", origin="y")
    assert first.outcome is HealingOutcome.RETRY
    assert calls["n"] == 1
    second = heal_error("test.cooldown", origin="y")     # inden for cooldown
    assert second.outcome is HealingOutcome.SHADOW
    assert second.detail == "cooldown"
    assert calls["n"] == 1                                # _do_heal blev IKKE kaldt igen


# ── DelegatedHealer: intet centralt, "handled in-band" ─────────────────────
def test_delegated_healer_does_nothing_central(monkeypatch, _clean):
    _enable_registry(_clean)
    for kind in ("provider.unavailable", "model.rate_limited",
                 "network.timeout", "tool.timeout"):
        res = heal_error(kind, origin="visible_runs")
        assert res.outcome is HealingOutcome.RETRY
        assert res.detail == "handled_in_band"


# ── Registry-opslag: ukendt kind → UNKNOWN ─────────────────────────────────
def test_unknown_kind_returns_unknown(monkeypatch, _clean):
    _enable_registry(_clean)
    res = heal_error("totally.unknown.kind", origin="z")
    assert res.outcome is HealingOutcome.UNKNOWN
    assert res.detail == "no_healer_for_kind"


# ── Global flag OFF (default) → SHADOW, intet kørt ─────────────────────────
def test_global_flag_off_shadows_everything(monkeypatch, _clean):
    # registret IKKE tændt → selv en LIVE-sikker healer shadow'es
    reset_calls: list[str] = []

    class _FakeBreaker:
        def reset(self, nerve): reset_calls.append(nerve)
        def is_open(self, nerve): return False

    monkeypatch.setattr("core.services.central_core.central",
                        lambda: type("C", (), {"_breaker": _FakeBreaker()})())
    res = heal_error("central.circuit_open", origin="n")
    assert res.outcome is HealingOutcome.SHADOW
    assert res.detail == "registry_disabled"
    assert reset_calls == []                              # intet kørt


# ── Self-safe: en healer der kaster → UNKNOWN, aldrig raise ─────────────────
def test_broken_healer_never_raises(monkeypatch, _clean):
    _enable_registry(_clean)

    class _Exploding(ErrorHealer):
        kind = "test.boom"
        cooldown_seconds = 0
        def _do_heal(self, ctx): raise RuntimeError("kaboom")

    register_healer(_Exploding())
    res = heal_error("test.boom", origin="x")            # må IKKE raise
    assert res.outcome is HealingOutcome.UNKNOWN
    assert "healer_error" in res.detail


# ── MC-overflade er self-safe og beskriver mode ────────────────────────────
def test_build_healer_surface(monkeypatch, _clean):
    surface = eh.build_healer_surface()
    assert "healers" in surface
    kinds = {h["kind"]: h for h in surface["healers"]}
    assert kinds["central.circuit_open"]["mode"] == "LIVE"
    assert kinds["central.daemon_dead"]["mode"] == "SHADOW-FIRST"
    assert kinds["central.daemon_dead"]["destructive"] is True
