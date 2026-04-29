import os
import shutil

import pytest

from core.tools.claude_dispatch.tool import _exec_dispatch_to_claude_code

MANUAL = os.environ.get("JARVIS_RUN_DISPATCH_SMOKE") == "1"


@pytest.mark.skipif(not MANUAL, reason="set JARVIS_RUN_DISPATCH_SMOKE=1 to run")
@pytest.mark.skipif(shutil.which("claude") is None, reason="claude CLI not on PATH")
def test_smoke_real_claude_minimal_task():
    result = _exec_dispatch_to_claude_code({
        "goal": "Print the contents of README.md, do not modify any files.",
        "scope_files": ["README.md"],
        "allowed_tools": ["Read"],
        "max_tokens": 5_000,
        "max_wall_seconds": 60,
        "permission_mode": "default",
    })
    assert result["status"] in {"ok", "error", "timeout"}
    assert "task_id" in result
