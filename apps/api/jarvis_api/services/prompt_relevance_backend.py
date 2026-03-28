from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from urllib import error as urllib_error
from urllib import request as urllib_request

from core.identity.workspace_bootstrap import TEMPLATE_DIR
from core.runtime.provider_router import resolve_provider_router_target
from core.runtime.settings import load_settings

RELEVANCE_TIMEOUT_SECONDS = 3
RELEVANCE_MAX_TEXT_CHARS = 240
MEMORY_SELECTION_MAX_ENTRIES = 8
MEMORY_ENTRY_MAX_CHARS = 140


@dataclass(slots=True)
class BoundedPromptRelevanceResult:
    backend: str
    mode: str
    memory_relevant: bool
    guidance_relevant: bool
    transcript_relevant: bool
    continuity_relevant: bool
    support_signals_relevant: bool
    confidence: str


@dataclass(slots=True)
class BoundedPromptRelevanceAttempt:
    attempted: bool
    success: bool
    backend: str
    provider: str | None
    model: str | None
    status: str
    result: BoundedPromptRelevanceResult | None


@dataclass(slots=True)
class BoundedMemorySelectionResult:
    backend: str
    selected_indexes: list[int]
    confidence: str


@dataclass(slots=True)
class BoundedMemorySelectionAttempt:
    attempted: bool
    success: bool
    backend: str
    provider: str | None
    model: str | None
    status: str
    result: BoundedMemorySelectionResult | None


def run_bounded_nl_prompt_relevance(
    *,
    text: str,
    mode: str,
    compact: bool,
    workspace_dir: Path,
) -> BoundedPromptRelevanceAttempt:
    supported_modes = {"visible_chat", "heartbeat", "future_agent_task"}
    if mode not in supported_modes:
        return BoundedPromptRelevanceAttempt(
            attempted=False,
            success=False,
            backend="bounded-local-ollama",
            provider=None,
            model=None,
            status="unsupported-mode",
            result=None,
        )

    target = _resolve_relevance_target()
    if target is None:
        return BoundedPromptRelevanceAttempt(
            attempted=False,
            success=False,
            backend="bounded-local-ollama",
            provider=None,
            model=_selected_relevance_model(),
            status="backend-unavailable",
            result=None,
        )

    instructions = load_visible_relevance_prompt(workspace_dir=workspace_dir)
    if not instructions:
        return BoundedPromptRelevanceAttempt(
            attempted=False,
            success=False,
            backend="bounded-local-ollama",
            provider=str(target.get("provider") or "").strip() or None,
            model=str(target.get("model") or "").strip() or None,
            status="prompt-missing",
            result=None,
        )

    prompt = _build_relevance_prompt(
        instructions=instructions,
        text=text,
        mode=mode,
        compact=compact,
    )
    payload = {
        "model": str(target.get("model") or "").strip(),
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0,
            "num_predict": 96,
        },
    }
    req = urllib_request.Request(
        f"{str(target.get('base_url') or '').rstrip('/')}/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib_request.urlopen(req, timeout=RELEVANCE_TIMEOUT_SECONDS) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (
        urllib_error.URLError,
        urllib_error.HTTPError,
        TimeoutError,
        json.JSONDecodeError,
        OSError,
    ):
        return BoundedPromptRelevanceAttempt(
            attempted=True,
            success=False,
            backend="bounded-local-ollama",
            provider=str(target.get("provider") or "").strip() or None,
            model=str(target.get("model") or "").strip() or None,
            status="request-failed",
            result=None,
        )

    parsed = _parse_relevance_response(str(data.get("response") or ""), mode)
    if parsed is None:
        return BoundedPromptRelevanceAttempt(
            attempted=True,
            success=False,
            backend="bounded-local-ollama",
            provider=str(target.get("provider") or "").strip() or None,
            model=str(target.get("model") or "").strip() or None,
            status="parse-failed",
            result=None,
        )
    return BoundedPromptRelevanceAttempt(
        attempted=True,
        success=True,
        backend="bounded-local-ollama",
        provider=str(target.get("provider") or "").strip() or None,
        model=str(target.get("model") or "").strip() or None,
        status="success",
        result=parsed,
    )


def bounded_nl_prompt_relevance_smoke(
    *,
    text: str,
    workspace_dir: Path,
    mode: str = "visible_chat",
    compact: bool = True,
) -> dict[str, object]:
    attempt = run_bounded_nl_prompt_relevance(
        text=text,
        mode=mode,
        compact=compact,
        workspace_dir=workspace_dir,
    )
    return {
        "backend": attempt.backend,
        "provider": attempt.provider,
        "model": attempt.model,
        "attempted": attempt.attempted,
        "success": attempt.success,
        "fallback_used": not attempt.success,
        "status": attempt.status,
        "confidence": attempt.result.confidence if attempt.result else None,
    }


def run_bounded_nl_memory_entry_selection(
    *,
    user_message: str,
    entries: list[str],
    max_lines: int,
    workspace_dir: Path,
    mode: str = "visible_chat",
) -> BoundedMemorySelectionAttempt:
    if not entries:
        return BoundedMemorySelectionAttempt(
            attempted=False,
            success=False,
            backend="bounded-local-ollama",
            provider=None,
            model=None,
            status="no-entries",
            result=None,
        )

    target = _resolve_relevance_target()
    if target is None:
        return BoundedMemorySelectionAttempt(
            attempted=False,
            success=False,
            backend="bounded-local-ollama",
            provider=None,
            model=_selected_relevance_model(),
            status="backend-unavailable",
            result=None,
        )

    instructions = load_visible_memory_selection_prompt(workspace_dir=workspace_dir)
    if not instructions:
        return BoundedMemorySelectionAttempt(
            attempted=False,
            success=False,
            backend="bounded-local-ollama",
            provider=str(target.get("provider") or "").strip() or None,
            model=str(target.get("model") or "").strip() or None,
            status="prompt-missing",
            result=None,
        )

    bounded_entries = _bounded_memory_candidates(entries)
    prompt = _build_memory_selection_prompt(
        instructions=instructions,
        user_message=user_message,
        entries=bounded_entries,
        max_lines=max_lines,
        mode=mode,
    )
    payload = {
        "model": str(target.get("model") or "").strip(),
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0,
            "num_predict": 96,
        },
    }
    req = urllib_request.Request(
        f"{str(target.get('base_url') or '').rstrip('/')}/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib_request.urlopen(req, timeout=RELEVANCE_TIMEOUT_SECONDS) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (
        urllib_error.URLError,
        urllib_error.HTTPError,
        TimeoutError,
        json.JSONDecodeError,
        OSError,
    ):
        return BoundedMemorySelectionAttempt(
            attempted=True,
            success=False,
            backend="bounded-local-ollama",
            provider=str(target.get("provider") or "").strip() or None,
            model=str(target.get("model") or "").strip() or None,
            status="request-failed",
            result=None,
        )

    parsed = _parse_memory_selection_response(
        str(data.get("response") or ""),
        entry_count=len(bounded_entries),
        max_lines=max_lines,
    )
    if parsed is None:
        return BoundedMemorySelectionAttempt(
            attempted=True,
            success=False,
            backend="bounded-local-ollama",
            provider=str(target.get("provider") or "").strip() or None,
            model=str(target.get("model") or "").strip() or None,
            status="parse-failed",
            result=None,
        )
    return BoundedMemorySelectionAttempt(
        attempted=True,
        success=True,
        backend="bounded-local-ollama",
        provider=str(target.get("provider") or "").strip() or None,
        model=str(target.get("model") or "").strip() or None,
        status="success",
        result=parsed,
    )


def load_visible_relevance_prompt(*, workspace_dir: Path) -> str | None:
    workspace_path = workspace_dir / "VISIBLE_RELEVANCE.md"
    if workspace_path.exists():
        return (
            workspace_path.read_text(encoding="utf-8", errors="replace").strip() or None
        )

    template_path = TEMPLATE_DIR / "VISIBLE_RELEVANCE.md"
    if template_path.exists():
        return (
            template_path.read_text(encoding="utf-8", errors="replace").strip() or None
        )
    return None


def load_visible_memory_selection_prompt(*, workspace_dir: Path) -> str | None:
    workspace_path = workspace_dir / "VISIBLE_MEMORY_SELECTION.md"
    if workspace_path.exists():
        return (
            workspace_path.read_text(encoding="utf-8", errors="replace").strip() or None
        )

    template_path = TEMPLATE_DIR / "VISIBLE_MEMORY_SELECTION.md"
    if template_path.exists():
        return (
            template_path.read_text(encoding="utf-8", errors="replace").strip() or None
        )
    return None


def _resolve_relevance_target() -> dict[str, str] | None:
    model = _selected_relevance_model()
    if not model:
        return None
    for lane in ("local", "visible"):
        target = resolve_provider_router_target(lane=lane)
        if not bool(target.get("active")):
            continue
        if str(target.get("provider") or "").strip() != "ollama":
            continue
        base_url = str(target.get("base_url") or "").strip()
        if base_url:
            return {
                "provider": "ollama",
                "model": model,
                "base_url": base_url,
            }
    return None


def _selected_relevance_model() -> str:
    settings = load_settings()
    selected = str(settings.relevance_model_name or "").strip()
    return selected or "llama3.1:8b"


def _build_relevance_prompt(
    *,
    instructions: str,
    text: str,
    mode: str,
    compact: bool,
) -> str:
    normalized = " ".join(str(text or "").split())
    if len(normalized) > RELEVANCE_MAX_TEXT_CHARS:
        normalized = normalized[: RELEVANCE_MAX_TEXT_CHARS - 1].rstrip() + "…"
    return "\n".join(
        [
            instructions,
            "Return JSON only with keys: memory_relevant, guidance_relevant, transcript_relevant, continuity_relevant, support_signals_relevant, confidence.",
            f"mode={mode}",
            f"compact={'true' if compact else 'false'}",
            f"user_message={normalized or '(empty)'}",
        ]
    )


def _build_memory_selection_prompt(
    *,
    instructions: str,
    user_message: str,
    entries: list[str],
    max_lines: int,
    mode: str = "visible_chat",
) -> str:
    normalized = " ".join(str(user_message or "").split())
    if len(normalized) > RELEVANCE_MAX_TEXT_CHARS:
        normalized = normalized[: RELEVANCE_MAX_TEXT_CHARS - 1].rstrip() + "…"
    entry_lines = [f"{index}: {entry}" for index, entry in enumerate(entries)]
    return "\n".join(
        [
            instructions,
            "Return JSON only with keys: selected_indexes, confidence.",
            f"mode={mode}",
            f"max_lines={max(max_lines, 1)}",
            f"user_message={normalized or '(empty)'}",
            "memory_entries:",
            *entry_lines,
        ]
    )


def _parse_relevance_response(
    text: str, mode: str
) -> BoundedPromptRelevanceResult | None:
    body = str(text or "").strip()
    if not body:
        return None
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        start = body.find("{")
        end = body.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            data = json.loads(body[start : end + 1])
        except json.JSONDecodeError:
            return None

    if not isinstance(data, dict):
        return None

    confidence = str(data.get("confidence") or "low").strip().lower()
    if confidence not in {"low", "medium", "high"}:
        confidence = "low"

    return BoundedPromptRelevanceResult(
        backend="bounded-local-ollama",
        mode=mode,
        memory_relevant=_coerce_bool(data.get("memory_relevant")),
        guidance_relevant=_coerce_bool(data.get("guidance_relevant")),
        transcript_relevant=_coerce_bool(data.get("transcript_relevant")),
        continuity_relevant=_coerce_bool(data.get("continuity_relevant")),
        support_signals_relevant=_coerce_bool(data.get("support_signals_relevant")),
        confidence=confidence,
    )


def _parse_memory_selection_response(
    text: str,
    *,
    entry_count: int,
    max_lines: int,
) -> BoundedMemorySelectionResult | None:
    body = str(text or "").strip()
    if not body:
        return None
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        start = body.find("{")
        end = body.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            data = json.loads(body[start : end + 1])
        except json.JSONDecodeError:
            return None

    if not isinstance(data, dict):
        return None

    raw_indexes = data.get("selected_indexes")
    if not isinstance(raw_indexes, list):
        return None
    selected_indexes: list[int] = []
    for item in raw_indexes:
        if not isinstance(item, int):
            continue
        if item < 0 or item >= entry_count:
            continue
        if item in selected_indexes:
            continue
        selected_indexes.append(item)
    if not selected_indexes:
        return None
    selected_indexes = selected_indexes[: max(max_lines, 1)]

    confidence = str(data.get("confidence") or "low").strip().lower()
    if confidence not in {"low", "medium", "high"}:
        confidence = "low"

    return BoundedMemorySelectionResult(
        backend="bounded-local-ollama",
        selected_indexes=selected_indexes,
        confidence=confidence,
    )


def _bounded_memory_candidates(entries: list[str]) -> list[str]:
    bounded = entries[-MEMORY_SELECTION_MAX_ENTRIES:]
    clipped: list[str] = []
    for entry in bounded:
        text = " ".join(str(entry or "").split())
        if len(text) > MEMORY_ENTRY_MAX_CHARS:
            text = text[: MEMORY_ENTRY_MAX_CHARS - 1].rstrip() + "…"
        clipped.append(text)
    return clipped


def _coerce_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    if isinstance(value, (int, float)):
        return bool(value)
    return False
