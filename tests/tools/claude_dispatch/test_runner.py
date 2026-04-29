from unittest.mock import patch, MagicMock

import pytest

from core.tools.claude_dispatch.runner import run_dispatch
from core.tools.claude_dispatch.spec import parse_spec
from core.tools.claude_dispatch.budget import BudgetExceeded


def _basic_spec():
    return parse_spec({
        "goal": "Add docstring", "scope_files": ["core/foo.py"],
        "allowed_tools": ["Read", "Edit"],
        "max_tokens": 10_000, "max_wall_seconds": 30,
    })


@pytest.fixture
def patched_runner(tmp_dispatch_db):
    with patch("core.tools.claude_dispatch.runner.create_worktree") as mw, \
         patch("core.tools.claude_dispatch.runner.worktree_diff") as md, \
         patch("core.tools.claude_dispatch.runner.subprocess.Popen") as mp:
        mw.return_value = "/media/projects/jarvis-v2/.claude/worktrees/claude-task-xyz"
        md.return_value = " core/foo.py | 2 +-\n 1 file changed"
        proc = MagicMock()
        proc.stdout = iter([
            '{"type":"assistant","message":{"content":[{"type":"text","text":"working"}]}}\n',
            '{"type":"result","subtype":"success","usage":{"input_tokens":100,"output_tokens":200},"total_cost_usd":0.01}\n',
        ])
        proc.wait.return_value = 0
        proc.poll.return_value = 0
        proc.returncode = 0
        mp.return_value = proc
        yield mw, md, mp


def test_run_dispatch_returns_ok_status(patched_runner):
    bus = MagicMock()
    result = run_dispatch(_basic_spec(), bus)
    assert result["status"] == "ok"
    assert result["tokens"] == 300
    assert result["task_id"]
    assert result["branch"].startswith("claude/")


def test_run_dispatch_publishes_events(patched_runner):
    bus = MagicMock()
    run_dispatch(_basic_spec(), bus)
    kinds = [c.args[0] for c in bus.publish.call_args_list]
    assert any(k.startswith("tool.dispatch.") for k in kinds)


def test_run_dispatch_passes_allowlist_to_subprocess(patched_runner):
    _, _, mp = patched_runner
    bus = MagicMock()
    run_dispatch(_basic_spec(), bus)
    cmd = mp.call_args.args[0]
    assert "claude" in cmd[0] or cmd[0] == "claude"
    assert "--allowed-tools" in cmd
    idx = cmd.index("--allowed-tools")
    assert "Read" in cmd[idx + 1] and "Edit" in cmd[idx + 1]
    assert "--add-dir" in cmd
    assert "--output-format" in cmd
    assert "stream-json" in cmd


def test_run_dispatch_blocks_when_budget_exhausted(tmp_dispatch_db):
    from core.tools.claude_dispatch.budget import BudgetTracker, MAX_DISPATCHES_PER_HOUR
    bt = BudgetTracker()
    for _ in range(MAX_DISPATCHES_PER_HOUR):
        bt.check_and_reserve()
    with pytest.raises(BudgetExceeded):
        run_dispatch(_basic_spec(), MagicMock())
