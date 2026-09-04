"""Post-run learning signals for a visible run (extracted from visible_runs.py,
Boy Scout 2026-09-04 while adding the lessons hook — memory repair, R4).

After a native-tool visible run completes, three things are recorded:

1. an experience episode (Lag 1 of the Runtime Decision Policy, 2026-05-09)
   — append-only substrate for embedding retrieval;
2. a *lesson* when a tool failed (new 2026-09-04): signature = tool name +
   error head, proposed until it happens twice, then active in [HUKOMMELSE];
3. the theory-of-mind update.

Every step is fail-soft; a failure in one never blocks the others.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def tool_names(collected_native_tool_calls: Any) -> list[str]:
    """Names of the native tool calls in order (objects or OpenAI-style dicts)."""
    out: list[str] = []
    for tc in collected_native_tool_calls or []:
        name = ""
        try:
            name = (
                getattr(tc, "name", None)
                or (tc.get("name") if isinstance(tc, dict) else "")
                or (tc.get("function", {}).get("name", "") if isinstance(tc, dict) else "")
            )
        except Exception:
            name = ""
        if name:
            out.append(str(name))
    return out


def record_visible_run_learning_signals(
    *,
    run_ref: Any,
    collected_native_tool_calls: Any,
    outcome_status: str,
    outcome_error: str | None,
    followup_text: str,
    output_tokens: int,
) -> None:
    seq = tool_names(collected_native_tool_calls)
    error_text = str(outcome_error or "")

    try:
        from core.services.experience_episodes import record_episode

        record_episode(
            session_id=run_ref.session_id,
            turn_id=run_ref.run_id,
            intent=str(run_ref.user_message or "")[:240],
            tool_sequence=seq,
            outcome_signals={
                "status": str(outcome_status or ""),
                "tool_errors": int(1 if error_text else 0),
                "tool_count": len(seq),
                "output_tokens": int(output_tokens or 0),
                "assistant_chars": len(followup_text or ""),
            },
            user_corrected=False,  # enriched later by experience_correction_listener
            session_phase="mid-task",
        )
    except Exception:
        logger.debug("learning_signals: record_episode failed", exc_info=True)

    if error_text:
        try:
            from core.services.lessons import record_tool_error

            record_tool_error(
                tool_name=(seq[-1] if seq else "ukendt"),
                error_text=error_text,
                context=str(run_ref.user_message or "")[:80],
            )
        except Exception:
            logger.debug("learning_signals: record_tool_error failed", exc_info=True)

    # Redesign 4/9: en vist "Siden sidst"-kandidat tæller som leveret når svaret nævner den.
    try:
        from core.services.proactive_candidates import mark_mentioned_if_overlap
        mark_mentioned_if_overlap(session_id=str(run_ref.session_id or ""),
                                  answer_text=followup_text or "", run_id=str(run_ref.run_id or ""))
    except Exception:
        logger.debug("learning_signals: mark_mentioned failed", exc_info=True)

    try:
        from core.services.theory_of_mind_engine import record_theory_of_mind_update

        record_theory_of_mind_update(
            user_message=run_ref.user_message,
            assistant_text=followup_text,
            outcome_status=outcome_status,
            source_run_id=run_ref.run_id,
        )
    except Exception:
        logger.debug("learning_signals: theory_of_mind failed", exc_info=True)
