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


def test_cli_quota_failure_is_typed_and_explicit():
    from core.services.agent_cli_backend import _cli_failure

    exc = _cli_failure(
        "codex-cli", 1, "", "You've hit your usage limit. Try again later.")
    assert exc.error_code == "CLI_QUOTA_EXHAUSTED"
    assert exc.error_phase == "provider"
    assert exc.provider_status == "quota_exhausted"
    assert "kvote" in str(exc)


def test_cli_non_quota_failure_stays_a_backend_failure():
    from core.services.agent_cli_backend import _cli_failure

    exc = _cli_failure("claude-cli", 2, "", "invalid command line option")
    assert exc.error_code == "CLI_BACKEND_FAILED"
    assert exc.provider_status == "failed"


def test_et_udloebet_claude_token_afvises_foer_dispatch(tmp_path, monkeypatch):
    """Binæren kan være der og alligevel være ubrugelig.

    Målt 9/11-2026: `resolve_executable` fandt `~/.local/bin/claude` (2.1.318) og
    `claude auth status` svarede `loggedIn: true` — men `claude --print` gav
    `401 OAuth access token is invalid`. Tokenet udløb 20/5-2026 og
    `refreshToken` er tom, så den kan ikke forny sig selv. Uden denne kontrol
    melder `admission_reason` «klar» og sender en Task af sted der fejler på
    provider-siden.
    """
    import core.services.agent_cli_backend as b

    creds = tmp_path / "creds.json"
    creds.write_text(json.dumps({
        "claudeAiOauth": {"accessToken": "sk-ant-oat01-x", "refreshToken": "",
                          "expiresAt": 1779292842159},
    }), encoding="utf-8")
    monkeypatch.setattr(b, "resolve_executable", lambda p: "/bin/claude")
    assert b._claude_auth_doed(creds) is True
    monkeypatch.setattr(b, "_claude_auth_doed", lambda credentials=None: True)
    assert b.admission_reason("claude-cli") == "claude_oauth_udloebet"


def test_et_gyldigt_claude_token_slipper_igennem(tmp_path, monkeypatch):
    import time

    import core.services.agent_cli_backend as b

    creds = tmp_path / "creds.json"
    creds.write_text(json.dumps({
        "claudeAiOauth": {"accessToken": "sk-ant-oat01-x", "refreshToken": "r",
                          "expiresAt": int((time.time() + 86400) * 1000)},
    }), encoding="utf-8")
    assert b._claude_auth_doed(creds) is False
    monkeypatch.setattr(b, "resolve_executable", lambda p: "/bin/claude")
    monkeypatch.setattr(b, "_claude_auth_doed", lambda credentials=None: False)
    monkeypatch.setattr("core.services.dispatch_quota.quota_preflight",
                        lambda backend: {"allow": True, "reason": ""})
    assert b.admission_reason("claude-cli") == ""


def test_en_manglende_credentials_fil_antager_brugbar(tmp_path):
    """Tvivl må ikke blokere: findes filen ikke, melder preflight-ens egne fejl i stedet."""
    from core.services.agent_cli_backend import _claude_auth_doed

    assert _claude_auth_doed(tmp_path / "findes-ikke.json") is False


