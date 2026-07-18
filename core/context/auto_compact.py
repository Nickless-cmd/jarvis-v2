"""Auto-compact: triggers smart session compaction when approaching context limit.

Called once per visible run, before the LLM call. Compacts chat history if the
session exceeds auto_compact_threshold_pct of context_run_compact_threshold_tokens.
Uses the smart prompt (preserves decisions/facts, discards routine).
"""
from __future__ import annotations

import logging

from core.services.model_context import model_context_window

logger = logging.getLogger(__name__)

_AUTO_COMPACT_PCT = 0.80          # flat fallback: 80% of configured threshold
_AUTO_COMPACT_WINDOW_PCT = 0.70   # model-window-aware: compact at 70% of the model's OWN window


def _compaction_threshold(*, provider: str, model: str, flat_fallback: int) -> int:
    """Model-window-aware compaction threshold: window × 0.70. So a 1M-window lane compacts at ~700k
    and a 128k lane at ~90k — each proportional to its own window, not one flat number. Falls back to
    flat_fallback when the window is unknown/zero. Self-safe."""
    try:
        window = int(model_context_window(provider, model) or 0)
        if window > 0:
            return int(window * _AUTO_COMPACT_WINDOW_PCT)
    except Exception:
        pass
    return int(flat_fallback)


def maybe_auto_compact_session(session_id: str, *, provider: str = "", model: str = "") -> bool:
    """Check session token count and compact if above threshold. Returns True if compacted.
    Threshold is model-window-aware when provider/model are given, else the flat fallback.

    SUPERSEDED (2026-07-18, live-compaction spec): the SINGLE source of truth for visible-
    lane compaction is now the BACKGROUND attention-budget path
    (transcript_sections._maybe_auto_compact_session → _run_session_compaction), which:
      - triggers on an absolute 35k attention budget (not window×0.70 ≈ 700k that never fired),
      - runs off the hot-path (non-blocking — Bjørn's 2026-06-23 principle),
      - sets `_compact_inflight` so the desk liveness indicator lights up (desk polls that,
        it does NOT consume this function's SSE event),
      - and produces the structured, round-atomic 2-stage summary.
    This synchronous pre-run path is therefore disabled to avoid a second, competing,
    blocking compactor writing its own marker with a different prompt. The body below is
    kept (dormant) for reference / possible revival as a synchronous emergency backstop.
    """
    return False
    try:  # noqa: unreachable — dormant legacy body, see docstring
        from core.runtime.settings import load_settings
        from core.context.token_estimate import estimate_tokens
        from core.services.chat_sessions import recent_chat_session_messages

        settings = load_settings()
        flat = int(settings.context_run_compact_threshold_tokens * _AUTO_COMPACT_PCT)
        threshold = _compaction_threshold(provider=provider, model=model, flat_fallback=flat)

        messages = recent_chat_session_messages(session_id, limit=300)
        if not messages:
            return False

        total_chars = sum(len(m.get("content") or "") for m in messages)
        est_tokens = estimate_tokens("x" * total_chars)

        if est_tokens < threshold:
            return False

        logger.info(
            "auto_compact: session %s at ~%d tokens (threshold %d) — compacting",
            session_id, est_tokens, threshold,
        )

        from core.context.session_compact import compact_session_history
        from core.context.compact_llm import call_compact_llm
        from core.context.compact_ground_truth import (
            collect_compact_ground_truth,
            format_ground_truth_block,
            get_current_git_sha,
        )

        from core.services.identity_composer import identity_prompt_prefix as _ipp

        # Lag A: collect ground truth and inject into prompt
        gt = collect_compact_ground_truth(session_id)
        gt_block = format_ground_truth_block(gt)
        current_sha = get_current_git_sha()

        _SMART_PROMPT = (
            f"{_ipp()}' kontekst-kompressor. Komprimér denne dialog.\n\n"
            f"{gt_block}\n\n"
            "BEVAR: eksplicitte beslutninger, tekniske fakta, fil-stier, åbne opgaver, "
            "brugerens præferencer og korrektioner.\n"
            "KASSÉR: statusbeskeder, trivielle bekræftelser, gentagne forsøg (bevar kun resultatet).\n\n"
            "FORMAT: ## Beslutninger / ## Fakta / ## Åbne punkter / ## Kontekst (max 150 ord)\n\n"
            "Samtale:\n"
        )

        result = compact_session_history(
            session_id,
            keep_recent=settings.context_keep_recent,
            summarise_fn=lambda msgs: call_compact_llm(
                _SMART_PROMPT
                + "\n".join(f"{m['role']}: {m.get('content', '')[:600]}" for m in msgs),
                max_tokens=600,
            ),
            git_sha=current_sha,
        )

        if result:
            logger.info(
                "auto_compact: freed %d tokens for session %s",
                result.freed_tokens, session_id,
            )
            return True
        return False

    except Exception as exc:
        logger.warning("auto_compact: error during auto-compact for %s: %s", session_id, exc)
        return False
