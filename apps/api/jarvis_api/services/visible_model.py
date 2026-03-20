from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class VisibleModelResult:
    text: str
    input_tokens: int
    output_tokens: int
    cost_usd: float


def execute_visible_model(*, message: str, provider: str, model: str) -> VisibleModelResult:
    text = (
        "Jarvis visible lane behandler din besked gennem runtime-graensen. "
        f"Phase 1 modtog: {message}. "
        f"Execution-adapteren kører nu via provider={provider} model={model}. "
        "Reel provider-integration kan senere erstatte denne adapter uden at aendre visible-run kontrakten."
    )
    return VisibleModelResult(
        text=text,
        input_tokens=_estimate_tokens(message),
        output_tokens=_estimate_tokens(text),
        cost_usd=0.0,
    )


def _estimate_tokens(text: str) -> int:
    words = [part for part in text.strip().split() if part]
    return max(1, len(words))
