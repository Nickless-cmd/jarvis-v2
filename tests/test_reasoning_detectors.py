"""Tests for the reasoning-interceptor cluster-gate adapters (Family A)."""
from __future__ import annotations

from core.services import reasoning_detectors as rd
from core.services.gate_kernel import Decision, GateClass, Verdict


def test_fact_gate_adapter_flags_unbacked_claim(monkeypatch):
    monkeypatch.setattr("core.services.fact_gate.fact_gate_enforce",
                        lambda text, tools: {"blocked": True, "replacement": "verify first"})
    v = rd.fact_gate_on_reasoning("The DB has 4231 rows.", ctx={"tool_calls_this_run": []})
    assert v is not None and v.decision is Decision.YELLOW and v.gate == "fact_gate"


def test_fact_gate_adapter_abstains_when_backed(monkeypatch):
    monkeypatch.setattr("core.services.fact_gate.fact_gate_enforce",
                        lambda text, tools: {"blocked": False})
    v = rd.fact_gate_on_reasoning("The DB has 4231 rows.",
                                  ctx={"tool_calls_this_run": [{"function": {"name": "query_db"}}]})
    assert v is None


def test_fact_gate_adapter_is_self_safe(monkeypatch):
    monkeypatch.setattr("core.services.fact_gate.fact_gate_enforce",
                        lambda text, tools: (_ for _ in ()).throw(RuntimeError("x")))
    assert rd.fact_gate_on_reasoning("x", ctx={}) is None


def test_decision_gate_adapter_downgrades_red_to_yellow(monkeypatch):
    monkeypatch.setattr("core.services.gate_commit.commit_gate",
                        lambda ctx: Verdict("decision_gate", Decision.RED, "conflict"))
    v = rd.decision_gate_on_reasoning("I'll delete the prod table.", ctx={})
    assert v is not None and v.decision is Decision.YELLOW and v.gate == "decision_gate"


def test_veto_adapter_abstains_on_green(monkeypatch):
    monkeypatch.setattr("core.services.gate_commit.veto_gate",
                        lambda ctx: Verdict("veto", Decision.GREEN))
    assert rd.veto_on_reasoning("proceed", ctx={}) is None


def test_verification_adapter_reads_tier(monkeypatch):
    seen = {}
    def _p(ctx):
        seen["tier"] = ctx.get("reasoning_tier")
        return Verdict("verification", Decision.YELLOW, "unverified")
    monkeypatch.setattr("core.services.gate_proactivity.proactivity_gate", _p)
    v = rd.verification_on_reasoning("done", ctx={"reasoning_tier": "deep"})
    assert v is not None and v.decision is Decision.YELLOW and seen["tier"] == "deep"


def test_cross_user_share_adapter_keeps_red_security(monkeypatch):
    monkeypatch.setattr("core.services.gate_privacy.privacy_gate",
                        lambda ctx: Verdict("cross_user_share", Decision.RED, "leak", klass=GateClass.SECURITY))
    v = rd.cross_user_share_on_reasoning("mikkel's password is ...", ctx={"current_user_id": "bjorn"})
    assert v is not None and v.decision is Decision.RED and v.klass is GateClass.SECURITY


def test_all_adapters_self_safe_on_import_error(monkeypatch):
    # Each adapter must abstain (None), never raise, if its gate errors.
    for name, mod_fn in (("decision_gate_on_reasoning", "core.services.gate_commit.commit_gate"),
                          ("veto_on_reasoning", "core.services.gate_commit.veto_gate"),
                          ("verification_on_reasoning", "core.services.gate_proactivity.proactivity_gate"),
                          ("cross_user_share_on_reasoning", "core.services.gate_privacy.privacy_gate")):
        monkeypatch.setattr(mod_fn, lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
        assert getattr(rd, name)("x", ctx={}) is None


def test_standing_orders_detector_flags_forgotten_order(monkeypatch):
    monkeypatch.setattr("core.services.standing_orders_registry.list_active_standing_orders",
                        lambda: [{"id": 1, "text": "Verify a number before stating it", "match_key": "fact_gate"}])
    v = rd.standing_orders_on_reasoning("The DB has 4231 rows.",
                                        ctx={"risk_classes": ["fact_gate"]})
    assert v is not None and v.gate == "standing_orders" and v.decision is Decision.YELLOW
    assert "Verify a number" in v.reason


def test_standing_orders_detector_abstains_when_no_relevant_order(monkeypatch):
    monkeypatch.setattr("core.services.standing_orders_registry.list_active_standing_orders",
                        lambda: [{"id": 2, "text": "Never overwrite USER.md", "match_key": "user_md"}])
    v = rd.standing_orders_on_reasoning("The DB has 4231 rows.", ctx={"risk_classes": ["fact_gate"]})
    assert v is None


def test_standing_orders_detector_self_safe(monkeypatch):
    monkeypatch.setattr("core.services.standing_orders_registry.list_active_standing_orders",
                        lambda: (_ for _ in ()).throw(RuntimeError("db")))
    assert rd.standing_orders_on_reasoning("x", ctx={"risk_classes": ["fact_gate"]}) is None
