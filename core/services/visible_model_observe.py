"""Central-observe helpers + thinking-delimiter cleanup for the visible lane.

Split out of ``core.services.visible_model`` (boy-scout, 2026-07-07). All
helpers are self-safe: observability must never disturb the stream/error path.
Re-exported verbatim from ``core.services.visible_model``.
"""

from __future__ import annotations


def _observe_visible_prefill(
    provider: str, model: str, *, prompt_tokens: int, prefill_ms: int,
) -> None:
    """Gør ollama-lanens PREFILL-cache MÅLBAR (2026-07-19, blind-spot-luk).

    ollama-cloud eksponerer IKKE cache-tokens i /api/chat's usage (kun
    prompt_eval_count) → costs.cache_hit_tokens=0 for ALLE ollama-visible-ture,
    selvom upstream (kimi/deepseek:cloud) reelt CACHER KV-prefixet (bevist:
    TTFT 2.1s→0.9s på identisk 42k-prefix). Vi kan ikke aflæse cachen fra
    svaret, så vi UDLEDER den fra prefill-hastigheden: en stor prompt der
    prefiller hurtigt = prefix genbrugt. DeepSeek's DIREKTE API rører vi ikke
    (den rapporterer eksakt cache) — dette er KUN for ollama, og signalet er
    LABELED 'inferred' så det aldrig forveksles med eksakte tal. Self-safe.
    """
    try:
        if prompt_tokens < 1 or prefill_ms < 1:
            return
        tok_per_s = int(prompt_tokens / (prefill_ms / 1000.0))
        # Heuristik (dokumenteret): ingen model prefiller ~25k+ tok/s koldt —
        # så høj throughput på en stor prompt ⇒ prefixet blev cachet upstream.
        # Små prompts (<4k) er uinteressante (prefill-tid domineres af overhead).
        cache_likely = bool(prompt_tokens >= 4000 and tok_per_s >= 25000)
        from core.services.central_core import central
        central().observe({
            "cluster": "stream",
            "nerve": "visible_prefill_cache",
            "lane": "visible", "provider": str(provider or ""),
            "model": str(model or ""),
            "prompt_tokens": int(prompt_tokens),
            "prefill_ms": int(prefill_ms),
            "prefill_tok_per_s": tok_per_s,
            "cache_inferred": cache_likely,
            "source": "inferred",  # ALDRIG eksakt — udledt af prefill-hastighed
        })
    except Exception:
        pass


def _observe_visible_provider_error(provider: str, model: str, status_code: int,
                                    detail: str) -> None:
    """Gør en VISIBLE-lane provider-fejl synlig i Centralen (stream-cluster). Self-safe.
    Samler ollama-lanens HTTP-fejl + tomme svar — de var FØR tavse ("spinner→stop→intet")."""
    try:
        from core.services.central_core import central
        central().observe({
            "cluster": "stream",
            "nerve": "provider_rate_limited" if status_code == 429 else "provider_error",
            "lane": "visible", "provider": str(provider or ""), "model": str(model or ""),
            "status_code": int(status_code), "detail": str(detail or "")[:200],
        })
    except Exception:
        pass


def _observe_malformed_stream_payload(
    provider: str, model: str, path: str, *, ended_malformed: bool, detail: str = "",
) -> None:
    """A11 (spec §11.1): den egne SSE/NDJSON-decoder mødte en malformet/trunkeret
    ``data:``-linje eller et split UTF-8-codepoint. Gør det MÅLBART i Centralen.

    To severities, BEVIDST adskilt så vi kan måle hvor ofte streamen FAKTISK dør:
      - ``ended_malformed=False`` → vi sprang ÉN dårlig chunk over på en ellers sund
        stream (lav severity — streamen overlevede, intet svar tabt).
      - ``ended_malformed=True``  → streamen sluttede uden terminal/``done`` efter et
        skip = den retryable ``malformed_stream_payload`` 4.1 kan retrye (høj severity).
    Self-safe: observabilitet må aldrig forstyrre stream-stien."""
    try:
        from core.services.central_core import central
        central().observe({
            "cluster": "stream",
            "nerve": "malformed_stream_payload",
            "lane": "visible", "provider": str(provider or ""), "model": str(model or ""),
            "path": str(path or ""),
            "severity": "fail" if ended_malformed else "skip",
            "ended_malformed": bool(ended_malformed),
            "detail": str(detail or "")[:200],
        })
    except Exception:
        pass


def _observe_content_empty_thinking_fallback(
    provider: str, model: str, path: str, thinking_len: int,
) -> None:
    """Reasoning-model svarede i `message.thinking` mens `message.content` var TOM
    (glm-5.2:cloud, deepseek thinking, ...). Vi surfacer thinking som svar i stedet
    for at raise empty_completion. Gør det MÅLBART i Centralen — vi kan ikke altid
    skelne (a) modellen lagde svaret i thinking by design fra (b) stream droppede
    efter thinking før content (transient). Begge surfaces, men signalet lader det
    højere lag måle hyppighed + evt. retrye. Self-safe."""
    try:
        from core.services.central_core import central
        central().observe({
            "cluster": "stream",
            "nerve": "content_empty_thinking_fallback",
            "lane": "visible", "provider": str(provider or ""), "model": str(model or ""),
            "path": str(path or ""), "thinking_len": int(thinking_len),
        })
    except Exception:
        pass


def _strip_thinking_delimiters(text: str) -> str:
    """Fjern løse thinking-delimiter-tokens hvis et thinking-felt surfaces som svar.
    Nogle modeller lækker rå tags (<think>...</think>, ◁think▷, [THINK]) ind i
    thinking-feltet. Vi rydder dem så brugeren ikke ser stilladset, men bevarer
    selve teksten."""
    import re
    if not text:
        return ""
    cleaned = re.sub(
        r"</?\s*think(?:ing)?\s*>|◁/?\s*think▷|\[/?\s*think(?:ing)?\s*\]",
        "", text, flags=re.IGNORECASE,
    )
    return cleaned.strip()
