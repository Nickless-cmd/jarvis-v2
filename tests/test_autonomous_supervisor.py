"""Tests for #3 autonom supervision (autonomous_supervisor) — vurdér run via korrelation."""
from __future__ import annotations

import pytest

from core.services import autonomous_supervisor as sup


@pytest.fixture
def patch_corr(monkeypatch):
    state = {"timeline": [], "break_point": None}
    monkeypatch.setattr("core.services.central_correlate.correlate",
                        lambda rid: {"timeline": state["timeline"], "break_point": state["break_point"]})
    # undgå rigtige observe/incident-skrivninger
    import core.services.central_core as cc
    monkeypatch.setattr(cc, "central", lambda: type("C", (), {"observe": lambda self, e: None})())
    flagged = {}
    monkeypatch.setattr("core.runtime.db_central_incidents.record_central_incident",
                        lambda **k: flagged.update(k))
    return state, flagged


def test_clean_completed_run(patch_corr):
    state, flagged = patch_corr
    rep = sup.supervise("r1", "completed")
    assert rep["verdict"] == "clean"
    assert not flagged  # rent run → ingen incident


def test_lie_detected_via_truth_red(patch_corr):
    state, flagged = patch_corr
    state["timeline"] = [{"cluster": "truth", "decision": "red", "nerve": "truth"}]
    rep = sup.supervise("r2", "completed")
    assert rep["verdict"] == "lied" and rep["lied"] is True
    assert flagged["severity"] == "severe"  # løgn = alvorligst


def test_looped_via_loop_red(patch_corr):
    state, flagged = patch_corr
    state["timeline"] = [{"cluster": "loop", "decision": "red", "nerve": "loop_control"}]
    rep = sup.supervise("r3", "completed")
    assert rep["verdict"] == "looped" and rep["looped"] is True


def test_connection_error_retryable(patch_corr):
    state, flagged = patch_corr
    rep = sup.supervise("r4", "failed", error="ConnectionResetError: connection reset by peer")
    assert rep["verdict"] == "connection_error"
    assert rep["retryable"] is True
    assert flagged["severity"] == "error"


def test_plain_failure_not_retryable(patch_corr):
    state, flagged = patch_corr
    rep = sup.supervise("r5", "failed", error="ValueError: bad input")
    assert rep["verdict"] == "failed" and rep["retryable"] is False


def test_self_safe_on_correlate_failure(monkeypatch):
    monkeypatch.setattr("core.services.central_correlate.correlate",
                        lambda rid: (_ for _ in ()).throw(RuntimeError("nede")))
    # må ikke kaste
    rep = sup.supervise("r6", "completed")
    assert "verdict" in rep


def test_catalog_has_supervision():
    from core.services import central_catalog as cc
    assert cc.validate() == []
    assert "supervision" in [n.name for n in cc.by_cluster("autonomous")]
