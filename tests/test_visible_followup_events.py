"""Carrier-typer for followup-loopet (visible_followup_events).

Dækker de rene data-shapes adapterne udveksler med pumpen — især at
``FollowupDone`` nu bærer ``finish_reason`` så en afkortet stream
(finish_reason="length") aldrig mere ligner en ren succes
(2026-08-19: "runnet stod som completed" men svaret døde midt i sætningen).
"""
from __future__ import annotations

from core.services.visible_followup_events import (
    FollowupDelta,
    FollowupDone,
    FollowupFailed,
    FollowupReasoningDelta,
    FollowupToolCalls,
    ToolExchange,
    ToolResult,
)


def test_followup_done_carries_finish_reason():
    """Truncation skal kunne ses på Done — default "" = ukendt/legacy."""
    done = FollowupDone(text="Hej", finish_reason="length")
    assert done.finish_reason == "length"
    # Legacy/adaptere der ikke sætter feltet → "" (ukendt), ikke crash.
    assert FollowupDone(text="Hej").finish_reason == ""


def test_followup_done_defaults_clean():
    done = FollowupDone(text="Svar.", reasoning_content="tænker")
    assert done.text == "Svar."
    assert done.reasoning_content == "tænker"
    assert done.finish_reason == ""


def test_carriers_roundtrip_basic_fields():
    delta = FollowupDelta(delta="d")
    assert delta.delta == "d"
    rd = FollowupReasoningDelta(delta="r")
    assert rd.delta == "r"
    tc = FollowupToolCalls(tool_calls=[{"id": "1", "type": "function",
                                        "function": {"name": "x", "arguments": "{}"}}])
    assert tc.tool_calls[0]["function"]["name"] == "x"
    failed = FollowupFailed(round_index=2, error="boom", summary="s",
                            failure_kind="provider_error", http_status=500)
    assert failed.round_index == 2 and failed.http_status == 500
    tr = ToolResult(tool_call_id="1", tool_name="x", content="ok")
    assert tr.content == "ok"
    ex = ToolExchange(text="t", tool_calls=[], results=[tr])
    assert ex.results[0].tool_call_id == "1"


def test_carriers_frozen():
    import pytest
    done = FollowupDone(text="x")
    with pytest.raises(Exception):
        done.text = "y"  # type: ignore[misc]
