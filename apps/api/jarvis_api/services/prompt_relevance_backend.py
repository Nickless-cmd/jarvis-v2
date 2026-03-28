from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from urllib import error as urllib_error
from urllib import request as urllib_request

from core.identity.workspace_bootstrap import TEMPLATE_DIR
from core.runtime.provider_router import resolve_provider_router_target

RELEVANCE_MODEL = "llama3.1:8b"
RELEVANCE_TIMEOUT_SECONDS = 3
RELEVANCE_MAX_TEXT_CHARS = 240


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


def run_bounded_nl_prompt_relevance(
    *,
    text: str,
    mode: str,
    compact: bool,
    workspace_dir: Path,
) -> BoundedPromptRelevanceResult | None:
    if mode != "visible_chat":
        return None

    base_url = _resolve_relevance_base_url()
    if not base_url:
        return None

    instructions = load_visible_relevance_prompt(workspace_dir=workspace_dir)
    if not instructions:
        return None

    prompt = _build_relevance_prompt(
        instructions=instructions,
        text=text,
        mode=mode,
        compact=compact,
    )
    payload = {
        "model": RELEVANCE_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0,
            "num_predict": 96,
        },
    }
    req = urllib_request.Request(
        f"{base_url.rstrip('/')}/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib_request.urlopen(req, timeout=RELEVANCE_TIMEOUT_SECONDS) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (urllib_error.URLError, urllib_error.HTTPError, TimeoutError, json.JSONDecodeError, OSError):
        return None

    parsed = _parse_relevance_response(str(data.get("response") or ""))
    if parsed is None:
        return None
    return parsed


def load_visible_relevance_prompt(*, workspace_dir: Path) -> str | None:
    workspace_path = workspace_dir / "VISIBLE_RELEVANCE.md"
    if workspace_path.exists():
        return workspace_path.read_text(encoding="utf-8", errors="replace").strip() or None

    template_path = TEMPLATE_DIR / "VISIBLE_RELEVANCE.md"
    if template_path.exists():
        return template_path.read_text(encoding="utf-8", errors="replace").strip() or None
    return None


def _resolve_relevance_base_url() -> str | None:
    for lane in ("local", "visible"):
        target = resolve_provider_router_target(lane=lane)
        if not bool(target.get("active")):
            continue
        if str(target.get("provider") or "").strip() != "ollama":
            continue
        base_url = str(target.get("base_url") or "").strip()
        if base_url:
            return base_url
    return None


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
            'Return JSON only with keys: memory_relevant, guidance_relevant, transcript_relevant, continuity_relevant, support_signals_relevant, confidence.',
            f"mode={mode}",
            f"compact={'true' if compact else 'false'}",
            f"user_message={normalized or '(empty)'}",
        ]
    )


def _parse_relevance_response(text: str) -> BoundedPromptRelevanceResult | None:
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
        mode="visible_chat",
        memory_relevant=_coerce_bool(data.get("memory_relevant")),
        guidance_relevant=_coerce_bool(data.get("guidance_relevant")),
        transcript_relevant=_coerce_bool(data.get("transcript_relevant")),
        continuity_relevant=_coerce_bool(data.get("continuity_relevant")),
        support_signals_relevant=_coerce_bool(data.get("support_signals_relevant")),
        confidence=confidence,
    )


def _coerce_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    if isinstance(value, (int, float)):
        return bool(value)
    return False
