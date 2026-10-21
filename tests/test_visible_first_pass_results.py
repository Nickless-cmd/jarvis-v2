from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from core.services.visible_first_pass_results import publish_first_pass_results


def _event(frame: str) -> tuple[str, dict]:
    lines = frame.strip().splitlines()
    return lines[0].split(":", 1)[1].strip(), json.loads(lines[1].split(":", 1)[1])


def _run(**overrides):
    values = {
        "run_id": "run-1",
        "session_id": "session-1",
        "user_message": "go",
        "autonomous": False,
        "trust_all": False,
        "user_id": "owner",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _result(status="ok", **overrides):
    values = {
        "tool_name": "bash",
        "call_id": "call-1",
        "status": status,
        "arguments": {"command": "printf hi"},
        "result": {"status": status, "exit_code": 0},
        "result_text": "hi",
    }
    values.update(overrides)
    return values


async def _collect(results, *, run=None, step_counter=None):
    out = {}
    frames = [frame async for frame in publish_first_pass_results(
        results,
        run=run or _run(),
        step_counter=len(results) if step_counter is None else step_counter,
        out=out,
    )]
    return [_event(frame) for frame in frames], out


@pytest.mark.asyncio
async def test_success_error_and_gate_blocked_keep_exact_terminal_order(monkeypatch):
    surfaced = []
    monkeypatch.setattr(
        "core.services.tool_execution_trace.surface_result",
        lambda call_id, **fields: surfaced.append((call_id, fields["status"])),
    )
    events, out = await _collect([
        _result(),
        _result("error", call_id="call-2", result_text="boom",
                result={"status": "error", "exit_code": 7}),
        _result("gate_blocked", call_id="call-3", tool_name="write_file",
                result={"gate_type": "decision_gate", "message": "nej"}),
    ], step_counter=3)

    assert [(name, payload["type"]) for name, payload in events] == [
        ("capability", "tool_result"),
        ("working_step", "working_step"),
        ("capability", "tool_result"),
        ("working_step", "working_step"),
        ("capability", "gate_blocked"),
        ("working_step", "working_step"),
    ]
    assert out["resolved_result_texts"] == {0: "hi", 1: "boom", 2: "[decision_gate] nej"}
    assert surfaced == [("call-1", "ok"), ("call-2", "error"), ("call-3", "gate_blocked")]


@pytest.mark.asyncio
async def test_autonomous_denial_and_trust_auto_approval_are_terminal(monkeypatch):
    surfaced = []
    monkeypatch.setattr(
        "core.services.tool_execution_trace.surface_result",
        lambda call_id, **fields: surfaced.append((call_id, fields["status"])),
    )
    approval = _result(
        "approval_needed",
        result={"status": "approval_needed", "result_text": "approved text"},
    )
    denied_events, denied_out = await _collect([approval], run=_run(autonomous=True))
    approved_events, approved_out = await _collect(
        [_result("approval_needed", call_id="call-2",
                 result={"status": "approval_needed", "result_text": "approved text"})],
        run=_run(trust_all=True),
    )

    assert [(n, p["type"]) for n, p in denied_events] == [("capability", "tool_denied")]
    assert "cannot approve" in denied_out["resolved_result_texts"][0]
    assert [(n, p["type"]) for n, p in approved_events] == [("capability", "tool_approved")]
    assert approved_out["resolved_result_texts"] == {0: "approved text"}
    assert surfaced == [("call-1", "denied"), ("call-2", "approved")]


@pytest.mark.asyncio
@pytest.mark.parametrize("approved", [True, False])
async def test_explicit_approval_request_precedes_terminal_result(monkeypatch, approved):
    from core.services import visible_runs

    monkeypatch.setattr(visible_runs, "saet_godkendelse", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(visible_runs, "_set_visible_approval_state", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(visible_runs, "_publicer_approval_requested", lambda **_kwargs: None)

    async def wait(**kwargs):
        kwargs["out"]["result_text"] = "executed" if approved else None
        if False:
            yield ""

    monkeypatch.setattr(visible_runs, "wait_for_approval", wait)
    events, out = await _collect([_result(
        "approval_needed",
        result={"status": "approval_needed", "message": "må jeg?", "command": "date"},
    )])

    assert [(n, p["type"]) for n, p in events] == [
        ("approval_request", "approval_request"),
        ("capability", "tool_result" if approved else "tool_denied"),
    ]
    expected = "executed" if approved else "[bash]: Tool call denied by user."
    assert out["resolved_result_texts"] == {0: expected}


@pytest.mark.asyncio
async def test_app_action_stays_after_result_and_working_step(monkeypatch):
    monkeypatch.setattr(
        "core.tools.app_control_tool.build_app_action_event",
        lambda *_args, **_kwargs: {"type": "app_action_request", "action": "open"},
    )
    events, _out = await _collect([_result(tool_name="request_app_action")])
    assert [(n, p["type"]) for n, p in events] == [
        ("capability", "tool_result"),
        ("working_step", "working_step"),
        ("app_action_request", "app_action_request"),
    ]


@pytest.mark.asyncio
async def test_vaekning_med_ejer_tilstede_faar_kortet_i_stedet_for_afvisning(monkeypatch):
    """To steder traf modsatte beslutninger om SAMME tilfælde.

    `visible_tool_exec` sætter `force = run.autonomous and not _tilstede` med
    begrundelsen: «En vækning i Bjørns samtale har et menneske der kan svare, så
    godkendelses-gaten skal være levende — ellers arvede kørslen rettighederne
    uden at arve spørgsmålet.» Kørslen bad altså om et kort.

    Men her afviste `run.autonomous`-grenen kortet ubetinget. Målt 20/10-2026:
    en vækning i Bjørns egen samtale kunne ikke verificere en release med
    `gh release view` — den fik «Autonomous run cannot approve tool calls»,
    selv om han sad ved skærmen og kunne have svaret.

    Reglen er nu: afvisningen gælder kun når der IKKE er nogen i den anden ende.
    """
    from core.services import visible_runs

    monkeypatch.setattr(
        "core.tools.autonomous_tool_policy.presence_for_run", lambda _run: True)
    monkeypatch.setattr(visible_runs, "saet_godkendelse", lambda *_a, **_k: None)
    monkeypatch.setattr(visible_runs, "_set_visible_approval_state", lambda *_a, **_k: None)
    monkeypatch.setattr(visible_runs, "_publicer_approval_requested", lambda **_k: None)

    async def godkend(**kwargs):
        kwargs["out"]["result_text"] = "executed"
        if False:
            yield ""

    monkeypatch.setattr(visible_runs, "wait_for_approval", godkend)

    events, out = await _collect(
        [_result("approval_needed",
                 result={"status": "approval_needed", "message": "må jeg?",
                         "command": "gh release view"})],
        run=_run(autonomous=True),
    )

    typer = [p["type"] for _n, p in events]
    assert "tool_denied" not in typer, "en vækning med ejeren til stede må ikke afvises"
    assert "approval_request" in typer, "kørslen bad om et kort — det skal vises"
    assert out["resolved_result_texts"] == {0: "executed"}


@pytest.mark.asyncio
async def test_vaekning_UDEN_ejer_tilstede_afvises_stadig(monkeypatch):
    """Modstykket: uden nogen i den anden ende er afvisningen stadig terminal.

    Uden dette led ville fixet ovenfor være en åbning for hvert eneste autonomt
    baggrunds-run til at vente på et kort ingen ser.
    """
    monkeypatch.setattr(
        "core.tools.autonomous_tool_policy.presence_for_run", lambda _run: False)

    events, out = await _collect(
        [_result("approval_needed",
                 result={"status": "approval_needed", "result_text": "x"})],
        run=_run(autonomous=True),
    )

    assert [p["type"] for _n, p in events] == ["tool_denied"]
    assert "cannot approve" in out["resolved_result_texts"][0]
