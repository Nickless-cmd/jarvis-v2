from __future__ import annotations

import importlib


def test_outbox_deduplicates_retries_and_delivers_after_failure(isolated_runtime) -> None:
    from core.services import approval_outbox

    outbox = importlib.reload(approval_outbox)
    db = isolated_runtime.db
    db.init_db()
    with db.connect() as conn:
        for _ in range(3):
            outbox.enqueue_approval_notification(
                conn,
                request_id="request-1",
                user_id="user-a",
                envelope={"request_id": "request-1", "capability_name": "Test"},
            )
        conn.commit()

    pending = outbox.pending_approval_notifications(limit=20)
    assert len(pending) == 1

    assert outbox.dispatch_pending_approval_notifications(
        deliver=lambda _user_id, _envelope: False
    ) == {"delivered": 0, "failed": 1}
    outbox.make_approval_notification_due("request-1")
    assert outbox.pending_approval_notifications(limit=20)[0]["attempts"] == 1

    delivered: list[str] = []
    assert outbox.dispatch_pending_approval_notifications(
        deliver=lambda _user_id, envelope: delivered.append(envelope["request_id"]) or True
    ) == {"delivered": 1, "failed": 0}
    assert delivered == ["request-1"]
    assert outbox.pending_approval_notifications(limit=20) == []


def test_capability_request_and_outbox_are_persisted_together(isolated_runtime) -> None:
    from core.identity.workspace_context import reset_context, set_context
    from core.services import approval_outbox
    from core.tools import workspace_capabilities

    isolated_runtime.db.init_db()
    outbox = importlib.reload(approval_outbox)
    capabilities = importlib.reload(workspace_capabilities)
    token = set_context(workspace_name="a", user_id="user-a", role="member")
    try:
        result = capabilities.invoke_workspace_capability(
            "tool:propose-workspace-memory-update",
            write_content="Outbox test content.\n",
        )
    finally:
        reset_context(token)

    request = isolated_runtime.db.latest_capability_approval_request(
        execution_mode="workspace-file-write", include_executed=False
    )
    pending = outbox.pending_approval_notifications(limit=20)
    assert result["status"] == "approval-required"
    assert request is not None
    assert [item["request_id"] for item in pending] == [request["request_id"]]
    assert pending[0]["user_id"] == "user-a"
