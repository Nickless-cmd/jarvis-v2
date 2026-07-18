"""Per-model context-vinduer + model-bevidst beskeds-trimning (delt kilde).

Registry'et bærer ikke modellernes context-vinduer, så vi kuraterer dem her pr.
familie (substring-match). Bruges af:
  - /chat/model-context (composer-ringen) — så ringen er nøjagtig pr. model.
  - _stream_ollama_model (visible lane) — sikkerhedsnet der trimmer den samlede
    prompt så den passer i modellens vindue (ellers fx GLM 200k → HTTP 400
    "prompt is too long" → tavst intet-svar).

Owner kan rette tallene her ét sted.
"""
from __future__ import annotations

# (substring i model-navn, vindue i tokens). Først match vinder.
_MODEL_CONTEXT_WINDOWS: tuple[tuple[str, int], ...] = (
    ("flash", 1_000_000),       # deepseek-v4-flash (1M)
    ("deepseek", 128_000),
    ("gemini", 1_000_000),
    # GLM: version-specifikke vinduer FØR den generiske glm-fallback (substring-match
    # returnerer FØRSTE træf). glm-5.2 = 1M (som deepseek-flash), glm-5.1 = 256k.
    ("glm-5.2", 1_000_000), ("glm5.2", 1_000_000),
    ("glm-5.1", 256_000), ("glm5.1", 256_000),
    ("glm", 200_000),
    ("opus", 200_000), ("sonnet", 200_000), ("haiku", 200_000), ("claude", 200_000),
    ("gpt-4o", 128_000),
    ("gpt-5", 400_000), ("codex", 400_000),
    ("qwen", 256_000),
    ("llama", 128_000),
    ("mistral", 128_000), ("mixtral", 64_000),
)


def model_context_window(provider: str, model: str) -> int:
    """Bedste bud på modellens context-vindue (tokens). 0 = ukendt."""
    m = (model or "").lower()
    p = (provider or "").lower()
    for needle, win in _MODEL_CONTEXT_WINDOWS:
        if needle in m:
            return win
    if p == "ollama":
        # Lokale ollama-modeller serveres med visible_ollama_num_ctx-loftet.
        try:
            from core.runtime.settings import load_settings
            return int(load_settings().visible_ollama_num_ctx or 0)
        except Exception:
            return 0
    return 0


def effective_context_limit(provider: str, model: str, compact_threshold: int) -> int:
    """Det første loft der rammer: min(modellens vindue, autocompact-tærskel)."""
    window = model_context_window(provider, model)
    if window > 0 and compact_threshold > 0:
        return min(window, compact_threshold)
    return window or compact_threshold


# Konservativt char→token-forhold. char/4 er standard-heuristikken, men dansk +
# kode + tool-schemas tokeniserer TÆTTERE: målt 209009 ægte tokens vs 156667 ved
# char/4 (≈1.33×) på en GLM-overløbet session. ÷3 matcher og over-trimmer hellere
# en smule end at lade prompten overløbe (→ HTTP 400).
_CHARS_PER_TOKEN = 3


def _est_tokens(text: str) -> int:
    return max(0, len(str(text or "")) // _CHARS_PER_TOKEN)


def fit_messages_to_window(
    messages: list[dict],
    *,
    provider: str,
    model: str,
    output_budget: int = 16_000,
    tools_reserve: int = 16_000,
    safety_margin: int = 4_000,
) -> tuple[list[dict], int]:
    """Model-bevidst sikkerhedsnet: drop ÆLDSTE ikke-system-beskeder indtil den
    samlede prompt passer i modellens vindue (med plads til output + tools).

    Bevarer system-beskeden (index 0 hvis role=system) + de NYESTE beskeder.
    Returnerer (trimmede_messages, antal_droppede). Ukendt vindue → ingen trim.
    """
    window = model_context_window(provider, model)
    if window <= 0 or not messages:
        return messages, 0
    budget = window - output_budget - tools_reserve - safety_margin
    if budget <= 0:
        return messages, 0

    # Bevar evt. ledende system-besked separat; trim kun samtale-halen.
    head: list[dict] = []
    body = list(messages)
    if body and str(body[0].get("role")) == "system":
        head = [body[0]]
        body = body[1:]

    head_tokens = sum(_est_tokens(m.get("content")) for m in head)

    def _body_tokens(msgs: list[dict]) -> int:
        return sum(_est_tokens(m.get("content")) for m in msgs)

    dropped = 0
    # Drop ældste body-besked indtil head+body er under budgettet (behold mindst
    # de seneste 2 så et svar overhovedet giver mening).
    while body and len(body) > 2 and (head_tokens + _body_tokens(body)) > budget:
        body.pop(0)
        dropped += 1

    if dropped == 0:
        return messages, 0
    return head + body, dropped
