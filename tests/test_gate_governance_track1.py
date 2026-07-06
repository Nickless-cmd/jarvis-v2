"""Track 1 — govern to u-governede gates gennem central().decide.

Sikkerheds-invariant: det returnerede dict er IDENTISK med den rå funktions retur,
uanset om central-stien lykkes eller kollapser → kald-site-enforcement er uændret.
"""
from __future__ import annotations

from unittest import mock

import core.services.skill_security_scanner as scanner_mod
import core.services.auto_code_review as review_mod
from core.services.gate_kernel import Decision, GateClass, Verdict


# ── GATE 1: skill_security_scanner (SECURITY, cluster="skill") ──────────────

def _fake_central_passthrough():
    """En falsk central hvis .decide bare kører fn(ctx) (som den ægte gør på happy-path)."""
    class _C:
        def decide(self, nerve, ctx, fn, *, cluster="", klass=None):
            return fn(ctx)
    return _C()


def test_skill_gated_returns_same_dict_on_critical():
    crit = {"status": "ok", "risk": "critical", "verdict": "BLOCK", "findings": []}
    with mock.patch.object(scanner_mod, "scan_skill_directory", return_value=crit) as raw, \
         mock.patch("core.services.central_core.central",
                    return_value=_fake_central_passthrough()):
        out = scanner_mod.scan_skill_directory_gated("/some/skill")
    assert out == crit
    assert out["risk"] == "critical"        # enforcement bevaret på kald-site
    raw.assert_called()


def test_skill_gated_central_crash_falls_back_to_raw_scan():
    crit = {"status": "ok", "risk": "critical", "verdict": "BLOCK", "findings": []}

    def _boom():
        raise RuntimeError("central nede")

    with mock.patch.object(scanner_mod, "scan_skill_directory", return_value=crit), \
         mock.patch("core.services.central_core.central", side_effect=_boom):
        out = scanner_mod.scan_skill_directory_gated("/some/skill")
    # central-sti kollapsede → rå scan, ALDRIG svækket
    assert out == crit
    assert out["risk"] == "critical"


def test_skill_gated_calls_central_with_skill_cluster_and_security_class():
    crit = {"status": "ok", "risk": "critical", "verdict": "BLOCK", "findings": []}
    captured = {}

    class _C:
        def decide(self, nerve, ctx, fn, *, cluster="", klass=None):
            captured["nerve"] = nerve
            captured["cluster"] = cluster
            captured["klass"] = klass
            return fn(ctx)   # kør fn så scanet bæres ud via ctx

    with mock.patch.object(scanner_mod, "scan_skill_directory", return_value=crit), \
         mock.patch("core.services.central_core.central", return_value=_C()):
        out = scanner_mod.scan_skill_directory_gated("/some/skill")
    assert captured["cluster"] == "skill"
    assert captured["klass"] is GateClass.SECURITY
    assert out == crit


def test_skill_gated_fn_maps_risk_to_verdict():
    """Verificér mapping-funktionen: critical→RED, error→YELLOW, clean→GREEN.
    Verdict fanges INDE i den patchede decide (fn er kun gyldigt der)."""
    captured = {}

    class _C:
        def decide(self, nerve, ctx, fn, *, cluster="", klass=None):
            captured["verdict"] = fn(ctx)
            return captured["verdict"]

    for scan, want_dec, want_action in [
        ({"status": "ok", "risk": "critical"}, Decision.RED, "block"),
        ({"status": "error", "risk": ""}, Decision.YELLOW, "warn"),
        ({"status": "ok", "risk": "low"}, Decision.GREEN, "none"),
    ]:
        with mock.patch.object(scanner_mod, "scan_skill_directory", return_value=scan), \
             mock.patch("core.services.central_core.central", return_value=_C()):
            scanner_mod.scan_skill_directory_gated("/p")
        v: Verdict = captured["verdict"]
        assert v.decision is want_dec
        assert v.action == want_action
        assert v.klass is GateClass.SECURITY


# ── GATE 2: auto_code_review (COGNITIVE, cluster="commit") ──────────────────

def test_review_gated_returns_same_dict_block():
    rev = {"status": "ok", "verdict": "needs-attention",
           "flags": [{"kind": "secrets-risk", "severity": "block", "message": "x"}]}
    with mock.patch.object(review_mod, "review_pending_commit", return_value=rev), \
         mock.patch("core.services.central_core.central",
                    return_value=_fake_central_passthrough()):
        out = review_mod.review_pending_commit_gated(
            repo_root="/r", files=["a"], message="m", rationale="r")
    assert out == rev


def test_review_gated_central_crash_falls_back_to_raw_review():
    rev = {"status": "ok", "verdict": "clean", "flags": []}
    with mock.patch.object(review_mod, "review_pending_commit", return_value=rev), \
         mock.patch("core.services.central_core.central",
                    side_effect=RuntimeError("central nede")):
        out = review_mod.review_pending_commit_gated(
            repo_root="/r", files=["a"], message="m", rationale="r")
    assert out == rev


def test_review_gated_calls_central_with_commit_cluster_and_cognitive_class():
    rev = {"status": "ok", "verdict": "clean", "flags": []}
    captured = {}

    class _C:
        def decide(self, nerve, ctx, fn, *, cluster="", klass=None):
            captured["cluster"] = cluster
            captured["klass"] = klass
            return fn(ctx)

    with mock.patch.object(review_mod, "review_pending_commit", return_value=rev), \
         mock.patch("core.services.central_core.central", return_value=_C()):
        out = review_mod.review_pending_commit_gated(
            repo_root="/r", files=["a"], message="m", rationale="r")
    assert captured["cluster"] == "commit"
    assert captured["klass"] is GateClass.COGNITIVE
    assert out == rev


def test_review_gated_fn_maps_block_to_yellow_else_green():
    captured = {}

    class _C:
        def decide(self, nerve, ctx, fn, *, cluster="", klass=None):
            captured["verdict"] = fn(ctx)
            return captured["verdict"]

    for rev, want_dec in [
        ({"status": "ok", "verdict": "needs-attention",
          "flags": [{"severity": "block"}]}, Decision.YELLOW),
        ({"status": "ok", "verdict": "clean", "flags": []}, Decision.GREEN),
    ]:
        with mock.patch.object(review_mod, "review_pending_commit", return_value=rev), \
             mock.patch("core.services.central_core.central", return_value=_C()):
            review_mod.review_pending_commit_gated(
                repo_root="/r", files=["a"], message="m", rationale="r")
        v: Verdict = captured["verdict"]
        assert v.decision is want_dec
        assert v.klass is GateClass.COGNITIVE
