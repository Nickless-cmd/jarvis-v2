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




# ── Værktøjskaldene skal MED ud af subprocessen (14/11-2026) ────────────────
# Målt 13/11-2026: to agenter kørte gennem `claude-cli`, læste filer og kørte
# grep, og efterlod NUL rækker i `agent_tool_calls`. Årsagen var ikke at de
# ikke kaldte værktøjer — det var at `--output-format json` kun giver
# slutresultatet, så kaldene aldrig forlod subprocessen. Den tomme tabel blev
# derefter læst som «agenten kan ikke kalde værktøjer», hvilket var en målefejl.

#: Ægte uddrag af `--output-format stream-json --verbose` fra CLI 2.1.318.
_STREAM_PROVE = "\n".join([
    '{"type":"system","subtype":"init","session_id":"s1"}',
    '{"type":"assistant","message":{"content":[{"type":"tool_use",'
    '"id":"toolu_01TyeCBEwwaTT1x6eN5dANmA","name":"Read",'
    '"input":{"file_path":"/media/projects/jarvis-v2/README.md"}}],'
    '"usage":{"input_tokens":2,"output_tokens":16}}}',
    '{"type":"user","message":{"content":[{"type":"tool_result",'
    '"tool_use_id":"toolu_01TyeCBEwwaTT1x6eN5dANmA","is_error":false,'
    '"content":"1\\t<h1 align=\\"center\\">J.A.R.V.I.S.</h1>"}]}}',
    '{"type":"result","subtype":"success","is_error":false,"num_turns":2,'
    '"result":"README.md er på 148 linjer.","total_cost_usd":0.0826,'
    '"usage":{"input_tokens":4,"output_tokens":120}}',
])


def test_claude_command_beder_om_stream_json(tmp_path):
    """Formatet er hele pointen: `json` giver kun slutresultatet.

    Uden `stream-json` findes værktøjskaldene ikke uden for subprocessen, og så
    kan ingen bogføring — uanset hvor mange kaldere `create_agent_tool_call`
    end har — se dem.
    """
    from core.services.agent_cli_backend import _command

    cmd = _command("claude-cli", "/bin/claude", "default", str(tmp_path), "gør det",
                   policy="read-only-runtime", output_path=str(tmp_path / "u"))
    assert cmd[cmd.index("--output-format") + 1] == "stream-json"
    assert "--verbose" in cmd
    # Sikkerhedsflagene må ikke være faldet af i samme hug.
    assert "--restricted" in cmd
    assert cmd[cmd.index("--permission-prompts") + 1] == "none"


def test_stream_json_udtraekker_vaerktoejskaldet():
    """Kaldet skal ud med navn, id og de faktiske argumenter."""
    from core.services.agent_cli_backend import _claude_parse

    p = _claude_parse(_STREAM_PROVE)
    assert [t["name"] for t in p["tool_uses"]] == ["Read"]
    assert p["tool_uses"][0]["id"] == "toolu_01TyeCBEwwaTT1x6eN5dANmA"
    assert p["tool_uses"][0]["input"]["file_path"].endswith("README.md")
    assert p["text"] == "README.md er på 148 linjer."
    assert (p["input_tokens"], p["output_tokens"]) == (4, 120)


def test_vaerktoejskaldet_bogfoeres_i_agent_tool_calls(monkeypatch, tmp_path):
    """Rækken skal faktisk lande i basen — ikke bare kaldes.

    Beviser koblingen hele vejen: stream → parser → `create_agent_tool_call`.
    Uden denne test kan bogføringen fjernes igen uden at nogen ser det.
    """
    import sqlite3

    import core.runtime.db_agent_runtime as rt
    from core.services.agent_cli_backend import _bogfoer_cli_vaerktoejskald, _claude_parse

    db = tmp_path / "prove.db"

    def _connect():
        # Produktionens `connect()` saetter `row_factory = sqlite3.Row`; uden
        # det fejler genlaesningen med «tuple indices must be integers», og
        # `create_agent_tool_call` sluger den og returnerer {}. En noegen
        # forbindelse maaler derfor ikke det produktionskoden goer.
        c = sqlite3.connect(db)
        c.row_factory = sqlite3.Row
        return c

    monkeypatch.setattr(rt, "connect", _connect)

    p = _claude_parse(_STREAM_PROVE)
    n = _bogfoer_cli_vaerktoejskald({"agent_id": "agent-x"}, "run-x",
                                    p["tool_uses"], p["tool_results"])
    assert n == 1

    conn = sqlite3.connect(db)
    try:
        row = conn.execute(
            "SELECT tool_call_id, run_id, agent_id, tool_name, status, arguments_json "
            "FROM agent_tool_calls"
        ).fetchone()
    finally:
        conn.close()
    assert row is not None, "bogføringen skrev ingen række"
    assert row[1] == "run-x" and row[2] == "agent-x" and row[3] == "Read"
    assert row[4] == "ok"
    assert "file_path" in row[5]


def test_en_fejlblob_er_ikke_en_leverance():
    """`is_error` er gyldig JSON. Uden tjek ville fejlen blive returneret som svar."""
    import pytest

    from core.services.agent_cli_backend import CliBackendError, _claude_parse

    with pytest.raises(CliBackendError):
        _claude_parse(json.dumps({
            "type": "result", "is_error": True, "result": "kvoten er brugt op",
            "usage": {}, "total_cost_usd": 0,
        }))


def test_tom_kaldliste_skriver_ingen_raekke(monkeypatch):
    """En agent der ikke kaldte noget må ikke efterlade en tom række som bevis."""
    from core.services.agent_cli_backend import _bogfoer_cli_vaerktoejskald

    kaldt = []
    import core.runtime.db as dbmod
    monkeypatch.setattr(dbmod, "create_agent_tool_call", lambda **kw: kaldt.append(kw))
    assert _bogfoer_cli_vaerktoejskald({"agent_id": "a"}, "r", [], []) == 0
    assert kaldt == []


def test_run_task_cli_bogfoerer_kaldene_gennem_hele_ruten(monkeypatch, tmp_path):
    """Ende-til-ende: `run_task_cli` skal selv kalde bogføringen.

    De øvrige tests beviser at parseren kan og at bogføringen kan. Denne beviser
    at nogen faktisk RÅBER op. Uden den kan koblingen fjernes fra
    `run_task_cli` uden at en eneste test rører sig — og så er de andre grønne
    af den forkerte grund.
    """
    import core.runtime.db as dbmod
    import core.services.agent_cli_backend as b

    class FakeProc:
        returncode = 0
        pid = 12345

        def communicate(self, timeout=None):
            return _STREAM_PROVE, ""

        def poll(self):
            return 0

        def wait(self, timeout=None):
            return 0

    monkeypatch.setattr(b, "resolve_executable", lambda p: "/bin/true")
    monkeypatch.setattr(b, "admission_reason", lambda p: "")
    monkeypatch.setattr(b, "_assignment", lambda aid: {})
    monkeypatch.setattr(b, "_working_root", lambda agent, asg: (str(tmp_path), False))
    monkeypatch.setattr(b.subprocess, "Popen", lambda *a, **k: FakeProc())

    skrevet = []
    monkeypatch.setattr(dbmod, "create_agent_tool_call", lambda **kw: skrevet.append(kw))

    ud = b.run_task_cli(
        agent={"agent_id": "agent-x", "provider": "claude-cli", "model": "sonnet",
               "tool_policy": "read-only-runtime"},
        prompt="læs README", run_id="run-x",
    )

    assert ud["status"] == "completed"
    assert ud["total_tool_calls"] == 1
    assert len(skrevet) == 1, "run_task_cli kaldte ikke bogfoeringen"
    assert skrevet[0]["tool_name"] == "Read"
    assert skrevet[0]["run_id"] == "run-x"
    assert skrevet[0]["agent_id"] == "agent-x"


def test_et_fejlet_vaerktoejskald_bogfoeres_som_error(monkeypatch, tmp_path):
    """Et kald der fejlede må ikke stå som `ok`.

    Mutationen `status="ok"` slap gennem hele suiten, fordi den eneste fixture
    havde `is_error: false`. Uden denne test er parringen dekoration: rækken
    findes, men den lyver om udfaldet.
    """
    import sqlite3

    import core.runtime.db_agent_runtime as rt
    from core.services.agent_cli_backend import _bogfoer_cli_vaerktoejskald

    db = tmp_path / "fejl.db"

    def _connect():
        c = sqlite3.connect(db)
        c.row_factory = sqlite3.Row
        return c

    monkeypatch.setattr(rt, "connect", _connect)

    n = _bogfoer_cli_vaerktoejskald(
        {"agent_id": "agent-x"}, "run-x",
        [{"id": "toolu_fejl", "name": "Read", "input": {"file_path": "/findes/ikke"}}],
        [{"tool_use_id": "toolu_fejl", "is_error": True, "preview": "No such file"}],
    )
    assert n == 1
    conn = sqlite3.connect(db)
    try:
        row = conn.execute(
            "SELECT status, result_preview FROM agent_tool_calls WHERE tool_call_id='toolu_fejl'"
        ).fetchone()
    finally:
        conn.close()
    assert row[0] == "error", f"fejlet kald stod som {row[0]!r}"
    assert "No such file" in row[1]
