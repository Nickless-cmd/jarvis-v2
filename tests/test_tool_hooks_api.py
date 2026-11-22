from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException


def test_hook_status_exposes_loaded_hooks_and_log_metadata(tmp_path, monkeypatch) -> None:
    from apps.api.jarvis_api.routes import tool_hooks as routes
    from core.services import tool_shell_hooks as hooks

    log = tmp_path / "tool_hooks.jsonl"
    log.write_text('{"time":"2026-11-22T10:00:00Z","tool":"bash"}\n', encoding="utf-8")
    (tmp_path / "tool_hooks.jsonl.1").write_text("old\n", encoding="utf-8")
    monkeypatch.setattr(hooks, "LOG_STI", log)
    monkeypatch.setattr(hooks, "status", lambda: {
        "enabled": True, "config": "/tmp/tool_hooks.json", "config_findes": True,
        "hooks": [{"name": "audit", "match": ".*", "before": False,
                   "after": True, "timeout_s": 5.0, "active": True}],
    })

    result = routes.get_tool_hooks()

    assert result["enabled"] is True
    assert result["hooks"][0]["name"] == "audit"
    assert result["log"]["size_bytes"] == log.stat().st_size
    assert result["log"]["rotated"] is True


def test_hook_log_returns_structured_tail_and_measured_coverage(tmp_path, monkeypatch) -> None:
    from apps.api.jarvis_api.routes import tool_hooks as routes
    from core.services import tool_shell_hooks as hooks

    now = datetime.now(UTC)
    rows = [
        {"time": (now - timedelta(minutes=3)).isoformat(), "tool": "bash", "phase": "after",
         "arguments": {"__result__": {"status": "ok", "confinement": {"actual": True}}}},
        {"time": (now - timedelta(minutes=2)).isoformat(), "tool": "bash", "phase": "after",
         "arguments": {"__result__": {"status": "ok", "confinement": {"requested": True, "actual": False}}}},
        {"time": (now - timedelta(minutes=1)).isoformat(), "tool": "read_file", "phase": "after",
         "result": "ok"},
    ]
    log = tmp_path / "tool_hooks.jsonl"
    log.write_text("not-json\n" + "\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    monkeypatch.setattr(hooks, "LOG_STI", log)

    result = routes.get_tool_hook_log(limit=2)

    assert [entry["tool"] for entry in result["entries"]] == ["bash", "read_file"]
    assert result["entries"][0]["result"] == "ok"
    assert result["coverage_24h"] == {"confined": 1, "fail_open": 1, "non_shell": 1}
    assert result["invalid_lines"] == 1


def test_reload_forces_service_reload(monkeypatch) -> None:
    from apps.api.jarvis_api.routes import tool_hooks as routes
    from core.services import tool_shell_hooks as hooks

    calls: list[bool] = []
    monkeypatch.setattr(hooks, "ensure_loaded", lambda *, tving=False: calls.append(tving) or True)
    monkeypatch.setattr(hooks, "status", lambda: {"enabled": True, "hooks": []})

    assert routes.reload_tool_hooks()["enabled"] is True
    assert calls == [True]


def test_github_routes_reuse_handlers_and_gate_creation(monkeypatch) -> None:
    from apps.api.jarvis_api.routes import github as routes

    monkeypatch.setattr(routes, "_bruger", lambda: "owner-1")
    monkeypatch.setattr(routes.github_tools, "execute_github_list_prs", lambda args: {
        "status": "ok", "prs": [{"number": 7, "title": "Visible", "url": "https://example/pr/7"}],
        "seen": args,
    })
    monkeypatch.setattr(routes.github_tools, "execute_github_ci_status", lambda args: {
        "status": "ok", "state": "success", "seen": args,
    })
    created: list[dict] = []
    monkeypatch.setattr(routes.github_tools, "execute_github_create_pr", lambda args: created.append(args) or {
        "status": "ok", "number": 8,
    })

    prs = routes.github_prs(repo="o/r")
    ci = routes.github_ci(repo="o/r", pull_number=7, commit_sha="")
    assert prs["prs"][0]["number"] == 7
    assert prs["seen"]["_runtime_user_id"] == "owner-1"
    assert ci["seen"]["pull_number"] == 7

    with pytest.raises(HTTPException) as denied:
        routes.github_create_pr(routes.CreatePrBody(repo="o/r", head="topic", title="T", approved=False))
    assert denied.value.status_code == 409
    assert created == []

    result = routes.github_create_pr(
        routes.CreatePrBody(repo="o/r", head="topic", base="main", title="T", approved=True),
    )
    assert result["number"] == 8
    assert created[0]["_runtime_user_id"] == "owner-1"

