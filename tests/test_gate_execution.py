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
