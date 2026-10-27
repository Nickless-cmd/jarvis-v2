from __future__ import annotations


def test_digest_keeps_legacy_completion_delivery(monkeypatch):
    from core.services import subagent_digest as digest

    monkeypatch.setattr(digest, "_load_marks", lambda: {})
    monkeypatch.setattr(digest, "_mark_seen", lambda *_: None)
    monkeypatch.setattr(
        "core.runtime.db.list_agent_registry_entries",
        lambda limit=80: [{
            "agent_id": "legacy-1",
            "owner_user_id": "legacy_unscoped",
            "role": "researcher",
            "status": "completed",
            "completed_at": "2026-10-27T10:00:00+00:00",
            "goal": "legacy work",
        }],
    )
    assert "legacy work" in (digest.subagent_digest_section("session-1") or "")


def test_digest_excludes_task_contract_results(monkeypatch):
    from core.services import subagent_digest as digest

    monkeypatch.setattr(digest, "_load_marks", lambda: {})
    monkeypatch.setattr(
        "core.runtime.db.list_agent_registry_entries",
        lambda limit=80: [{
            "agent_id": "task-1",
            "owner_user_id": "owner-1",
            "role": "critic",
            "status": "completed",
            "completed_at": "2026-10-27T10:00:00+00:00",
            "goal": "contract work",
        }],
    )
    assert digest.subagent_digest_section("session-1") is None
