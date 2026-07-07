"""Cognitive-frame cache + attention-budget selection for prompts.

Udskilt fra core/services/prompt_contract.py (Boy Scout-split, ren
kode-flytning, 0 logik-ændring). Re-importeret i prompt_contract under de
oprindelige navne, så orchestratoren + eksterne call-sites
(invalidate_cognitive_frame_cache, get_last_attention_traces) + tests'
monkeypatch/direkte-mutation af prompt_contract.<navn> fortsat virker.

Modulet ejer den delte mutable state (_frame_cache*, _last_attention_traces).
Fordi navnene re-importeres i prompt_contract peger begge moduler på SAMME
objekter — dict-mutation (tests' pc._last_attention_traces[p]=..) rammer stadig
den dict get_last_attention_traces læser. Kun ren flytning.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.services.attention_budget import AttentionTrace


_FRAME_CACHE_TTL = 180.0  # 3 min — matches rule_conclusions
_frame_cache: str | None = None
_frame_cache_at: float = 0.0
_frame_cache_lock = None  # threading.Lock, lazy init


def invalidate_cognitive_frame_cache() -> None:
    """Force next call to rebuild. For tests + heartbeat-driven refresh."""
    global _frame_cache, _frame_cache_at
    _frame_cache = None
    _frame_cache_at = 0.0


def _cognitive_frame_section() -> str | None:
    """Build a compact cognitive frame section for prompt inclusion.

    Cached for _FRAME_CACHE_TTL (180s). build_cognitive_frame() runs 30+
    sequential _safe_*() DB queries which contributes ~3-6s to assembly.
    Frame state changes slowly (mode, salience, affordances) — 3-min stale
    is acceptable in visible chat.

    Perf-fix 2026-05-12: identified via per-section instrumentation.
    """
    global _frame_cache, _frame_cache_at, _frame_cache_lock
    import time as _t_mod
    if _frame_cache_lock is None:
        import threading
        _frame_cache_lock = threading.Lock()

    now = _t_mod.monotonic()
    if _frame_cache is not None and (now - _frame_cache_at) < _FRAME_CACHE_TTL:
        return _frame_cache

    with _frame_cache_lock:
        now = _t_mod.monotonic()
        if _frame_cache is not None and (now - _frame_cache_at) < _FRAME_CACHE_TTL:
            return _frame_cache
        try:
            from core.services.runtime_cognitive_conductor import (
                build_cognitive_frame_prompt_section,
            )
            _frame_cache = build_cognitive_frame_prompt_section()
        except Exception:
            _frame_cache = None
        _frame_cache_at = now
        return _frame_cache


def _micro_cognitive_frame_section() -> str | None:
    """Build a micro cognitive frame for compact visible prompts (~150 chars)."""
    try:
        from core.services.attention_budget import (
            build_micro_cognitive_frame,
        )

        return build_micro_cognitive_frame()
    except Exception:
        return None


# Module-level store for latest attention traces (MC observability)
_last_attention_traces: dict[str, object] = {}


def get_last_attention_traces() -> dict[str, dict[str, object]]:
    """Return the last attention trace summaries for each prompt path.

    Used by Mission Control to expose the actual runtime selection truth.
    """
    result: dict[str, dict[str, object]] = {}
    for profile, trace in _last_attention_traces.items():
        try:
            result[profile] = trace.summary()
        except Exception:
            result[profile] = {"profile": profile, "error": "trace-unavailable"}
    return result


def _run_budget_selection(
    *,
    profile: str,
    sections: dict[str, str | None],
) -> tuple[dict[str, str | None], "AttentionTrace"]:
    """Run budget-controlled section selection.

    Returns (selected_sections, trace).
    Falls back to passthrough if budget module is unavailable.
    """
    try:
        from core.services.attention_budget import (
            get_attention_budget,
            select_sections_under_budget,
        )

        budget = get_attention_budget(profile)
        selected, trace = select_sections_under_budget(budget=budget, sections=sections)
        trace.authority_mode = "budgeted"
        _last_attention_traces[profile] = trace
        return selected, trace
    except Exception as exc:
        # Fallback: include everything as-is, no budget enforcement
        from core.services.attention_budget import (
            AttentionTrace,
            SectionResult,
        )

        trace = AttentionTrace(
            profile=profile,
            total_char_target=0,
            authority_mode="fallback_passthrough",
            fallback_reason=f"{type(exc).__name__}: {exc}",
        )
        for name, content in sections.items():
            trace.sections.append(
                SectionResult(
                    name=name,
                    included=content is not None and bool(content),
                    chars_used=len(content) if content else 0,
                    omission_reason="budget-fallback" if not content else "",
                )
            )
            trace.total_chars_used += len(content) if content else 0
        _last_attention_traces[profile] = trace
        return sections, trace
