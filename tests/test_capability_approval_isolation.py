from __future__ import annotations

import pytest
from fastapi import HTTPException


def _insert_request(db, request_id: str, user_id: str | None) -> None:
    with db.connect() as conn:
        conn.execute(
            """
            INSERT INTO capability_approval_requests (
                request_id, capability_id, execution_mode, requested_at, status,
                scheduled_for_user_id
            ) VALUES (?, 'tool:test', 'workspace-file-write',
                      '2026-09-02T12:00:00+00:00', 'pending', ?)
            """,
            (request_id, user_id),
        )
        conn.commit()


def test_capability_approval_route_returns_404_for_cross_user_request(
    isolated_runtime,
) -> None:
    from core.identity.workspace_context import reset_context, set_context

    db = isolated_runtime.db
    db.init_db()
    _insert_request(db, "request-a", "user-a")

    token = set_context(workspace_name="b", user_id="user-b", role="member")
    try:
        with pytest.raises(HTTPException) as exc_info:
            isolated_runtime.mission_control.mc_approve_capability_request("request-a")
        assert exc_info.value.status_code == 404
    finally:
        reset_context(token)

    token = set_context(workspace_name="a", user_id="user-a", role="member")
    try:
        result = isolated_runtime.mission_control.mc_approve_capability_request("request-a")
        assert result["request"]["status"] == "approved"
    finally:
        reset_context(token)
