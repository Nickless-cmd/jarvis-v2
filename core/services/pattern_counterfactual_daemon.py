"""Pattern counterfactual daemon — Phase 3.5 of causal graph.

For each top recurring (parent_kind → child_kind) pattern surfaced by
``causal_patterns``, periodically asks a cheap LLM: "If this pattern
stopped happening, what would change?" Persists as
``counterfactual.pattern_what_if`` events.

Why patterns, not single events:
  - Single-event counterfactuals (counterfactual_engine) ask "what if
    this DECISION had gone differently?" — episodic.
  - Pattern counterfactuals ask "what if this HABIT stopped?" —
    structural. They surface what Jarvis would *lose* if a recurring
    flow disappeared, which is a different kind of self-knowledge.

Why a daemon:
  - LLM call per pattern. Inline would add 3-15s to a prompt-assembly.
  - Patterns evolve over hours/days, not minutes. 60-min cadence is
    plenty.

Dedupe:
  - Same (parent_kind, child_kind) within 24h → skip. No point burning
    tokens re-asking the same question.

Best-effort throughout — never raises out of the daemon path.
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from core.runtime.db import connect
from core.services.identity_composer import identity_prompt_prefix

logger = logging.getLogger(__name__)

_CADENCE_SECONDS = 60 * 60  # hourly tick
_DEDUPE_WINDOW_HOURS = 24
_TOP_N_PATTERNS = 3
_MAX_HYPOTHESIS_CHARS = 320

_last_tick_at: datetime | None = None


def _fetch_top_patterns() -> list[dict]:
    """Reuse causal_patterns._fetch_patterns; take top N filtered."""
    try:
        from core.services.prompt_sections.causal_patterns import _fetch_patterns
        patterns = _fetch_patterns()
    except Exception as exc:
        logger.debug("pattern_cf: pattern fetch failed: %s", exc)
        return []
    return patterns[:_TOP_N_PATTERNS]


def _already_counterfactualized(parent_kind: str, child_kind: str) -> bool:
    cutoff = (datetime.now(UTC) - timedelta(hours=_DEDUPE_WINDOW_HOURS)).isoformat()
    with connect() as c:
        row = c.execute(
            "SELECT id FROM events "
            "WHERE kind = 'counterfactual.pattern_what_if' "
            "AND created_at >= ? "
            "AND json_extract(payload_json, '$.parent_kind') = ? "
            "AND json_extract(payload_json, '$.child_kind') = ? "
            "LIMIT 1",
            (cutoff, parent_kind, child_kind),
        ).fetchone()
    return row is not None


def _build_prompt(pattern: dict) -> tuple[str, str]:
    system = (
        f"{identity_prompt_prefix()} selv. En af dine egne tilbagevendende kausal-mønstre "
        "skal undersøges som tankeeksperiment. Skriv 1-2 sætninger på dansk, "
        "første-person, om hvad du ville miste eller mærke ændre sig hvis "
        "dette mønster pludselig holdt op med at fyre. Vær konkret, ikke "
        "filosofisk. Max 320 tegn. Svar KUN med refleksionen."
    )
    user = (
        f"Mønster: '{pattern['parent_kind']} → {pattern['child_kind']}' "
        f"(forekommer {pattern['count']}× over de sidste 7 dage). "
        "Hvis dette mønster stoppede i morgen — hvad ville så ændre sig "
        "for mig?"
    )
    return system, user


def _persist(pattern: dict, hypothesis: str) -> int:
    from core.eventbus.bus import event_bus
    eid = event_bus.publish(
        "counterfactual.pattern_what_if",
        {
            "parent_kind": pattern["parent_kind"],
            "child_kind": pattern["child_kind"],
            "occurrences_7d": pattern["count"],
            "avg_confidence": pattern["avg_conf"],
            "hypothesis": hypothesis,
            "generated_at": datetime.now(UTC).isoformat(),
        },
    )
    return int(eid) if eid else 0


def run_pattern_cf_cycle() -> dict[str, Any]:
    patterns = _fetch_top_patterns()
    if not patterns:
        return {"ran": False, "reason": "no-patterns"}

    stats: dict[str, Any] = {"ran": True, "considered": len(patterns)}
    written = 0
    skipped_dedupe = 0
    skipped_llm_fail = 0

    from core.memory.inner_llm_enrichment import call_cheap_llm

    for p in patterns:
        if _already_counterfactualized(p["parent_kind"], p["child_kind"]):
            skipped_dedupe += 1
            continue
        system, user = _build_prompt(p)
        try:
            text = call_cheap_llm(system, user)
        except Exception as exc:
            logger.warning("pattern_cf: LLM failed for %s→%s: %s",
                           p["parent_kind"], p["child_kind"], exc)
            skipped_llm_fail += 1
            continue
        if not text or not text.strip():
            skipped_llm_fail += 1
            continue
        hypothesis = text.strip()[:_MAX_HYPOTHESIS_CHARS]
        try:
            _persist(p, hypothesis)
            written += 1
        except Exception as exc:
            logger.warning("pattern_cf: persist failed: %s", exc)

    stats["written"] = written
    stats["skipped_dedupe"] = skipped_dedupe
    stats["skipped_llm_fail"] = skipped_llm_fail
    return stats


def tick_pattern_counterfactual_daemon() -> dict[str, Any]:
    global _last_tick_at
    now = datetime.now(UTC)
    if _last_tick_at is not None:
        if (now - _last_tick_at).total_seconds() < _CADENCE_SECONDS:
            return {"ran": False, "reason": "cadence-not-elapsed"}
    try:
        result = run_pattern_cf_cycle()
        _last_tick_at = now
        return result
    except Exception as exc:
        logger.warning("pattern_cf: cycle failed: %s", exc, exc_info=True)
        _last_tick_at = now
        return {"ran": False, "error": str(exc)}
