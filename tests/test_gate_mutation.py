"""Paritets-tests for Mutation-cluster-gaten (gate_mutation).

Verificerer at konsolideringen af de tre spredte mutations-sikkerheds-funktioner +
de tre overlappende blocklists bevarer adfærd: kanonisk single-source, grader pr.
kind (module/prompt/record), eksakte beskeder, og at de gamle re-eksporter matcher.
"""
from __future__ import annotations

import pytest

from core.services import gate_mutation as gm
from core.services.gate_kernel import Decision


def g(kind, target):
    return gm.mutation_gate({"kind": kind, "target": target})


# ── kanonisk single-source (dual-truth fjernet) ──────────────────────────
def test_infrastructure_list_is_single_source():
    import core.services.identity_mutation_log as iml
    import core.services.auto_improvement_proposer as aip
    # begge moduler peger nu på SAMME frozenset-objekt
    assert iml.INFRASTRUCTURE_BLOCKED_MODULES is gm.INFRASTRUCTURE_BLOCKED_MODULES
    assert aip._INFRASTRUCTURE_BLOCKED_MODULES is gm.INFRASTRUCTURE_BLOCKED_MODULES


def test_prompt_lists_single_source():
    import core.services.prompt_mutation_loop as pml
    assert pml._PROTECTED_FILES is gm.PROTECTED_IDENTITY_FILES
    assert pml._EVOLVABLE_FILES is gm.EVOLVABLE_FILES


# ── kind=module (_is_safe_target paritet) ────────────────────────────────
def test_module_safe_non_module_target():
    assert g("module", "update SOUL.md").decision is Decision.GREEN
    assert g("module", "change tool description").decision is Decision.GREEN
    assert g("module", "core.services.context_window_manager:baz").decision is Decision.GREEN


def test_module_blocks_infrastructure():
    for m in ("core.services.auto_improvement_proposer:foo",
              "core.services.plan_proposals:bar",
              "core.services.identity_mutation_log:x",
              "core.services.approvals:y",
              "core.runtime.policy:z"):
        assert g("module", m).decision is Decision.RED, m


def test_module_empty_red():
    assert g("module", "").decision is Decision.RED


# ── kind=prompt (_check_target paritet, eksakte beskeder) ────────────────
def test_prompt_evolvable_green():
    assert g("prompt", "HEARTBEAT.md").decision is Decision.GREEN


def test_prompt_empty():
    v = g("prompt", "")
    assert v.decision is Decision.RED
    assert v.reason == "target_file is empty"


def test_prompt_path_traversal():
    v = g("prompt", "../etc/passwd")
    assert v.decision is Decision.RED
    assert "bare filename" in v.reason


def test_prompt_protected():
    v = g("prompt", "SOUL.md")
    assert v.decision is Decision.RED
    assert "is protected" in v.reason


def test_prompt_not_evolvable():
    v = g("prompt", "RANDOM.md")
    assert v.decision is Decision.RED
    assert "evolvable whitelist" in v.reason


# ── kind=record (record_mutation paritet, eksakte blok-grunde) ───────────
def test_record_disabled(monkeypatch):
    import core.services.identity_mutation_log as iml
    monkeypatch.setattr(iml, "is_auto_mutation_enabled", lambda: {"enabled": False})
    v = g("record", "SOUL.md")
    assert v.decision is Decision.RED
    assert v.reason == "auto-mutation disabled in authorization file"


def test_record_authorized_when_enabled(monkeypatch):
    import core.services.identity_mutation_log as iml
    monkeypatch.setattr(iml, "is_auto_mutation_enabled", lambda: {"enabled": True})
    assert g("record", "SOUL.md").decision is Decision.GREEN


def test_record_not_authorized_scope(monkeypatch):
    import core.services.identity_mutation_log as iml
    monkeypatch.setattr(iml, "is_auto_mutation_enabled", lambda: {"enabled": True})
    v = g("record", "/home/x/random.txt")
    assert v.decision is Decision.RED
    assert "not in authorized scope" in v.reason


def test_record_tmp_allowed(monkeypatch):
    import core.services.identity_mutation_log as iml
    monkeypatch.setattr(iml, "is_auto_mutation_enabled", lambda: {"enabled": True})
    assert g("record", "/tmp/scratch.md").decision is Decision.GREEN


def test_record_kill_switch_read_fails_fail_closed(monkeypatch):
    import core.services.identity_mutation_log as iml
    def boom():
        raise RuntimeError("auth file gone")
    monkeypatch.setattr(iml, "is_auto_mutation_enabled", boom)
    assert g("record", "SOUL.md").decision is Decision.RED  # fail-CLOSED


# ── routing gennem Centralen (check_* helpers) ───────────────────────────
def test_check_module_routes():
    assert gm.check_module("core.services.approvals:x") is False
    assert gm.check_module("update SOUL.md") is True


def test_check_prompt_target_routes():
    mc = gm.check_prompt_target("SOUL.md")
    assert mc.allowed is False and "protected" in mc.reason


def test_check_record_routes(monkeypatch):
    import core.services.identity_mutation_log as iml
    monkeypatch.setattr(iml, "is_auto_mutation_enabled", lambda: {"enabled": False})
    mc = gm.check_record("SOUL.md")
    assert mc.allowed is False


# ── katalog-integritet ───────────────────────────────────────────────────
def test_catalog_validates_with_mutation():
    from core.services import central_catalog as cc
    assert cc.validate() == []
    assert "mutation" in cc.clusters()
