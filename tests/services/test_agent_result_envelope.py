"""A3: agent_runtime_base._run_agent_tool_loop must return a real typed
dispatch envelope, not a hardcoded ``"status": "completed"``.

The model-call seam is ``execute_with_role_or_fallback``, resolved through the
facade module (``core.services.agent_runtime``). Tool payload building and tool
execution are patched on the base module so the loop path is exercised without
touching the real tool catalog or the world.
"""

import time

import core.services.agent_runtime as facade
import core.services.agent_runtime_base as base
from core.services.dispatch_status import DispatchStatus, is_failure


_ENVELOPE_KEYS = {
    "status", "tokens_in", "tokens_out", "cost_usd",
    "duration_ms", "tool_calls", "result",
}


def _force_tool_loop(monkeypatch):
    """Make the loop body run: non-empty tools payload + stubbed tool exec."""
    monkeypatch.setattr(
        base, "_build_agent_tools_payload",
        lambda allowed: [{"type": "function", "function": {"name": "read_file"}}],
    )
    monkeypatch.setattr(
        base, "_execute_agent_tool_call",
        lambda tc, *, agent_id="": '{"ok": true}',
    )


def _agent():
    return {
        "agent_id": "a1", "provider": "p", "model": "m",
        "allowed_tools_json": '["read_file"]',
    }


def test_success_full_envelope(monkeypatch):
    _force_tool_loop(monkeypatch)
    calls = {"n": 0}

    def fake(**kw):
        calls["n"] += 1
        time.sleep(0.002)  # ensure the monotonic-bracketed duration is measurable
        if calls["n"] == 1:
            return {
                "text": "", "input_tokens": 5, "output_tokens": 3, "cost_usd": 0.01,
                "tool_calls": [{"id": "c1", "function": {"name": "read_file", "arguments": "{}"}}],
            }
        return {
            "text": "final answer", "input_tokens": 4, "output_tokens": 6,
            "cost_usd": 0.02, "tool_calls": [],
        }

    monkeypatch.setattr(facade, "execute_with_role_or_fallback", fake)

    res = base._run_agent_tool_loop(agent=_agent(), prompt="hi", requires_tools=True)

    # all 7 envelope keys present (superset allowed)
    assert _ENVELOPE_KEYS.issubset(res.keys())
    assert res["status"] == DispatchStatus.COMPLETED
    assert res["tokens_in"] == 9 and res["tokens_out"] == 9
    assert res["cost_usd"] > 0
    assert res["duration_ms"] > 0
    assert res["tool_calls"] == 1  # exactly one tool call was executed
    assert res["result"] == "final answer"
    # legacy aliases preserved for existing callers
    assert res["input_tokens"] == 9 and res["output_tokens"] == 9
    assert res["text"] == "final answer"


def test_exception_is_failed_not_completed(monkeypatch):
    _force_tool_loop(monkeypatch)

    def boom(**kw):
        raise RuntimeError("provider exploded")

    monkeypatch.setattr(facade, "execute_with_role_or_fallback", boom)

    res = base._run_agent_tool_loop(agent=_agent(), prompt="hi", requires_tools=True)

    # regression guard: the fake-success must be gone
    assert res["status"] != "completed"
    assert res["status"] == DispatchStatus.FAILED
    assert is_failure(res["status"])
    assert "provider exploded" in str(res["result"])
    # usage still present (may be 0) + envelope shape intact
    assert _ENVELOPE_KEYS.issubset(res.keys())
    assert res["tokens_in"] == 0 and res["tokens_out"] == 0


def test_empty_return_is_blocked_not_completed(monkeypatch):
    _force_tool_loop(monkeypatch)

    monkeypatch.setattr(
        facade, "execute_with_role_or_fallback",
        lambda **kw: {"text": "", "input_tokens": 2, "output_tokens": 0,
                      "cost_usd": 0.0, "tool_calls": []},
    )

    res = base._run_agent_tool_loop(agent=_agent(), prompt="hi", requires_tools=True)

    assert res["status"] != "completed"
    assert res["status"] == DispatchStatus.BLOCKED
    assert _ENVELOPE_KEYS.issubset(res.keys())
