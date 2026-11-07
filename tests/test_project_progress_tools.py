"""sustained_project og creative_project (core/tools/project_progress_tools.py).

Testene kalder ``execute_tool`` — den indgang Jarvis' modelkald går igennem — og
læser tilstanden direkte fra JSON-filen bagefter, ikke gennem service-laget.
Fjernes kaldet til service-funktionen i værktøjet, står filen uændret og testen
fejler (mutationskørsel: se docs/notes/2026-11-07-dormant-triage.md).
"""
from __future__ import annotations

import json

import pytest

import core.services.creative_projects as creative
import core.services.sustained_attention as sustained
from core.tools.simple_tools import _TOOL_HANDLERS, execute_tool
from core.tools.simple_tools_definitions import TOOL_DEFINITIONS

def _file(path):
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def sustained_file(tmp_path, monkeypatch):
    path = tmp_path / "sustained_attention.json"
    monkeypatch.setattr(sustained, "_storage_path", lambda: path)
    return path


@pytest.fixture
def creative_file(tmp_path, monkeypatch):
    path = tmp_path / "creative_projects.json"
    monkeypatch.setattr(creative, "_storage_path", lambda: path)
    return path


_NEW_TOOLS = ('sustained_project', 'creative_project')


def test_new_tools_are_registered_in_both_tables():
    defined = {d["function"]["name"] for d in TOOL_DEFINITIONS}
    for name in _NEW_TOOLS:
        assert name in defined, f"{name} has no schema in TOOL_DEFINITIONS"
        assert name in _TOOL_HANDLERS, f"{name} has no handler in the dispatch table"


# ── sustained_attention.add_progress (+ create_project) ────────────────────

def test_sustained_create_then_progress_lands_in_the_file(sustained_file):
    created = execute_tool("sustained_project", {
        "action": "create", "name": "Bygge broen", "why": "Den mangler", "priority": "high",
    })
    assert created["status"] == "ok"
    pid = created["project"]["id"]
    on_disk = _file(sustained_file)
    assert [p["id"] for p in on_disk] == [pid]
    assert on_disk[0]["progress_notes"] == []

    result = execute_tool("sustained_project", {
        "action": "progress", "project_id": pid, "note": "Pillerne står",
    })

    assert result["status"] == "ok"
    on_disk = _file(sustained_file)
    assert [n["note"] for n in on_disk[0]["progress_notes"]] == ["Pillerne står"]
    assert on_disk[0]["last_worked_at"] == on_disk[0]["progress_notes"][0]["at"]
    assert result["project"]["progress_notes"][0]["note"] == "Pillerne står"


def test_sustained_progress_resumes_a_paused_project(sustained_file):
    pid = execute_tool("sustained_project", {"action": "create", "name": "P"})["project"]["id"]
    sustained.set_status(pid, "paused")

    execute_tool("sustained_project", {"action": "progress", "project_id": pid, "note": "tilbage"})

    assert _file(sustained_file)[0]["status"] == "active"


def test_sustained_list_returns_what_is_on_disk(sustained_file):
    execute_tool("sustained_project", {"action": "create", "name": "A"})
    result = execute_tool("sustained_project", {"action": "list"})
    assert result["status"] == "ok"
    assert result["count"] == 1
    assert [p["name"] for p in result["projects"]] == ["A"]


@pytest.mark.parametrize(
    ("args", "fragment"),
    [
        ({}, "action must be one of"),
        ({"action": "wipe"}, "action must be one of"),
        ({"action": "create"}, "name is required"),
        ({"action": "progress", "note": "x"}, "project_id is required"),
        ({"action": "progress", "project_id": "proj-x"}, "note is required"),
        ({"action": "progress", "project_id": "proj-ukendt", "note": "x"}, "not found"),
    ],
)
def test_sustained_errors_are_honest_and_write_nothing(sustained_file, args, fragment):
    result = execute_tool("sustained_project", args)
    assert result["status"] == "error"
    assert fragment in result["error"]
    assert not sustained_file.exists()


def test_sustained_progress_on_a_completed_project_names_the_status(sustained_file):
    pid = execute_tool("sustained_project", {"action": "create", "name": "P"})["project"]["id"]
    sustained.set_status(pid, "completed")

    result = execute_tool("sustained_project", {"action": "progress", "project_id": pid, "note": "x"})

    assert result["status"] == "error"
    assert "completed" in result["error"]
    assert _file(sustained_file)[0]["progress_notes"] == []


def test_sustained_create_surfaces_the_active_cap_as_an_error(sustained_file):
    for i in range(sustained._MAX_ACTIVE):
        assert execute_tool("sustained_project", {"action": "create", "name": f"P{i}"})["status"] == "ok"

    result = execute_tool("sustained_project", {"action": "create", "name": "for mange"})

    assert result["status"] == "error"
    assert "Max" in result["error"]
    assert len(_file(sustained_file)) == sustained._MAX_ACTIVE


# ── creative_projects.add_progress_note ────────────────────────────────────

def test_creative_progress_note_lands_in_the_file(creative_file):
    pid = creative.create_project(title="Digtet", intent="Om havet")["project_id"]
    before = _file(creative_file)["projects"][0]["updated_at"]

    result = execute_tool("creative_project", {
        "action": "progress", "project_id": pid, "note": "Første strofe",
    })

    assert result["status"] == "ok"
    project = _file(creative_file)["projects"][0]
    assert [n["note"] for n in project["progress_notes"]] == ["Første strofe"]
    assert project["updated_at"] >= before
    assert result["project"]["progress_notes"][0]["note"] == "Første strofe"


@pytest.mark.parametrize(
    ("args", "fragment"),
    [
        ({"action": "create"}, "action must be one of"),
        ({"action": "progress", "note": "x"}, "project_id is required"),
        ({"action": "progress", "project_id": "cp-x"}, "note is required"),
        ({"action": "progress", "project_id": "cp-ukendt", "note": "x"}, "not found"),
    ],
)
def test_creative_errors_are_honest_and_write_nothing(creative_file, args, fragment):
    creative.create_project(title="T", intent="i")
    snapshot = creative_file.read_text(encoding="utf-8")

    result = execute_tool("creative_project", args)

    assert result["status"] == "error"
    assert fragment in result["error"]
    assert creative_file.read_text(encoding="utf-8") == snapshot


def test_creative_list_filters_by_status(creative_file):
    creative.create_project(title="A", intent="i", status="active")
    creative.create_project(title="D", intent="i")
    result = execute_tool("creative_project", {"action": "list", "status": "active"})
    assert result["status"] == "ok"
    assert [p["title"] for p in result["projects"]] == ["A"]
