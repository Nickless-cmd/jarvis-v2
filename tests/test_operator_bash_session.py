"""Tests for operator_bash_session — server-emuleret persistent operator-shell."""
from __future__ import annotations

import core.tools.operator_bash_session as obs


def _mk_bridge(monkeypatch, captured: list):
    """Mock _exec_operator_bash så vi fanger den wrappede kommando + styrer svaret."""
    import core.tools.simple_tools as st

    def fake(args):
        captured.append(args)
        return {"status": "ok", "result": {
            "platform": "darwin", "shell": "bash",
            "stdout": "hello-output\n__OBS_CWD__:/Users/x/proj\n",
            "stderr": "", "exit_code": 0, "timed_out": False}}
    monkeypatch.setattr(st, "_exec_operator_bash", fake)


def test_open_returns_session_id():
    res = obs._exec_operator_bash_session_open({"_user_id": "u1"})
    assert res["status"] == "ok" and res["session_id"].startswith("opsess-")


def test_run_strips_marker_and_persists_cwd(monkeypatch):
    cap: list = []
    _mk_bridge(monkeypatch, cap)
    sid = obs._exec_operator_bash_session_open({"_user_id": "u1"})["session_id"]
    res = obs._exec_operator_bash_session_run({"session_id": sid, "command": "ls"})
    # markøren er fjernet fra det Jarvis ser:
    assert res["result"]["stdout"] == "hello-output"
    assert "__OBS_CWD__" not in res["result"]["stdout"]
    # cwd er persisteret på sessionen:
    with obs._LOCK:
        assert obs._SESSIONS[sid]["cwd"] == "/Users/x/proj"
    # næste run prepender cd til den gemte cwd:
    obs._exec_operator_bash_session_run({"session_id": sid, "command": "pwd"})
    assert "cd /Users/x/proj" in cap[-1]["command"]
    # env persisteres via operator-side .env-fil:
    assert ".jarvis_opsess_" in cap[-1]["command"] and "export -p" in cap[-1]["command"]


def test_run_unknown_session_errors():
    res = obs._exec_operator_bash_session_run({"session_id": "opsess-nope", "command": "ls"})
    assert res["status"] == "error" and "unknown session_id" in res["error"]


def test_close_drops_session(monkeypatch):
    _mk_bridge(monkeypatch, [])
    sid = obs._exec_operator_bash_session_open({"_user_id": "u1"})["session_id"]
    assert obs._exec_operator_bash_session_close({"session_id": sid})["closed"] is True
    with obs._LOCK:
        assert sid not in obs._SESSIONS


def test_registered_in_tool_handlers_and_scope():
    import core.tools.simple_tools as st
    from core.tools.tool_scoping import CODE_MODE_TOOLS_BASE
    for n in ("operator_bash_session_open", "operator_bash_session_run",
              "operator_bash_session_close", "operator_bash_session_list"):
        assert n in st._TOOL_HANDLERS
        assert n in CODE_MODE_TOOLS_BASE


# ---------------------------------------------------------------------------
# 4. sep 2026. Bjørn: «det er under eller efter en tool runde cutoff opstår».
# Det var ikke et cut — resultatet manglede en `text`-nøgle og faldt derfor
# igennem til JSON-dumpet, som er cappet ved 8000 tegn (søsteren bash_session
# har 16000). En læsning på 9665 tegn mistede 1534 tegn ud af MIDTEN.
# ---------------------------------------------------------------------------

def test_result_has_a_text_key_so_it_escapes_the_8000_json_cap(monkeypatch):
    import core.tools.operator_bash_session as m

    monkeypatch.setattr(m, "_SESSIONS", {"s1": {"user_id": "u", "cwd": "/tmp", "last": 0}})
    monkeypatch.setattr(
        "core.tools.simple_tools._exec_operator_bash",
        lambda a: {"status": "ok", "result": {
            "platform": "linux", "shell": "bash",
            "stdout": "linje1\nlinje2\n", "stderr": "", "exit_code": 0, "timed_out": False}},
    )
    res = m._exec_operator_bash_session_run({"session_id": "s1", "command": "echo hej"})
    assert "text" in res, "uden en text-nøgle rammer resultatet 8000-cappen"
    assert res["text"] == "linje1\nlinje2"


def test_long_output_keeps_the_middle_now_that_the_cap_is_the_bash_one(monkeypatch):
    """9665 tegn blev klippet før. Med bash-loftet (16000) er der intet hul."""
    import core.tools.operator_bash_session as m

    lang = "\n".join(f"kodelinje {i}" for i in range(700))   # ~9,7k tegn
    assert 8000 < len(lang) < 16000
    monkeypatch.setattr(m, "_SESSIONS", {"s1": {"user_id": "u", "cwd": "", "last": 0}})
    monkeypatch.setattr(
        "core.tools.simple_tools._exec_operator_bash",
        lambda a: {"status": "ok", "result": {
            "stdout": lang, "stderr": "", "exit_code": 0, "timed_out": False}},
    )
    res = m._exec_operator_bash_session_run({"session_id": "s1", "command": "cat fil"})
    assert "udeladt i midten" not in res["text"]
    assert "kodelinje 350" in res["text"], "midten skal være der"


def test_stderr_and_nonzero_exit_are_reported_but_a_clean_run_is_quiet(monkeypatch):
    """En exit=0 i hver eneste besked er støj der skubber rigtigt indhold ud."""
    import core.tools.operator_bash_session as m

    monkeypatch.setattr(m, "_SESSIONS", {"s1": {"user_id": "u", "cwd": "", "last": 0}})
    monkeypatch.setattr(
        "core.tools.simple_tools._exec_operator_bash",
        lambda a: {"status": "ok", "result": {
            "stdout": "noget", "stderr": "advarsel", "exit_code": 3, "timed_out": False}},
    )
    t = m._exec_operator_bash_session_run({"session_id": "s1", "command": "x"})["text"]
    assert "[stderr]\nadvarsel" in t and "[exit=3]" in t

    monkeypatch.setattr(
        "core.tools.simple_tools._exec_operator_bash",
        lambda a: {"status": "ok", "result": {
            "stdout": "fint", "stderr": "", "exit_code": 0, "timed_out": False}},
    )
    t2 = m._exec_operator_bash_session_run({"session_id": "s1", "command": "x"})["text"]
    assert t2 == "fint" and "exit" not in t2


def test_et_kald_uden_cwd_markoer_holder_stadig_sessionen_i_live(monkeypatch):
    """«unknown session_id (udløbet?)» midt i et stykke arbejde (Jarvis 4. sep).

    Levetiden er 30 min — rigelig. Men `last` blev kun opdateret når
    cwd-markøren kunne udtrækkes. En fejlet kommando eller et uventet output
    talte derfor som INGEN aktivitet, og sessionen kunne ældes ihjel mens den
    var i brug.
    """
    import core.tools.operator_bash_session as m

    m._SESSIONS.clear()
    m._SESSIONS["s1"] = {"user_id": "u", "cwd": "/tmp", "last": 1000.0}
    monkeypatch.setattr(m, "_now", lambda: 2000.0)
    # Output UDEN cwd-markør — fx en kommando der fejlede.
    monkeypatch.setattr(
        "core.tools.simple_tools._exec_operator_bash",
        lambda a: {"status": "ok", "result": {
            "stdout": "bash: kommando ikke fundet\n", "stderr": "", "exit_code": 127,
            "timed_out": False}},
    )
    m._exec_operator_bash_session_run({"session_id": "s1", "command": "findes-ikke"})
    assert m._SESSIONS["s1"]["last"] == 2000.0, "brug SKAL holde sessionen i live"
    assert m._SESSIONS["s1"]["cwd"] == "/tmp", "cwd må ikke ændres af et output uden markør"
