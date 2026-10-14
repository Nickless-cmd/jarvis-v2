from __future__ import annotations

import pytest


def test_recall_defaults_off_when_runtime_flag_missing(monkeypatch):
    from core.services import scoped_recall_policy as policy

    monkeypatch.setattr(
        policy, "get_runtime_state_value", lambda key, default=None: default
    )
    assert policy.recall_enabled() is False
    assert policy.recall_migration_enabled() is False


def test_only_literal_boolean_true_enables_flags(monkeypatch):
    from core.services import scoped_recall_policy as policy

    monkeypatch.setattr(
        policy, "get_runtime_state_value", lambda key, default=None: "true"
    )
    assert policy.recall_enabled() is False
    assert policy.recall_migration_enabled() is False


def test_setters_store_actual_booleans(monkeypatch):
    from core.services import scoped_recall_policy as policy

    writes = []
    monkeypatch.setattr(
        policy, "set_runtime_state_value", lambda key, value: writes.append((key, value))
    )
    policy.set_recall_enabled(True)
    policy.set_recall_migration_enabled(False)
    assert writes == [
        (policy.RECALL_FLAG, True),
        (policy.MIGRATION_FLAG, False),
    ]


def test_private_scope_fails_closed_without_bound_user(monkeypatch):
    from core.services import scoped_recall_policy as policy

    monkeypatch.setattr(policy, "current_user_id", lambda: "")
    monkeypatch.setattr(policy, "current_session_id", lambda: "")
    with pytest.raises(policy.MissingRecallScope):
        policy.require_private_scope()


def test_private_scope_can_use_authoritative_session_owner(monkeypatch):
    from core.services import scoped_recall_policy as policy

    monkeypatch.setattr(policy, "current_user_id", lambda: "")
    monkeypatch.setattr(policy, "current_session_id", lambda: "session-owner")
    monkeypatch.setattr(policy, "get_session_owner", lambda sid: "owner-1")
    assert policy.require_private_scope() == "owner-1"


def test_private_scope_converges_external_subject_to_canonical_user(monkeypatch):
    from core.services import routine_migration
    from core.services import scoped_recall_policy as policy

    monkeypatch.setattr(policy, "current_user_id", lambda: "discord-1")
    monkeypatch.setattr(routine_migration, "resolve_canonical_identity", lambda token: "canonical-1")

    assert policy.require_private_scope() == "canonical-1"


def test_disabled_result_has_no_private_payload():
    from core.services import scoped_recall_policy as policy

    assert policy.disabled_result("recall") == {
        "status": "disabled", "path": "recall", "results": [], "count": 0,
    }
