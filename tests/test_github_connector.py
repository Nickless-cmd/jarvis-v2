"""GitHub-connector: tool-handlers bruger fresh token + kalder GitHub API."""
from __future__ import annotations

import core.services.github_connector as gh


def test_list_issues(monkeypatch):
    monkeypatch.setattr(gh, "get_fresh_token", lambda uid, pid="github": {"access_token": "t"})
    import httpx
    class _R:
        status_code = 200
        def json(self): return [{"number": 1, "title": "Bug", "state": "open"}]
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _R())
    out = gh.list_issues("alice", repo="o/r")
    assert out["status"] == "ok" and out["issues"][0]["title"] == "Bug"


def test_list_issues_not_connected(monkeypatch):
    monkeypatch.setattr(gh, "get_fresh_token", lambda uid, pid="github": None)
    out = gh.list_issues("alice", repo="o/r")
    assert out["status"] == "error" and out["error"] == "github_not_connected"


def test_list_prs(monkeypatch):
    monkeypatch.setattr(gh, "get_fresh_token", lambda uid, pid="github": {"access_token": "t"})
    import httpx
    class _R:
        status_code = 200
        def json(self): return [{"number": 7, "title": "Feat", "state": "open"}]
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _R())
    out = gh.list_prs("alice", repo="o/r")
    assert out["status"] == "ok" and out["prs"][0]["number"] == 7
