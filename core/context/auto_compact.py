"""Auto-compact: triggers smart session compaction when approaching context limit.

Called once per visible run, before the LLM call. Compacts chat history if the
session exceeds auto_compact_threshold_pct of context_run_compact_threshold_tokens.
Uses the smart prompt (preserves decisions/facts, discards routine).
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_AUTO_COMPACT_PCT = 0.80  # trigger at 80% of configured threshold


def maybe_auto_compact_session(session_id: str) -> bool:
    """Check session token count and compact if above threshold. Returns True if compacted."""
    try:
        from core.runtime.settings import load_settings
        from core.context.token_estimate import estimate_tokens
        from core.services.chat_sessions import recent_chat_session_messages

        settings = load_settings()
        threshold = int(settings.context_run_compact_threshold_tokens * _AUTO_COMPACT_PCT)

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

        _SMART_PROMPT = (
            "Du er Jarvis' kontekst-kompressor. Komprimér denne dialog.\n\n"
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
