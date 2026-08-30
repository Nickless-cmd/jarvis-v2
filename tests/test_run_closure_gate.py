"""Tests for run_closure_gate — detect silent runs + unstaged changes.

2026-05-22 (Claude): added after Bjørn reported the pattern where agentic
runs end without delivering a reply, or leave uncommitted code in the
working tree. The gate must:
  1. snapshot git state pre-run, diff post-run, publish notice if new
  2. detect tool-call-without-output and publish silent-run event
"""
from __future__ import annotations

import subprocess
from types import SimpleNamespace
from unittest.mock import patch

from core.services.run_closure_gate import (
    _summarize_unstaged,
    _record_pre_run_state,
    _pop_pre_run_state,
    _record_tool_call,
    _pop_tool_calls,
)


class TestSummarizeUnstaged:
    def test_extracts_paths_from_porcelain_lines(self):
        diff = {" M core/foo.py", "?? new/bar.py", "M  staged/baz.py"}
        out = _summarize_unstaged(diff)
        assert out["count"] == 3
        assert "core/foo.py" in out["paths"]
        assert "new/bar.py" in out["paths"]
        assert "staged/baz.py" in out["paths"]

    def test_truncates_at_limit(self):
        diff = {f" M file{i:02d}.py" for i in range(20)}
        out = _summarize_unstaged(diff, limit=5)
        assert out["count"] == 20
        assert len(out["paths"]) == 5
        assert out["truncated"] is True

    def test_empty_input(self):
        out = _summarize_unstaged(set())
        assert out["count"] == 0
        assert out["paths"] == []
        assert out["truncated"] is False


class TestPreRunGitSnapshot:
    def test_record_and_pop_round_trip(self):
        with patch(
            "core.services.run_closure_gate._git_porcelain_status",
            return_value={" M file.py", "?? other.py"},
        ), patch(
            "core.services.run_closure_gate._git_dirty_content_hashes",
            return_value={"file.py": "abc123"},
        ):
            _record_pre_run_state("test-run-1")
        lines, hashes = _pop_pre_run_state("test-run-1")
        assert " M file.py" in lines
        assert "?? other.py" in lines
        assert hashes == {"file.py": "abc123"}

    def test_pop_unknown_returns_empty(self):
        lines, hashes = _pop_pre_run_state("nonexistent")
        assert lines == set()
        assert hashes == {}

    def test_pop_is_destructive(self):
        with patch(
            "core.services.run_closure_gate._git_porcelain_status",
            return_value={" M f.py"},
        ), patch(
            "core.services.run_closure_gate._git_dirty_content_hashes",
            return_value={"f.py": "h1"},
        ):
            _record_pre_run_state("rid-2")
        lines, hashes = _pop_pre_run_state("rid-2")
        assert lines == {" M f.py"}
        assert hashes == {"f.py": "h1"}
        # second pop returns empty
        lines2, hashes2 = _pop_pre_run_state("rid-2")
        assert lines2 == set()
        assert hashes2 == {}

    def test_empty_run_id_ignored(self):
        _record_pre_run_state("")  # no-op, shouldn't raise


class TestToolCallTracking:
    def test_records_tools_per_run(self):
        _record_tool_call("rid-A", "bash")
        _record_tool_call("rid-A", "edit_file")
        _record_tool_call("rid-A", "bash")
        out = _pop_tool_calls("rid-A")
        assert out == ["bash", "edit_file", "bash"]

    def test_isolates_runs(self):
        _record_tool_call("rid-X", "bash")
        _record_tool_call("rid-Y", "edit_file")
        assert _pop_tool_calls("rid-X") == ["bash"]
        assert _pop_tool_calls("rid-Y") == ["edit_file"]

    def test_pop_unknown_returns_empty(self):
        assert _pop_tool_calls("nonexistent") == []

    def test_empty_inputs_ignored(self):
        _record_tool_call("", "bash")
        _record_tool_call("rid", "")
        assert _pop_tool_calls("rid") == []


class TestOnRunCompletedFlow:
    def test_publishes_unstaged_when_diff(self):
        from core.services.run_closure_gate import _on_run_completed

        published_events = []

        class FakeBus:
            def publish(self, kind, payload):
                published_events.append((kind, payload))

        with patch(
            "core.services.run_closure_gate._git_porcelain_status",
            return_value={" M new_file.py"},
        ), patch(
            "core.services.run_closure_gate._git_dirty_content_hashes",
            return_value={"new_file.py": "h-after"},
        ), patch(
            "core.eventbus.bus.event_bus", FakeBus(),
        ), patch(
            "core.services.run_closure_gate._pop_pre_run_state",
            return_value=(set(), {}),
        ):
            _on_run_completed({"run_id": "test-rid", "session_id": "test-sid"})

        kinds = [k for k, _ in published_events]
        assert "runtime.run_left_unstaged_changes" in kinds

    def test_no_publish_when_no_diff(self):
        from core.services.run_closure_gate import _on_run_completed

        published = []

        class FakeBus:
            def publish(self, kind, payload):
                published.append(kind)

        # Pre and post identical → no diff
        with patch(
            "core.services.run_closure_gate._git_porcelain_status",
            return_value={" M existing.py"},
        ), patch(
            "core.services.run_closure_gate._git_dirty_content_hashes",
            return_value={"existing.py": "same-hash"},
        ), patch(
            "core.eventbus.bus.event_bus", FakeBus(),
        ), patch(
            "core.services.run_closure_gate._pop_pre_run_state",
            return_value=({" M existing.py"}, {"existing.py": "same-hash"}),
        ):
            _on_run_completed({"run_id": "r", "session_id": "s"})

        assert "runtime.run_left_unstaged_changes" not in published

    def test_content_change_detected_even_when_porcelain_unchanged(self):
        """Critical: modify-modify within run window must be detected.

        Pre and post both show " M file.py" in porcelain — diff is empty
        — but the content hash changed, so the gate should still fire.
        """
        from core.services.run_closure_gate import _on_run_completed

        published = []

        class FakeBus:
            def publish(self, kind, payload):
                published.append((kind, payload))

        with patch(
            "core.services.run_closure_gate._git_porcelain_status",
            return_value={" M file.py"},  # same line both pre and post
        ), patch(
            "core.services.run_closure_gate._git_dirty_content_hashes",
            return_value={"file.py": "hash-after"},
        ), patch(
            "core.eventbus.bus.event_bus", FakeBus(),
        ), patch(
            "core.services.run_closure_gate._pop_pre_run_state",
            return_value=({" M file.py"}, {"file.py": "hash-before"}),
        ):
            _on_run_completed({"run_id": "r", "session_id": "s"})

        kinds = [k for k, _ in published]
        assert "runtime.run_left_unstaged_changes" in kinds
        # And the payload should mention the file
        payload = next(p for k, p in published if k == "runtime.run_left_unstaged_changes")
        assert "file.py" in payload["summary"]["paths"]


class TestAutoCommitExclusion:
    """Artefakt-filer må aldrig auto-committes — de hører ikke i git."""

    def test_excludes_backup_and_artifact_suffixes(self):
        from core.services.run_closure_gate import _is_auto_commit_excluded
        assert _is_auto_commit_excluded("core/foo.py.bak")
        assert _is_auto_commit_excluded("core/foo.py.orig")
        assert _is_auto_commit_excluded("core/foo.py~")
        assert _is_auto_commit_excluded("core/foo.tmp")
        assert _is_auto_commit_excluded("core/foo.pyc")

    def test_excludes_pycache_and_lock_parts(self):
        from core.services.run_closure_gate import _is_auto_commit_excluded
        assert _is_auto_commit_excluded("core/__pycache__/foo.cpython-311.pyc")
        assert _is_auto_commit_excluded("dist/foo.lock")

    def test_keeps_real_source_paths(self):
        from core.services.run_closure_gate import _is_auto_commit_excluded
        assert not _is_auto_commit_excluded("core/foo.py")
        assert not _is_auto_commit_excluded("docs/notes.md")
        assert not _is_auto_commit_excluded("tests/test_foo.py")


class TestAutoCommitGate:
    """_try_auto_commit: forsegl autonome runs' rørte filer gennem git commit."""

    def _fake_git(self, *, commit_rc: int = 0, commit_stderr: str = ""):
        """Return (fake_run, calls) der dispatcher på git-subkommandoer."""
        calls: list[list[str]] = []

        def fake_run(args, **kwargs):
            calls.append(list(args))
            if args[:2] == ["git", "add"]:
                return SimpleNamespace(returncode=0, stdout="", stderr="")
            if args[:2] == ["git", "commit"]:
                return SimpleNamespace(returncode=commit_rc, stdout="", stderr=commit_stderr)
            if args[:2] == ["git", "rev-parse"]:
                return SimpleNamespace(returncode=0, stdout="abc1234\n", stderr="")
            if args[:2] == ["git", "restore"]:
                return SimpleNamespace(returncode=0, stdout="", stderr="")
            return subprocess.run(args, **kwargs)

        return fake_run, calls

    def test_commits_touched_paths_and_returns_short_hash(self):
        from core.services.run_closure_gate import _try_auto_commit
        fake_run, calls = self._fake_git()
        with patch("core.services.run_closure_gate._git_staged_paths", return_value=set()), \
             patch("core.services.run_closure_gate.subprocess.run", side_effect=fake_run):
            short = _try_auto_commit(
                {"core/services/run_closure_gate.py"},
                run_id="rid-1", session_id="sid-1", focus="test fix",
            )
        assert short == "abc1234"
        # add kaldt med præcis den rørte fil — aldrig -A
        add_call = next(c for c in calls if c[:2] == ["git", "add"])
        assert "core/services/run_closure_gate.py" in add_call

    def test_never_commits_artifacts(self):
        from core.services.run_closure_gate import _try_auto_commit
        fake_run, _ = self._fake_git()
        with patch("core.services.run_closure_gate._git_staged_paths", return_value=set()), \
             patch("core.services.run_closure_gate.subprocess.run", side_effect=fake_run):
            short = _try_auto_commit(
                {"core/foo.py.bak", "core/__pycache__/x.pyc"},
                run_id="rid-2", session_id="sid-2", focus="only artifacts",
            )
        assert short is None

    def test_abstains_when_user_has_staged_changes(self):
        from core.services import run_closure_gate as gate_mod
        from core.services.run_closure_gate import _try_auto_commit
        fake_run, calls = self._fake_git()
        with patch("core.services.run_closure_gate._git_staged_paths",
                   return_value={"core/user_work.py"}), \
             patch("core.services.run_closure_gate.subprocess.run", side_effect=fake_run):
            short = _try_auto_commit(
                {"core/services/run_closure_gate.py"},
                run_id="rid-3", session_id="sid-3", focus="x",
            )
        assert short is None
        assert "allerede staged" in gate_mod._last_auto_commit_error
        # git add må ALDRIG have kørt oven i brugerens staged arbejde
        assert not any(c[:2] == ["git", "add"] for c in calls)

    def test_unstages_and_records_error_when_hook_blocks(self):
        from core.services import run_closure_gate as gate_mod
        from core.services.run_closure_gate import _try_auto_commit
        fake_run, calls = self._fake_git(
            commit_rc=1, commit_stderr="docs-drift: API docs are stale\n"
        )
        with patch("core.services.run_closure_gate._git_staged_paths", return_value=set()), \
             patch("core.services.run_closure_gate.subprocess.run", side_effect=fake_run):
            short = _try_auto_commit(
                {"core/services/run_closure_gate.py"},
                run_id="rid-4", session_id="sid-4", focus="x",
            )
        assert short is None
        assert "docs-drift" in gate_mod._last_auto_commit_error
        # staging rullet tilbage så ændringerne forbliver synlige
        assert any(c[:2] == ["git", "restore"] for c in calls)


class TestAutoCommitBlockedNotification:
    def test_nudges_via_bridge_when_commit_blocked(self):
        from core.services.run_closure_gate import _notify_auto_commit_blocked
        sent: list[str] = []
        with patch("core.services.run_closure_gate._last_auto_commit_error",
                   "hook blokerede"), \
             patch("core.services.outbound_nudges.push_nudge",
                   return_value={"status": "ok"}) as push:
            _notify_auto_commit_blocked(
                {"count": 2, "paths": ["a.py", "b.py"], "truncated": False},
                run_id="rid-9", session_id="sid-9",
            )
        assert push.call_count == 1
        msg = push.call_args.kwargs["message"]
        assert "rid-9" in msg
        assert "hook blokerede" in msg

    def test_falls_back_to_session_notification(self):
        from core.services.run_closure_gate import _notify_auto_commit_blocked
        sent: list[str] = []
        with patch("core.services.run_closure_gate._last_auto_commit_error", ""), \
             patch("core.services.outbound_nudges.push_nudge",
                   return_value={"status": "disabled"}), \
             patch("core.services.notification_bridge.send_session_notification",
                   side_effect=lambda m, source, urgent: sent.append(m)) as fb:
            _notify_auto_commit_blocked(
                {"count": 1, "paths": ["x.py"], "truncated": False},
                run_id="rid-10", session_id="sid-10",
            )
        assert len(sent) == 1
        assert "rid-10" in sent[0]
