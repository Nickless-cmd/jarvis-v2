from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from core.services.attributed_git_commit import AttributedCommitResult
from core.services.autonomy_proposal_queue import (
    _auto_commit_after_source_edit,
    _execute_git_commit_proposal,
    approve_proposal,
)


def _successful_add(*args, **kwargs):
    return SimpleNamespace(returncode=0, stdout="", stderr="")


def test_source_edit_commit_carries_proposal_attribution(tmp_path):
    target = tmp_path / "core" / "changed.py"
    target.parent.mkdir()
    target.write_text("changed = True\n")
    proposal = {
        "proposal_id": "proposal-1",
        "run_id": "run-1",
        "session_id": "session-1",
        "rationale": "Fix the runtime",
        "payload": {
            "project_root": str(tmp_path),
            "target_path": str(target),
            "relative_path": "core/changed.py",
        },
    }

    with patch("subprocess.run", side_effect=_successful_add), patch(
        "core.services.autonomy_proposal_queue.commit_with_attribution",
        return_value=AttributedCommitResult(0, sha="abc123"),
    ) as commit:
        _auto_commit_after_source_edit(proposal, {"status": "executed"})

    kwargs = commit.call_args.kwargs
    assert kwargs["paths"] == ("core/changed.py",)
    assert kwargs["author"] == "Jarvis <jarvis@srvlab.dk>"
    assert kwargs["attribution"].actor == "jarvis"
    assert kwargs["attribution"].run_id == "run-1"
    assert kwargs["attribution"].session_id == "session-1"
    assert kwargs["attribution"].origin == "autonomous"
    assert kwargs["attribution"].approved_by == "bjorn"


def test_git_commit_proposal_uses_reserved_approval_context(tmp_path):
    payload = {
        "files": ["core/changed.py"],
        "message": "fix: approved proposal",
        "project_root": str(tmp_path),
        "_proposal_context": {
            "proposal_id": "proposal-2",
            "run_id": "run-2",
            "session_id": "session-2",
            "approved_by": "bjorn",
        },
    }

    with patch("subprocess.run", side_effect=_successful_add), patch(
        "core.services.autonomy_proposal_queue.commit_with_attribution",
        return_value=AttributedCommitResult(0, stdout="committed", sha="def456"),
    ) as commit:
        result = _execute_git_commit_proposal(payload)

    assert result["status"] == "executed"
    assert result["commit"] == "def456"
    attribution = commit.call_args.kwargs["attribution"]
    assert attribution.run_id == "run-2"
    assert attribution.session_id == "session-2"
    assert attribution.approved_by == "bjorn"


def test_approval_passes_proposal_context_to_executor():
    captured = {}

    def executor(payload):
        captured.update(payload)
        return {"status": "executed"}

    proposal = {
        "proposal_id": "proposal-3",
        "run_id": "run-3",
        "session_id": "session-3",
        "status": "pending",
        "kind": "test-attribution",
        "payload": {"value": 42},
    }

    with patch(
        "core.services.autonomy_proposal_queue.get_autonomy_proposal",
        return_value=proposal,
    ), patch(
        "core.services.autonomy_proposal_queue.resolve_autonomy_proposal",
        return_value=proposal,
    ), patch.dict(
        "core.services.autonomy_proposal_queue._PROPOSAL_EXECUTORS",
        {"test-attribution": executor},
        clear=False,
    ):
        result = approve_proposal("proposal-3")

    assert result["status"] == "executed"
    assert captured["value"] == 42
    assert captured["_proposal_context"] == {
        "proposal_id": "proposal-3",
        "run_id": "run-3",
        "session_id": "session-3",
        "approved_by": "bjorn",
    }
