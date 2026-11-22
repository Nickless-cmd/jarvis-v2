from __future__ import annotations

import pytest

from core.runtime import db_core


@pytest.fixture
def artifact_db(monkeypatch, tmp_path):
    monkeypatch.setattr(db_core, "DB_PATH", tmp_path / "artifact.db")
    db_core._conn_pool.conn = None
    db_core._conn_pool.conn_path = None
    yield
    conn = getattr(db_core._conn_pool, "conn", None)
    if conn is not None:
        import sqlite3

        sqlite3.Connection.close(conn)
    db_core._conn_pool.conn = None
    db_core._conn_pool.conn_path = None


def test_canvas_document_survives_reads_and_tracks_versions(artifact_db):
    from core.services.artifact_document import create_document, get_document, update_document

    created = create_document(
        session_id="chat-1", title="Udkast", content="første", content_type="text/markdown"
    )
    assert created["version"] == 1
    assert get_document(created["document_id"])["content"] == "første"

    updated = update_document(
        created["document_id"], content="andet", expected_version=1
    )
    assert updated["version"] == 2
    assert get_document(created["document_id"])["content"] == "andet"


def test_canvas_document_rejects_stale_update(artifact_db):
    from core.services.artifact_document import VersionConflict, create_document, update_document

    created = create_document(session_id="chat-1", title="Udkast", content="v1")
    update_document(created["document_id"], content="v2", expected_version=1)

    with pytest.raises(VersionConflict):
        update_document(created["document_id"], content="tabt", expected_version=1)


def test_canvas_documents_are_listed_per_session(artifact_db):
    from core.services.artifact_document import create_document, list_documents

    create_document(session_id="chat-1", title="A", content="a")
    create_document(session_id="chat-2", title="B", content="b")

    docs = list_documents("chat-1")
    assert [doc["title"] for doc in docs] == ["A"]
