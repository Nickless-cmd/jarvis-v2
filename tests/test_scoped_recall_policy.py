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
        "status": "disabled",
        "path": "recall",
        "note": (
            "recall: privat recall er slaaet fra (scoped_recall_enabled=false). "
            "Dette er IKKE et tomt resultat — der blev ikke soegt."
        ),
        "items": [],
        "results": [],
        "count": 0,
    }


def test_disabled_result_kan_ikke_forveksles_med_tomt():
    """«Slukket» maa ikke se ud som «tomt».

    Maalt 14/10-2026: `recall_sensory_memories` svarede `count: 0` for
    query="stue" mens arkivet havde 188 traef. Modellen laeste det som
    «der er intet» — ikke «soegningen blev ikke koert». Noeglen `items`
    skal vaere den samme som normal-vejen bruger, og `note` skal sige
    hoejt at der ikke blev soegt.
    """
    from core.services import scoped_recall_policy as policy

    tomt = policy.disabled_result("sensory_recall")
    assert tomt["items"] == [], "normal-vejens noegle skal ogsaa findes her"
    assert "IKKE et tomt resultat" in str(tomt["note"])
