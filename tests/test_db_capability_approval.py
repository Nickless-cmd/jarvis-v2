from __future__ import annotations

import json



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
        approved_at=_nu(60),
        user_id="user-b",
        include_unassigned=False,
    ) is None
    assert db.record_capability_approval_request_execution(
        "request-a",
        executed_at=_nu(120),
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


def test_execution_claim_is_atomic_and_completed_result_is_replayed(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    db.init_db()
    _insert_request(db, "request-a", "user-a")

    first = db.claim_capability_approval_request_execution(
        "request-a",
        approved_at=_nu(60),
        user_id="user-a",
        include_unassigned=False,
    )
    competing = db.claim_capability_approval_request_execution(
        "request-a",
        approved_at=_nu(61),
        user_id="user-a",
        include_unassigned=False,
    )
    assert first["state"] == "claimed"
    assert competing["state"] == "already-executing"

    response = {"ok": True, "status": "executed", "invocation": {"value": 1}}
    db.complete_capability_approval_request_execution(
        "request-a",
        executed_at=_nu(120),
        invocation_status="executed",
        invocation_execution_mode="workspace-file-write",
        execution_result_json=json.dumps(response),
        user_id="user-a",
        include_unassigned=False,
    )
    replay = db.claim_capability_approval_request_execution(
        "request-a",
        approved_at=_nu(180),
        user_id="user-a",
        include_unassigned=False,
    )

    assert replay["state"] == "completed"
    assert json.loads(replay["request"]["execution_result_json"]) == response
