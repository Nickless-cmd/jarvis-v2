from __future__ import annotations

import json


def test_cli_aliases_are_explicit_and_not_fuzzy():
    from core.services.agent_cli_backend import parse_preference

    assert parse_preference("claude-code") == ("claude-cli", "default")
    assert parse_preference("codex-cli/gpt-5.4") == ("codex-cli", "gpt-5.4")
    assert parse_preference("claudish") is None


def test_codex_command_uses_task_root_and_native_sandbox(tmp_path):
    from core.services.agent_cli_backend import _command

    out = str(tmp_path / "out")
    cmd = _command("codex-cli", "/bin/codex", "default", str(tmp_path), "gør det",
                   writes=True, output_path=out)
    assert cmd[:2] == ["/bin/codex", "exec"]
    assert cmd[cmd.index("-C") + 1] == str(tmp_path)
    assert cmd[cmd.index("--sandbox") + 1] == "workspace-write"
    assert "--ephemeral" in cmd and "--model" not in cmd


def test_claude_command_is_restricted_and_has_no_shell(tmp_path):
    from core.services.agent_cli_backend import _command

    cmd = _command("claude-cli", "/bin/claude", "sonnet", str(tmp_path), "gør det",
                   writes=True, output_path=str(tmp_path / "unused"))
    assert "--restricted" in cmd and "--permission-prompts" in cmd
    tools = cmd[cmd.index("--tools") + 1]
    assert "Edit" in tools and "Write" in tools and "Bash" not in tools
    assert cmd[cmd.index("--permission-mode") + 1] == "acceptEdits"
    assert cmd[cmd.index("--model") + 1] == "sonnet"


def test_cli_prompt_translates_the_workers_virtual_work_path():
    from core.services.agent_cli_backend import _prompt

    result = _prompt(
        "Runtime boundary: your workspace root is /work. Use absolute paths inside that root; done.",
        writes=True,
    )
    assert "workspace root is /work" not in result
    assert "current working directory" in result


def test_claude_json_result_is_mapped_to_runtime_shape():
    from core.services.agent_cli_backend import _claude_text

    text, inp, out = _claude_text(json.dumps({
        "result": "færdig", "usage": {"input_tokens": 12, "output_tokens": 3},
    }))
    assert (text, inp, out) == ("færdig", 12, 3)


