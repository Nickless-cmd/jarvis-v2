"""Tests for §4 cluster-arbitrage (central_arbitration) + §8 demokrati-invariant.

Verificerer at SECURITY-RED er absolut, at ties brydes af deklareret cluster-prioritet, at
et fejlende COGNITIVE-cluster (SKIP) aldrig blokerer, og at Verdict bærer cluster.
"""
from __future__ import annotations

from core.services.central_arbitration import arbitrate, explain
from core.services.central_catalog import cluster_rank, CLUSTER_PRIORITY
from core.services.gate_kernel import Decision, GateClass, Verdict


def _v(cluster, decision, klass=GateClass.COGNITIVE):
    return Verdict("g", decision, "", klass=klass, cluster=cluster)


# ── cluster_rank / prioritet ──────────────────────────────────────────────
def test_security_clusters_outrank_cognitive():
    assert cluster_rank("auth") < cluster_rank("loop")
    assert cluster_rank("privacy") < cluster_rank("tools")
    assert cluster_rank("execution") < cluster_rank("system")


def test_unknown_cluster_lowest_priority():
    assert cluster_rank("nonexistent") > cluster_rank(CLUSTER_PRIORITY[-1])


# ── arbitrate ─────────────────────────────────────────────────────────────
def test_security_red_is_absolute():
    # auth RED kan ALDRIG overrules af et kognitivt GREEN
    win = arbitrate([_v("proactivity", Decision.GREEN),
                     _v("auth", Decision.RED, GateClass.SECURITY)])
    assert win.decision is Decision.RED and win.cluster == "auth"


def test_worst_decision_wins_among_cognitive():
    win = arbitrate([_v("loop", Decision.GREEN), _v("truth", Decision.RED),
                     _v("tools", Decision.YELLOW)])
    assert win.decision is Decision.RED and win.cluster == "truth"


def test_ties_broken_by_cluster_priority():
    # to YELLOW fra forskellige clusters → højest prioritet (lavest rank) vinder
    win = arbitrate([_v("tools", Decision.YELLOW), _v("commit", Decision.YELLOW)])
    assert win.cluster == "commit"  # commit > tools i prioritet


def test_empty_verdicts_green():
    assert arbitrate([]).decision is Decision.GREEN


def test_two_security_reds_highest_priority_wins():
    win = arbitrate([_v("skill", Decision.RED, GateClass.SECURITY),
                     _v("auth", Decision.RED, GateClass.SECURITY)])
    assert win.cluster == "auth"  # auth > skill


# ── §8 demokrati: fejlende COGNITIVE (SKIP) blokerer aldrig ───────────────
def test_cognitive_skip_never_blocks():
    # et crashed cognitive (SKIP) + et security GREEN → GREEN vinder (intet block)
    win = arbitrate([_v("loop", Decision.SKIP), _v("auth", Decision.GREEN, GateClass.SECURITY)])
    assert win.decision is not Decision.RED


def test_fail_verdict_cognitive_is_skip_not_red():
    from core.services.central_core import Central
    from core.services.central_trace import TraceSink
    from core.services.central_switches import CircuitBreaker
    c = Central(sink=TraceSink(), breaker=CircuitBreaker(), emit=lambda *a: None)
    # en kognitiv nerve der KASTER → SKIP (aldrig RED)
    v = c.decide("x", {"run_id": "d"}, lambda ctx: (_ for _ in ()).throw(RuntimeError("boom")),
                 cluster="loop", klass=GateClass.COGNITIVE)
    assert v.decision is Decision.SKIP


# ── Verdict bærer cluster ─────────────────────────────────────────────────
def test_decide_sets_cluster_on_verdict():
    from core.services.central_core import Central
    from core.services.central_trace import TraceSink
    from core.services.central_switches import CircuitBreaker
    c = Central(sink=TraceSink(), breaker=CircuitBreaker(), emit=lambda *a: None)
    v = c.decide("x", {"run_id": "d"}, lambda ctx: None, cluster="truth",
                 klass=GateClass.COGNITIVE)
    assert v.cluster == "truth"


def test_explain_returns_winner_and_considered():
    e = explain([_v("loop", Decision.GREEN), _v("auth", Decision.RED, GateClass.SECURITY)])
    assert e["winner"]["cluster"] == "auth"
    assert len(e["considered"]) == 2


# ── §11 Trin 1: observe_shadow (0-risiko måling, egress-frit) ──────────────
def test_observe_shadow_agrees_when_arbitration_matches_enforced(monkeypatch):
    import core.services.central_arbitration as ca
    captured = {}
    monkeypatch.setattr("core.services.central_private_observe.record_private",
                        lambda cluster, nerve, **kw: captured.update({"nerve": nerve, **kw}) or True)
    ca.observe_shadow([_v("commit", Decision.RED), _v("commit", Decision.GREEN)],
                      enforced_blocked=True, where="pre_exec")
    assert captured["nerve"] == "arbitration_shadow"
    assert captured["meta"]["agree"] is True
    assert captured["meta"]["arbitrated"] == Decision.RED.value


def test_observe_shadow_flags_divergence(monkeypatch):
    import core.services.central_arbitration as ca
    captured = {}
    monkeypatch.setattr("core.services.central_private_observe.record_private",
                        lambda cluster, nerve, **kw: captured.update({**kw}) or True)
    ca.observe_shadow([_v("commit", Decision.GREEN)], enforced_blocked=True)
    assert captured["meta"]["agree"] is False
    assert captured["value"] == 0.0


def test_observe_shadow_self_safe_on_empty_and_none():
    from core.services.central_arbitration import observe_shadow
    observe_shadow([], enforced_blocked=False)
    observe_shadow([None, None], enforced_blocked=True)  # ingen fejl
