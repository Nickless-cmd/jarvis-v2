from __future__ import annotations

import sqlite3

import pytest

from core.runtime import db_core


@pytest.fixture
def mention_db(monkeypatch, tmp_path):
    monkeypatch.setattr(db_core, "DB_PATH", tmp_path / "mentions.db")
    db_core._conn_pool.conn = None
    db_core._conn_pool.conn_path = None
    yield
    conn = getattr(db_core._conn_pool, "conn", None)
    if conn is not None:
        sqlite3.Connection.close(conn)
    db_core._conn_pool.conn = None
    db_core._conn_pool.conn_path = None


def test_file_mention_is_replaced_with_actual_file_content(mention_db, tmp_path):
    from core.services.file_mention_resolver import resolve_file_mentions

    root = tmp_path / "project"
    (root / "docs").mkdir(parents=True)
    (root / "docs" / "brief.md").write_text("Dette er den faktiske brief.", encoding="utf-8")

    resolved = resolve_file_mentions(
        "Sammenfat @docs/brief.md tak", session_id="chat-1", workspace_root=str(root)
    )

    assert "Dette er den faktiske brief." in resolved
    assert "@docs/brief.md" not in resolved
    assert "docs/brief.md" in resolved


def test_project_material_can_be_resolved_without_workspace_root(mention_db, tmp_path):
    from core.services.file_mention_resolver import resolve_file_mentions
    from core.services.project_context import add_file_material, create_project

    source = tmp_path / "facts.csv"
    source.write_text("name,value\nalpha,7\n", encoding="utf-8")
    project = create_project(session_id="chat-1", name="Analyse")
    add_file_material(project["project_id"], path=str(source))

    resolved = resolve_file_mentions("Læs @facts.csv", session_id="chat-1")
    assert "alpha,7" in resolved
    assert "@facts.csv" not in resolved


def test_unknown_mention_is_not_forwarded_as_raw_text(mention_db, tmp_path):
    from core.services.file_mention_resolver import FileMentionNotFound, resolve_file_mentions

    with pytest.raises(FileMentionNotFound):
        resolve_file_mentions(
            "Læs @missing.txt", session_id="chat-1", workspace_root=str(tmp_path)
        )


def test_email_address_is_not_treated_as_file_mention(mention_db, tmp_path):
    from core.services.file_mention_resolver import resolve_file_mentions

    message = "Skriv til bjorn@example.dk"
    assert resolve_file_mentions(
        message, session_id="chat-1", workspace_root=str(tmp_path)
    ) == message
