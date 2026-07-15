"""C2 — signal-delta trigger tests (the economic-proof tests).

The trigger REPLACES a blind 30-min timer. These tests prove it fires on real
change but refuses to out-burn the timer: no fire on noise, no flapping, a
durable global cooldown, and cold-start suppression. `evaluate` must be pure
(never touch an LLM/provider).

`signal_baseline` (C1, parallel) and `db_core.get/set_runtime_state_value` are
MOCKED here per the task contract.
"""
from __future__ import annotations

import sys
import types

import pytest


# --------------------------------------------------------------------------- #
# Fixtures: fake baseline module + dict-backed durable runtime-state.
# --------------------------------------------------------------------------- #
@pytest.fixture()
def fake_baseline(monkeypatch):
    """Inject a controllable fake `core.services.signal_baseline`."""
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


@pytest.fixture()
def runtime_state(monkeypatch, isolated_runtime):
    """Durable dict-backed runtime-state (proves cooldown survives 'restart')."""
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
def trigger(fake_baseline, runtime_state):
    import importlib

    mod = importlib.import_module("core.services.signal_delta_trigger")
    return mod


def _set_cfg(store, **kw):
    for k, v in kw.items():
        store[f"signal_delta_trigger:{k}"] = v


# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #
def test_fires_on_real_rise(trigger, fake_baseline):
    fake_baseline._store["cpu"] = 0.20
    decision = trigger.evaluate({"cpu": 0.55})
    assert decision is not None
    assert decision["crossed"] == ["cpu"]
    assert "cpu" in decision["movements"]
    assert decision["movements"]["cpu"] == pytest.approx(0.35)
    assert isinstance(decision["reason"], str) and decision["reason"]


def test_flat_does_not_fire(trigger, fake_baseline):
    fake_baseline._store["cpu"] = 0.50
    assert trigger.evaluate({"cpu": 0.50}) is None

    # Purity: the module must never reference an LLM/provider facade.
    import inspect

    src = inspect.getsource(trigger).lower()
    for forbidden in (
        "call_llm",
        "provider_router",
        "visible_model",
        "cheap_provider",
        "openai",
        "anthropic",
        "complete_chat",
        "chat_completion",
    ):
        assert forbidden not in src, f"impure: found {forbidden!r}"


def test_hysteresis_no_reflap(trigger, fake_baseline, runtime_state):
    # Disable cooldown so we isolate hysteresis; keep values below theta_abs.
    _set_cfg(runtime_state, cooldown_s=0)
    fake_baseline._store["q"] = 0.20

    # 1) big rise → fires; baseline moves to 0.55, signal is now "hot".
    assert trigger.evaluate({"q": 0.55}) is not None
    # 2) still far from baseline (delta 0.25 > theta_low 0.15) → suppressed.
    assert trigger.evaluate({"q": 0.80}) is None
    # 3) settle within theta_low of baseline (delta 0.05) → clears hot, no fire.
    assert trigger.evaluate({"q": 0.60}) is None
    # 4) now a fresh large excursion is allowed to fire again.
    assert trigger.evaluate({"q": 0.20}) is not None


def test_cooldown_blocks_second(trigger, fake_baseline, runtime_state):
    # Default cooldown (1200s) active. Two DIFFERENT qualifying signals so
    # hysteresis cannot be the reason the second is blocked — only the global
    # durable cooldown can.
    fake_baseline._store["a"] = 0.20
    fake_baseline._store["b"] = 0.20

    assert trigger.evaluate({"a": 0.55}) is not None
    assert trigger.evaluate({"b": 0.55}) is None
    # cooldown timestamp is durable (written through db_core mock).
    assert "signal_delta_trigger:last_dispatch_ts" in runtime_state


def test_absolute_floor_fires_on_high_value(trigger, fake_baseline):
    # Tiny delta (0.02 << theta_high 0.30) but absolute value >= theta_abs 0.85.
    fake_baseline._store["load"] = 0.84
    decision = trigger.evaluate({"load": 0.86})
    assert decision is not None
    assert "load" in decision["crossed"]


def test_cold_start_establishes_and_suppresses(trigger, fake_baseline):
    fake_baseline._cold = True
    assert trigger.evaluate({"a": 0.10, "b": 0.90, "c": 0.50}) is None
    # baselines established for every signal on first sight.
    assert fake_baseline._store == {"a": 0.10, "b": 0.90, "c": 0.50}


def test_composite_coalesce(trigger, fake_baseline, runtime_state):
    _set_cfg(runtime_state, cooldown_s=0)
    fake_baseline._store["x"] = 0.20
    fake_baseline._store["y"] = 0.20

    decision = trigger.evaluate({"x": 0.60, "y": 0.70})
    # ONE decision carrying BOTH signals — never one-per-signal.
    assert decision is not None
    assert sorted(decision["crossed"]) == ["x", "y"]
    assert set(decision["movements"]) == {"x", "y"}


# --------------------------------------------------------------------------- #
# Bilag 2 — scope-aware evaluate ("one self, many projections")
# --------------------------------------------------------------------------- #
@pytest.fixture()
def scoped_baseline(monkeypatch):
    """Scope-aware fake `signal_baseline` with a per-scope store."""
    ns = types.ModuleType("core.services.signal_baseline")
    ns._stores = {None: {}}  # scope -> {signal: value}
    ns._cold = {}  # scope -> bool

    def _store(scope):
        return ns._stores.setdefault(scope, {})

    def get_baseline(signal, scope=None):
        return _store(scope).get(str(signal))

    def set_baseline(signal, value, scope=None):
        _store(scope)[str(signal)] = float(value)

    def is_cold_start(min_signals: int = 3, scope=None):
        return bool(ns._cold.get(scope, False))

    ns.get_baseline = get_baseline
    ns.set_baseline = set_baseline
    ns.is_cold_start = is_cold_start

    monkeypatch.setitem(sys.modules, "core.services.signal_baseline", ns)
    import core.services as _svc

    monkeypatch.setattr(_svc, "signal_baseline", ns, raising=False)
    return ns


@pytest.fixture()
def scoped_trigger(scoped_baseline, runtime_state):
    import importlib

    mod = importlib.import_module("core.services.signal_delta_trigger")
    return mod


def test_scope_none_is_the_global_default(scoped_trigger, scoped_baseline):
    """(1) The default (scope=None) path is unchanged and carries no scope tag."""
    scoped_baseline._stores[None]["cpu"] = 0.20
    decision = scoped_trigger.evaluate({"cpu": 0.55})
    assert decision is not None
    assert decision["crossed"] == ["cpu"]
    assert "scope" not in decision


def test_scoped_fires_against_own_baseline_and_tags_scope(
    scoped_trigger, scoped_baseline
):
    """(2) A scope evaluates against its OWN baseline and tags the decision."""
    scoped_baseline._stores["userA"] = {"tension": 0.20}
    decision = scoped_trigger.evaluate({"tension": 0.60}, scope="userA")
    assert decision is not None
    assert decision["crossed"] == ["tension"]
    assert decision["scope"] == "userA"


def test_user_scoped_delta_does_not_leak_to_other_scope(
    scoped_trigger, scoped_baseline, runtime_state
):
    """(3) A per-user delta fires in its room without touching another scope."""
    scoped_baseline._stores["userA"] = {"tension": 0.20}
    scoped_baseline._stores["userB"] = {"tension": 0.20}
    scoped_baseline._stores[None] = {"tension": 0.20}

    fired = scoped_trigger.evaluate({"tension": 0.70}, scope="userA")
    assert fired is not None and fired["scope"] == "userA"

    # userB's and the global baseline are untouched by userA's fire.
    assert scoped_baseline._stores["userB"]["tension"] == 0.20
    assert scoped_baseline._stores[None]["tension"] == 0.20
    # Durable hot/cooldown are namespaced to userA only.
    assert "signal_delta_trigger:last_dispatch_ts:userA" in runtime_state
    assert "signal_delta_trigger:last_dispatch_ts" not in runtime_state
    assert "signal_delta_trigger:last_dispatch_ts:userB" not in runtime_state


def test_cooldown_is_per_scope_no_cross_block(
    scoped_trigger, scoped_baseline, runtime_state
):
    """A global (or userA) dispatch's cooldown never gates another scope."""
    # Default cooldown (1200s) is active after the first fire.
    scoped_baseline._stores[None] = {"s": 0.20}
    scoped_baseline._stores["userA"] = {"s": 0.20}

    assert scoped_trigger.evaluate({"s": 0.60}) is not None  # global fires
    # global is now in cooldown, but userA has its OWN cooldown → still fires.
    scoped = scoped_trigger.evaluate({"s": 0.60}, scope="userA")
    assert scoped is not None and scoped["scope"] == "userA"
    # a second global fire IS blocked by the global cooldown (proves it is real).
    scoped_baseline._stores[None]["s"] = 0.20
    assert scoped_trigger.evaluate({"s": 0.61}) is None
