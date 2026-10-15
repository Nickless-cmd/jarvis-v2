from __future__ import annotations

import importlib
from datetime import UTC, datetime, timedelta

import pytest


def _service():
    import core.services.chat_flow_preferences as module

    return importlib.reload(module)


def test_defaults_and_principals_are_isolated(isolated_runtime):
    service = _service()

    assert service.get_chat_flow_state("user:a")["preference"] == "living"
    service.set_chat_flow_state("user:a", preference="calm", explicit=True)

    assert service.get_chat_flow_state("user:a")["preference"] == "calm"
    assert service.get_chat_flow_state("user:a")["explicit_user_choice"] is True
    assert service.get_chat_flow_state("user:b")["preference"] == "living"


def test_rejects_invalid_preference(isolated_runtime):
    service = _service()

    with pytest.raises(ValueError, match="chat flow preference"):
        service.set_chat_flow_state("user:a", preference="technical")


def test_verified_identity_is_required_and_native_owner_is_stable(isolated_runtime):
    service = _service()
    from core.identity.workspace_context import reset_context, set_context

    member = set_context(workspace_name="member", user_id="member-1", role="member")
    try:
        assert service.resolve_chat_flow_principal() == "user:member-1"
    finally:
        reset_context(member)

    owner = set_context(workspace_name="bjorn", user_id="", role="owner")
    try:
        assert service.resolve_chat_flow_principal() == "native-owner"
    finally:
        reset_context(owner)

    unverified = set_context(workspace_name="bjorn", user_id="owner-1", role="")
    try:
        with pytest.raises(service.ChatFlowIdentityError, match="verified"):
            service.resolve_chat_flow_principal()
    finally:
        reset_context(unverified)

    unstable = set_context(workspace_name="public", user_id="", role="guest")
    try:
        with pytest.raises(service.ChatFlowIdentityError, match="stable"):
            service.resolve_chat_flow_principal()
    finally:
        reset_context(unstable)


def test_onboarding_claim_is_atomic_expires_and_marks_seen_only_after_ack(isolated_runtime):
    service = _service()
    now = datetime(2026, 10, 15, 16, 0, tzinfo=UTC)

    first = service.claim_chat_flow_onboarding("user:a", "run-1", now=now)
    second = service.claim_chat_flow_onboarding("user:a", "run-2", now=now)

    assert first["claimed"] is True
    assert second["claimed"] is False
    assert service.get_chat_flow_state("user:a")["onboarding_seen"] is False

    expired = service.claim_chat_flow_onboarding(
        "user:a", "run-3", now=now + timedelta(minutes=6)
    )
    assert expired["claimed"] is True
    assert expired["claim_id"] != first["claim_id"]

    with pytest.raises(ValueError, match="claim"):
        service.ack_chat_flow_onboarding("user:a", first["claim_id"])

    acknowledged = service.ack_chat_flow_onboarding("user:a", expired["claim_id"])
    assert acknowledged["onboarding_seen"] is True
    assert service.claim_chat_flow_onboarding("user:a", "run-4")["claimed"] is False


def test_observations_store_bounded_counters_not_conversation_text(isolated_runtime):
    service = _service()

    observed = service.record_chat_flow_observation(
        "user:a", meaningful_steps=99, expanded_work=True, manual_override="living"
    )

    assert observed["multi_step_runs"] == 1
    assert observed["work_expansions"] == 1
    assert observed["living_overrides"] == 1
    with isolated_runtime.db.connect() as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(chat_flow_preferences)")}
    assert not ({"raw_text", "message", "conversation"} & columns)


def test_suggestion_rejection_and_disable_are_persisted(isolated_runtime):
    service = _service()

    rejected = service.record_chat_flow_suggestion(
        "user:a", kind="calm", outcome="rejected"
    )
    disabled = service.set_chat_flow_state("user:a", suggestions_enabled=False)

    assert rejected["last_suggestion_kind"] == "calm"
    assert rejected["suggestion_rejections"] == 1
    assert disabled["suggestions_enabled"] is False
