"""Google Tasks-spejlet er ekstra holdbarhed, aldrig lokal sandhed."""
from __future__ import annotations

import core.services.google_tasks_mirror as mirror


class _Response:
    def __init__(self, status_code: int, payload: dict | None = None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self) -> dict:
        return self._payload


def _state(monkeypatch):
    state: dict = {}
    monkeypatch.setattr(mirror, "get_runtime_state_value", lambda key, default=None: state.get(key, default))
    monkeypatch.setattr(mirror, "set_runtime_state_value", lambda key, value: state.__setitem__(key, value))
    monkeypatch.setattr(mirror, "get_fresh_token", lambda user_id, provider: {"access_token": "token"})
    return state


def test_create_mirror_records_remote_id_and_precise_time(monkeypatch):
    state = _state(monkeypatch)
    seen = {}

    def post(url, **kwargs):
        seen.update({"url": url, **kwargs})
        return _Response(200, {"id": "google-1"})

    monkeypatch.setattr("httpx.post", post)
    result = mirror.create_task_mirror("user-1", {
        "task_id": "sched-1", "focus": "Ring til tandlægen",
        "run_at": "2026-11-02T09:15:00+01:00",
    })

    assert result["status"] == "mirrored"
    assert seen["url"].endswith("/lists/@default/tasks")
    assert "2026-11-02T09:15:00+01:00" in seen["json"]["notes"]
    assert state["google_task_mirrors"]["user-1"]["sched-1"]["task_id"] == "google-1"


def test_create_mirror_reports_google_failure_without_raising(monkeypatch):
    _state(monkeypatch)
    monkeypatch.setattr("httpx.post", lambda *args, **kwargs: _Response(403))

    result = mirror.create_task_mirror("user-1", {
        "task_id": "sched-1", "focus": "Noget", "run_at": "2026-11-02T09:15:00Z",
    })

    assert result == {
        "status": "unavailable",
        "error": "google_tasks_scope_or_api_unavailable",
    }


def test_cancel_mirror_deletes_google_copy_and_mapping(monkeypatch):
    state = _state(monkeypatch)
    state["google_task_mirrors"] = {
        "user-1": {"sched-1": {"tasklist_id": "@default", "task_id": "google-1"}},
    }
    seen = []
    monkeypatch.setattr("httpx.delete", lambda url, **kwargs: seen.append(url) or _Response(204))

    result = mirror.cancel_task_mirror("user-1", "sched-1")

    assert result["status"] == "cancelled"
    assert seen[0].endswith("/lists/@default/tasks/google-1")
    assert "user-1" not in state["google_task_mirrors"]


def test_update_mirror_keeps_mapping_and_updates_content(monkeypatch):
    state = _state(monkeypatch)
    state["google_task_mirrors"] = {
        "user-1": {"sched-1": {"tasklist_id": "@default", "task_id": "google-1"}},
    }
    seen = {}

    def patch(url, **kwargs):
        seen.update({"url": url, **kwargs})
        return _Response(200, {"id": "google-1"})

    monkeypatch.setattr("httpx.patch", patch)
    result = mirror.update_task_mirror("user-1", {
        "task_id": "sched-1", "focus": "Nyt fokus", "run_at": "2026-11-03T10:00:00Z",
    })

    assert result["status"] == "mirrored"
    assert seen["json"]["title"] == "Nyt fokus"
    assert state["google_task_mirrors"]["user-1"]["sched-1"]["task_id"] == "google-1"
