"""Tests for de udskilte capability-declaration-parsere + sti-resolution."""
from __future__ import annotations

from pathlib import Path


def test_declared_read_file_path_valid_and_invalid() -> None:
    from core.tools.workspace_capability_decl import _declared_read_file_path
    assert _declared_read_file_path("path: notes/log.md") == "notes/log.md"
    assert _declared_read_file_path("path: /etc/passwd") is None   # absolut afvist
    assert _declared_read_file_path("path: ../escape") is None     # traversal afvist
    assert _declared_read_file_path("query: hi") is None           # ingen path


def test_declared_search_file_spec() -> None:
    from core.tools.workspace_capability_decl import _declared_search_file_spec
    spec = _declared_search_file_spec("path: a/b.md\nquery: hello")
    assert spec == {"path": "a/b.md", "query": "hello"}
    assert _declared_search_file_spec("path: a/b.md") is None       # mangler query


def test_declared_exec_spec_sources() -> None:
    from core.tools.workspace_capability_decl import _declared_exec_spec
    assert _declared_exec_spec("command: ls -la")["command_source"] == "declared-command"
    assert _declared_exec_spec("command_from: user-message")["command_source"] == "invocation-argument"
    assert _declared_exec_spec("noise: x") is None


def test_is_valid_workspace_relative_path() -> None:
    from core.tools.workspace_capability_decl import _is_valid_workspace_relative_path
    assert _is_valid_workspace_relative_path("a/b.md") is True
    assert _is_valid_workspace_relative_path("/abs") is False
    assert _is_valid_workspace_relative_path("../up") is False


def test_resolve_workspace_relative_path_jail(tmp_path) -> None:
    from core.tools.workspace_capability_decl import _resolve_workspace_relative_path
    inside = _resolve_workspace_relative_path(tmp_path, "sub/file.md")
    assert inside == (tmp_path / "sub" / "file.md").resolve()
    assert _resolve_workspace_relative_path(tmp_path, "../outside.md") is None


def test_is_within_workspace_root(tmp_path) -> None:
    from core.tools.workspace_capability_decl import _is_within_workspace_root
    assert _is_within_workspace_root(tmp_path, tmp_path / "x.md") is True
    assert _is_within_workspace_root(tmp_path, Path("/etc/passwd")) is False


def test_expand_declared_path_tokens(tmp_path) -> None:
    from core.tools.workspace_capability_decl import _expand_declared_path
    expanded = _expand_declared_path("${WORKSPACE_ROOT}/x", workspace_dir=tmp_path)
    assert str(tmp_path.resolve()) in expanded
    assert _expand_declared_path("", workspace_dir=tmp_path) == ""
