"""A message undo restores only its own file writes when nothing changed since."""
from __future__ import annotations

import json
import sqlite3

import pytest

from core.undo import message_edits as undo


@pytest.fixture(autouse=True)
def store(monkeypatch):
    saved: dict[str, object] = {}
    monkeypatch.setattr(undo, "_load", lambda key: saved.get(key))
    monkeypatch.setattr(undo, "_save", lambda key, value: saved.__setitem__(key, value))
    return saved


def test_restores_only_the_message_files(tmp_path, monkeypatch):
    first = tmp_path / "first.txt"
    other = tmp_path / "other.txt"
    first.write_text("before")
    other.write_text("keep")
    before = undo.capture_before("s1", "call-1", "write_file", {"path": str(first)})
    first.write_text("after")
    undo.capture_after(before, {"status": "ok"})
    monkeypatch.setattr(undo, "_message_blocks", lambda sid, mid: [
        {"type": "tool_use", "id": "call-1", "name": "write_file"}
    ])
    result = undo.undo_message("s1", "m1")
    assert result["status"] == "ok"
    assert first.read_text() == "before"
    assert other.read_text() == "keep"


def test_refuses_to_overwrite_later_edits(tmp_path, monkeypatch):
    path = tmp_path / "file.txt"
    path.write_text("before")
    before = undo.capture_before("s1", "call-1", "edit_file", {"path": str(path)})
    path.write_text("after")
    undo.capture_after(before, {"status": "ok"})
    path.write_text("newer")
    monkeypatch.setattr(undo, "_message_blocks", lambda sid, mid: [
        {"type": "tool_use", "id": "call-1", "name": "edit_file"}
    ])
    assert undo.undo_message("s1", "m1")["status"] == "conflict"
    assert path.read_text() == "newer"


def test_restores_created_file_by_removing_it(tmp_path, monkeypatch):
    path = tmp_path / "new.txt"
    before = undo.capture_before("s1", "call-1", "write_file", {"path": str(path)})
    path.write_text("created")
    undo.capture_after(before, {"status": "ok"})
    monkeypatch.setattr(undo, "_message_blocks", lambda sid, mid: [
        {"type": "tool_use", "id": "call-1", "name": "write_file"}
    ])
    assert undo.undo_message("s1", "m1")["status"] == "ok"
    assert not path.exists()


def test_same_file_twice_returns_to_original(tmp_path, monkeypatch):
    path = tmp_path / "file.txt"
    path.write_text("one")
    a = undo.capture_before("s1", "call-1", "edit_file", {"path": str(path)})
    path.write_text("two")
    undo.capture_after(a, {"status": "ok"})
    b = undo.capture_before("s1", "call-2", "edit_file", {"path": str(path)})
    path.write_text("three")
    undo.capture_after(b, {"status": "ok"})
    monkeypatch.setattr(undo, "_message_blocks", lambda sid, mid: [
        {"type": "tool_use", "id": "call-1", "name": "edit_file"},
        {"type": "tool_use", "id": "call-2", "name": "edit_file"},
    ])
    assert undo.undo_message("s1", "m1")["status"] == "ok"
    assert path.read_text() == "one"


def test_external_change_between_two_calls_blocks_undo(tmp_path, monkeypatch):
    path = tmp_path / "file.txt"
    path.write_text("one")
    a = undo.capture_before("s1", "call-1", "edit_file", {"path": str(path)})
    path.write_text("two")
    undo.capture_after(a, {"status": "ok"})
    path.write_text("external")
    b = undo.capture_before("s1", "call-2", "edit_file", {"path": str(path)})
    path.write_text("three")
    undo.capture_after(b, {"status": "ok"})
    monkeypatch.setattr(undo, "_message_blocks", lambda sid, mid: [
        {"type": "tool_use", "id": "call-1", "name": "edit_file"},
        {"type": "tool_use", "id": "call-2", "name": "edit_file"},
    ])
    assert undo.undo_message("s1", "m1")["status"] == "conflict"
    assert path.read_text() == "three"


def test_operator_file_uses_bridge_snapshot(monkeypatch):
    remote = {"/home/bs/file.txt": "one"}
    monkeypatch.setattr(undo, "_remote_read", lambda path, user: remote[path])
    monkeypatch.setattr(undo, "_remote_write", lambda path, user, content: remote.__setitem__(path, content))
    before = undo.capture_before("s1", "call-1", "operator_edit_file",
                                 {"path": "/home/bs/file.txt", "_runtime_user_id": "bjorn"})
    remote["/home/bs/file.txt"] = "two"
    undo.capture_after(before, {"status": "ok"})
    monkeypatch.setattr(undo, "_message_blocks", lambda sid, mid: [
        {"type": "tool_use", "id": "call-1", "name": "operator_edit_file"}
    ])
    assert undo.undo_message("s1", "m1")["status"] == "ok"
    assert remote["/home/bs/file.txt"] == "one"


def test_conflict_in_one_file_keeps_all_files(tmp_path, monkeypatch):
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_text("a0")
    b.write_text("b0")
    for call_id, path, after in [("a", a, "a1"), ("b", b, "b1")]:
        before = undo.capture_before("s1", call_id, "edit_file", {"path": str(path)})
        path.write_text(after)
        undo.capture_after(before, {"status": "ok"})
    b.write_text("b2")
    monkeypatch.setattr(undo, "_message_blocks", lambda sid, mid: [
        {"type": "tool_use", "id": "a", "name": "edit_file"},
        {"type": "tool_use", "id": "b", "name": "edit_file"},
    ])
    assert undo.undo_message("s1", "m1")["status"] == "conflict"
    assert a.read_text() == "a1"
    assert b.read_text() == "b2"


def test_message_lookup_is_bound_to_session(tmp_path, monkeypatch):
    database = tmp_path / "chat.db"
    with sqlite3.connect(database) as conn:
        conn.execute("CREATE TABLE chat_messages (session_id TEXT, message_id TEXT, role TEXT, content_json TEXT)")
        conn.execute("INSERT INTO chat_messages VALUES (?, ?, ?, ?)",
                     ("s1", "m1", "assistant", json.dumps([{"type": "tool_use", "id": "a"}])))

    def connect():
        conn = sqlite3.connect(database)
        conn.row_factory = sqlite3.Row
        return conn

    monkeypatch.setattr("core.runtime.db_core.connect", connect)
    assert undo._message_blocks("s1", "m1") == [{"type": "tool_use", "id": "a"}]
    assert undo._message_blocks("s2", "m1") is None


def test_permission_change_after_message_blocks_undo(tmp_path, monkeypatch):
    path = tmp_path / "file.txt"
    path.write_text("before")
    before = undo.capture_before("s1", "call-1", "edit_file", {"path": str(path)})
    path.write_text("after")
    undo.capture_after(before, {"status": "ok"})
    path.chmod(0o600)
    monkeypatch.setattr(undo, "_message_blocks", lambda sid, mid: [
        {"type": "tool_use", "id": "call-1", "name": "edit_file"}
    ])
    assert undo.undo_message("s1", "m1")["status"] == "conflict"
    assert path.read_text() == "after"
