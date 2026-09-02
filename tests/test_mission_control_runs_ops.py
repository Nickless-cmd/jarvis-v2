from __future__ import annotations


def test_mc_runs_respects_requested_limit_beyond_surface_cap(
    isolated_runtime,
    monkeypatch,
) -> None:
    mc = isolated_runtime.mission_control
    rows = [{"run_id": f"run-{index}", "status": "completed"} for index in range(8)]
    monkeypatch.setattr(mc, "recent_visible_runs", lambda limit: rows[:limit])
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
