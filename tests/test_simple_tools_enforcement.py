from unittest.mock import patch

from core.tools.simple_tools_enforcement import _attach_repo_state


def test_attributed_commit_resets_edit_counter():
    result = {"status": "ok", "stdout": "commit=abc123\n"}
    command = (
        "python scripts/commit_with_attribution.py --repo . "
        "--actor codex --origin delegated --approved-by bjorn --message fix"
    )

    with patch(
        "core.tools.simple_tools_enforcement._repo_state_reset_counter"
    ) as reset, patch(
        "apps.api.jarvis_api.routes.chat._git_status_sync",
        return_value={"dirty": 0},
    ):
        attached = _attach_repo_state(
            result,
            session_id="session-1",
            bumped=True,
            bash_command=command,
        )

    reset.assert_called_once_with("session-1")
    assert attached["_repo_state"]["edits_since_commit"] == 0


def test_attributed_commit_nochange_does_not_reset_counter():
    result = {"status": "ok", "stdout": "nothing to commit, working tree clean"}

    with patch(
        "core.tools.simple_tools_enforcement._repo_state_reset_counter"
    ) as reset, patch(
        "core.tools.simple_tools_enforcement._repo_state_bump_counter",
        return_value=4,
    ), patch(
        "apps.api.jarvis_api.routes.chat._git_status_sync",
        return_value={"dirty": 1},
    ):
        attached = _attach_repo_state(
            result,
            session_id="session-1",
            bumped=True,
            bash_command="python scripts/commit_with_attribution.py --message fix",
        )

    reset.assert_not_called()
    assert attached["_repo_state"]["edits_since_commit"] == 4
