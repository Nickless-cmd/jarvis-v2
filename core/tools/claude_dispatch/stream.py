from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass
class ParsedEvent:
    kind: str
    text: str = ""
    tokens: int = 0
    cost_usd: float = 0.0
    raw: dict[str, Any] | None = None


def parse_stream_line(line: str) -> ParsedEvent | None:
    line = line.strip()
    if not line:
        return None
    try:
        data = json.loads(line)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    kind = str(data.get("type", "unknown"))

    text = ""
    if kind == "assistant":
        msg = data.get("message") or {}
        content = msg.get("content") or []
        if isinstance(content, list):
            text = " ".join(
                c.get("text", "") for c in content
                if isinstance(c, dict) and c.get("type") == "text"
            )

    tokens = 0
    cost = 0.0
    if kind == "result":
        usage = data.get("usage") or {}
        tokens = int(usage.get("input_tokens", 0)) + int(usage.get("output_tokens", 0))
        cost = float(data.get("total_cost_usd", 0.0))

    return ParsedEvent(kind=kind, text=text, tokens=tokens, cost_usd=cost, raw=data)
