"""Turn raw tool failures into short, actionable text for visible surfaces."""
from __future__ import annotations

from typing import Any


def _field(raw_result: object, name: str) -> Any:
    return raw_result.get(name) if isinstance(raw_result, dict) else None


def normalise_tool_failure(
    status: str,
    result_text: str,
    raw_result: object,
    *,
    timeout_s: float | None = None,
) -> str:
    """Keep existing detail, otherwise derive a concrete cause from raw output."""
    existing = str(result_text or "").strip()
    if existing or str(status).lower() not in {"error", "failed", "timeout"}:
        return existing

    error = str(_field(raw_result, "error") or "").strip()
    message = str(_field(raw_result, "message") or "").strip()
    stderr = str(_field(raw_result, "stderr") or "").strip()
    exit_code = _field(raw_result, "exit_code")
    combined = " ".join(part for part in (error, message, stderr) if part).lower()

    if str(status).lower() == "timeout" or "timeout" in combined or "timed out" in combined:
        if timeout_s is not None:
            seconds = int(timeout_s) if float(timeout_s).is_integer() else timeout_s
            return f"Timeout efter {seconds} sekunder"
        return "Værktøjet fik timeout"

    parts: list[str] = []
    if isinstance(exit_code, int):
        parts.append(f"exit code {exit_code}")
    detail = stderr or error or message
    if detail:
        parts.append(detail)
    return ": ".join(parts) if parts else "Værktøjet fejlede uden yderligere detaljer"
