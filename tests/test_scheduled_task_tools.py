"""Tool-livscyklussen beholder lokal succes og viser Google-spejlets tilstand."""
from __future__ import annotations

import core.services.google_tasks_mirror as mirror
import core.services.peak_hours as peak_hours
import core.services.scheduled_tasks as scheduled_tasks
import core.tools.scheduled_task_tools as tools


def test_schedule_creates_local_first_and_reports_successful_mirror(monkeypatch):
    order = []
    task = {
        "task_id": "sched-1", "focus": "Husk mødet",
        "run_at": "2026-11-02T09:00:00+00:00",
    }
    monkeypatch.setattr(
        scheduled_tasks, "push_scheduled_task",
        lambda **kwargs: order.append("local") or task,
    )
    monkeypatch.setattr(tools, "_operator_user_id", lambda args: "user-1")
    monkeypatch.setattr(
        mirror, "create_task_mirror",
        lambda user_id, local_task: order.append("google") or {"status": "mirrored", "task_id": "g-1"},
    )
    monkeypatch.setattr(peak_hours, "tilfoej_booking_varsel", lambda result, run_at: result)

    result = tools._exec_schedule_task({"focus": "Husk mødet", "delay_minutes": 15})

    assert order == ["local", "google"]
    assert result["status"] == "ok"
    assert result["google_tasks"]["status"] == "mirrored"
    assert "Google Tasks: mirrored" in result["text"]


def test_schedule_keeps_local_success_when_google_is_down(monkeypatch):
    monkeypatch.setattr(scheduled_tasks, "push_scheduled_task", lambda **kwargs: {
        "task_id": "sched-1", "focus": "Husk mødet", "run_at": "2026-11-02T09:00:00Z",
    })
    monkeypatch.setattr(tools, "_operator_user_id", lambda args: "user-1")
    monkeypatch.setattr(mirror, "create_task_mirror", lambda *args: {
        "status": "error", "error": "google_tasks_http_503",
    })
    monkeypatch.setattr(peak_hours, "tilfoej_booking_varsel", lambda result, run_at: result)

    result = tools._exec_schedule_task({"focus": "Husk mødet", "delay_minutes": 15})

    assert result["status"] == "ok"
    assert result["task_id"] == "sched-1"
    assert result["google_tasks"]["status"] == "error"
    assert "local operation succeeded" in result["text"]


def test_schedule_keeps_local_success_when_mirror_code_raises(monkeypatch):
    monkeypatch.setattr(scheduled_tasks, "push_scheduled_task", lambda **kwargs: {
        "task_id": "sched-1", "focus": "Husk mødet", "run_at": "2026-11-02T09:00:00Z",
    })
    monkeypatch.setattr(tools, "_operator_user_id", lambda args: "user-1")
    monkeypatch.setattr(mirror, "create_task_mirror", lambda *args: (_ for _ in ()).throw(RuntimeError("boom")))
    monkeypatch.setattr(peak_hours, "tilfoej_booking_varsel", lambda result, run_at: result)

    result = tools._exec_schedule_task({"focus": "Husk mødet", "delay_minutes": 15})

    assert result["status"] == "ok"
    assert result["google_tasks"]["status"] == "error"
    assert "google_tasks_internal_error" in result["google_tasks"]["error"]


def test_cancel_removes_google_copy_after_local_cancel(monkeypatch):
    monkeypatch.setattr(scheduled_tasks, "cancel_scheduled_task", lambda task_id: True)
    monkeypatch.setattr(tools, "_operator_user_id", lambda args: "user-1")
    monkeypatch.setattr(mirror, "cancel_task_mirror", lambda user_id, task_id: {
        "status": "cancelled", "task_id": "g-1",
    })

    result = tools._exec_cancel_task({"task_id": "sched-1"})

    assert result["status"] == "ok"
    assert result["google_tasks"]["status"] == "cancelled"


def test_edit_updates_google_copy_after_local_edit(monkeypatch):
    task = {"task_id": "sched-1", "focus": "Nyt", "run_at": "2026-11-03T10:00:00Z"}
    monkeypatch.setattr(scheduled_tasks, "edit_scheduled_task", lambda *args, **kwargs: {
        "status": "ok", "task": task, "text": "Updated task sched-1",
    })
    monkeypatch.setattr(tools, "_operator_user_id", lambda args: "user-1")
    monkeypatch.setattr(mirror, "update_task_mirror", lambda user_id, local_task: {"status": "mirrored"})

    result = tools._exec_edit_task({"task_id": "sched-1", "focus": "Nyt"})

    assert result["status"] == "ok"
    assert result["google_tasks"]["status"] == "mirrored"
