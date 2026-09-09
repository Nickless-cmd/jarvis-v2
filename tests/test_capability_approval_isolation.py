from __future__ import annotations

import pytest
from fastapi import HTTPException



# ── hvorfor tidsstemplet er RELATIVT ────────────────────────────────────────
# Testen stod med et hardkodet '2026-09-02T12:00:00+00:00' — den dag den blev
# skrevet. `capability_approval_request_is_stale` maaler mod `datetime.now()`
# med en 24-timers taerskel, saa anmodningen blev forældet dagen efter.
#
# Maalt 9/9-2026: anmodningen var 173 timer gammel, og alle tre tests i
# familien havde vaeret roede siden 3. september. De vogter praecis de
# invarianter man mest vil have vogtet — atomisk claim, og at en aendret
# envelope ikke kan eksekveres — og de var blevet til stoej alle havde laert
# at ignorere.
#
# En test der kun bestaar den dag den skrives, er vaerre end ingen test.
# Nu måles invarianten, ikke kalenderen.
def _nu(offset_s: int = 0) -> str:
    from datetime import UTC, datetime, timedelta
    return (datetime.now(UTC) + timedelta(seconds=offset_s)).isoformat()


def _insert_request(db, request_id: str, user_id: str | None) -> None:
    with db.connect() as conn:
        conn.execute(
            """
            INSERT INTO capability_approval_requests (
                request_id, capability_id, execution_mode, requested_at, status,
                scheduled_for_user_id
            ) VALUES (?, 'tool:test', 'workspace-file-write',
                      ?, 'pending', ?)
            """,
            (request_id, _nu(-60), user_id),
        )
        row = conn.execute(
            "SELECT * FROM capability_approval_requests WHERE request_id = ?",
            (request_id,),
        ).fetchone()
        request = db._capability_approval_request_from_row(row)
        conn.execute(
            """
            UPDATE capability_approval_requests
            SET approval_envelope_fingerprint = ? WHERE request_id = ?
            """,
            (db.capability_approval_envelope_fingerprint(request), request_id),
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


def test_approve_and_execute_replays_without_invoking_twice(
    isolated_runtime,
    monkeypatch,
) -> None:
    from core.identity.workspace_context import reset_context, set_context

    db = isolated_runtime.db
    db.init_db()
    _insert_request(db, "request-once", "user-a")
    invocations: list[str] = []

    def fake_invoke(capability_id: str, **_kwargs):
        invocations.append(capability_id)
        return {"status": "executed", "execution_mode": "workspace-file-write"}

    monkeypatch.setattr(
        isolated_runtime.mission_control,
        "invoke_workspace_capability",
        fake_invoke,
    )
    token = set_context(workspace_name="a", user_id="user-a", role="member")
    try:
        first = isolated_runtime.mission_control.mc_approve_and_execute_capability_request(
            "request-once"
        )
        replay = isolated_runtime.mission_control.mc_approve_and_execute_capability_request(
            "request-once"
        )
    finally:
        reset_context(token)

    assert first["ok"] is True
    assert replay == {**first, "replayed": True}
    assert invocations == ["tool:test"]


def test_stale_capability_request_cannot_be_approved_and_executed(
    isolated_runtime,
) -> None:
    from core.identity.workspace_context import reset_context, set_context

    db = isolated_runtime.db
    db.init_db()
    _insert_request(db, "stale-request", "user-a")
    with db.connect() as conn:
        conn.execute(
            "UPDATE capability_approval_requests SET requested_at = ? WHERE request_id = ?",
            ("2000-01-01T00:00:00+00:00", "stale-request"),
        )
        conn.commit()

    token = set_context(workspace_name="a", user_id="user-a", role="member")
    try:
        with pytest.raises(HTTPException) as exc_info:
            isolated_runtime.mission_control.mc_approve_and_execute_capability_request(
                "stale-request"
            )
        assert exc_info.value.status_code == 409
        assert "stale" in str(exc_info.value.detail).lower()
    finally:
        reset_context(token)


def test_changed_capability_envelope_cannot_be_executed(isolated_runtime) -> None:
    from core.identity.workspace_context import reset_context, set_context

    db = isolated_runtime.db
    db.init_db()
    _insert_request(db, "changed-request", "user-a")
    with db.connect() as conn:
        conn.execute(
            """
            UPDATE capability_approval_requests
            SET proposal_content = 'changed after approval request'
            WHERE request_id = 'changed-request'
            """
        )
        conn.commit()

    token = set_context(workspace_name="a", user_id="user-a", role="member")
    try:
        with pytest.raises(HTTPException) as exc_info:
            isolated_runtime.mission_control.mc_approve_and_execute_capability_request(
                "changed-request"
            )
        assert exc_info.value.status_code == 409
        assert "envelope" in str(exc_info.value.detail).lower()
    finally:
        reset_context(token)
