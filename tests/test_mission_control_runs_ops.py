from __future__ import annotations


def test_mc_runs_respects_requested_limit_beyond_surface_cap(
    isolated_runtime,
    monkeypatch,
) -> None:
    mc = isolated_runtime.mission_control
    rows = [{"run_id": f"run-{index}", "status": "completed"} for index in range(8)]
    # Ruten sender nu ogsaa kalderens identitet med (6/9-2026): den
    # returnerede foer ALLE brugeres runs. Dubletten fanger begge dele, saa
    # scopet ikke kan falde ud igen uden at en test siger fra.
    set_scope: dict = {}

    def _falsk(limit, *, user_id=None, include_unassigned=False):
        set_scope["user_id"] = user_id
        set_scope["include_unassigned"] = include_unassigned
        return rows[:limit]

    monkeypatch.setattr(mc, "recent_visible_runs", _falsk)
    monkeypatch.setattr(
        mc,
        "_visible_run_surface",
        lambda: {"active_run": None, "last_outcome": None, "last_capability_use": None},
    )
    monkeypatch.setattr(
        mc,
        "_visible_work_surface",
        lambda: {"persisted_recent_units": [], "persisted_recent_notes": []},
    )

    assert len(mc.mc_runs(limit=20)["recent_runs"]) == 8
    assert len(mc.mc_runs(limit=3)["recent_runs"]) == 3
    assert "user_id" in set_scope, "ruten skal sende kalderens identitet med"
    assert "include_unassigned" in set_scope


def test_mc_approvals_respects_requested_limit_beyond_surface_cap(
    isolated_runtime,
    monkeypatch,
) -> None:
    mc = isolated_runtime.mission_control
    rows = [{"request_id": f"request-{index}", "status": "pending"} for index in range(8)]
    monkeypatch.setattr(
        mc,
        "recent_capability_approval_requests",
        lambda *, limit, user_id, include_unassigned: rows[:limit],
    )
    monkeypatch.setattr(
        mc,
        "_capability_invocation_surface",
        lambda: {"persisted_recent_invocations": [], "recent_events": []},
    )

    assert len(mc.mc_approvals(limit=20)["requests"]) == 8
    assert len(mc.mc_approvals(limit=3)["requests"]) == 3


def test_mc_approvals_combines_capability_and_expired_tool_intent(
    isolated_runtime,
) -> None:
    from core.identity.workspace_context import reset_context, set_context

    db = isolated_runtime.db
    db.init_db()
    token = set_context(workspace_name="a", user_id="user-a", role="member")
    try:
        db.create_tool_intent_approval_request(
            intent_key="intent-expired",
            intent_type="write",
            intent_target="MEMORY.md",
            approval_scope="workspace",
            approval_required=True,
            approval_reason="test",
            requested_at="2000-01-01T00:00:00+00:00",
            expires_at="2000-01-01T00:15:00+00:00",
        )
        payload = isolated_runtime.mission_control.mc_approvals(limit=20)
    finally:
        reset_context(token)

    tool_request = next(
        item for item in payload["requests"] if item["approval_system"] == "tool-intent"
    )
    assert tool_request["status"] == "expired"
    assert tool_request["active"] is False
    assert payload["summary"]["pending_count"] == 0
