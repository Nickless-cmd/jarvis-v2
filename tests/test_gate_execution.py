"""Paritets-tests for Execution-cluster-gaten (gate_execution).

Verificerer at konsolideringen af de seks spredte execution-safety-checks bevarer
adfærd: grader (RED/YELLOW/GREEN), rækkefølge (bash rbw→classify, write classify→rbw),
blocked_only-stien (force), edit uden rbw, samt _to_check-mapping inkl. isoleret-RED.
"""
from __future__ import annotations

import pytest

from core.services import gate_execution as ge
from core.services.gate_kernel import Decision, Verdict


def g(action, **kw):
    return ge.execution_gate({"action": action, **kw})


@pytest.fixture
def patch_classify(monkeypatch):
    import core.tools.simple_tools as st
    state = {"command": "auto", "file": "auto"}
    monkeypatch.setattr(st, "classify_command", lambda c: state["command"])
    monkeypatch.setattr(st, "classify_file_write", lambda p: state["file"])
    return state


@pytest.fixture
def patch_rbw(monkeypatch):
    import core.services.read_before_write_guard as rbw
    state = {"bash_ok": True, "file_ok": True, "op_ok": True, "reason": "RBW-BLOK"}
    monkeypatch.setattr(
        rbw, "check_bash_command_safe",
        lambda command, session_id="default": (
            state["bash_ok"], None if state["bash_ok"] else state["reason"]))
    monkeypatch.setattr(
        rbw, "check_read_before_write",
        lambda path, session_id="default": (
            state["file_ok"], None if state["file_ok"] else state["reason"]))
    monkeypatch.setattr(
        rbw, "check_operator_read_before_write",
        lambda path, session_id="default", file_exists=None: (
            state["op_ok"], None if state["op_ok"] else state["reason"]))
    return state


# ── command grading ──────────────────────────────────────────────────────
def test_command_auto(patch_classify, patch_rbw):
    patch_classify["command"] = "auto"
    assert g("command", command="ls").decision is Decision.GREEN


def test_command_blocked(patch_classify, patch_rbw):
    patch_classify["command"] = "blocked"
    v = g("command", command="x")
    assert v.decision is Decision.RED
    assert v.evidence["classification"] == "blocked"


def test_command_destructive_yellow(patch_classify, patch_rbw):
    patch_classify["command"] = "destructive"
    v = g("command", command="x")
    assert v.decision is Decision.YELLOW
    assert v.evidence["classification"] == "destructive"


def test_command_approval_yellow(patch_classify, patch_rbw):
    patch_classify["command"] = "approval"
    assert g("command", command="x").decision is Decision.YELLOW


def test_command_rbw_blocks_before_classify(patch_classify, patch_rbw):
    # read-before-write skal vinde FØR classify (paritet med _exec_bash)
    patch_classify["command"] = "destructive"
    patch_rbw["bash_ok"] = False
    v = g("command", command="cp x SOUL.md")
    assert v.decision is Decision.RED
    assert v.evidence["classification"] == "guard_blocked"
    assert "RBW-BLOK" in v.reason


def test_command_blocked_only_skips_rbw_and_approval(patch_classify, patch_rbw):
    # force-stien (blocked_only) springer rbw + approval over; kun blocked blokerer
    patch_classify["command"] = "destructive"
    patch_rbw["bash_ok"] = False
    assert g("command", command="x", blocked_only=True).decision is Decision.GREEN


def test_command_blocked_only_still_blocks_blocked(patch_classify, patch_rbw):
    patch_classify["command"] = "blocked"
    assert g("command", command="x", blocked_only=True).decision is Decision.RED


# ── file grading ─────────────────────────────────────────────────────────
def test_file_blocked(patch_classify, patch_rbw):
    patch_classify["file"] = "blocked"
    assert g("file", path="/etc/passwd").decision is Decision.RED


def test_file_approval(patch_classify, patch_rbw):
    patch_classify["file"] = "approval"
    assert g("file", path="/x").decision is Decision.YELLOW


def test_file_auto(patch_classify, patch_rbw):
    patch_classify["file"] = "auto"
    assert g("file", path="/x").decision is Decision.GREEN


def test_file_rbw_after_classify(patch_classify, patch_rbw):
    # classify=auto → rbw kører bagefter (paritet med _exec_write_file)
    patch_classify["file"] = "auto"
    patch_rbw["file_ok"] = False
    v = g("file", path="/x", kind="write")
    assert v.decision is Decision.RED
    assert v.evidence["classification"] == "guard_blocked"


def test_file_edit_skips_rbw(patch_classify, patch_rbw):
    # edit har historisk ingen read-before-write
    patch_classify["file"] = "auto"
    patch_rbw["file_ok"] = False
    assert g("file", path="/x", kind="edit").decision is Decision.GREEN


# ── workspace trust ──────────────────────────────────────────────────────
def test_workspace_trust_untrusted(monkeypatch):
    import core.services.workspace_trust as wt
    monkeypatch.setattr(wt, "guard_code_write", lambda name: "untrusted-besked")
    v = g("workspace_trust", tool_name="write_file")
    assert v.decision is Decision.RED
    assert v.evidence["classification"] == "untrusted"
    assert v.reason == "untrusted-besked"


def test_workspace_trust_ok(monkeypatch):
    import core.services.workspace_trust as wt
    monkeypatch.setattr(wt, "guard_code_write", lambda name: None)
    assert g("workspace_trust", tool_name="write_file").decision is Decision.GREEN


# ── operator ─────────────────────────────────────────────────────────────
def test_operator_block(patch_rbw):
    patch_rbw["op_ok"] = False
    v = g("operator", path="/x")
    assert v.decision is Decision.RED
    assert v.evidence["classification"] == "guard_blocked"


def test_operator_ok(patch_rbw):
    assert g("operator", path="/x").decision is Decision.GREEN


# ── _to_check mapping ────────────────────────────────────────────────────
def test_to_check_isolated_red_defaults_blocked():
    ec = ge._to_check(Verdict("exec_command", Decision.RED, "isoleret-deny", action="block"))
    assert ec.classification == "blocked"
    assert ec.allowed is False


def test_to_check_green_allowed():
    ec = ge._to_check(Verdict("exec_file", Decision.GREEN, "auto",
                              evidence={"classification": "auto"}))
    assert ec.allowed is True
    assert ec.classification == "auto"


# ── routing gennem Centralen (check_* helpers) ───────────────────────────
def test_check_command_routes_through_central(patch_classify, patch_rbw):
    patch_classify["command"] = "blocked"
    ec = ge.check_command("x")
    assert ec.classification == "blocked"
    assert ec.allowed is False


def test_check_file_routes_through_central(patch_classify, patch_rbw):
    patch_classify["file"] = "auto"
    ec = ge.check_file("/x", kind="write")
    assert ec.allowed is True


# ── katalog-integritet ───────────────────────────────────────────────────
def test_catalog_validates_with_execution():
    from core.services import central_catalog as cc
    assert cc.validate() == []
    assert "execution" in cc.clusters()


# ── A1: upload malware-scan (2026-06-22) ─────────────────────────────────
def test_upload_scan_infected_blocks(monkeypatch):
    import core.services.malware_scan as ms
    rep = ms.ScanReport("infected", signature="Eicar-Test", detail="fundet")
    monkeypatch.setattr(ms, "is_upload_allowed", lambda path, block_on_unavailable=False: (False, rep))
    v = g("upload_scan", path="/tmp/x")
    assert v.decision is Decision.RED
    assert v.evidence["classification"] == "infected"
    assert "Eicar" in v.reason


def test_upload_scan_clean_allows(monkeypatch):
    import core.services.malware_scan as ms
    rep = ms.ScanReport("clean")
    monkeypatch.setattr(ms, "is_upload_allowed", lambda path, block_on_unavailable=False: (True, rep))
    v = g("upload_scan", path="/tmp/x")
    assert v.decision is Decision.GREEN


def test_upload_scan_unavailable_fail_open(monkeypatch):
    import core.services.malware_scan as ms
    rep = ms.ScanReport("unavailable")
    monkeypatch.setattr(ms, "is_upload_allowed", lambda path, block_on_unavailable=False: (True, rep))
    ec = ge.check_upload("/tmp/x")  # default block_on_unavailable=False → tilladt
    assert ec.allowed is True


def test_upload_scan_unavailable_fail_closed(monkeypatch):
    import core.services.malware_scan as ms
    rep = ms.ScanReport("unavailable")
    monkeypatch.setattr(ms, "is_upload_allowed",
                        lambda path, block_on_unavailable=False: (not block_on_unavailable, rep))
    ec = ge.check_upload("/tmp/x", block_on_unavailable=True)  # member-upload → blokeret
    assert ec.allowed is False


# --- In-loop gate-observationer (Bjørns gate-princip, 18. aug 2026) ---
from core.services.gate_execution import (
    ExecCheck, Decision, gate_observation, reset_gate_repeat_counts,
)
from unittest.mock import patch as _patch


def _check(classification="blocked", reason="rm -rf mod beskyttet sti"):
    return ExecCheck(allowed=False, decision=Decision.RED,
                     classification=classification, reason=reason)


class TestGateObservation:
    def setup_method(self):
        reset_gate_repeat_counts()

    def test_begrundelsen_naar_frem(self):
        """KERNEN: før blev _ec.reason smidt væk → han kunne ikke rette sig selv."""
        with _patch("core.runtime.db_central_incidents.record_central_incident"):
            out = gate_observation(_check(), gate="exec_command", subject="rm -rf /",
                                   remedy="brug en indsnævret sti")
        assert out["status"] == "blocked"
        assert "rm -rf mod beskyttet sti" in out["error"]      # ÅRSAG med
        assert "brug en indsnævret sti" in out["error"]        # NÆSTE SKRIDT med
        assert out["gate"] == "exec_command"                   # hvilken gate

    def test_er_non_blocking_returnerer_resultat(self):
        """Gaten må aldrig kaste/dræbe — den returnerer et tool-resultat ind i loopet."""
        with _patch("core.runtime.db_central_incidents.record_central_incident"):
            out = gate_observation(_check(), gate="g", subject="x")
        assert isinstance(out, dict) and out["status"] == "blocked"

    def test_gentagelse_eskalerer_synligt(self):
        with _patch("core.runtime.db_central_incidents.record_central_incident"):
            first = gate_observation(_check(), gate="g", subject="samme")
            second = gate_observation(_check(), gate="g", subject="samme")
        assert first["repeat_count"] == 1
        assert "gange i denne session" not in first["error"]
        assert second["repeat_count"] == 2
        assert "2 gange i denne session" in second["error"]

    def test_forskellige_emner_taelles_hver_for_sig(self):
        with _patch("core.runtime.db_central_incidents.record_central_incident"):
            a = gate_observation(_check(), gate="g", subject="cmd-A")
            b = gate_observation(_check(), gate="g", subject="cmd-B")
        assert a["repeat_count"] == 1 and b["repeat_count"] == 1

    def test_incident_er_klient_synlig_med_gate_navn(self):
        with _patch("core.runtime.db_central_incidents.record_central_incident") as inc:
            gate_observation(_check(), gate="exec_command", subject="rm -rf /")
        assert inc.called
        kw = inc.call_args.kwargs
        assert kw["nerve"] == "exec_command"
        assert kw["kind"] == "gate_fired"
        assert "rm -rf mod beskyttet sti" in kw["message"]

    def test_telemetri_fejl_forhindrer_ikke_resultatet(self):
        def _boom(*_a, **_k):
            raise RuntimeError("db nede")
        with _patch("core.runtime.db_central_incidents.record_central_incident", _boom):
            out = gate_observation(_check(), gate="g", subject="x")
        assert out["status"] == "blocked"      # resultatet kommer altid igennem

    def test_manglende_begrundelse_siger_det_aabent(self):
        with _patch("core.runtime.db_central_incidents.record_central_incident"):
            out = gate_observation(_check(reason=""), gate="g", subject="x")
        assert "ikke oplyst" in out["error"]
