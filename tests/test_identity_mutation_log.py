"""Unit tests for identity_mutation_log."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import core.services.identity_mutation_log as iml


def test_is_target_authorized_for_identity_files():
    assert iml.is_target_authorized("/home/bs/.jarvis-v2/workspaces/default/SOUL.md")
    assert iml.is_target_authorized("/home/bs/.jarvis-v2/workspaces/default/IDENTITY.md")
    assert iml.is_target_authorized("/home/bs/.jarvis-v2/workspaces/default/MANIFEST.md")
    assert iml.is_target_authorized("/home/bs/.jarvis-v2/workspaces/default/USER.md")


def test_is_target_authorized_rejects_other_files():
    assert not iml.is_target_authorized("/etc/passwd")
    assert not iml.is_target_authorized("")
    assert not iml.is_target_authorized("/some/random/file.md")


def test_is_infrastructure_blocked():
    assert iml.is_infrastructure_blocked("core.services.auto_improvement_proposer")
    assert iml.is_infrastructure_blocked("core.services.plan_proposals")
    assert iml.is_infrastructure_blocked("core.services.identity_mutation_log")
    assert not iml.is_infrastructure_blocked("core.services.context_window_manager")
    assert not iml.is_infrastructure_blocked("/path/to/SOUL.md")


def test_record_mutation_blocked_when_disabled(monkeypatch):
    monkeypatch.setattr(iml, "is_auto_mutation_enabled",
                        lambda: {"enabled": False, "reason": "test disabled"})
    result = iml.record_mutation(
        target_path="/path/SOUL.md",
        before_content="a", after_content="b", reason="x",
    )
    assert result["status"] == "blocked"


def test_record_mutation_blocked_for_unauthorized_target(monkeypatch):
    monkeypatch.setattr(iml, "is_auto_mutation_enabled", lambda: {"enabled": True})
    result = iml.record_mutation(
        target_path="/etc/passwd",
        before_content="a", after_content="b", reason="x",
    )
    assert result["status"] == "blocked"


def test_record_mutation_succeeds_for_authorized_file(monkeypatch):
    state: list = []
    monkeypatch.setattr(iml, "is_auto_mutation_enabled", lambda: {"enabled": True})
    monkeypatch.setattr(iml, "load_json", lambda *a, **k: list(state))
    monkeypatch.setattr(iml, "save_json", lambda k, v: state.clear() or state.extend(v))
    result = iml.record_mutation(
        target_path="/home/bs/.jarvis-v2/workspaces/default/SOUL.md",
        before_content="old soul", after_content="new soul",
        reason="experimental refinement",
    )
    assert result["status"] == "ok"
    assert result["mutation_id"].startswith("imut-")
    assert result["diff_summary"]["delta_chars"] == len("new soul") - len("old soul")
    assert len(state) == 1


def test_rollback_restores_before_content(tmp_path, monkeypatch):
    target = tmp_path / "SOUL.md"
    target.write_text("AFTER content", encoding="utf-8")
    fake_record = {
        "mutation_id": "imut-test",
        "target_path": str(target),
        "before_content": "BEFORE content",
        "after_content": "AFTER content",
        "rolled_back": False,
        "before_hash": "abc",
    }
    state = [fake_record]
    monkeypatch.setattr(iml, "load_json", lambda *a, **k: list(state))
    monkeypatch.setattr(iml, "save_json", lambda k, v: state.clear() or state.extend(v))
    result = iml.rollback_mutation("imut-test")
    assert result["status"] == "ok"
    assert target.read_text() == "BEFORE content"
    assert state[0]["rolled_back"] is True


def test_rollback_fails_for_unknown_mutation(monkeypatch):
    monkeypatch.setattr(iml, "load_json", lambda *a, **k: [])
    result = iml.rollback_mutation("imut-bogus")
    assert result["status"] == "error"


def test_rollback_fails_when_already_rolled_back(monkeypatch):
    fake = [{"mutation_id": "imut-x", "rolled_back": True, "target_path": "/tmp/x"}]
    monkeypatch.setattr(iml, "load_json", lambda *a, **k: list(fake))
    result = iml.rollback_mutation("imut-x")
    assert result["status"] == "error"
    assert "already" in result["error"]


def test_list_mutations_returns_recent_first(monkeypatch):
    state = [
        {"mutation_id": "imut-1", "recorded_at": "2026-04-26T00:00:00Z",
         "target_path": "/x", "reason": "first", "rolled_back": False, "diff_summary": {}, "proposer": "p"},
        {"mutation_id": "imut-2", "recorded_at": "2026-04-27T00:00:00Z",
         "target_path": "/x", "reason": "second", "rolled_back": False, "diff_summary": {}, "proposer": "p"},
    ]
    monkeypatch.setattr(iml, "load_json", lambda *a, **k: list(state))
    out = iml.list_mutations()
    assert out[0]["mutation_id"] == "imut-2"


def test_list_mutations_filters_by_target(monkeypatch):
    state = [
        {"mutation_id": "imut-soul", "target_path": "/path/SOUL.md",
         "recorded_at": "x", "reason": "", "rolled_back": False, "diff_summary": {}, "proposer": ""},
        {"mutation_id": "imut-identity", "target_path": "/path/IDENTITY.md",
         "recorded_at": "x", "reason": "", "rolled_back": False, "diff_summary": {}, "proposer": ""},
    ]
    monkeypatch.setattr(iml, "load_json", lambda *a, **k: list(state))
    out = iml.list_mutations(target_filter="IDENTITY.md")
    assert len(out) == 1
    assert "IDENTITY" in out[0]["target_path"]
