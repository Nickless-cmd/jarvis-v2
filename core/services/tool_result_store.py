from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from core.runtime.config import TOOL_RESULTS_DIR

TOOL_RESULT_REFERENCE_RE = re.compile(r"^\[tool_result:(?P<result_id>[A-Za-z0-9_-]+)\]")
_DEFAULT_SUMMARY_LENGTH = 500


def summarize_result(content: str, max_length: int = _DEFAULT_SUMMARY_LENGTH) -> str:
    normalized = " ".join(str(content or "").split()).strip()
    if len(normalized) <= max_length:
        return normalized or "[empty tool result]"
    return normalized[: max_length - 1].rstrip() + "…"


def save_tool_result(
    tool_name: str,
    arguments: dict[str, object] | None,
    result_content: str,
    *,
    created_at: str | None = None,
) -> str:
    TOOL_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    result_id = f"tool-result-{uuid4().hex}"
    timestamp = created_at or datetime.now(UTC).isoformat()
    payload = {
        "result_id": result_id,
        "tool_name": str(tool_name or "").strip(),
        "arguments": dict(arguments or {}),
        "result": str(result_content or ""),
        "created_at": timestamp,
        "summary": summarize_result(result_content),
    }
    target = _result_path(result_id)
    tmp_target = target.with_suffix(f".{uuid4().hex}.tmp")
    tmp_target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp_target.replace(target)
    return result_id


def get_tool_result(result_id: str) -> dict[str, object] | None:
    normalized = str(result_id or "").strip()
    if not normalized:
        return None
    path = _result_path(normalized)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    return data


def cleanup_old_results(max_age_days: int = 7) -> int:
    TOOL_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    cutoff = datetime.now(UTC) - timedelta(days=max(max_age_days, 0))
    removed = 0
    for path in TOOL_RESULTS_DIR.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        created_at = _parse_dt(str((data or {}).get("created_at") or ""))
        if created_at is None or created_at > cutoff:
            continue
        path.unlink(missing_ok=True)
        removed += 1
    return removed


def build_tool_result_reference(result_id: str, *, tool_name: str, summary: str) -> str:
    normalized_tool = str(tool_name or "").strip() or "tool"
    normalized_summary = summarize_result(summary)
    return "\n".join(
        [
            f"[tool_result:{result_id}]",
            f"[{normalized_tool}]: {normalized_summary}",
            f'Use read_tool_result with result_id="{result_id}" to inspect the full output.',
        ]
    )


def parse_tool_result_reference(content: str) -> dict[str, str] | None:
    raw = str(content or "").strip()
    match = TOOL_RESULT_REFERENCE_RE.match(raw)
    if not match:
        return None
    result_id = str(match.group("result_id") or "").strip()
    if not result_id:
        return None
    lines = raw.splitlines()
    summary_line = lines[1].strip() if len(lines) > 1 else ""
    return {
        "result_id": result_id,
        "summary": summary_line,
    }


def render_tool_result_for_prompt(
    content: str,
    *,
    expand: bool,
    max_chars: int = 1200,
) -> str:
    raw = str(content or "").strip()
    ref = parse_tool_result_reference(raw)
    if not ref:
        normalized = " ".join(raw.split()).strip()
        if len(normalized) <= max_chars:
            return normalized
        return normalized[: max_chars - 1].rstrip() + "…"

    data = get_tool_result(ref["result_id"])
    if not data:
        normalized = " ".join(raw.split()).strip()
        return normalized[: max_chars - 1].rstrip() + "…" if len(normalized) > max_chars else normalized

    tool_name = str(data.get("tool_name") or "tool").strip() or "tool"
    if expand:
        result_text = " ".join(str(data.get("result") or "").split()).strip()
        bounded = result_text[: max_chars - 1].rstrip() + "…" if len(result_text) > max_chars else result_text
        return _prefixed_tool_text(tool_name, bounded or "[empty tool result]")

    summary = str(data.get("summary") or ref.get("summary") or "").strip()
    normalized_summary = summarize_result(summary, max_length=max_chars)
    return _prefixed_tool_text(tool_name, normalized_summary)


def _result_path(result_id: str) -> Path:
    return TOOL_RESULTS_DIR / f"{result_id}.json"


def _prefixed_tool_text(tool_name: str, text: str) -> str:
    normalized = str(text or "").strip()
    prefix = f"[{tool_name}]:"
    if normalized.startswith(prefix):
        return normalized
    return f"{prefix} {normalized}".strip()


def _parse_dt(value: str) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
