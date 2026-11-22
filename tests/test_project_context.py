from __future__ import annotations

import sqlite3

import pytest

from core.runtime import db_core


@pytest.fixture
def project_db(monkeypatch, tmp_path):
    monkeypatch.setattr(db_core, "DB_PATH", tmp_path / "project.db")
    db_core._conn_pool.conn = None
    db_core._conn_pool.conn_path = None
    yield
    conn = getattr(db_core._conn_pool, "conn", None)
    if conn is not None:
        sqlite3.Connection.close(conn)
    db_core._conn_pool.conn = None
    db_core._conn_pool.conn_path = None


def test_project_binds_materials_to_session_across_calls(project_db, tmp_path):
    from core.services.project_context import (
        add_file_material,
        add_text_material,
        create_project,
        get_project_for_session,
    )

    source = tmp_path / "brief.md"
    source.write_text("kravene", encoding="utf-8")
    project = create_project(session_id="chat-1", name="Lancering")
    add_file_material(project["project_id"], path=str(source), title="Brief")
    add_text_material(project["project_id"], content="Husk målgruppen", title="Note")

    loaded = get_project_for_session("chat-1")
    assert loaded["name"] == "Lancering"
    assert [(item["kind"], item["title"]) for item in loaded["materials"]] == [
        ("file", "Brief"),
        ("text", "Note"),
    ]
    assert loaded["materials"][0]["path"] == str(source.resolve())


def test_rebinding_session_moves_it_to_new_project(project_db):
    from core.services.project_context import bind_session, create_project, get_project_for_session

    first = create_project(session_id="chat-1", name="Første")
    second = create_project(session_id="chat-2", name="Andet")
    bind_session(second["project_id"], "chat-1")

    assert get_project_for_session("chat-1")["project_id"] == second["project_id"]
    assert get_project_for_session("chat-2")["project_id"] == second["project_id"]
    assert first["project_id"] != second["project_id"]


def test_file_material_requires_real_file(project_db, tmp_path):
    from core.services.project_context import add_file_material, create_project

    project = create_project(session_id="chat-1", name="P")
    with pytest.raises(FileNotFoundError):
        add_file_material(project["project_id"], path=str(tmp_path / "missing.txt"))
