"""visible_work_surfaces: udskilt fra visible_runs, samme adfaerd og samme navne."""
from __future__ import annotations

import pytest

NAMES = ("get_visible_work", "get_visible_work_surface", "get_visible_selected_work_surface",
         "get_visible_selected_work_item", "get_visible_selected_work_note")


@pytest.mark.parametrize("name", NAMES)
def test_every_function_is_reexported_from_visible_runs(name):
    from core.services import visible_runs, visible_work_surfaces

    assert getattr(visible_runs, name) is getattr(visible_work_surfaces, name)


def test_active_run_is_read_through_visible_runs_so_patches_still_apply(monkeypatch):
    from core.services import visible_runs

    monkeypatch.setattr(visible_runs, "get_active_visible_run", lambda: {
        "run_id": "r-1", "lane": "visible", "provider": "p", "model": "m",
        "started_at": "t", "current_user_message_preview": "hej", "capability_id": "c"})
    assert visible_runs.get_visible_work() == {
        "active": True, "run_id": "r-1", "status": "running", "lane": "visible",
        "provider": "p", "model": "m", "started_at": "t",
        "current_user_message_preview": "hej", "capability_id": "c"}


def test_idle_shape_comes_from_last_outcome_and_last_capability(monkeypatch):
    from core.services import visible_runs

    monkeypatch.setattr(visible_runs, "get_active_visible_run", lambda: None)
    monkeypatch.setattr(visible_runs, "get_last_visible_run_outcome", lambda: {
        "run_id": "r-0", "status": "completed", "lane": "visible", "provider": "p",
        "model": "m", "text_preview": "svar"})
    monkeypatch.setattr(visible_runs, "get_last_visible_capability_use",
                        lambda: {"capability_id": "cap"})
    assert visible_runs.get_visible_work() == {
        "active": False, "run_id": "r-0", "status": "completed", "lane": "visible",
        "provider": "p", "model": "m", "started_at": None,
        "current_user_message_preview": "svar", "capability_id": "cap"}


def test_idle_without_any_history_reports_idle(monkeypatch):
    from core.services import visible_runs

    monkeypatch.setattr(visible_runs, "get_active_visible_run", lambda: None)
    monkeypatch.setattr(visible_runs, "get_last_visible_run_outcome", lambda: None)
    monkeypatch.setattr(visible_runs, "get_last_visible_capability_use", lambda: None)
    out = visible_runs.get_visible_work()
    assert (out["active"], out["status"], out["run_id"]) == (False, "idle", None)
