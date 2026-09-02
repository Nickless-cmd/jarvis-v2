from __future__ import annotations


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


def test_capability_approval_crud_is_scoped_to_requesting_user(isolated_runtime) -> None:
    db = isolated_runtime.db
    db.init_db()
    _insert_request(db, "request-a", "user-a")
    _insert_request(db, "request-b", "user-b")

    requests = db.recent_capability_approval_requests(
        limit=20, user_id="user-a", include_unassigned=False
    )
    assert [item["request_id"] for item in requests] == ["request-a"]
    assert db.get_capability_approval_request(
        "request-a", user_id="user-b", include_unassigned=False
    ) is None
    assert db.approve_capability_approval_request(
        "request-a",
        approved_at="2026-09-02T12:01:00+00:00",
        user_id="user-b",
        include_unassigned=False,
    ) is None
    assert db.record_capability_approval_request_execution(
        "request-a",
        executed_at="2026-09-02T12:02:00+00:00",
        invocation_status="executed",
        invocation_execution_mode="workspace-file-write",
        user_id="user-b",
        include_unassigned=False,
    ) is None
    request = db.get_capability_approval_request(
        "request-a", user_id="user-a", include_unassigned=False
    )
    assert request["status"] == "pending"
    assert request["executed"] is False


def test_unassigned_capability_requests_are_visible_only_in_owner_scope(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    db.init_db()
    _insert_request(db, "legacy-request", None)

    assert db.get_capability_approval_request(
        "legacy-request", user_id="member", include_unassigned=False
    ) is None
    assert db.get_capability_approval_request(
        "legacy-request", user_id="owner", include_unassigned=True
    )["request_id"] == "legacy-request"
