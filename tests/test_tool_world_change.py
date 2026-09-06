"""Ændrede kaldet verden? (loop-fix 5/9-2026)

Grundlaget for at verifikation efter skrivning må gentage en tidligere
kommando — og for ikke at læse en skrivende runde som "ingen fremgang".
"""
from __future__ import annotations

import pytest

from core.services import tool_world_change as TWC


@pytest.mark.parametrize("tool", ["edit_file", "write_file", "publish_file", "stage_edit_file"])
def test_file_writers_change_the_world(tool):
    assert TWC.call_changed_the_world(tool_name=tool, arguments={"path": "/x/USER.md"}) is True


@pytest.mark.parametrize("cmd,changed", [
    ("grep -n 'DeepSeek' /home/bs/.jarvis-v2/workspaces/bjorn/USER.md", False),
    ("cat USER.md", False),
    ("ls -la ~/.jarvis-v2/workspaces/bjorn", False),
    ("sed -i 's/a/b/' USER.md", True),
    ("echo hej > fil.txt", True),
    ("python scripts/user_md_learned_migration.py --apply", True),
])
def test_bash_is_judged_on_the_command_not_the_name(cmd, changed):
    assert TWC.call_changed_the_world(tool_name="bash", arguments={"command": cmd}) is changed


def test_a_failed_call_changed_nothing():
    assert TWC.call_changed_the_world(
        tool_name="edit_file", arguments={"path": "/x"}, status="error") is False
    assert TWC.call_changed_the_world(
        tool_name="bash", arguments={"command": "sed -i s/a/b/ f"},
        status="duplicate_suppressed") is False


def test_pure_readers_change_nothing():
    for tool in ("read_file", "search_memory", "recall_memories", "find_files"):
        assert TWC.call_changed_the_world(tool_name=tool, arguments={"path": "/x"}) is False


def test_bash_without_a_command_is_not_a_mutation():
    assert TWC.call_changed_the_world(tool_name="bash", arguments={}) is False


def test_round_is_a_mutation_if_any_call_was():
    results = [
        {"tool_name": "read_file", "arguments": {"path": "/x"}, "status": "ok"},
        {"tool_name": "edit_file", "arguments": {"path": "/x"}, "status": "ok"},
    ]
    assert TWC.round_changed_the_world(results) is True
    assert TWC.round_changed_the_world(results[:1]) is False
    assert TWC.round_changed_the_world([]) is False
    assert TWC.round_changed_the_world(None) is False


def test_malformed_results_never_raise():
    assert TWC.round_changed_the_world(["ikke en dict", None, {}]) is False
