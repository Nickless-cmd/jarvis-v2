"""Time-gap microcompaction for visible transcript tool results.

This is deliberately not a sliding recency policy. It only activates after a
quiet gap, when provider prefix caches are already cold enough that rewriting
old tool payloads is cheaper than carrying them forward forever.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

_ENABLED_KEY = "time_gap_microcompact_enabled"
DEFAULT_GAP_MINUTES = 60
DEFAULT_KEEP_RECENT_TOOLS = 5
_STUB_PREFIX = "[old_tool_result:"


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _enabled() -> bool:
    try:
        from core.runtime.db_core import get_runtime_state_bool
        return get_runtime_state_bool(_ENABLED_KEY, default=True)
    except Exception:
        return True


def _parse_dt(value: Any) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _latest_assistant_at(messages: list[dict[str, Any]]) -> datetime | None:
    for message in reversed(messages):
        if str(message.get("role") or "") == "assistant":
            parsed = _parse_dt(message.get("created_at"))
            if parsed is not None:
                return parsed
    return None


def _is_stubbed(content: Any) -> bool:
    return str(content or "").startswith(_STUB_PREFIX)


def _stub_tool_result(message: dict[str, Any]) -> dict[str, Any]:
    content = str(message.get("content") or "")
    stub = dict(message)
    stub["content"] = f"{_STUB_PREFIX}{message.get('id', '?')} - {len(content)} chars]"
    return stub


def apply_time_gap_microcompact(
    messages: list[dict[str, Any]],
    *,
    now: datetime | None = None,
    gap_minutes: int = DEFAULT_GAP_MINUTES,
    keep_recent_tools: int = DEFAULT_KEEP_RECENT_TOOLS,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Stub old tool results after a long quiet gap.

    Input is never mutated. Unknown timestamps fail open by preserving history.
    The output is deterministic for the same messages, keeping DeepSeek's prefix
    cache stable on repeated builds after the same quiet gap.
    """
    if not messages:
        return [], {"active": False, "folded_tool_results": 0, "reason": "empty"}
    if not _enabled():
        return list(messages), {"active": False, "folded_tool_results": 0, "reason": "disabled"}

    latest = _latest_assistant_at(messages)
    if latest is None:
        return list(messages), {"active": False, "folded_tool_results": 0, "reason": "no_assistant_timestamp"}

    current = now or _now_utc()
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    current = current.astimezone(UTC)
    gap_seconds = (current - latest).total_seconds()
    threshold_seconds = max(int(gap_minutes), 0) * 60
    if gap_seconds < threshold_seconds:
        return list(messages), {"active": False, "folded_tool_results": 0, "reason": "gap_below_threshold"}

    tool_positions = [idx for idx, message in enumerate(messages)
                      if str(message.get("role") or "") == "tool"]
    keep = max(int(keep_recent_tools), 0)
    if len(tool_positions) <= keep:
        return list(messages), {"active": True, "folded_tool_results": 0, "reason": "nothing_old_enough"}

    fold_positions = set(tool_positions[:-keep]) if keep > 0 else set(tool_positions)
    folded = 0
    out: list[dict[str, Any]] = []
    for idx, message in enumerate(messages):
        if idx in fold_positions and not _is_stubbed(message.get("content")):
            out.append(_stub_tool_result(message))
            folded += 1
        else:
            out.append(message)

    return out, {
        "active": True,
        "folded_tool_results": folded,
        "reason": "quiet_gap",
        "gap_minutes": int(gap_seconds // 60),
        "keep_recent_tools": keep,
    }
