from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ParsedEvent:
    kind: str
    text: str = ""
    tokens: int = 0
    cost_usd: float = 0.0
    raw: dict[str, Any] | None = None
    # (14/11-2026) Værktøjskaldene selv, ikke kun teksten om dem. Før blev
    # `tool_use`-blokke kastet væk her, så en CLI-agent der læste 14 filer
    # efterlod nul spor i `agent_tool_calls` — og den tomme tabel blev læst som
    # «agenten kan ikke kalde værktøjer». Formen er målt mod CLI 2.1.318:
    # `{"type":"tool_use","id":…,"name":…,"input":{…}}` i assistant-blokke.
    tool_uses: list[dict[str, Any]] = field(default_factory=list)
    tool_results: list[dict[str, Any]] = field(default_factory=list)


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
    tool_uses: list[dict[str, Any]] = []
    tool_results: list[dict[str, Any]] = []
    if kind in {"assistant", "user"}:
        msg = data.get("message") or {}
        content = msg.get("content") or []
        if isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                btype = block.get("type")
                if btype == "text":
                    text = f"{text} {block.get('text', '')}".strip() if text else str(
                        block.get("text", "")
                    )
                elif btype == "tool_use":
                    tool_uses.append(
                        {
                            "id": str(block.get("id") or ""),
                            "name": str(block.get("name") or ""),
                            "input": block.get("input") or {},
                        }
                    )
                elif btype == "tool_result":
                    raw_content = block.get("content")
                    if isinstance(raw_content, str):
                        preview = raw_content
                    else:
                        preview = json.dumps(raw_content, ensure_ascii=False)
                    tool_results.append(
                        {
                            "tool_use_id": str(block.get("tool_use_id") or ""),
                            "is_error": bool(block.get("is_error")),
                            "preview": preview,
                        }
                    )

    tokens = 0
    cost = 0.0
    if kind == "result":
        usage = data.get("usage") or {}
        tokens = int(usage.get("input_tokens", 0)) + int(usage.get("output_tokens", 0))
        cost = float(data.get("total_cost_usd", 0.0))

    return ParsedEvent(
        kind=kind,
        text=text,
        tokens=tokens,
        cost_usd=cost,
        raw=data,
        tool_uses=tool_uses,
        tool_results=tool_results,
    )
