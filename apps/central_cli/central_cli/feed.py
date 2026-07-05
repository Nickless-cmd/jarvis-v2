from __future__ import annotations

from collections import deque
from dataclasses import dataclass

_COLOR = {"error": "red", "critical": "red", "degraded": "yellow",
          "warning": "yellow", "observe": "green", "info": "blue"}


@dataclass(frozen=True)
class FeedLine:
    cluster: str
    nerve: str
    decision: str
    text: str
    color: str


def feed_line_from_event(ev: dict) -> FeedLine:
    cluster = str(ev.get("cluster") or "?")
    nerve = str(ev.get("nerve") or "?")
    decision = str(ev.get("decision") or "observe")
    reason = str(ev.get("reason") or "")
    color = _COLOR.get(decision, "white")
    text = f"● {cluster}/{nerve} · {decision}" + (f" — {reason}" if reason else "")
    return FeedLine(cluster, nerve, decision, text, color)


class FeedBuffer:
    """Bounded, nyeste-først feed-buffer (live nerve-firings)."""
    def __init__(self, cap: int = 200):
        self._dq: deque[FeedLine] = deque(maxlen=cap)

    def add(self, line: FeedLine) -> None:
        self._dq.append(line)

    def recent(self) -> list[FeedLine]:
        return list(reversed(self._dq))
