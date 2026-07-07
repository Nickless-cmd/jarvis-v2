"""Central-observe helpers + thinking-delimiter cleanup for the visible lane.

Split out of ``core.services.visible_model`` (boy-scout, 2026-07-07). All
helpers are self-safe: observability must never disturb the stream/error path.
Re-exported verbatim from ``core.services.visible_model``.
"""

from __future__ import annotations


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
