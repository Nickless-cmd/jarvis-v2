from __future__ import annotations


def test_runtime_browser_body_persists_profile_and_tabs(isolated_runtime) -> None:
    runtime_browser_body = __import__(
        "core.services.runtime_browser_body",
        fromlist=["ensure_browser_body"],
    )

    body = runtime_browser_body.ensure_browser_body(
        profile_name="jarvis-browser",
        active_task_id="task-123",
        active_flow_id="flow-123",
    )

    assert body["profile_name"] == "jarvis-browser"
    assert body["active_task_id"] == "task-123"
    assert body["active_flow_id"] == "flow-123"
    assert body["status"] == "idle"

    updated = runtime_browser_body.record_tab_snapshot(
        body_id=body["body_id"],
        tab_id="tab-1",
        url="https://example.com/docs",
        title="Docs",
        summary="Initial documentation tab",
        selected=True,
    )

    assert updated is not None
    assert updated["focused_tab_id"] == "tab-1"
    assert updated["last_url"] == "https://example.com/docs"
    assert len(updated["tabs"]) == 1

    updated = runtime_browser_body.record_tab_snapshot(
        body_id=body["body_id"],
        tab_id="tab-2",
        url="https://example.com/repo",
        title="Repo",
        summary="Repository view",
        selected=False,
    )

    assert updated is not None
    assert len(updated["tabs"]) == 2

    fetched = runtime_browser_body.get_browser_body(body["body_id"])
    assert fetched is not None
    assert fetched["body_id"] == body["body_id"]
    assert fetched["focused_tab_id"] == "tab-1"

    listed = runtime_browser_body.list_browser_bodies()
    assert any(item["body_id"] == body["body_id"] for item in listed)
