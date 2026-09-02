from __future__ import annotations


def test_recent_tool_intent_approvals_are_scoped_and_expiry_is_projected(
    isolated_runtime,
) -> None:
    from core.identity.workspace_context import reset_context, set_context

    db = isolated_runtime.db
    db.init_db()
    token = set_context(workspace_name="a", user_id="user-a", role="member")
    try:
        db.create_tool_intent_approval_request(
            intent_key="expired-a",
            intent_type="write",
            intent_target="MEMORY.md",
            approval_scope="workspace",
            approval_required=True,
            approval_reason="test",
            requested_at="2000-01-01T00:00:00+00:00",
            expires_at="2000-01-01T00:15:00+00:00",
        )
    finally:
        reset_context(token)

    own = db.recent_tool_intent_approval_requests(
        limit=20, user_id="user-a", include_unassigned=False
    )
    other = db.recent_tool_intent_approval_requests(
        limit=20, user_id="user-b", include_unassigned=False
    )
    assert own[0]["effective_approval_state"] == "expired"
    assert own[0]["scheduled_for_user_id"] == "user-a"
    assert other == []
