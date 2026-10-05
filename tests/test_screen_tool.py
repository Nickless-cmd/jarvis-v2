"""Tests for core.tools.screen_tool.

Målt 5/10-2026: den gamle udgave kaldte `xset dpms` på DISPLAY=:1 — død kode,
fordi (a) runtimen kører på serveren, ikke på CheifOne, og (b) sessionen er
Wayland, hvor XWayland svarer "Server does not have the DPMS Extension".

Disse tests beviser at den ikke længere kalder xset, at kommandoen bygges mod
sysfs, og at et nede bro giver en ÆRLIG fejl i stedet for `command not found`.
Ingen af dem rører en rigtig skærm.
"""
from __future__ import annotations

import ast
import inspect

import pytest

import core.tools.screen_tool as mod


# ── kildekode-værn ──────────────────────────────────────────────────────


def test_import_smoke():
    assert hasattr(mod, "_exec_screen_control")
    assert hasattr(mod, "SCREEN_TOOL_DEFINITIONS")


def test_source_wires_record_private():
    src = inspect.getsource(mod)
    assert "record_private" in src


def test_source_does_not_call_xset():
    """Hovedbeviset: xset bruges ikke som kommando længere.

    Ordet må gerne stå i docstringen (hvor det forklares hvorfor), men det må
    ikke optræde som en streng-konstant — altså som et programnavn i et kald.
    """
    tree = ast.parse(inspect.getsource(mod))
    konstanter = [
        n.value for n in ast.walk(tree)
        if isinstance(n, ast.Constant) and isinstance(n.value, str)
    ]
    assert "xset" not in konstanter, "xset bruges stadig som kommando"
    assert not any("XAUTHORITY" in k for k in konstanter)


def test_module_runs_nothing_locally():
    """Al udførelse skal gennem broen — ingen lokal subprocess."""
    tree = ast.parse(inspect.getsource(mod))
    importerede = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            importerede.update(a.name for a in n.names)
        elif isinstance(n, ast.ImportFrom):
            importerede.add(n.module or "")
    assert "subprocess" not in importerede
    assert not any(m.startswith("subprocess") for m in importerede)


# ── kommando-byggeren ───────────────────────────────────────────────────


def test_off_command_targets_sysfs_dpms():
    cmd = mod._dpms_command("off")
    assert "/sys/class/drm" in cmd
    assert "dpms" in cmd
    assert '"off"' in cmd or "off" in cmd
    assert "sudo -n" in cmd
    assert "xset" not in cmd


def test_status_command_reads_but_does_not_set():
    cmd = mod._dpms_command("status")
    assert "/sys/class/drm" in cmd
    assert "dpms" in cmd
    # status må ikke skrive til dpms-filen
    assert "tee" not in cmd
    assert "xset" not in cmd


def test_command_skips_unconnected_outputs():
    for action in ("on", "off", "standby"):
        cmd = mod._dpms_command(action)
        assert "connected" in cmd, "skal springe ikke-tilsluttede udgange over"


# ── ærlig fejl når broen er nede ────────────────────────────────────────


@pytest.fixture
def fake_bridge(monkeypatch):
    """Fanger hvad der sendes til broen, uden at røre en rigtig maskine."""
    calls: list[tuple[str, str]] = []

    def _fake_run_operator_async(coro_fn, *, tool_name, timeout_s=150.0):
        calls.append(("dispatch", tool_name))
        return {"status": "ok", "result": {"stdout": "card1-DP-4: Off", "stderr": "", "exit_code": 0}}

    monkeypatch.setattr("core.tools.simple_tools._run_operator_async", _fake_run_operator_async)
    monkeypatch.setattr("core.tools.simple_tools._operator_user_id", lambda args: "u-1")
    return calls


def test_bridge_down_gives_honest_error(monkeypatch):
    def _fail(coro_fn, *, tool_name, timeout_s=150.0):
        return {"status": "error", "error": "bridge_not_connected"}

    monkeypatch.setattr("core.tools.simple_tools._run_operator_async", _fail)
    monkeypatch.setattr("core.tools.simple_tools._operator_user_id", lambda args: "u-1")

    out = mod._exec_screen_control({"action": "off"})
    assert out["status"] == "error"
    assert "bridge_not_connected" in out["text"]
    # må ikke lyve om at handlingen skete
    assert "command not found" not in out["text"]


def test_ok_path_uses_bridge(fake_bridge):
    out = mod._exec_screen_control({"action": "off"})
    assert out["status"] == "ok"
    assert fake_bridge, "skal have gået gennem broen"


def test_status_reports_sysfs_lines(fake_bridge):
    out = mod._exec_screen_control({"action": "status"})
    assert out["status"] == "ok"
    assert "card1-DP-4" in out["text"]


def test_command_failure_is_surfaced(monkeypatch):
    def _fake(coro_fn, *, tool_name, timeout_s=150.0):
        return {"status": "ok", "result": {"stdout": "", "stderr": "sudo: a password is required", "exit_code": 1}}

    monkeypatch.setattr("core.tools.simple_tools._run_operator_async", _fake)
    monkeypatch.setattr("core.tools.simple_tools._operator_user_id", lambda args: "u-1")

    out = mod._exec_screen_control({"action": "off"})
    assert out["status"] == "error"
    assert "password" in out["text"]


def test_no_outputs_found_uses_dbus_fallback_for_off(monkeypatch):
    seen: list[str] = []

    def _fake(coro_fn, *, tool_name, timeout_s=150.0):
        # første kald (sysfs) finder intet; andet kald (D-Bus) lykkes
        if not seen:
            seen.append("sysfs")
            return {"status": "ok", "result": {"stdout": "", "stderr": "ingen tilsluttede", "exit_code": 3}}
        seen.append("dbus")
        return {"status": "ok", "result": {"stdout": "", "stderr": "", "exit_code": 0}}

    monkeypatch.setattr("core.tools.simple_tools._run_operator_async", _fake)
    monkeypatch.setattr("core.tools.simple_tools._operator_user_id", lambda args: "u-1")

    out = mod._exec_screen_control({"action": "off"})
    assert out["status"] == "ok"
    assert seen == ["sysfs", "dbus"]
    assert "låser" in out["text"]


def test_no_outputs_found_is_error_for_on(monkeypatch):
    def _fake(coro_fn, *, tool_name, timeout_s=150.0):
        return {"status": "ok", "result": {"stdout": "", "stderr": "ingen tilsluttede DP-udgange", "exit_code": 3}}

    monkeypatch.setattr("core.tools.simple_tools._run_operator_async", _fake)
    monkeypatch.setattr("core.tools.simple_tools._operator_user_id", lambda args: "u-1")

    out = mod._exec_screen_control({"action": "on"})
    assert out["status"] == "error"
    assert "ingen tilsluttede" in out["text"]


# ── argument-håndtering ─────────────────────────────────────────────────


def test_invalid_action():
    out = mod._exec_screen_control({"action": "explode"})
    assert out["status"] == "error"
    assert "Invalid action" in out["text"]


def test_missing_action():
    out = mod._exec_screen_control({})
    assert out["status"] == "error"


def test_command_alias_still_accepted(fake_bridge):
    """Runtimen sender 'command'; ældre kald sendte 'action'."""
    out = mod._exec_screen_control({"command": "status"})
    assert out["status"] == "ok"


def test_definitions_do_not_mention_xset():
    blob = str(mod.SCREEN_TOOL_DEFINITIONS)
    assert "xset" not in blob
