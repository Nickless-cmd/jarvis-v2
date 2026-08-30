from core.tools.claude_dispatch.runner import _build_prompt
from core.tools.claude_dispatch.spec import TaskSpec


def test_claude_dispatch_prompt_requires_attributed_wrapper():
    spec = TaskSpec(
        goal="inspect bounded cache regression",
        scope_files=("core/cache.py", "tests/test_cache.py"),
        allowed_tools=("Read", "Edit", "Bash"),
    )

    prompt = _build_prompt(spec, task_id="task-abc123")

    assert "scripts/commit_with_attribution.py" in prompt
    assert "--actor opus" in prompt
    assert "--run-id task-abc123" in prompt
    assert "--origin delegated" in prompt
    assert "--approved-by policy:claude-dispatch-v1" in prompt
    assert "--path core/cache.py" in prompt
    assert "--path tests/test_cache.py" in prompt
    assert "git add -A && git commit" not in prompt
    assert "git add -- core/cache.py tests/test_cache.py" in prompt


def test_claude_dispatch_quotes_commit_subject():
    spec = TaskSpec(
        goal="fix user's cache",
        scope_files=("core/cache.py",),
        allowed_tools=("Read", "Edit", "Bash"),
    )

    prompt = _build_prompt(spec, task_id="task-quoted")

    assert "--message 'feat(worker): fix user'\"'\"'s cache'" in prompt
