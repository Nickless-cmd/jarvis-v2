from __future__ import annotations

from core.tools import github_pr_tools as tools


def test_create_pr_reuses_connector(monkeypatch) -> None:
    called = {}

    def create_pr(user_id, repo, *, head, base, title, body=""):
        called.update({
            "user_id": user_id, "repo": repo, "head": head, "base": base,
            "title": title, "body": body,
        })
        return {"status": "ok", "number": 7, "url": "https://example/pr/7"}

    monkeypatch.setattr("core.services.github_connector.create_pr", create_pr)
    result = tools.execute_github_create_pr({
        "repo": "acme/widgets", "head": "feature", "base": "main",
        "title": "Ship it", "body": "Details", "_runtime_user_id": "u1",
    })

    assert result["number"] == 7
    assert called == {
        "user_id": "u1", "repo": "acme/widgets", "head": "feature",
        "base": "main", "title": "Ship it", "body": "Details",
    }


def test_ci_status_resolves_pr_head_and_combines_checks(monkeypatch) -> None:
    responses = {
        "/repos/acme/widgets/pulls/12": {
            "status": "ok", "data": {"head": {"sha": "abc123"}}
        },
        "/repos/acme/widgets/commits/abc123/check-runs": {
            "status": "ok", "data": {"check_runs": [
                {"name": "tests", "status": "completed", "conclusion": "success", "html_url": "u1"},
                {"name": "lint", "status": "in_progress", "conclusion": None, "html_url": "u2"},
            ]}
        },
        "/repos/acme/widgets/commits/abc123/status": {
            "status": "ok", "data": {"state": "pending", "statuses": []}
        },
    }
    monkeypatch.setattr(
        "core.services.github_connector._get",
        lambda user_id, path, params=None: responses[path],
    )

    result = tools.execute_github_ci_status({
        "repo": "acme/widgets", "pull_number": 12, "_runtime_user_id": "u1",
    })

    assert result["status"] == "ok"
    assert result["sha"] == "abc123"
    assert result["state"] == "pending"
    assert result["summary"] == {"total": 2, "successful": 1, "pending": 1, "failed": 0}


def test_ci_status_requires_exactly_one_target() -> None:
    assert tools.execute_github_ci_status({"repo": "a/b"}) == {
        "status": "error", "error": "commit_sha_or_pull_number_required"
    }
    assert tools.execute_github_ci_status({
        "repo": "a/b", "commit_sha": "abc", "pull_number": 1,
    }) == {"status": "error", "error": "choose_commit_sha_or_pull_number"}


def test_tools_are_registered_without_simple_tools_definitions_change() -> None:
    from core.tools import simple_tools

    names = {d.get("function", {}).get("name") for d in simple_tools.TOOL_DEFINITIONS}
    assert {"github_create_pr", "github_ci_status"} <= names
    assert simple_tools._TOOL_HANDLERS["github_create_pr"] is tools.execute_github_create_pr
    assert simple_tools._TOOL_HANDLERS["github_ci_status"] is tools.execute_github_ci_status


def test_github_connector_unlocks_pr_and_ci_tools() -> None:
    from core.services import connectors

    github = next(item for item in connectors._CATALOG if item["id"] == "github")
    assert {"github_create_pr", "github_ci_status"} <= set(github["tools"])


def test_connected_github_tools_are_visible_in_owner_code_scope(monkeypatch) -> None:
    from core.tools import simple_tools, tool_scoping

    monkeypatch.setattr(
        tool_scoping,
        "_forbundne_connector_vaerktoejer",
        lambda: frozenset({"github_create_pr", "github_ci_status"}),
    )
    names = {
        definition.get("function", {}).get("name")
        for definition in simple_tools.get_tool_definitions(role="owner", scope="code")
    }
    assert {"github_create_pr", "github_ci_status"} <= names
