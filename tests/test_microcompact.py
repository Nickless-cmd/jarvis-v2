from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from core.services.prompt_sections import transcript_sections as ts


def _msg(mid: int, role: str, content: str, created_at: datetime) -> dict[str, object]:
    return {
        "id": mid,
        "role": role,
        "content": content,
        "created_at": created_at.isoformat(),
        "user_id": "",
    }


def test_time_gap_microcompact_stubs_old_tool_results():
    from core.context.microcompact import apply_time_gap_microcompact

    now = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)
    old = now - timedelta(hours=2)
    messages = [_msg(1, "assistant", "done", old)]
    for idx in range(2, 9):
        messages.append(_msg(idx, "tool", f"tool result {idx}", old))

    out, stats = apply_time_gap_microcompact(messages, now=now, keep_recent_tools=2)

    assert stats["folded_tool_results"] == 5
    assert [m["content"] for m in out if m["role"] == "tool"][-2:] == [
        "tool result 7",
        "tool result 8",
    ]
    assert str(out[1]["content"]).startswith("[old_tool_result:")
    assert "13 chars" in str(out[1]["content"])


def test_time_gap_microcompact_does_not_mutate_input():
    from core.context.microcompact import apply_time_gap_microcompact

    now = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)
    messages = [_msg(1, "assistant", "done", now - timedelta(hours=2))]
    messages.append(_msg(2, "tool", "x" * 20, now - timedelta(hours=2)))
    before = [dict(m) for m in messages]

    apply_time_gap_microcompact(messages, now=now, keep_recent_tools=0)

    assert messages == before


def test_time_gap_microcompact_keeps_active_session_unchanged():
    from core.context.microcompact import apply_time_gap_microcompact

    now = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)
    messages = [
        _msg(1, "assistant", "done", now - timedelta(minutes=20)),
        _msg(2, "tool", "fresh tool result", now - timedelta(minutes=19)),
    ]

    out, stats = apply_time_gap_microcompact(messages, now=now)

    assert out == messages
    assert stats["folded_tool_results"] == 0
    assert stats["reason"] == "gap_below_threshold"


def test_structured_transcript_uses_time_gap_microcompact():
    now = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)
    old = now - timedelta(hours=2)
    hist = [
        _msg(1, "user", "run tools", old),
        _msg(2, "assistant", "ok", old),
        _msg(3, "tool", "x" * 200, old),
        _msg(4, "tool", "new 4", old),
        _msg(5, "tool", "new 5", old),
        _msg(6, "tool", "new 6", old),
        _msg(7, "tool", "new 7", old),
        _msg(8, "tool", "new 8", old),
        _msg(9, "assistant", "done", old),
    ]

    with patch.object(ts, "chat_session_messages_since_last_compact", return_value=hist), \
         patch.object(ts, "_lifecycle_enabled", return_value=False), \
         patch.object(ts, "_round_collapse_enabled", return_value=False), \
         patch("core.context.microcompact._now_utc", return_value=now), \
         patch("core.services.prompt_contract._get_compact_marker_for_transcript",
               return_value=None), \
         patch("core.services.prompt_contract._maybe_auto_compact_session"):
        out = ts._build_structured_transcript_messages("s1", limit=60, include=True)

    blob = "\n".join(message["content"] for message in out)
    assert "[old_tool_result:" in blob
    assert "200 chars" in blob
    assert "x" * 100 not in blob
