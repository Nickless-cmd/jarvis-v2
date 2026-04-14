"""Tests for MEMORY.md / USER.md path canonicalization in write/edit tools."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from core.tools import simple_tools


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    ws = tmp_path / "workspaces" / "default"
    ws.mkdir(parents=True)
    monkeypatch.setattr(simple_tools, "WORKSPACE_DIR", ws)
    monkeypatch.setattr(simple_tools, "_AUTO_APPROVE_WRITE_PATHS", {
        str(ws / "MEMORY.md"), str(ws / "USER.md"),
    })
    monkeypatch.setattr(simple_tools, "_AUTO_APPROVE_WRITE_PREFIXES", [str(ws) + "/", "/tmp/"])
    return ws


def test_memory_write_to_wrong_path_redirects(workspace, tmp_path):
    wrong = tmp_path / "repo_root" / "MEMORY.md"
    result = simple_tools._exec_write_file({"path": str(wrong), "content": "- test\n"})
    assert result["status"] == "ok"
    assert result["path"] == str(workspace / "MEMORY.md")
    assert result["redirected_from"] == str(wrong.resolve())
    assert (workspace / "MEMORY.md").read_text() == "- test\n"
    assert not wrong.exists()


def test_user_md_also_redirects(workspace, tmp_path):
    wrong = tmp_path / "other" / "USER.md"
    result = simple_tools._exec_write_file({"path": str(wrong), "content": "hi"})
    assert result["status"] == "ok"
    assert result["path"] == str(workspace / "USER.md")
    assert result["redirected_from"] == str(wrong.resolve())


def test_correct_path_not_redirected(workspace):
    correct = workspace / "MEMORY.md"
    result = simple_tools._exec_write_file({"path": str(correct), "content": "x"})
    assert result["status"] == "ok"
    assert "redirected_from" not in result


def test_unrelated_file_not_redirected(workspace, tmp_path):
    other = tmp_path / "notes.md"
    result = simple_tools._exec_write_file({"path": str(other), "content": "x"})
    # Not auto-approved workspace, goes through approval flow — but path not mangled
    assert result.get("path") == str(other.resolve())
    assert "redirected_from" not in result


def test_edit_memory_wrong_path_redirects(workspace, tmp_path):
    # Seed canonical
    (workspace / "MEMORY.md").write_text("foo\n")
    wrong = tmp_path / "wrong" / "MEMORY.md"
    result = simple_tools._exec_edit_file({
        "path": str(wrong), "old_text": "foo", "new_text": "bar",
    })
    assert result["status"] == "ok"
    assert result["path"] == str(workspace / "MEMORY.md")
    assert result["redirected_from"] == str(wrong.resolve())
    assert (workspace / "MEMORY.md").read_text() == "bar\n"


def test_force_write_redirects(workspace, tmp_path):
    wrong = tmp_path / "wrong" / "MEMORY.md"
    result = simple_tools._force_write_file({"path": str(wrong), "content": "z"})
    assert result["status"] == "ok"
    assert result["path"] == str(workspace / "MEMORY.md")
    assert result["redirected_from"] == str(wrong.resolve())
