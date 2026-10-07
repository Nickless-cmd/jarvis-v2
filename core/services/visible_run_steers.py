"""Keep real mid-flight user steers distinct from runtime turn notices."""
from __future__ import annotations

from typing import Any

from core.services.run_trailing import RundeHale


_STOP_WORDS = frozenset({"stop", "stop.", "cancel", "afbryd", "abort", "stop nu"})


def append_real_user_steers(
    tail: RundeHale, steers: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], bool]:
    """Append only genuine client steers with user role; stop at a cancel steer."""
    accepted: list[dict[str, Any]] = []
    for steer in steers:
        content = str(steer.get("content") or "").strip()
        if not content:
            continue
        tail.tilfoej_vedvarende(content, rolle="user")
        accepted.append({**steer, "content": content})
        if content.lower() in _STOP_WORDS:
            return accepted, True
    return accepted, False
