"""Verifikation efter skrivning må ikke afvises som dublet (loop-fix 5/9-2026).

Rekonstruktion af Bjørns session 5. september kl. 06:05: Jarvis retter en linje
i USER.md, vil verificere at den landede, kører samme bash-kommando som før
skrivningen — og får «[Duplicate tool call skipped in same visible run]».
"""
from __future__ import annotations

import types

import core.services.simple_tool_executor as STE


def _controller():
    return types.SimpleNamespace(
        seen_simple_tool_call_signatures=set(), trust_all=False)


def _finalize(ctrl, *, tool, arguments, status="ok"):
    token = {"name": tool, "arguments": dict(arguments),
             "signature": STE.json.dumps({"tool_name": tool, "arguments": arguments},
                                         ensure_ascii=False, sort_keys=True),
             "soft_warn": ""}
    return STE._finalize_call(
        token, {"status": status}, controller=ctrl,
        exec_fmt=lambda _n, _r: "resultat")


def test_a_write_makes_earlier_observations_repeatable(monkeypatch):
    monkeypatch.setattr("core.services.agentic_tool_cache.store_result",
                        lambda **_kw: None, raising=False)
    ctrl = _controller()
    verify = {"command": "grep -n DeepSeek USER.md"}
    _finalize(ctrl, tool="bash", arguments=verify)
    assert len(ctrl.seen_simple_tool_call_signatures) == 1

    # Skrivningen rydder sættet: verden er en anden nu.
    _finalize(ctrl, tool="edit_file", arguments={"path": "USER.md", "old": "a", "new": "b"})
    sigs = ctrl.seen_simple_tool_call_signatures
    assert len(sigs) == 1, "kun selve skrivningen skal staa tilbage"
    assert "edit_file" in next(iter(sigs))

    # ... og den samme verifikation kan koeres igen.
    verify_sig = STE.json.dumps({"tool_name": "bash", "arguments": verify},
                                ensure_ascii=False, sort_keys=True)
    assert verify_sig not in ctrl.seen_simple_tool_call_signatures


def test_the_write_itself_stays_deduplicated(monkeypatch):
    """Ryddes ALT, ville et gentaget identisk skrive-kald blive udfoert to gange."""
    monkeypatch.setattr("core.services.agentic_tool_cache.store_result",
                        lambda **_kw: None, raising=False)
    ctrl = _controller()
    args = {"path": "USER.md", "old": "a", "new": "b"}
    _finalize(ctrl, tool="edit_file", arguments=args)
    sig = STE.json.dumps({"tool_name": "edit_file", "arguments": args},
                         ensure_ascii=False, sort_keys=True)
    assert sig in ctrl.seen_simple_tool_call_signatures


def test_a_read_does_not_clear_the_guard(monkeypatch):
    """Spin-vaernet skal blive: laesninger rydder ingenting."""
    monkeypatch.setattr("core.services.agentic_tool_cache.store_result",
                        lambda **_kw: None, raising=False)
    ctrl = _controller()
    _finalize(ctrl, tool="bash", arguments={"command": "ls -la"})
    _finalize(ctrl, tool="read_file", arguments={"path": "USER.md"})
    assert len(ctrl.seen_simple_tool_call_signatures) == 2


def test_a_failed_write_does_not_clear_the_guard(monkeypatch):
    monkeypatch.setattr("core.services.agentic_tool_cache.store_result",
                        lambda **_kw: None, raising=False)
    ctrl = _controller()
    _finalize(ctrl, tool="bash", arguments={"command": "ls -la"})
    _finalize(ctrl, tool="edit_file", arguments={"path": "x"}, status="error")
    assert len(ctrl.seen_simple_tool_call_signatures) == 1
