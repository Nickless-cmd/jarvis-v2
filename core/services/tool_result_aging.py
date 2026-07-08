"""Provider-agnostic tool-result aging for the visible agentic loop.

Keeps the ``keep_full`` most-recent tool exchanges full; ages older ones by
clearing (default, deterministic) or LLM-compressing (deep+large runs) each
tool result's content. Operates on the shared ``_followup_exchanges`` list so
every provider lane benefits (only the Ollama adapter had crude per-adapter
bounding before). Gated to strong lanes past a round threshold — weak lanes are
capped at ~4-8 rounds so aging never amortizes there.

Cache: the caller applies the returned list forward-carried at end-of-round
(outside the retry fence), so each aged result serializes byte-identically on
later rounds. Default mode is shadow (observe would-be savings, mutate nothing).
Never raises into the hot loop.
"""
from __future__ import annotations

import os
from typing import Callable

from core.services.visible_followup_events import ToolExchange, ToolResult

_AGING_MIN_ROUND = 6
_AGING_COMPRESS_ROUND = 12
_AGING_COMPRESS_MIN_CHARS = 2000
_CLEAR_PREFIX = "[tool-resultat ryddet"

_MODE_ENV = "JARVIS_TOOL_RESULT_AGING_MODE"
_VALID_MODES = ("off", "shadow", "active")


def tool_result_aging_mode() -> str:
    """Current aging mode: 'off' | 'shadow' | 'active'. Default 'shadow'.

    Env ``JARVIS_TOOL_RESULT_AGING_MODE`` wins over runtime-config. Self-safe."""
    env = os.environ.get(_MODE_ENV)
    if env is not None:
        v = env.strip().lower()
        if v in _VALID_MODES:
            return v
    try:
        from core.runtime.settings import load_settings
        v = str(load_settings().extra.get("tool_result_aging_mode", "shadow")).strip().lower()
        return v if v in _VALID_MODES else "shadow"
    except Exception:
        return "shadow"


def _clear_placeholder(n: int) -> str:
    return f"[tool-resultat ryddet — {n} tegn. Kald værktøjet igen hvis du har brug for det.]"


def _is_already_aged(content: str) -> bool:
    return content.startswith(_CLEAR_PREFIX)


def age_tool_results(
    exchanges: list[ToolExchange],
    *,
    keep_full: int = 5,
    mode: str,
    strength: str,
    round_index: int,
    compress_fn: Callable[[str], str] | None = None,
) -> tuple[list[ToolExchange], dict]:
    """Age tool-result content on exchanges older than the ``keep_full`` most recent.

    Returns ``(exchanges_out, metrics)``. In shadow mode ``exchanges_out`` IS the
    input list (unchanged) but ``metrics`` carry ``would_free_tokens``. In active
    mode a new list is returned. Never raises."""
    metrics: dict = {"changed": False, "mode": mode, "aged_exchanges": 0,
                     "cleared": 0, "compressed": 0, "would_free_chars": 0,
                     "would_free_tokens": 0}
    try:
        if mode == "off":
            return exchanges, metrics
        if strength != "strong" or round_index < _AGING_MIN_ROUND:
            return exchanges, metrics
        if len(exchanges) <= keep_full:
            return exchanges, metrics

        cut = len(exchanges) - keep_full
        old = exchanges[:cut]
        recent = exchanges[cut:]
        deep = round_index >= _AGING_COMPRESS_ROUND

        new_old: list[ToolExchange] = []
        freed = aged_ex = cleared = compressed = 0
        for ex in old:
            new_results: list[ToolResult] = []
            touched = False
            for tr in ex.results:
                content = str(tr.content or "")
                if not content or _is_already_aged(content):
                    new_results.append(tr)
                    continue
                do_compress = (deep and len(content) >= _AGING_COMPRESS_MIN_CHARS
                               and compress_fn is not None)
                replacement = ""
                if do_compress:
                    try:
                        replacement = str(compress_fn(content) or "").strip()
                    except Exception:
                        replacement = ""
                    if replacement:
                        compressed += 1
                    else:
                        replacement = _clear_placeholder(len(content))
                        cleared += 1
                else:
                    replacement = _clear_placeholder(len(content))
                    cleared += 1
                freed += max(0, len(content) - len(replacement))
                touched = True
                new_results.append(ToolResult(
                    tool_call_id=tr.tool_call_id,
                    tool_name=tr.tool_name,
                    content=replacement,
                ))
            if touched:
                aged_ex += 1
                new_old.append(ToolExchange(
                    text=ex.text, tool_calls=list(ex.tool_calls),
                    results=new_results, reasoning_content=ex.reasoning_content,
                ))
            else:
                new_old.append(ex)

        metrics.update({"aged_exchanges": aged_ex, "cleared": cleared,
                        "compressed": compressed, "would_free_chars": freed,
                        "would_free_tokens": freed // 4})
        if aged_ex == 0:
            return exchanges, metrics
        if mode == "shadow":
            return exchanges, metrics
        metrics["changed"] = True
        return new_old + recent, metrics
    except Exception:
        return exchanges, {"changed": False, "mode": mode, "error": True}
