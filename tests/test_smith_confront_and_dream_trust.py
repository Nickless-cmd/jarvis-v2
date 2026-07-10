from __future__ import annotations

import core.services.central_agent_smith as smith
import core.services.central_agent_smith_escalation as esc
import core.services.central_adaptation as adapt


# ── Agent Smith Trin 3 (real-time konfront via standing-order) ──────────────
def test_arm_confront_shadow_registers_nothing(monkeypatch):
    # Default shadow (gate_enforce.agent_smith OFF) → ingen standing-order registreres
    monkeypatch.setattr(smith, "_agent_smith_enforced", lambda: False)
    called = {}
    monkeypatch.setattr("core.services.standing_orders_registry.add_standing_order",
                        lambda **k: called.setdefault("hit", True) or 99)
    oid = smith._execute_arm_confront("phrase:vil du have", "vil du have")
    assert oid is None and "hit" not in called


def test_arm_confront_enforced_registers_standing_order(monkeypatch):
    monkeypatch.setattr(smith, "_agent_smith_enforced", lambda: True)
    captured = {}
    def fake_add(**kw):
        captured.update(kw)
        return 42
    monkeypatch.setattr("core.services.standing_orders_registry.add_standing_order", fake_add)
    oid = smith._execute_arm_confront("phrase:vil du have", "vil du have")
    assert oid == 42
    assert captured["match_key"] == "vil du have"
    assert "vil du have" in captured["text"]


def test_resolve_deactivates_standing_order():
    # Et resolved mønster med en armeret standing-order → deactivate_order-action
    state = {"patterns": {"phrase:x": {"kind": "phrase", "label": "x", "rung": 3,
                                       "baseline": 5, "last_metric": 5, "cycles_at_rung": 0,
                                       "decision_id": "dec_1", "standing_order_id": 7,
                                       "first_seen": "t0", "history": []}},
             "resolved": []}
    _, actions = esc.step_escalation(state, {}, "t1")  # mønster forsvandt → resolve
    kinds = [(a["type"], a.get("order_id")) for a in actions if a["type"] == "deactivate_order"]
    assert ("deactivate_order", 7) in kinds


def test_agent_smith_default_shadow():
    assert smith._agent_smith_enforced() is False  # default OFF


# ── dream_trust-forbruger ───────────────────────────────────────────────────
def test_dream_trust_factor_neutral_in_shadow(monkeypatch):
    monkeypatch.setattr(adapt, "is_live_enabled", lambda cls=None: False)  # shadow
    assert adapt.effective_dream_trust_factor() == 1.0


def test_dream_trust_factor_scales_when_live(monkeypatch):
    monkeypatch.setattr(adapt, "is_live_enabled", lambda cls=None: True)
    monkeypatch.setattr(adapt, "get_bias", lambda cls=None: 0.2)  # positiv track-record
    assert adapt.effective_dream_trust_factor() == 1.2
    monkeypatch.setattr(adapt, "get_bias", lambda cls=None: -0.3)  # modsagte drømme
    assert adapt.effective_dream_trust_factor() == 0.7


def test_dream_trust_factor_clamped(monkeypatch):
    monkeypatch.setattr(adapt, "is_live_enabled", lambda cls=None: True)
    monkeypatch.setattr(adapt, "get_bias", lambda cls=None: 5.0)  # ekstrem → clamp 1.5
    assert adapt.effective_dream_trust_factor() == 1.5
