"""Tests for core.services.central_absorb.

The `absorb` helper is the shared "full treatment" pattern: every MC-category
wiring calls it so a producer-service value becomes a LIVING central nerve
(trace via central().observe + conditional flag/notification + learning hook),
not a dead observe. It must NEVER raise.
"""
from __future__ import annotations


def test_absorb_observes_and_flags(monkeypatch):
    import core.services.central_absorb as a
    seen = {"obs": [], "pub": []}
    monkeypatch.setattr(
        "core.services.central_core.central",
        lambda: type("C", (), {"observe": lambda self, e: seen["obs"].append(e)})(),
    )
    monkeypatch.setattr(
        "core.eventbus.bus.event_bus.publish",
        lambda k, p=None, **kw: seen["pub"].append((k, p)),
    )
    a.absorb("cost", "daily", {"usd": 25.4}, flag_if=lambda v: v["usd"] > 10, flag_reason="høj")
    assert seen["obs"] and seen["obs"][0]["cluster"] == "cost"
    assert any(k.endswith(".flag") for k, _ in seen["pub"])


def test_absorb_no_flag_does_not_publish_flag(monkeypatch):
    import core.services.central_absorb as a
    seen = {"obs": [], "pub": []}
    monkeypatch.setattr(
        "core.services.central_core.central",
        lambda: type("C", (), {"observe": lambda self, e: seen["obs"].append(e)})(),
    )
    monkeypatch.setattr(
        "core.eventbus.bus.event_bus.publish",
        lambda k, p=None, **kw: seen["pub"].append((k, p)),
    )
    # flag_if returns falsy → no flag event, but observe still happens.
    a.absorb("cost", "daily", {"usd": 5.0}, flag_if=lambda v: v["usd"] > 10, flag_reason="høj")
    assert seen["obs"] and seen["obs"][0]["cluster"] == "cost"
    assert not any(k.endswith(".flag") for k, _ in seen["pub"])


def test_absorb_no_flag_if_never_flags(monkeypatch):
    import core.services.central_absorb as a
    seen = {"obs": [], "pub": []}
    monkeypatch.setattr(
        "core.services.central_core.central",
        lambda: type("C", (), {"observe": lambda self, e: seen["obs"].append(e)})(),
    )
    monkeypatch.setattr(
        "core.eventbus.bus.event_bus.publish",
        lambda k, p=None, **kw: seen["pub"].append((k, p)),
    )
    a.absorb("cost", "daily", {"usd": 25.4})
    assert seen["obs"]
    assert not any(k.endswith(".flag") for k, _ in seen["pub"])


def test_absorb_learn_key_publishes_learn(monkeypatch):
    import core.services.central_absorb as a
    seen = {"obs": [], "pub": []}
    monkeypatch.setattr(
        "core.services.central_core.central",
        lambda: type("C", (), {"observe": lambda self, e: seen["obs"].append(e)})(),
    )
    monkeypatch.setattr(
        "core.eventbus.bus.event_bus.publish",
        lambda k, p=None, **kw: seen["pub"].append((k, p)),
    )
    a.absorb("cost", "daily", {"usd": 25.4}, learn_key="cost.daily")
    learn = [(k, p) for k, p in seen["pub"] if k == "central.learn"]
    assert learn and learn[0][1]["key"] == "cost.daily"


def test_absorb_never_raises_when_central_throws(monkeypatch):
    import core.services.central_absorb as a

    def _boom():
        raise RuntimeError("central down")

    monkeypatch.setattr("core.services.central_core.central", _boom)
    # publish also blows up to prove full self-safety.
    monkeypatch.setattr(
        "core.eventbus.bus.event_bus.publish",
        lambda k, p=None, **kw: (_ for _ in ()).throw(RuntimeError("bus down")),
    )
    # Must NOT raise; returns None.
    assert a.absorb("cost", "daily", {"usd": 25.4}, flag_if=lambda v: True,
                    flag_reason="x", learn_key="k") is None
