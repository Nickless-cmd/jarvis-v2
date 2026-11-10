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
                   policy="worktree-write", output_path=out)
    assert cmd[:2] == ["/bin/codex", "exec"]
    assert cmd[cmd.index("-C") + 1] == str(tmp_path)
    assert cmd[cmd.index("--sandbox") + 1] == "workspace-write"
    assert "--ephemeral" in cmd and "--model" not in cmd


def test_claude_command_is_restricted_and_has_no_shell(tmp_path):
    from core.services.agent_cli_backend import _command

    cmd = _command("claude-cli", "/bin/claude", "sonnet", str(tmp_path), "gør det",
                   policy="worktree-write", output_path=str(tmp_path / "unused"))
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


def test_spawn_env_baerer_det_levende_claude_token(monkeypatch):
    """Headless `claude -p` autentificerer via CLAUDE_CODE_OAUTH_TOKEN, ikke credentials-filen.

    Målt 9/11-2026: spawn'en arvede `os.environ` uden variablen, faldt tilbage på
    `~/.claude/.credentials.json` (udløbet 20/5-2026) og svarede
    `401 OAuth access token is invalid` — mens tokenet i `claude_dispatch.env`
    virkede (samme kommando svarede `hej`, exit 0). Uden denne linje er lane'en
    død uanset hvad preflighten siger.
    """
    import core.services.agent_cli_backend as b
    import core.services.dispatch_quota as q

    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
    monkeypatch.setattr(q, "_claude_token", lambda: ("sk-ant-oat01-live", "env_file"))
    env = b._claude_spawn_env("claude-cli")
    assert env["CLAUDE_CODE_OAUTH_TOKEN"] == "sk-ant-oat01-live"


def test_spawn_env_overskriver_ikke_miljoeets_token(monkeypatch):
    """Miljøet vinder: et token der allerede er sat må ikke erstattes af filens."""
    import core.services.agent_cli_backend as b
    import core.services.dispatch_quota as q

    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "sk-ant-oat01-fra-miljoe")
    monkeypatch.setattr(q, "_claude_token", lambda: ("sk-ant-oat01-fra-fil", "env_file"))
    assert b._claude_spawn_env("claude-cli")["CLAUDE_CODE_OAUTH_TOKEN"] == "sk-ant-oat01-fra-miljoe"


def test_codex_spawn_env_roerer_ikke_claude_tokenet(monkeypatch):
    """Codex autentificerer selv; den skal ikke have Claudes token ind i miljøet."""
    import core.services.agent_cli_backend as b
    import core.services.dispatch_quota as q

    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
    monkeypatch.setattr(q, "_claude_token", lambda: ("sk-ant-oat01-live", "env_file"))
    assert "CLAUDE_CODE_OAUTH_TOKEN" not in b._claude_spawn_env("codex-cli")


def test_admission_slipper_igennem_naar_preflight_tillader(monkeypatch):
    """Dommen om et dødt token ligger i quota_preflight, ikke i en lokal kopi.

    Den tidligere kontrol læste `.credentials.json` og erklærede en lane død der
    faktisk svarede (målt 9/11-2026). Preflighten bruger `_claude_token()`s fulde
    kæde og er derfor den eneste dommer.
    """
    import core.services.agent_cli_backend as b

    monkeypatch.setattr(b, "resolve_executable", lambda p: "/bin/claude")
    monkeypatch.setattr("core.services.dispatch_quota.quota_preflight",
                        lambda backend: {"allow": True, "reason": ""})
    assert b.admission_reason("claude-cli") == ""


def test_admission_afviser_naar_preflight_blokerer(monkeypatch):
    import core.services.agent_cli_backend as b

    monkeypatch.setattr(b, "resolve_executable", lambda p: "/bin/claude")
    monkeypatch.setattr("core.services.dispatch_quota.quota_preflight",
                        lambda backend: {"allow": False, "reason": "tokenet blev afvist (HTTP 401)"})
    assert b.admission_reason("claude-cli").startswith("quota:")


